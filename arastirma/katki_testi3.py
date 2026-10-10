"""Katki testi, ucuncu grup ve 12 katman (1 dk; 22 Binance USDT-M paritesi; 2025 kesif / 2026 dogrulama).

Kullanici: "6 katmanin yeterli oldugundan emin misin?" -> Katmanlar 12'ye cikarildi. Komisyon sifir (BULGULAR 14b); makas dahil degil.
Yeni gostergeler arastirma/k3_*.py modullerinde (her biri bagimsiz bir ajanla Pine koduna karsi mum mum dogrulandi):
  k3_izleyen: Chandelier Exit [everget, GPL-3.0], Pivot Point SuperTrend [LonesomeTheBlue], AlphaTrend [KivancOzbilgic]
  k3_seviye : Support Resistance Dynamic v2, Breakout Finder, Trend Lines v2 [LonesomeTheBlue]
  k3_smcmum : Super OrderBlock / FVG / BoS Tools [makuchaku & eFe], CM Price Action Bars [ChrisMoody]
  k3_serit  : EMA 20/50/100/200, Madrid Moving Average Ribbon [Madrid], Volume Flow Indicator [LazyBear]
  k3_vsz    : Volume-based Support & Resistance Zones V2 [synapticex, Lij_MC]: hacim onayli fraktal seviyeleri 1 dk, 4 saat ve gun
              (kirilim VSZB_*, bolge tepkisi VSZR_*); literal donguyle birebir ve kesme testiyle repaint yok (ust zaman dilimi yalnizca tamamlanmis mumlardan).

ON KAYIT (sonuclardan once yazildi). "VSP islemleri": v6.1 sinyali (sert 15 dk hareket sonrasi geri donus), piyasa girisi, stop 2 sigma15, hedef 2R, 5 dk.
 1) Sinyal: yeni adaylar (modullerin S ciktilari) 54 ayarlik izgarada; kural 2025 R > 0, t >= 2; 2026 R > 0, t >= 3.
 2) Filtre: yeni D/U durumlari VSP islemlerinde; kural katki_testi2 ile ayni (iki yil ayni isaret, |fark| >= 1 bp, t 2/3, kapsam %20-80).
 3) Oynaklik bilgisi: R2 artisi iki yilda >= 0,005.
 4) Yon bilgisi: sonraki 15 dk farki iki yilda ayni isaret, >= 1 bp, t 2/3.
 5) Seviyeler: SRD, BOF, TLB2, PPDD, OBFVG, BOS1, VSZB_*, VSZR_* dokunus/kirilim sinyalleri 1. katmanda.
 6) Cikis: Chandelier Exit, Pivot Point SuperTrend, AlphaTrend donusu (katki_testi2.exits ile ayni; kabul: iki yilda >= +0,5 bp, 2026 t >= 3).
 7) Stop yerlesimi (VSP olaylari, bagimsiz, eslestirilmis): stop = 1 / 2 (temel) / 3 sigma15; son 10 mumun dibi/tepesi - 0,1 sigma15 (yapisal);
    Chandelier stopu; Pivot Point SuperTrend stopu. Hedef 2R, en fazla 5 dk. Olcu R (brut / stop mesafesi). Stop girisin yanlis tarafindaysa olay atlanir.
    Kabul: R farki (alternatif - temel) iki yilda >= +0,01 ve 2026 t >= 3.
 8) Giris zamanlamasi (VSP olaylari): hemen (temel), 1 ve 2 mum bekle, ilk dogru renkli mum (AL'da yesil) sonrasi, sinyal mumunun tepesi (AL) asilinca;
    onay 5 mum icinde gelmezse islem yok. Cikis girisle ayni kural. Olcu: alinan islemlerde (alternatif - temel) brut bp, eslestirilmis.
    Kabul: iki yilda >= +0,5 bp ve 2026 t >= 3 ve alinma orani >= %30.
 9) Uyum: VSP isleminin yonunde son 5 mumda (sinyal mumu dahil) uyumsuzluk (Divergence v4), SMA20 donusu, pin bar ya da mum formasyonu;
    puan = bu dort olayin kac tanesi var. Filtre kuraliyla: "puan >= 1" ve "puan >= 2" durumlari, ayrica her biri tek tek.
 10) Coin secimi: parite bazinda VSP brut ortalamasi; 2025 ve 2026 sira korelasyonu (Spearman) ve 2025'in ilk 11 paritesi ile son 11 paritesi arasindaki
    2026 farki (gun kumelenmis t). Kabul: rho >= 0,3, fark >= 1 bp, t >= 2,5.
 11) Saat ve gun: VSP islemleri UTC 4 saatlik dilimlere (6) ve haftanin gunlerine (7) gore; 2025 ve 2026 sira korelasyonu; 2025'in en iyi 2 dilimi ile en kotu 2
    diliminin 2026 farki. Kabul: rho >= 0,5, fark >= 1 bp, t >= 3.
 12) BTC baglami (yalnizca altcoin islemleri): sinyal dakikasinda BTC'de de ayni yonde sert 15 dk hareket (z15 <= -3 AL icin), BTC 15 dk getirisi isleme ters yonde
    (AL'da BTC dusmus), BTC'de de VSP sinyali. Filtre kuraliyla.
Kullanim: VSP_VERI=<klasor> python3 arastirma/katki_testi3.py
"""
import math, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
import katki_testi as K1
import katki_testi2 as K2
import k3_izleyen, k3_seviye, k3_smcmum, k3_serit, k3_vsz
from topluluk_sinyal import sma, pivot

