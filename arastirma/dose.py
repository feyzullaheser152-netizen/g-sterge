import sys, glob, os, numpy as np, pandas as pd
sys.argv = ["x", "../data_bn/npz"]
exec(open("events_bn.py").read().split("def main():")[0])
syms = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(SRC, "*.npz")))
rows = []
for s in syms:
    F = feats(load(s))
    z, im = F["z15"], F["imb15"]
    ok = np.isfinite(z) & np.isfinite(im) & (np.abs(z) >= 2)
    idx = thin(ok, 15)
    for i in idx:
        sg = -np.sign(z[i])
        rows.append(dict(sym=s, part="2025" if F["ts"][i] < CUT else "2026", az=abs(z[i]), aim=im[i] * np.sign(z[i]), rv=F["rvol5"][i],
                         f5=F["fwd"][5][i] * sg, f15=F["fwd"][15][i] * sg, f30=F["fwd"][30][i] * sg, f60=F["fwd"][60][i] * sg))
df = pd.DataFrame(rows)
df.to_pickle("dose.pkl")
df["zb"] = pd.cut(df.az, [2, 3, 4, 5, 100], right=False, labels=["z2-3", "z3-4", "z4-5", "z5+"])
df["ib"] = pd.cut(df.aim, [-9, 0, 0.15, 0.3, 0.5, 9], labels=["akış ters", "0-.15", ".15-.3", ".3-.5", ".5+"])
for part in ("2025", "2026"):
    print(f"\n{part}: 15 dk ileri getiri (dönüş yönü, bp) | n")
    g = df[df.part == part]
    tab = g.pivot_table(index="zb", columns="ib", values="f15", aggfunc="mean", observed=False).round(1)
    cnt = g.pivot_table(index="zb", columns="ib", values="f15", aggfunc="count", observed=False)
    print(tab.astype(str) + " | " + cnt.astype(str))
