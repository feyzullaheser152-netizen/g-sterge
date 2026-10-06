import glob, os, numpy as np, pandas as pd
SRC = "../data_bn/npz"; CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
from numpy.lib.stride_tricks import sliding_window_view as swv
rows = []; hits = []
for f in sorted(glob.glob(f"{SRC}/*.npz"))[::2]:   # 11 parite
    s = os.path.basename(f)[:-4]; z = np.load(f)
    c, h, l, ts = z["c"], z["h"], z["l"], z["ts"]
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    vS = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    s1 = np.sqrt(vS)
    idx = np.arange(2000, len(c) - 121, 11)
    part = np.where(ts[idx] < CUT, "2025", "2026")
    LH = np.log(swv(h, 120)[idx + 1] / c[idx][:, None]); LL = np.log(swv(l, 120)[idx + 1] / c[idx][:, None])
    for N in (5, 15, 30):
        sg = s1[idx] * np.sqrt(N)
        for k in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            hl = (LL[:, :N] <= -k * sg[:, None]).any(1); hs = (LH[:, :N] >= k * sg[:, None]).any(1)
            hits.append(pd.DataFrame({"N": N, "k": k, "part": np.r_[part, part], "hit": np.r_[hl, hs].astype(float)}))
    sg = s1[idx] * np.sqrt(15)
    for slk in (1.0, 2.0):
        for R in (1.0, 1.5, 2.0, 3.0):
            sl = slk * sg; tp = R * sl
            iS = np.where((LL <= -sl[:, None]).any(1), (LL <= -sl[:, None]).argmax(1), 999)
            iT = np.where((LH >= tp[:, None]).any(1), (LH >= tp[:, None]).argmax(1), 999)
            done = (iS < 999) | (iT < 999)
            win = (iT < iS)
            rows.append(pd.DataFrame({"slk": slk, "R": R, "part": part, "win": win[done].astype(float) if False else np.where(done, win, np.nan)}))
H = pd.concat(hits); B = pd.concat(rows)
print("Stopun vurulma oranı (%), öngörülen σ×√N biriminde mesafe k; N = süre (dk)")
print((H.groupby(["N", "k", "part"]).hit.mean().unstack() * 100).round(1).unstack(0).to_string())
print("\nRastgele girişte hedefin stoptan önce gelme oranı (%) | kenarsız teorik 1/(1+R)")
T = (B.groupby(["slk", "R", "part"]).win.mean().unstack() * 100).round(1)
T["teorik"] = [round(100 / (1 + R), 1) for _, R in T.index]
print(T.to_string())
