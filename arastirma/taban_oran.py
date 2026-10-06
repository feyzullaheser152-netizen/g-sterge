"""Normal dakika tabani: tum mumlarda ortalama |r1| / sigma_base (sigma_base = onceki 1440 mumun r1 std'si, bir mum gecikmeli).
Kalin kuyruklar yuzunden bu oran normal zamanda 1 degil ~0,7-0,8'dir; 'x kat normal' ifadeleri bu tabana bolunerek hesaplanir."""
import glob
import numpy as np, pandas as pd
SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
S = {"2025": [0.0, 0], "2026": [0.0, 0]}
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    z = np.load(f); ts, c = z["ts"], z["c"]
    r = np.r_[np.nan, np.diff(np.log(c))]
    x = np.abs(r) / pd.Series(r).rolling(1440).std(ddof=0).shift(1).to_numpy()
    x[:3000] = np.nan
    for y, m in (("2025", ts < 1767225600), ("2026", ts >= 1767225600)):
        v = x[m]; v = v[np.isfinite(v)]; S[y][0] += v.sum(); S[y][1] += len(v)
for y, (s, n) in S.items():
    print(y, "ortalama |r1|/sigma_base:", round(s / n, 3), "n:", n)
