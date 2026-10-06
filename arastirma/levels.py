"""Topluluk gostergelerindeki seviye kavramlarinin testi (22 Binance paritesi, 2025 / 2026).
Seviyeler: Fair Value Gap (FVG), Order Block (OB), onceki gun Volume Profile POC / VAH / VAL, gun acilisi (HTF Power of Three),
gunluk VWAP. Karsilastirma: gun boyu sabit rastgele seviyeler.
Olcumler (ilk temastan itibaren):
  tepki: seviyeden 15 dk sonra geri itilme (bp, pozitif = seviye tuttu)
  tutma: 15 dk icinde kapanisin seviyenin 0.5 sigma otesine gecmeme orani
  oynaklik: sonraki 15 dk gerceklesen oynaklik / EWMA tahmini"""
import glob, os, sys
import numpy as np, pandas as pd

SRC = "../data_bn/npz"
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
rng_ = np.random.default_rng(11)


def lag(x, k=1):
    o = np.full(len(x), np.nan); o[k:] = x[:-k]; return o


def measure(kind, lvl_name, ix, lvl, sgn, c, h, l, ew, rvf, ts, sym):
    """sgn=+1: destek (alttan geri itilme beklenir, fiyat yukaridan gelir); -1: direnc."""
    ok = (ix > 3000) & (ix < len(c) - H - 1) & np.isfinite(lvl)
    ix, lvl, sgn = ix[ok], lvl[ok], sgn[ok]
    if len(ix) == 0:
        return None
    react = np.log(c[ix + H] / lvl) * 1e4 * sgn
    sig = np.sqrt(ew[ix] * H)
    beyond = np.array([np.any(sgn[k] * np.log(c[ix[k] + 1: ix[k] + H + 1] / lvl[k]) < -0.5 * sig[k]) for k in range(len(ix))])
    vol = rvf[ix] / sig
    return pd.DataFrame({"sym": sym, "lvl": lvl_name, "kind": kind, "part": np.where(ts[ix] < CUT, "2025", "2026"), "react": react, "hold": ~beyond, "vol": vol})


def first_touch(day, cond):
    dfh = pd.DataFrame({"d": day, "c": cond, "i": np.arange(len(cond))})
    return dfh[dfh.c].groupby("d").i.first().to_numpy()


def daily_level_events(name, L, Rnd, c, h, l, day, ew, rvf, ts, sym, out):
    for kind, LL in (("seviye", L), ("rastgele", Rnd)):
        same = day == np.r_[day[:1], day[:-1]]
        sup = np.nan_to_num((lag(l) > lag(LL)) & (l <= LL)).astype(bool) & same   # yukaridan inerek temas -> destek
        res = np.nan_to_num((lag(h) < lag(LL)) & (h >= LL)).astype(bool) & same   # asagidan cikarak temas -> direnc
        for cond, sg in ((sup, 1), (res, -1)):
            ix = first_touch(day, cond)
            m = measure(kind, name, ix, LL[ix] if len(ix) else np.array([]), np.full(len(ix), sg), c, h, l, ew, rvf, ts, sym)
            if m is not None:
                out.append(m)


