import glob, os, sys
import numpy as np, pandas as pd
exec(open("tvind.py").read().split("def indicators")[0])
b = np.load("volmodel_b.npy")
prows, crow = [], []
rng_ = np.random.default_rng(7)
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]; z = np.load(f)
    o, h, l, c, v, ts = z["o"], z["h"], z["l"], z["c"], z["v"], z["ts"]
    t = pd.to_datetime(ts, unit="s", utc=True); day = t.floor("D")
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    tr = np.maximum(h - l, np.maximum(np.abs(h - lag(c)), np.abs(l - lag(c)))); atr = rma(np.nan_to_num(tr), 14)
    ewv = S(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    fwd15 = np.r_[lc[15:] - lc[:-15], np.full(15, np.nan)]
    # --- birlesik model kalibrasyonu ---
    sigA = np.sqrt(ewv * 15)
    sigB = np.exp(b[0] + b[1] * 0.5 * np.log(ewv) + b[2] * np.log(atr / c))
    idx = np.arange(3000, len(c) - 20, 7)
    part = np.where(ts[idx] < CUT, "2025", "2026")
    for name, sg in (("EWMA (v5.1)", sigA), ("EWMA + ATR (yeni)", sigB)):
        x = np.abs(fwd15[idx]) / sg[idx]
        crow.append(pd.DataFrame({"model": name, "part": part, "x": x, "la": np.log(np.abs(fwd15[idx]) + 1e-9), "lf": np.log(sg[idx])}))
    # --- pivot testi ---
    dH = pd.Series(h, index=t).groupby(day).max(); dL = pd.Series(l, index=t).groupby(day).min(); dC = pd.Series(c, index=t).groupby(day).last()
    P = (dH + dL + dC) / 3
    levels = {"P": P, "R1": 2 * P - dL, "S1": 2 * P - dH}
    days = P.index
    for name, ser in levels.items():
        L = ser.shift(1)
        Rnd = L * (1 + pd.Series(rng_.uniform(-0.01, 0.01, len(days)), index=days))
        for kind, LL in (("pivot", L), ("rastgele", Rnd)):
            lvl = LL.reindex(day).to_numpy()
            for dirn in (1, -1):  # 1: alttan temas (geri itilme = asagi), -1: ustten temas
                hit = (lag(h) < lag(lvl)) & (h >= lvl) if dirn == 1 else (lag(l) > lag(lvl)) & (l <= lvl)
                hit = np.nan_to_num(hit).astype(bool) & (day == pd.Series(day).shift(1).to_numpy())  # gun ici
                dfh = pd.DataFrame({"d": day, "hit": hit, "i": np.arange(len(c))})
                first = dfh[dfh.hit].groupby("d").i.first().to_numpy()
                first = first[(first > 3000) & (first < len(c) - 20)]
                react = np.log(lvl[first] / c[first + 15]) * 1e4 * dirn   # seviyeden 15 dk sonra geri itilme (bp)
                prows.append(pd.DataFrame({"lvl": name, "kind": kind, "part": np.where(ts[first] < CUT, "2025", "2026"), "react": react, "sym": s}))
    print("tamam", s, file=sys.stderr)
C = pd.concat(crow)
print("1) Oynaklık modeli: |15 dk getiri| / öngörülen σ dilimleri ve log korelasyon")
for (m, p), g in C.groupby(["model", "part"]):
    ok = np.isfinite(g.la) & np.isfinite(g.lf)
    print(f"{m:20s} {p}: %50 {g.x.quantile(.5):.3f} | %80 {g.x.quantile(.8):.3f} | %95 {g.x.quantile(.95):.3f} | log korelasyon {np.corrcoef(g.la[ok], g.lf[ok])[0,1]:.3f}")
Pv = pd.concat(prows)
print("\n2) Pivot: seviyeye günün ilk temasından 15 dk sonra seviyeden geri itilme (bp, pozitif = seviye tuttu)")
t = Pv.groupby(["part", "lvl", "kind"]).react.agg(["mean", "count"]).unstack("kind")
print(t.round(1).to_string())