KS, RS, HS = sinyal_v6.KS, sinyal_v6.RS, sinyal_v6.HS
MODS = [k3_izleyen, k3_seviye, k3_smcmum, k3_serit, k3_vsz]
IZGARA = os.environ.get("K3_IZGARA", "1") != "0"  # 0: 1. katman izgarasi onceki calismanin katki3_A.csv dosyasindan okunur (kurallar ayni)


def btc_baglam():
    z = np.load(os.path.join(izleme.NPZ, "BTCUSDT.npz"))
    ts, c = z["ts"], z["c"]
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    sd1 = pd.Series(r).rolling(1440).std(ddof=0).to_numpy()
    lc15 = np.r_[np.full(15, np.nan), lc[:-15]]
    z15 = np.where(sd1 > 0, (lc - lc15) / (sd1 * np.sqrt(15)), 0.0)
    E = sinyal_v6.olaylar("BTCUSDT")
    ev = np.zeros(len(ts), np.int64)
    ev[np.searchsorted(ts, E["ts"])] = E["yon"]
    return ts, np.nan_to_num(z15), np.nan_to_num(lc - lc15), ev


@njit(cache=True)
def stop_varyant(o, h, l, c, ix, y, sg, stopd):
    """stopd: olay basina stop mesafesi (log). Hedef 2R, 5 mum. Cikti brut log getiri ve R (stopd <= 0 ise nan)."""
    m = len(ix)
    n = len(c)
    br = np.full(m, np.nan)
    rr = np.full(m, np.nan)
    for q in range(m):
        i = ix[q]
        d = stopd[q]
        if i + 7 >= n or not (d > 0):
            continue
        yy = y[q]
        ent = o[i + 1]
        stop = ent * math.exp(-yy * d)
        tgt = ent * math.exp(yy * 2.0 * d)
        px = c[i + 5]
        for j in range(5):
            b = i + 1 + j
            hs = l[b] <= stop if yy > 0 else h[b] >= stop
            ht = h[b] > tgt if yy > 0 else l[b] < tgt
            if hs:
                px = min(stop, o[b]) if yy > 0 else max(stop, o[b])
                break
            if ht:
                px = tgt
                break
        g = yy * (math.log(px) - math.log(ent))
        br[q] = g
        rr[q] = g / d
    return br, rr