def main():
    out = []
    for f in sorted(glob.glob(f"{SRC}/*.npz"))[:int(os.environ.get("NSYM", "99"))]:
        s = os.path.basename(f)[:-4]
        z = np.load(f)
        o, h, l, c, v, ts = z["o"], z["h"], z["l"], z["c"], z["v"], z["ts"]
        t = pd.to_datetime(ts, unit="s", utc=True); day = t.floor("D").to_numpy()
        lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
        ew = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
        rvf = np.sqrt(pd.Series(r * r)[::-1].rolling(H).sum()[::-1].to_numpy()); rvf = np.r_[rvf[1:], np.nan]
        tr = np.maximum(h - l, np.maximum(np.abs(h - lag(c)), np.abs(l - lag(c))))
        atr = pd.Series(np.nan_to_num(tr)).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        days = pd.unique(day)
        rnd_off = pd.Series(rng_.uniform(-0.01, 0.01, len(days)), index=days)
        # --- gunluk seviyeler ---
        dO = pd.Series(o, index=day).groupby(level=0).first()
        # Volume Profile: onceki gunun POC / VAH / VAL (100 kutu)
        poc, vah, val = {}, {}, {}
        dfp = pd.DataFrame({"d": day, "p": (h + l + c) / 3, "v": v})
        for d, g in dfp.groupby("d"):
            p, vv = g.p.to_numpy(), g.v.to_numpy()
            lo, hi = p.min(), p.max()
            if hi <= lo:
                continue
            bins = np.linspace(lo, hi, 101); hist = np.bincount(np.clip(np.digitize(p, bins) - 1, 0, 99), weights=vv, minlength=100)
            k = hist.argmax(); a, b_ = k, k; tot = hist.sum(); acc = hist[k]
            while acc < 0.7 * tot and (a > 0 or b_ < 99):
                na_ = hist[a - 1] if a > 0 else -1; nb = hist[b_ + 1] if b_ < 99 else -1
                if na_ >= nb: a -= 1; acc += hist[a]
                else: b_ += 1; acc += hist[b_]
            ctr = (bins[:-1] + bins[1:]) / 2
            poc[d], vah[d], val[d] = ctr[k], bins[b_ + 1], bins[a]
        prev = lambda dct: pd.Series(dct).shift(1).reindex(day).to_numpy()
        ref = pd.Series(c, index=day).groupby(level=0).first().reindex(day).to_numpy()
        Rnd = ref * (1 + rnd_off.reindex(day).to_numpy())
        daily_level_events("Gün açılışı", dO.reindex(day).to_numpy(), Rnd, c, h, l, day, ew, rvf, ts, s, out)
        daily_level_events("Önceki gün POC", prev(poc), Rnd, c, h, l, day, ew, rvf, ts, s, out)
        daily_level_events("Önceki gün VAH", prev(vah), Rnd, c, h, l, day, ew, rvf, ts, s, out)
        daily_level_events("Önceki gün VAL", prev(val), Rnd, c, h, l, day, ew, rvf, ts, s, out)
        hlc3 = (h + l + c) / 3
        cv = pd.Series(hlc3 * v).groupby(day).cumsum().to_numpy() / pd.Series(v).groupby(day).cumsum().to_numpy()
        vw = lag(cv)  # bir onceki mumun VWAP'i (temas olcumu icin sabit referans)
        # VWAP temasi: gun ici ilk degil, 60 dk ayrikli tum temaslar
        for kind, LL in (("seviye", vw), ("rastgele", vw * (1 + rnd_off.reindex(day).to_numpy() * 0.5))):
            sup = np.nan_to_num((lag(l) > LL) & (l <= LL)).astype(bool)
            res = np.nan_to_num((lag(h) < LL) & (h >= LL)).astype(bool)
            for cond, sg in ((sup, 1), (res, -1)):
                ix = np.flatnonzero(cond)
                keep, last = [], -10**9
                for i in ix:
                    if i - last >= 60: keep.append(i); last = i
                ix = np.array(keep, int)
                m = measure(kind, "VWAP", ix, LL[ix] if len(ix) else np.array([]), np.full(len(ix), sg), c, h, l, ew, rvf, ts, s)
                if m is not None: out.append(m)
        # --- Haftalik ve 4 saatlik pivot (CM Pivot Points MTF) ---
        tt = pd.Series(np.arange(len(c)), index=t)
        for pname, rule in (("Haftalık pivot P", "W-SUN"), ("4 saatlik pivot P", "4h")):
            key = t.to_period(rule.replace("4h", "4h")) if rule == "W-SUN" else t.floor("4h")
            key = np.asarray(key.astype(str))
            gH = pd.Series(h).groupby(key).max(); gL = pd.Series(l).groupby(key).min(); gC = pd.Series(c).groupby(key).last()
            order = pd.Series(np.arange(len(c))).groupby(key).first().sort_values().index
            Pp = ((gH + gL + gC) / 3).reindex(order).shift(1)
            LL = Pp.reindex(key).to_numpy()
            refk = pd.Series(c).groupby(key).first().reindex(key).to_numpy()
            offs = pd.Series(rng_.uniform(-0.01, 0.01, len(order)), index=order).reindex(key).to_numpy()
            daily_level_events(pname, LL, refk * (1 + offs), c, h, l, key, ew, rvf, ts, s, out)
        # --- Salinim tepe/dip seviyeleri (Pivot Points High Low, Price Action S/R, Key Levels) ---
        R_ = 10
        win = 2 * R_ + 1
        from numpy.lib.stride_tricks import sliding_window_view as swv
        isPH = np.zeros(len(c), bool); isPL = np.zeros(len(c), bool)
        isPH[2 * R_:] = swv(h, win).argmax(1) == R_
        isPL[2 * R_:] = swv(l, win).argmin(1) == R_
        evs = []
        for mask, src, sg in ((isPH, h, -1), (isPL, l, 1)):
            for i in np.flatnonzero(mask):
                lvl = src[i - R_]
                seg = slice(i + 1, min(i + 241, len(c)))
                hit = np.flatnonzero((h[seg] >= lvl) if sg == -1 else (l[seg] <= lvl))
                if len(hit):
                    evs.append((i + 1 + hit[0], lvl, sg))
        if evs:
            ix = np.array([e[0] for e in evs]); lv = np.array([e[1] for e in evs]); sg = np.array([e[2] for e in evs])
            out.append(measure("seviye", "Salınım tepe/dip", ix, lv, sg, c, h, l, ew, rvf, ts, s))
            lv2 = lv * (1 - sg * 0.003)
            ix2 = []
            for k in range(len(ix)):
                seg = slice(ix[k], min(ix[k] + 240, len(c)))
                hit = np.flatnonzero((l[seg] <= lv2[k]) if sg[k] == 1 else (h[seg] >= lv2[k]))
                ix2.append(ix[k] + hit[0] if len(hit) else -1)
            ix2 = np.array(ix2); ok = ix2 > 0
            out.append(measure("rastgele", "Salınım tepe/dip", ix2[ok], lv2[ok], sg[ok], c, h, l, ew, rvf, ts, s))
        # --- FVG ve Order Block (bolgeye ilk geri donus) ---
        for name in ("FVG", "Order block"):
            evs = []
            if name == "FVG":
                bull = (l > lag(h, 2)) & ((l - lag(h, 2)) >= 0.5 * atr)
                bear = (h < lag(l, 2)) & ((lag(l, 2) - h) >= 0.5 * atr)
                zt_b, zt_s = l, h           # bolgenin fiyata yakin kenari: boga FVG ust kenari = l[i]
            else:
                disp_up = (c - lag(c, 3)) >= 3 * atr
                disp_dn = (lag(c, 3) - c) >= 3 * atr
                # son ters renkli mum: 3 mum onceki mum (basitlestirilmis LuxAlgo mantigi)
                ob_up = disp_up & (lag(c, 3) < lag(o, 3)); ob_dn = disp_dn & (lag(c, 3) > lag(o, 3))
                bull, bear = ob_up, ob_dn
                zt_b, zt_s = lag(h, 3), lag(l, 3)   # boga OB ust kenari (destek), ayi OB alt kenari (direnc)
            for mask, zt, sg in ((bull, zt_b, 1), (bear, zt_s, -1)):
                for i in np.flatnonzero(np.nan_to_num(mask).astype(bool)):
                    lvl = zt[i]
                    seg = slice(i + 2, min(i + 241, len(c)))
                    hit = np.flatnonzero((l[seg] <= lvl) if sg == 1 else (h[seg] >= lvl))
                    if len(hit):
                        evs.append((i + 2 + hit[0], lvl, sg))
            if evs:
                ix = np.array([e[0] for e in evs]); lv = np.array([e[1] for e in evs]); sg = np.array([e[2] for e in evs])
                out.append(measure("seviye", name, ix, lv, sg, c, h, l, ew, rvf, ts, s))
                # rastgele: ayni anda, fiyatin ayni uzakligindaki ters taraftaki seviye yerine, seviyeyi %0.3 kaydir
                lv2 = lv * (1 - sg * 0.003)
                ix2 = []
                for k in range(len(ix)):
                    seg = slice(ix[k], min(ix[k] + 240, len(c)))
                    hit = np.flatnonzero((l[seg] <= lv2[k]) if sg[k] == 1 else (h[seg] >= lv2[k]))
                    ix2.append(ix[k] + hit[0] if len(hit) else -1)
                ix2 = np.array(ix2); ok = ix2 > 0
                out.append(measure("rastgele", name, ix2[ok], lv2[ok], sg[ok], c, h, l, ew, rvf, ts, s))
        print("tamam", s, file=sys.stderr)
    D = pd.concat([d for d in out if d is not None])
    D.to_pickle("levels.pkl")
    print("İlk temas sonrası 15 dk: tepki (bp, + = seviye tuttu), tutma oranı (%), oynaklık / tahmin")
    T = D.groupby(["lvl", "part", "kind"]).agg(n=("react", "size"), tepki=("react", "mean"), tutma=("hold", "mean"), oyn=("vol", "median")).unstack("kind")
    T[("tutma", "seviye")] *= 100; T[("tutma", "rastgele")] *= 100
    print(T.round(2).to_string())


main()
