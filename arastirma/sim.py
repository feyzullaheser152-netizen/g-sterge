"""VSP v4 sinyal ve pozisyon yonetimi simulasyonu (Pine mantigiyla ayni sira)."""
import numpy as np

DEFAULT = dict(
    emaF=9, emaS=21, htfLen=50, rangeLen=240, freshBars=30, stopLook=5, atrLen=14, rsiLen=14, adxLen=14,
    rvolLen=20, erLen=20, bvcLen=100, dLen=3, vpinLen=50, vrQ=15, vrWin=240,
    # kurallar
    useTrend=True, useSweep=True, useMss=True, entry="limit", fillBars=3,
    makerFee=0.02, takerFee=0.05, slip=0.01, maxCostR=0.20, minScore=60, cooldown=5,
    tp1R=1.0, tp2R=2.0, partQ=0.5, timeStop=20, stopBuf=0.2, minStopAtr=0.6, maxStopAtr=3.0,
    spikeAtr=4.0, erMin=0.30, adxMin=20, rvolMin=1.3, dMin=0.10, vpinMax=90, chaseZ=2.0,
    rsiMaxL=72, rsiMinS=28, swMinAtr=0.1, swMaxAtr=1.5, mssBars=5,
    usePD=True, useAsia=True, useRange=True, fundBlock=3, fundHours=8,
    sweepHtfAlign=False, sweepEntry="close", trendEntry="close", hours=None,
)


def crossover(a, b):
    pa, pb = np.roll(a, 1), np.roll(b, 1)
    out = (a > b) & (pa <= pb)
    out[0] = False
    return out


