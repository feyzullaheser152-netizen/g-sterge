"""Aday 5 (v5.7): Turuncu uyarida BVC filtresi gerekli mi? Akis tanimi 'z15 <= -3 ve imb15 <= -0,15' (BVC) yerine yalnizca 'z15 <= -3'.
On kayitli kural (iki yilda da): olay kumelerinin Jaccard orani >= %99; L=0'da SHORT kovalama kaybi (5 ve 15 dk) en fazla 0,3 bp degisir;
iki yonde sert akis 'x normal' degeri en fazla 0,05 degisir. Tutarsa BVC, flowImb girdisi ve 'Tahmini delta' kaldirilir."""
import glob, os
import numpy as np, pandas as pd

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
BASE = {"2025": 0.725, "2026": 0.701}


def son_ind(m):
    idx = np.where(m, np.arange(len(m)), -10**9)
    return np.r_[-10**9, np.maximum.accumulate(idx)[:-1]]


rows, tw = [], []
J = {"2025": [0, 0], "2026": [0, 0]}
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]
    z = np.load(f); ts, c, v = z["ts"], z["c"], z["v"]
    n = len(c); t = np.arange(n)
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    dp = np.r_[np.nan, np.diff(c)]
    dps = pd.Series(dp).rolling(100).std(ddof=0).to_numpy()
    ok = dps > 0
    bf = np.where(ok, 1 / (1 + np.exp(-1.702 * np.nan_to_num(dp) / np.where(ok, dps, 1))), 0.5)
    v15 = pd.Series(v).rolling(15).sum().to_numpy()
    imb = np.where(v15 > 0, pd.Series(v * (2 * bf - 1)).rolling(15).sum().to_numpy() / np.where(v15 > 0, v15, 1), 0)
    sd = pd.Series(r).rolling(1440).std(ddof=0).to_numpy()
    z15 = np.where(sd > 0, (lc - np.r_[np.full(15, np.nan), lc[:-15]]) / (sd * np.sqrt(15)), 0)
    x = np.abs(r) / pd.Series(r).rolling(1440).std(ddof=0).shift(1).to_numpy()
    yr = np.where(ts < 1767225600, "2025", "2026")
    for tanim, up, dn in (("BVC", np.nan_to_num((z15 >= 3) & (imb >= 0.15)).astype(bool), np.nan_to_num((z15 <= -3) & (imb <= -0.15)).astype(bool)), ("z15", np.nan_to_num(z15 >= 3).astype(bool), np.nan_to_num(z15 <= -3).astype(bool))):
        dnAgo = (t - 1) - son_ind(dn); upAgo = (t - 1) - son_ind(up)
        newDn = dn & (dnAgo >= 15)
        ix = np.flatnonzero(newDn & (t >= 3000) & (t < n - 16))
        for h in (5, 15):
            rows.append(pd.DataFrame({"tanim": tanim, "sym": s, "h": h, "yil": yr[ix], "gun": ts[ix] // 86400, "ix": ix, "kayip": (lc[ix + h] - lc[ix]) * 1e4}))
        two = (upAgo < 15) & (dnAgo < 15) & (t >= 3000) & np.isfinite(x)
        for y in ("2025", "2026"):
            m = two & (yr == y)
            tw.append({"tanim": tanim, "yil": y, "s": x[m].sum(), "n": int(m.sum())})
D = pd.concat(rows)
print("SHORT kovalama, L=0 (ilk sert satis mumunun kapanisi), ortalama kayip bp (gun kumelenmis t)")
for (tanim, h, y), g in D.groupby(["tanim", "h", "yil"]):
    m = g.kayip.mean(); psi = (g.kayip - m).groupby(g.gun).sum(); se = np.sqrt((psi ** 2).sum()) / len(g)
    print(f"  {tanim:4s} {h:2d} dk {y}: {m:+.2f} (t {m / se:.2f}) n {len(g)}")
print("\nJaccard (SHORT olay kumeleri, h=5 satirlari)")
for y in ("2025", "2026"):
    a = set(map(tuple, D[(D.tanim == "BVC") & (D.h == 5) & (D.yil == y)][["sym", "ix"]].to_numpy()))
    b = set(map(tuple, D[(D.tanim == "z15") & (D.h == 5) & (D.yil == y)][["sym", "ix"]].to_numpy()))
    print(f"  {y}: {len(a & b) / len(a | b) * 100:.2f}% (BVC {len(a)}, z15 {len(b)})")
T = pd.DataFrame(tw).groupby(["tanim", "yil"]).sum()
print("\nIki yonde sert akis, x normal")
for (tanim, y), r_ in T.iterrows():
    print(f"  {tanim:4s} {y}: {r_.s / r_.n / BASE[y]:.3f} (n {int(r_.n)})")
