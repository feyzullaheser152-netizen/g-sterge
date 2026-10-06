"""Seans (saat), pivot noktalari, ADR testleri ve EWMA + ATR birlesik oynaklik kalibrasyonu."""
import glob, os, sys
import numpy as np, pandas as pd
exec(open("tvind.py").read().split("def indicators")[0])

vrows, prows, arows, cal = [], [], [], []
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]
    z = np.load(f)
    o, h, l, c, v, ts = z["o"], z["h"], z["l"], z["c"], z["v"], z["ts"]
    t = pd.to_datetime(ts, unit="s", utc=True); hr = t.hour.to_numpy(); day = t.floor("D")
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    tr = np.maximum(h - l, np.maximum(np.abs(h - lag(c)), np.abs(l - lag(c))))
    atr = rma(np.nan_to_num(tr), 14)
    ewv = S(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    def fwd_rv(n):
        x = np.sqrt(S(r * r)[::-1].rolling(n).sum()[::-1].to_numpy()); return np.r_[x[1:], np.nan]
    rv15, rv60 = fwd_rv(15), fwd_rv(60)
    fwd15 = np.r_[lc[15:] - lc[:-15], np.full(15, np.nan)]
    fwd5 = np.r_[lc[5:] - lc[:-5], np.full(5, np.nan)]
    # saat profili: onceki 20 gunun saatlik ortalama r^2'si (ileriye bakma yok)
    hd = pd.DataFrame({"d": day, "h": hr, "r2": r * r}).groupby(["d", "h"]).r2.mean().unstack()
    prof = hd.ewm(span=20).mean().shift(1)
    nxt = (hr + 1) % 24
    pn = prof.stack().reindex(pd.MultiIndex.from_arrays([day, nxt])).to_numpy()
    pc = prof.stack().reindex(pd.MultiIndex.from_arrays([day, hr])).to_numpy()
    seas = np.log(pn / pc)
    # ADR: bugunku aralik / son 14 gunun ortalama gunluk araligi
    dh = pd.Series(h, index=t).groupby(day).cummax().to_numpy(); dl = pd.Series(l, index=t).groupby(day).cummin().to_numpy()
    drng = pd.Series(h, index=t).groupby(day).max() - pd.Series(l, index=t).groupby(day).min()
    adr = (drng.rolling(14).mean().shift(1)).reindex(day).to_numpy()
    used = (dh - dl) / adr
    idx = np.arange(3000, len(c) - 61, 5)
    part = np.where(ts[idx] < CUT, "2025", "2026")
    df = pd.DataFrame({"part": part, "y15": np.log(rv15[idx]), "y60": np.log(rv60[idx]), "lew": 0.5 * np.log(ewv[idx]), "latr": np.log(atr[idx] / c[idx]), "seas": seas[idx], "used": np.log(used[idx])}).replace([np.inf, -np.inf], np.nan).dropna()
    for p, g in df.groupby("part"):
        def r2(cols, y):
            X = np.c_[np.ones(len(g)), g[cols].to_numpy()]; b = np.linalg.lstsq(X, g[y], rcond=None)[0]
            return 1 - np.var(g[y] - X @ b) / np.var(g[y])
        base = r2(["lew", "latr"], "y60")
        vrows.append(dict(sym=s, part=p, seans_60dk=r2(["lew", "latr", "seas"], "y60") - base, adr_60dk=r2(["lew", "latr", "used"], "y60") - base))
    # EWMA+ATR birlesik tahmin katsayilari (2025'te kestir)
    g = df[df.part == "2025"]
    cal.append(g.assign(sym=s))
    # Pivot noktalari (standart, onceki gun H/L/C)
    dH = pd.Series(h, index=t).groupby(day).max(); dL = pd.Series(l, index=t).groupby(day).min(); dC = pd.Series(c, index=t).groupby(day).last()
    P = (dH + dL + dC) / 3
    lv = {"P": P, "R1": 2 * P - dL, "S1": 2 * P - dH, "R2": P + (dH - dL), "S2": P - (dH - dL)}
    for name, ser in lv.items():
        L = ser.shift(1).reindex(day).to_numpy()
        lvl_rand = L * (1 + np.where(np.arange(len(c)) % 2 == 0, 0.0037, -0.0037))  # karsilastirma: yakindaki rastgele seviye
        for kind, LL in (("pivot", L), ("rastgele", lvl_rand)):
            fromBelow = (lag(h) < lag(LL)) & (h >= LL)   # alttan ilk temas
            fromAbove = (lag(l) > lag(LL)) & (l <= LL)
            for m, sg in ((fromBelow, -1), (fromAbove, 1)):   # seviyeden geri itilme yonu
                ix = np.flatnonzero(np.nan_to_num(m).astype(bool))
                ix = ix[(ix > 3000) & (ix < len(c) - 20)]
                if len(ix) == 0: continue
                # temas fiyati seviye; tepki = sonraki 15 dk getiri, seviyeden olculur, geri itilme yonunde
                react = np.log(c[ix + 15] / LL[ix]) * 1e4 * sg
                prows.append(pd.DataFrame({"sym": s, "lvl": name, "kind": kind, "part": np.where(ts[ix] < CUT, "2025", "2026"), "react": react}))
    print("tamam", s, file=sys.stderr)

V = pd.DataFrame(vrows)
print("1) SEANS ve ADR: sonraki 60 dk oynaklık tahminine ek açıklama gücü (EWMA + ATR üstüne, R² artışı)")
print(V.groupby("part")[["seans_60dk", "adr_60dk"]].mean().round(4).to_string())
Pv = pd.concat(prows)
print("\n2) PİVOT: seviyeye ilk temastan sonra 15 dk 'geri itilme' getirisi (bp). Pivot vs yakındaki rastgele seviye")
print(Pv.groupby(["part", "lvl", "kind"]).react.agg(["mean", "count"]).unstack("kind").round(1).to_string())
C = pd.concat(cal)
X = np.c_[np.ones(len(C)), C.lew, C.latr]; b = np.linalg.lstsq(X, C.y15, rcond=None)[0]
print("\n3) Birleşik oynaklık modeli (2025 kestirimi): log σ15 =", np.round(b, 4))
np.save("volmodel_b.npy", b)