def precompute(f, P):
    o, h, l, c = f["o"], f["h"], f["l"], f["c"]
    atr = f["atr"]
    nz = lambda x: np.nan_to_num(x, nan=0.0)
    g = {}
    up = (f["emaF"] > f["emaS"]) & (c > f["vwap"])
    dn = (f["emaF"] < f["emaS"]) & (c < f["vwap"])
    reg = f["er"] >= P["erMin"]
    htfUp = f["htfC"] > f["htfE"]
    htfDn = f["htfC"] < f["htfE"]
    vr = f["vr"]
    vrOk = ~np.isnan(vr)
    longTrig = crossover(c, f["emaF"]) | ((l <= f["emaF"]) & (c > f["emaF"]) & (c > o))
    shortTrig = crossover(-c, -f["emaF"]) | ((h >= f["emaF"]) & (c < f["emaF"]) & (c < o))
    atrp = np.where(np.isnan(f["atr_prev"]), atr, f["atr_prev"])
    spikeT = f["rng"] > P["spikeAtr"] * atrp
    spikeS = f["rng"] > P["spikeAtr"] * 2 * atrp
    liquid = (f["hour"] >= 7) & (f["hour"] < 21)
    if P["hours"] is not None:
        allowed = np.isin(f["hour"], P["hours"])
    else:
        allowed = np.ones(len(c), bool)

    g["tValidL"] = P["useTrend"] & up & longTrig & htfUp & reg & (~vrOk | (vr > 1)) & (f["z15"] < P["chaseZ"]) & (f["rsi"] < P["rsiMaxL"]) & (c < f["vwapU"]) & ~spikeT
    g["tValidS"] = P["useTrend"] & dn & shortTrig & htfDn & reg & (~vrOk | (vr > 1)) & (f["z15"] > -P["chaseZ"]) & (f["rsi"] > P["rsiMinS"]) & (c > f["vwapL"]) & ~spikeT
    oiNeutral = 5
    g["tScoreL"] = np.clip(50 + np.where((f["adx"] >= P["adxMin"]) & (f["diP"] > f["diM"]), 10, 0) + np.where(f["dRatio"] >= P["dMin"], 15, 0) + oiNeutral + np.where(f["rvol"] >= P["rvolMin"], 10, 0) + np.where(liquid, 5, 0), 0, 100)
    g["tScoreS"] = np.clip(50 + np.where((f["adx"] >= P["adxMin"]) & (f["diM"] > f["diP"]), 10, 0) + np.where(f["dRatio"] <= -P["dMin"], 15, 0) + oiNeutral + np.where(f["rvol"] >= P["rvolMin"], 10, 0) + np.where(liquid, 5, 0), 0, 100)

    def swept_below(lvl):
        d = lvl - l
        return (~np.isnan(lvl)) & (l < lvl) & (c > lvl) & (f["lowF"] > lvl) & (d >= P["swMinAtr"] * atr) & (d <= P["swMaxAtr"] * atr)

    def swept_above(lvl):
        d = h - lvl
        return (~np.isnan(lvl)) & (h > lvl) & (c < lvl) & (f["highF"] < lvl) & (d >= P["swMinAtr"] * atr) & (d <= P["swMaxAtr"] * atr)

    lvlL = np.zeros(len(c)); lvlS = np.zeros(len(c))
    levL = np.full(len(c), np.nan); levS = np.full(len(c), np.nan)
    for use, name, pts in [(P["useRange"], "rng", 15), (P["useAsia"], "asia", 20), (P["usePD"], "pd", 25)]:
        if not use:
            continue
        lo = {"rng": f["rngLo"], "asia": f["asiaLo"], "pd": f["pdl"]}[name]
        hi = {"rng": f["rngHi"], "asia": f["asiaHi"], "pd": f["pdh"]}[name]
        bl, ba = swept_below(lo), swept_above(hi)
        lvlL = np.where(bl, pts, lvlL); levL = np.where(bl, lo, levL)
        lvlS = np.where(ba, pts, lvlS); levS = np.where(ba, hi, levS)
    g["levL"], g["levS"] = levL, levS
    dprev = np.roll(f["dRatio"], 1)
    g["sScoreL"] = np.clip(np.round((lvlL + np.where(f["rvol"] >= P["rvolMin"], 20, 0) + np.where(f["clv"] >= 0.5, 15, 0) + 7 + 10 + np.where(c < f["vwap"], 15, 0) + np.where(vrOk, np.where(vr < 1, 10, 0), 5) + np.where(dprev <= -2 * P["dMin"], 10, 0)) * 100 / 130), 0, 100)
    g["sScoreS"] = np.clip(np.round((lvlS + np.where(f["rvol"] >= P["rvolMin"], 20, 0) + np.where(f["clv"] <= -0.5, 15, 0) + 7 + 10 + np.where(c > f["vwap"], 15, 0) + np.where(vrOk, np.where(vr < 1, 10, 0), 5) + np.where(dprev >= 2 * P["dMin"], 10, 0)) * 100 / 130), 0, 100)
    toxic = f["vpinPr"] >= P["vpinMax"]
    sL = P["useSweep"] & (lvlL > 0) & (f["clv"] >= 0.2) & ~spikeS & ~toxic & ~(dn & reg & htfDn)
    sS = P["useSweep"] & (lvlS > 0) & (f["clv"] <= -0.2) & ~spikeS & ~toxic & ~(up & reg & htfUp)
    if P["sweepHtfAlign"]:
        sL &= htfUp
        sS &= htfDn
    g["sValidL"], g["sValidS"] = sL, sS

    qh = np.where(f["min_close"] % 15 == 0, 1.5, 1.0)
    takerX = P["takerFee"] + P["slip"] * qh
    entryX = P["makerFee"] if P["entry"] == "limit" else takerX
    g["takerX"] = takerX
    g["entryX"] = entryX * np.ones(len(c))
    g["costPx"] = c * (g["entryX"] + takerX) / 100
    mins = (f["hour"] % P["fundHours"]) * 60 + f["minute"]
    per = P["fundHours"] * 60
    g["nearFund"] = (P["fundBlock"] > 0) & ((mins < P["fundBlock"]) | (mins >= per - P["fundBlock"]))
    g["gateBase"] = (~g["nearFund"]) & (nz(f["volMa"]) > 0) & allowed
    g["htfUp"], g["htfDn"], g["liquid"] = htfUp, htfDn, liquid
    return g