@njit(cache=True)
def giris_varyant(o, h, l, c, ix, y, sg, mode):
    """mode 0: hemen; 1/2: k mum bekle; 3: ilk dogru renkli mum; 4: sinyal mumunun tepesi/dibi asilinca. Cikis: stop 2 sigma, hedef 2R, 5 mum."""
    m = len(ix)
    n = len(c)
    br = np.full(m, np.nan)
    for q in range(m):
        i = ix[q]
        yy = y[q]
        if i + 15 >= n:
            continue
        e = -1
        if mode == 0:
            e = i + 1
        elif mode == 1 or mode == 2:
            e = i + 1 + mode
        else:
            for j in range(i + 1, i + 6):
                if mode == 3:
                    ok = c[j] > o[j] if yy > 0 else c[j] < o[j]
                else:
                    ok = c[j] > h[i] if yy > 0 else c[j] < l[i]
                if ok:
                    e = j + 1
                    break
        if e < 0:
            continue
        ent = o[e]
        d = 2.0 * sg[q]
        stop = ent * math.exp(-yy * d)
        tgt = ent * math.exp(yy * 2.0 * d)
        px = c[e + 4]
        for j in range(5):
            b = e + j
            hs = l[b] <= stop if yy > 0 else h[b] >= stop
            ht = h[b] > tgt if yy > 0 else l[b] < tgt
            if hs:
                px = min(stop, o[b]) if yy > 0 else max(stop, o[b])
                break
            if ht:
                px = tgt
                break
        br[q] = yy * (math.log(px) - math.log(ent))
    return br


def son_k(mask, k=5):
    """Son k mum icinde (dahil) True olan."""
    s = pd.Series(mask.astype(float)).rolling(k, min_periods=1).max().to_numpy()
    return s > 0


