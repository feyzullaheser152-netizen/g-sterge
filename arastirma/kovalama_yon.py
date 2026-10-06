"""Kovalama uyarisi yon ayrimi (bagimsiz kontrol): sert alis akisi (LONG kovalama) ve sert satis akisi (SHORT kovalama)
ilk mumda ayri ayri. Tanimlar Pine ile ayni (BVC, z15 >= 3, imb15 >= 0,15). Olay: onceki 15 mumda ayni yonde akis yok.
Giris: olay mumunun kapanisi (L=0). Kayip = -isaret * ln(c[t+h]/c[t]) * 1e4 bp, h = 5 ve 15. Gun kumelenmis t."""
import glob, os
import numpy as np, pandas as pd

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
rows = []
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]
    z = np.load(f); ts, c, v = z["ts"], z["c"], z["v"]
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    dp = np.r_[np.nan, np.diff(c)]
    dps = pd.Series(dp).rolling(100).std(ddof=0).to_numpy()
    bf = np.where(dps > 0, 1 / (1 + np.exp(-1.702 * dp / np.where(dps > 0, dps, 1))), 0.5)
    sv = v * (2 * bf - 1)
    v15 = pd.Series(v).rolling(15).sum().to_numpy(); imb = np.where(v15 > 0, pd.Series(sv).rolling(15).sum().to_numpy() / np.where(v15 > 0, v15, 1), 0)
    sd = pd.Series(r).rolling(1440).std(ddof=0).to_numpy()
    z15 = np.where(sd > 0, (lc - np.r_[np.full(15, np.nan), lc[:-15]]) / (sd * np.sqrt(15)), 0)
    for sg, cond in ((1, (z15 >= 3) & (imb >= 0.15)), (-1, (z15 <= -3) & (imb <= -0.15))):
        cond = np.nan_to_num(cond).astype(bool)
        prev = pd.Series(cond.astype(float)).shift(1).rolling(15, min_periods=1).max().fillna(0).to_numpy() > 0
        ev = np.flatnonzero(cond & ~prev)
        ev = ev[(ev > 3000) & (ev < len(c) - 16)]
        for h in (5, 15):
            loss = -sg * (lc[ev + h] - lc[ev]) * 1e4
            rows.append(pd.DataFrame({"sym": s, "yon": "LONG kovalama (sert alış)" if sg == 1 else "SHORT kovalama (sert satış)", "h": h, "yil": np.where(ts[ev] < 1767225600, "2025", "2026"), "gun": ts[ev] // 86400, "kayip": loss}))
D = pd.concat(rows)
out = []
for (yon, h, yil), g in D.groupby(["yon", "h", "yil"]):
    m = g.kayip.mean(); dm = g.groupby("gun").kayip.agg(["sum", "size"])
    psi = (g.kayip - m).groupby(g.gun).sum(); se = np.sqrt((psi ** 2).sum()) / len(g)
    ps = g.groupby("sym").kayip.mean()
    out.append({"yön": yon, "ufuk dk": h, "yıl": yil, "n": len(g), "ort. kayıp bp": round(m, 2), "t": round(m / se, 2), "medyan": round(g.kayip.median(), 2), "+ parite %": round((ps > 0).mean() * 100)})
print(pd.DataFrame(out).to_string(index=False))
ex = D[(D.gun != 20371)]
print("\n10 Ekim 2025 haric (yalniz 2025):")
for (yon, h), g in ex[ex.yil == "2025"].groupby(["yon", "h"]):
    print(yon, h, round(g.kayip.mean(), 2))