def simulate(f, P, g=None):
    if g is None:
        g = precompute(f, P)
    o, h, l, c, atr = f["o"], f["h"], f["l"], f["c"], f["atr"]
    n = len(c)
    clampD = lambda d, a: min(max(d, a * P["minStopAtr"]), a * P["maxStopAtr"])
    trades = []
    dir_ = 0; entry = sl = tp1 = tp2 = risk = 0.0; gross = fee = 0.0; remQ = 1.0; tp1Hit = False
    entryBar = -1; lastSig = -10**9; pos = {}
    pDir = 0; pPx = pDist = 0.0; pBar = -1; pInfo = {}
    nMiss = 0
    armL = armS = False; armLo = armHi = armSLo = armSHi = 0.0; armBar = armSBar = -1; armSc = armSSc = 0; armInfoL = armInfoS = {}
    tVL, tVS, tSL, tSS = g["tValidL"], g["tValidS"], g["tScoreL"], g["tScoreS"]
    sVL, sVS, sSL, sSS = g["sValidL"], g["sValidS"], g["sScoreL"], g["sScoreS"]
    costPx, takerX, gateBase = g["costPx"], g["takerX"], g["gateBase"]
    mk = P["makerFee"]
    lowN, highN = f["lowN"], f["highN"]
    for i in range(300, n):
        closedR = None
        a = atr[i]
        tx = takerX[i]
        # 1) yonetim
        if dir_ != 0 and i > entryBar:
            hitSL = l[i] <= sl if dir_ == 1 else h[i] >= sl
            hitT1 = h[i] >= tp1 if dir_ == 1 else l[i] <= tp1
            hitT2 = h[i] >= tp2 if dir_ == 1 else l[i] <= tp2
            held = i - entryBar
            reason = None
            if hitSL:
                gross += remQ * (sl - entry) * dir_; fee += remQ * sl * tx / 100
                reason = "BE" if tp1Hit else "SL"
            elif hitT2:
                if not tp1Hit:
                    gross += P["partQ"] * (tp1 - entry) * dir_; fee += P["partQ"] * tp1 * mk / 100
                    remQ = 1 - P["partQ"]
                gross += remQ * (tp2 - entry) * dir_; fee += remQ * tp2 * mk / 100
                reason = "TP2"
            else:
                if hitT1 and not tp1Hit:
                    tp1Hit = True
                    gross += P["partQ"] * (tp1 - entry) * dir_; fee += P["partQ"] * tp1 * mk / 100
                    remQ = 1 - P["partQ"]; sl = entry
                if tp1Hit and remQ <= 0:
                    reason = "TP1"
                elif (not tp1Hit and held >= P["timeStop"]) or held >= P["timeStop"] * 3:
                    gross += remQ * (c[i] - entry) * dir_; fee += remQ * c[i] * tx / 100
                    reason = "TIME"
            if reason:
                closedR = reason; dir_ = 0
        # 2) limit dolumu
        if pDir != 0 and dir_ == 0 and closedR is None and i > pBar:
            if i - pBar > P["fillBars"]:
                nMiss += 1; pDir = 0
            elif (l[i] < pPx) if pDir == 1 else (h[i] > pPx):
                dir_ = pDir; entry = pPx; risk = pDist; sl = pPx - pDir * pDist
                tp1 = pPx + pDir * pDist * P["tp1R"]; tp2 = pPx + pDir * pDist * P["tp2R"]
                gross = 0.0; fee = pPx * mk / 100; remQ = 1.0; tp1Hit = False; entryBar = i; pos = dict(pInfo, entry_i=i)
                pDir = 0
                if (l[i] <= sl) if dir_ == 1 else (h[i] >= sl):
                    gross += (sl - entry) * dir_; fee += sl * tx / 100
                    closedR = "SL_FILLBAR"; dir_ = 0
        # sweep MSS
        mssL = armL and i > armBar and c[i] > armHi
        mssS = armS and i > armSBar and c[i] < armSLo
        if P["useMss"]:
            dSwL = clampD(c[i] - (armLo - a * P["stopBuf"]), a)
            dSwS = clampD((armSHi + a * P["stopBuf"]) - c[i], a)
            fireL, fireS, scL, scS = mssL, mssS, armSc, armSSc
        else:
            dSwL = clampD(c[i] - (l[i] - a * P["stopBuf"]), a)
            dSwS = clampD((h[i] + a * P["stopBuf"]) - c[i], a)
            fireL = sVL[i] and sSL[i] >= P["minScore"]; fireS = sVS[i] and sSS[i] >= P["minScore"]
            scL, scS = sSL[i], sSS[i]
        dTL = clampD(c[i] - (lowN[i] - a * P["stopBuf"]), a)
        dTS = clampD((highN[i] + a * P["stopBuf"]) - c[i], a)
        cp = costPx[i]
        okTL = tVL[i] and tSL[i] >= P["minScore"] and cp / dTL <= P["maxCostR"]
        okSL = fireL and cp / dSwL <= P["maxCostR"]
        okTS = tVS[i] and tSS[i] >= P["minScore"] and cp / dTS <= P["maxCostR"]
        okSS = fireS and cp / dSwS <= P["maxCostR"]
        lt = 1 if okTL and (not okSL or tSL[i] >= scL) else (2 if okSL else 0)
        st = 1 if okTS and (not okSS or tSS[i] >= scS) else (2 if okSS else 0)
        lsc = tSL[i] if lt == 1 else (scL if lt == 2 else 0)
        ssc = tSS[i] if st == 1 else (scS if st == 2 else 0)
        gate = gateBase[i] and (i - lastSig > P["cooldown"])
        longSig = gate and lt > 0 and dir_ != 1 and lsc > ssc
        shortSig = gate and st > 0 and dir_ != -1 and ssc > lsc
        # 4) ters sinyal
        if (longSig or shortSig) and dir_ != 0:
            gross += remQ * (c[i] - entry) * dir_; fee += remQ * c[i] * tx / 100
            closedR = "REV"; dir_ = 0
        if closedR is not None:
            trades.append(dict(pos, exit_i=i, reason=closedR, grossR=gross / risk, feeR=fee / risk, netR=(gross - fee) / risk))
        # 6) yeni sinyal
        if longSig or shortSig:
            d = 1 if longSig else -1
            typ = lt if longSig else st
            sc = lsc if longSig else ssc
            dist = (dTL if typ == 1 else dSwL) if longSig else (dTS if typ == 1 else dSwS)
            info = dict(sig_i=i, dir=d, type=typ, score=sc, costR=cp / dist, hour=int(f["hour"][i]))
            if typ == 2 and P["useMss"]:
                info.update(armInfoL if longSig else armInfoS)
            lastSig = i
            px = c[i]
            if typ == 2 and P["sweepEntry"] == "level" and P["entry"] == "limit":
                lv = info.get("level", np.nan)
                if not np.isnan(lv):
                    stop = c[i] - d * dist
                    px = lv; dist = abs(px - stop)
            if P["entry"] == "limit":
                pDir = d; pPx = px; pBar = i; pDist = dist; pInfo = info
            else:
                dir_ = d; entry = c[i]; risk = dist; sl = entry - d * dist
                tp1 = entry + d * dist * P["tp1R"]; tp2 = entry + d * dist * P["tp2R"]
                gross = 0.0; fee = entry * tx / 100; remQ = 1.0; tp1Hit = False; entryBar = i; pos = dict(info, entry_i=i)
        # 7) arm
        if armL and (i - armBar >= P["mssBars"] or l[i] < armLo or mssL):
            armL = False
        if armS and (i - armSBar >= P["mssBars"] or h[i] > armSHi or mssS):
            armS = False
        if P["useMss"] and sVL[i] and sSL[i] >= P["minScore"]:
            armL = True; armLo = l[i]; armHi = h[i]; armBar = i; armSc = sSL[i]
            armInfoL = dict(arm_i=i, level=g["levL"][i], htfAl=bool(g["htfUp"][i]), vr_arm=f["vr"][i], liq=bool(g["liquid"][i]))
        if P["useMss"] and sVS[i] and sSS[i] >= P["minScore"]:
            armS = True; armSLo = l[i]; armSHi = h[i]; armSBar = i; armSSc = sSS[i]
            armInfoS = dict(arm_i=i, level=g["levS"][i], htfAl=bool(g["htfDn"][i]), vr_arm=f["vr"][i], liq=bool(g["liquid"][i]))
    return trades, nMiss


def summarize(tr, label=""):
    if not tr:
        return f"{label}: işlem yok"
    r = np.array([t["netR"] for t in tr]); gr = np.array([t["grossR"] for t in tr]); fr = np.array([t["feeR"] for t in tr])
    n = len(r); m = r.mean(); sd = r.std(ddof=1) if n > 1 else 0
    tstat = m / (sd / np.sqrt(n)) if sd > 0 else 0
    pf = r[r > 0].sum() / -r[r <= 0].sum() if (r <= 0).any() else np.inf
    return f"{label}: n={n} isabet={np.mean(r>0)*100:.0f}% netR={r.sum():.1f} ort={m:+.3f} brüt={gr.mean():+.3f} maliyet={fr.mean():.3f} PF={pf:.2f} t={tstat:+.2f}"