def parite_isle(arg):
    s, BTC = arg
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    yilb = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    gunb = (ts // 86400 - TS.GUN0).astype(np.int64)
    S, D, U, X, STOPS = {}, {}, {}, {}, {}
    for M in MODS:
        R_ = M.hesapla(z)
        S.update(R_.get("S", {}))
        D.update(R_.get("D", {}))
        U.update(R_.get("U", {}))
        X.update(R_.get("X", {}))
        STOPS.update(R_.get("STOPS", {}))
    gec = (t >= 5000) & (t < n - TS.NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
    out = {"A": {}}
    # 1) sinyal
    for ad, (al, sat) in (S.items() if IZGARA else ()):
        al = np.asarray(al, bool)
        sat = np.asarray(sat, bool)
        ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
        y = np.where(al[ix], 1, -1).astype(np.int64)
        sg, blk = sigall[ix], engel[ix]
        for giris in ("P", "L"):
            for k in KS:
                for R in RS:
                    for H in HS:
                        res = TS.sim_izgara(o, h, l, c, ix, y, sg, blk, k, R, H, giris == "L", 0.0, 0.0, 0.0, False)
                        out["A"][(ad, "izgara", giris, k, R, H)] = TS.toplam(yilb, gunb, *res)
    # VSP olaylari
    E = sinyal_v6.olaylar(s)
    ixv = np.searchsorted(ts, E["ts"])
    m = (ixv >= 5000) & (ixv < n - 40)
    ixv, yv, sgv = ixv[m], E["yon"][m].astype(np.int64), E["sig"][m]
    # 9) uyum olaylari
    bull, bear, doji, ham, inv = K2.candles(o, h, l, c)
    rsi14 = K1.rsi(c, 14)
    macd = TS.ema(c, 12) - TS.ema(c, 26)
    hist = macd - TS.ema(macd, 9)
    hh14, ll14 = TS.highest(h, 14), TS.lowest(l, 14)
    stk = sma(100 * (c - ll14) / np.where(hh14 - ll14 > 0, hh14 - ll14, np.nan), 3)
    cci10 = K1.cci(c, 10)
    mom = c - np.r_[np.full(10, np.nan), c[:-10]]
    obv = np.cumsum(np.sign(np.r_[0, np.diff(c)]) * v)
    vwm = sma(c * v, 12) / np.where(sma(v, 12) > 0, sma(v, 12), np.nan) - sma(c * v, 26) / np.where(sma(v, 26) > 0, sma(v, 26), np.nan)
    cmfm = ((c - l) - (h - c)) / np.where(h - l > 0, h - l, np.nan)
    cmf = sma(np.nan_to_num(cmfm) * v, 21) / np.where(sma(v, 21) > 0, sma(v, 21), np.nan)
    Mx = np.column_stack([macd, hist, rsi14, stk, cci10, mom, obv, vwm, cmf, K2.mfi(h, l, c, v, 14)])
    pos, neg = K2.divergences(np.ascontiguousarray(Mx), c, pivot(c, 5, 5, True), pivot(c, 5, 5, False), 5, 10, 100)
    s20 = sma(c, 20)
    mup = np.nan_to_num(s20 >= np.r_[np.full(2, np.nan), s20[:-2]]).astype(bool)
    mup1 = np.r_[False, mup[:-1]]
    pin_al, pin_sat = S["PIN"]
    olay_al = {"uyumsuzluk": son_k(pos > 0), "SMA20 dönüşü": son_k(mup & ~mup1), "pin bar": son_k(np.asarray(pin_al, bool)), "mum formasyonu": son_k(bull)}
    olay_sat = {"uyumsuzluk": son_k(neg > 0), "SMA20 dönüşü": son_k(~mup & mup1), "pin bar": son_k(np.asarray(pin_sat, bool)), "mum formasyonu": son_k(bear)}
    oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ixv, yv, sgv, np.zeros(len(ixv), bool), 2.0, 2.0, 5, False, 0.0, 0.0, 0.0, False)
    B = pd.DataFrame({"sym": s, "gun": ts[oi] // 86400, "yil": yilb[oi], "yon": oy, "brut": ob * 1e4,
                      "saat": pd.to_datetime(ts[oi], unit="s", utc=True).hour.to_numpy() // 4, "hgun": pd.to_datetime(ts[oi], unit="s", utc=True).dayofweek.to_numpy()})
    for ad, d in D.items():
        B["D:" + ad] = np.asarray(d)[oi] * oy > 0
    for ad, u in U.items():
        B["U:" + ad] = np.asarray(u, bool)[oi]
    puan = np.zeros(len(oi), np.int64)
    for ad in olay_al:
        hit = np.where(oy > 0, olay_al[ad][oi], olay_sat[ad][oi])
        B["W:" + ad] = hit
        puan += hit.astype(np.int64)
    B["W:puan >= 1"] = puan >= 1
    B["W:puan >= 2"] = puan >= 2
    # 12) BTC baglami
    if s != "BTCUSDT":
        bts, bz, br15, bev = BTC
        j = np.searchsorted(bts, ts[oi])
        okj = (j < len(bts)) & (bts[np.minimum(j, len(bts) - 1)] == ts[oi])
        jj = np.minimum(j, len(bts) - 1)
        B["B:BTC'de de aynı yönde sert hareket"] = okj & np.where(oy > 0, bz[jj] <= -3, bz[jj] >= 3)
        B["B:BTC 15 dk işleme ters yönde (AL'da BTC düşmüş)"] = okj & (br15[jj] * oy < 0)
        B["B:BTC'de de VSP sinyali"] = okj & (bev[jj] == oy)
    out["B"] = B
    # 3) ve 4)
    r2 = np.nan_to_num(r * r)
    cs = np.r_[0, np.cumsum(r2)]
    fut = np.sqrt(cs[np.minimum(t + 16, n)] - cs[np.minimum(t + 1, n)])
    idx = np.flatnonzero(gec & (t % 15 == 0) & (fut > 0))
    C = pd.DataFrame({"yil": yilb[idx], "gun": ts[idx] // 86400, "y": np.log(fut[idx]), "x0": np.log(sigall[idx]), "f15": (lc[np.minimum(idx + 15, n - 1)] - lc[idx]) * 1e4})
    for ad, u in U.items():
        C["U:" + ad] = np.asarray(u, bool)[idx].astype(float)
    for ad, d in D.items():
        C["D:" + ad] = np.asarray(d)[idx].astype(float)
    out["C"] = C
    # 6) cikis
    F = pd.DataFrame({"sym": s, "gun": ts[ixv] // 86400, "yil": yilb[ixv]})
    for ad, fl in X.items():
        base, alt = K2.exits(o, h, l, c, ixv, yv, sgv, np.asarray(fl, float), 30)
        F["base"] = base * 1e4
        F["X:" + ad] = alt * 1e4
    out["F"] = F
    # 7) stop yerlesimi
    G = pd.DataFrame({"sym": s, "gun": ts[ixv] // 86400, "yil": yilb[ixv]})
    ent = o[ixv + 1]
    var = {"1 sigma": 1.0 * sgv, "2 sigma (temel)": 2.0 * sgv, "3 sigma": 3.0 * sgv}
    lo10 = TS.lowest(l, 10)[ixv]
    hi10 = TS.highest(h, 10)[ixv]
    var["Son 10 mum dibi/tepesi"] = np.where(yv > 0, np.log(ent / (lo10 * np.exp(-0.1 * sgv))), np.log(hi10 * np.exp(0.1 * sgv) / ent))
    for ad, (ls, ss) in STOPS.items():
        ls, ss = np.asarray(ls, float), np.asarray(ss, float)
        var[ad + " stopu"] = np.where(yv > 0, np.log(ent / ls[ixv]), np.log(ss[ixv] / ent))
    for ad, dd in var.items():
        dd = np.where(np.isfinite(dd), dd, np.nan)
        b_, r_ = stop_varyant(o, h, l, c, ixv, yv, sgv, dd)
        G["R:" + ad] = r_
        G["bp:" + ad] = b_ * 1e4
    out["G"] = G
    # 8) giris zamanlamasi
    Hh = pd.DataFrame({"sym": s, "gun": ts[ixv] // 86400, "yil": yilb[ixv]})
    for mode, ad in ((0, "hemen (temel)"), (1, "1 mum bekle"), (2, "2 mum bekle"), (3, "ilk doğru renkli mum"), (4, "sinyal mumunun tepesi/dibi aşılınca")):
        Hh[ad] = giris_varyant(o, h, l, c, ixv, yv, sgv, mode) * 1e4
    out["H"] = Hh
    print(s, "tamam", flush=True)
    return out


def esli_fark(d, a, b):
    if a == b:  # temel kendisiyle karsilastirilmaz
        return 0.0, np.nan, int(d[a].notna().sum())
    x = d[[a, b, "gun"]].dropna()
    df_ = x[a] - x[b]
    g = (df_ - df_.mean()).groupby(x["gun"]).sum()
    se = math.sqrt((g ** 2).sum()) / max(len(x), 1)
    return df_.mean(), (df_.mean() / se if se > 0 else np.nan), len(x)


def gun_t(d, kol="brut"):
    m = d[kol].mean()
    g = (d[kol] - m).groupby(d["gun"]).sum()
    se = math.sqrt((g ** 2).sum()) / len(d)
    return m, se


def main():
    BTC = btc_baglam()
    A, B, C, F, G, H = {}, [], [], [], [], []
    with Pool(4) as p:
        for parca in p.imap_unordered(parite_isle, [(s, BTC) for s in izleme.SYMS]):
            A = TS.birlestir([A, parca["A"]]) if A else TS.birlestir([parca["A"]])
            B.append(parca["B"]); C.append(parca["C"]); F.append(parca["F"]); G.append(parca["G"]); H.append(parca["H"])
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 40)
    # 1
    pd.to_pickle(dict(B=B, C=C, F=F, G=G, H=H), os.path.join(izleme.VERI, "katki3_parca.pkl"))
    if IZGARA:
        rows = []
        for key, yl in A.items():
            for y in (2025, 2026):
                rows.append(dict(aday=key[0], giris=key[2], k=key[3], R=key[4], H=key[5], yil=y, **TS.ozet(yl[y])))
        DA = pd.DataFrame(rows)
        DA.to_csv(os.path.join(izleme.VERI, "katki3_A.csv"), index=False)
    else:
        DA = pd.read_csv(os.path.join(izleme.VERI, "katki3_A.csv"))
    kar = []
    for ad in DA["aday"].unique():
        d = DA[DA["aday"] == ad]
        a25 = d[d["yil"] == 2025].sort_values("netR", ascending=False).iloc[0]
        sel = d[(d["giris"] == a25["giris"]) & (d["k"] == a25["k"]) & (d["R"] == a25["R"]) & (d["H"] == a25["H"])]
        r25, r26 = sel[sel["yil"] == 2025].iloc[0], sel[sel["yil"] == 2026].iloc[0]
        gecti = r25["netR"] > 0 and r26["netR"] > 0 and r25["t"] >= 2 and r26["t"] >= 3
        kar.append(dict(aday=ad, ayar=f"{a25['giris']} k{a25['k']} R{a25['R']} H{a25['H']}", n25=r25["n"], n26=r26["n"], R25=r25["netR"], t25=r25["t"],
                        R26=r26["netR"], t26=r26["t"], bp25=r25["brut_bp"], bp26=r26["brut_bp"], AL26=r26["brutAL_bp"], SAT26=r26["brutSAT_bp"], karar="GECTI" if gecti else "gecmedi"))
    print("=== 1) Sinyal ===")
    print(pd.DataFrame(kar).round(3).to_string())
    DB = pd.concat(B, ignore_index=True)
    # 2, 9, 12
    print("\n=== 2) Filtre, 9) Uyum, 12) BTC baglami (VSP islemleri) ===")
    fr = []
    for kol in [k for k in DB.columns if k[:2] in ("D:", "U:", "W:", "B:")]:
        dd = DB.dropna(subset=[kol]) if DB[kol].dtype == object else DB
        if kol.startswith("B:"):
            dd = DB[DB["sym"] != "BTCUSDT"].copy()
            dd[kol] = dd[kol].astype(bool)
        res = {yl: K1.iki_grup(dd[dd["yil"] == yl], kol) for yl in (2025, 2026)}
        f25, t25, p25 = res[2025]
        f26, t26, p26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3 and min(p25, p26) >= 0.2 and max(p25, p26) <= 0.8
        fr.append(dict(durum=kol, pay25=p25, fark25=f25, t25=t25, pay26=p26, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(fr).round(3).to_string())
    # 3, 4
    DC = pd.concat(C, ignore_index=True)
    print("\n=== 3) Oynaklik bilgisi ===")
    cr = []
    for kol in [k for k in DC.columns if k.startswith("U:") or k.startswith("D:")]:
        tmp = DC
        if kol.startswith("D:"):
            tmp = DC.copy()
            tmp[kol] = (tmp[kol] != 0).astype(float)
        a = K1.r2_artis(tmp, kol)
        cr.append(dict(ozellik=kol, r2_25=a[2025], r2_26=a[2026], karar="KABUL" if min(a.values()) >= 0.005 else ""))
    print(pd.DataFrame(cr).round(4).to_string())
    print("\n=== 4) Yon bilgisi ===")
    yr = []
    for kol in [k for k in DC.columns if k.startswith("D:")]:
        res = {yl: K2.yon_farki(DC[DC["yil"] == yl], kol) for yl in (2025, 2026)}
        f25, t25 = res[2025]
        f26, t26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3
        yr.append(dict(durum=kol, fark25=f25, t25=t25, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(yr).round(3).to_string())
    # 6
    DF = pd.concat(F, ignore_index=True)
    print("\n=== 6) Cikis ===")
    xr = []
    for kol in [k for k in DF.columns if k.startswith("X:")]:
        rr = {yl: esli_fark(DF[DF["yil"] == yl], kol, "base") for yl in (2025, 2026)}
        ok = rr[2025][0] >= 0.5 and rr[2026][0] >= 0.5 and rr[2026][1] >= 3
        xr.append(dict(cikis=kol, fark25=rr[2025][0], t25=rr[2025][1], fark26=rr[2026][0], t26=rr[2026][1], karar="KABUL" if ok else ""))
    print(pd.DataFrame(xr).round(3).to_string())
    # 7
    DG = pd.concat(G, ignore_index=True)
    print("\n=== 7) Stop yerlesimi (R ve bp; fark = alternatif - 2 sigma) ===")
    gr = []
    for kol in [k for k in DG.columns if k.startswith("R:")]:
        ad = kol[2:]
        row = dict(stop=ad)
        for yl in (2025, 2026):
            d = DG[DG["yil"] == yl]
            row[f"R{yl % 100}"] = d[kol].mean()
            row[f"bp{yl % 100}"] = d["bp:" + ad].mean()
            f, tt, nn = esli_fark(d, kol, "R:2 sigma (temel)")
            row[f"fark{yl % 100}"] = f
            row[f"t{yl % 100}"] = tt
            row[f"n{yl % 100}"] = nn
        row["karar"] = "KABUL" if (ad != "2 sigma (temel)" and row["fark25"] >= 0.01 and row["fark26"] >= 0.01 and row["t26"] >= 3) else ""
        gr.append(row)
    print(pd.DataFrame(gr).round(4).to_string())
    # 8
    DH = pd.concat(H, ignore_index=True)
    print("\n=== 8) Giris zamanlamasi (alinan islemlerde alternatif - hemen, bp) ===")
    hr = []
    for kol in ["1 mum bekle", "2 mum bekle", "ilk doğru renkli mum", "sinyal mumunun tepesi/dibi aşılınca", "hemen (temel)"]:
        row = dict(giris=kol)
        for yl in (2025, 2026):
            d = DH[DH["yil"] == yl]
            row[f"bp{yl % 100}"] = d[kol].mean()
            row[f"alinma{yl % 100}"] = d[kol].notna().mean()
            f, tt, nn = esli_fark(d, kol, "hemen (temel)")
            row[f"fark{yl % 100}"] = f
            row[f"t{yl % 100}"] = tt
        row["karar"] = "KABUL" if (kol != "hemen (temel)" and row["fark25"] >= 0.5 and row["fark26"] >= 0.5 and row["t26"] >= 3 and min(row["alinma25"], row["alinma26"]) >= 0.3) else ""
        hr.append(row)
    print(pd.DataFrame(hr).round(3).to_string())
    # 10
    print("\n=== 10) Coin secimi ===")
    pp = DB.groupby(["sym", "yil"])["brut"].mean().unstack()
    print(pp.round(2).sort_values(2025, ascending=False).to_string())
    rho = pp[2025].rank().corr(pp[2026].rank())
    top = pp[2025].sort_values(ascending=False).index[:11]
    d26 = DB[DB["yil"] == 2026].copy()
    d26["ust"] = d26["sym"].isin(top)
    f, tt, pay = K1.iki_grup(d26, "ust")
    print(f"Spearman rho = {rho:.3f}; 2026'da 2025'in ilk 11 paritesi - son 11 = {f:.3f} bp (t {tt:.2f})",
          "KABUL" if (rho >= 0.3 and f >= 1 and tt >= 2.5) else "")
    # 11
    print("\n=== 11) Saat ve gun ===")
    for kol, ad in (("saat", "UTC 4 saatlik dilim"), ("hgun", "haftanin gunu (0 = Pazartesi)")):
        tb = DB.groupby([kol, "yil"])["brut"].mean().unstack()
        print(ad)
        print(tb.round(2).to_string())
        rho = tb[2025].rank().corr(tb[2026].rank())
        best = tb[2025].sort_values(ascending=False).index[:2]
        worst = tb[2025].sort_values().index[:2]
        d26 = DB[(DB["yil"] == 2026) & DB[kol].isin(list(best) + list(worst))].copy()
        d26["iyi"] = d26[kol].isin(best)
        f, tt, pay = K1.iki_grup(d26, "iyi")
        print(f"rho = {rho:.3f}; 2026'da en iyi 2 - en kotu 2 = {f:.3f} bp (t {tt:.2f})", "KABUL" if (rho >= 0.5 and f >= 1 and tt >= 3) else "")


if __name__ == "__main__":
    main()
