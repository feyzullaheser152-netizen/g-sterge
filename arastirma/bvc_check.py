import sys, glob, os, numpy as np, pandas as pd
sys.argv = ["x", "../data_bn/npz"]
exec(open("events_bn.py").read().split("def main():")[0])
rows = []
for s in sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(SRC, "*.npz"))):
    z = load(s); F = feats(z); c, v = z["c"], z["v"]
    dp = np.r_[np.nan, np.diff(c)]
    sd = pd.Series(dp).rolling(100).std().to_numpy()
    buy = 1 / (1 + np.exp(-1.702 * np.nan_to_num(dp / sd)))
    sv = v * (2 * buy - 1)
    bimb = roll_sum(sv, 15) / roll_sum(v, 15)
    real = F["imb15"]
    ok = np.isfinite(bimb) & np.isfinite(real)
    corr = np.corrcoef(bimb[ok], real[ok])[0, 1]
    zz = F["z15"]
    for name, im in (("gerçek delta", real), ("BVC tahmini", bimb)):
        m = np.isfinite(zz) & (np.abs(zz) >= 3) & (im * np.sign(zz) >= 0.15)
        for i in thin(np.nan_to_num(m).astype(bool), 30):
            sg = -np.sign(zz[i])
            rows.append(dict(sym=s, kind=name, part="2025" if F["ts"][i] < CUT else "2026", f5=F["fwd"][5][i] * sg, f15=F["fwd"][15][i] * sg, corr=corr))
R = pd.DataFrame(rows)
print("BVC ile gerçek 15 dk dengesizlik korelasyonu (parite ortalaması):", round(R.groupby("sym")["corr"].first().mean(), 2))
print(R.groupby(["kind", "part"])[["f5", "f15"]].agg(["mean", "count"]).round(1).to_string())
