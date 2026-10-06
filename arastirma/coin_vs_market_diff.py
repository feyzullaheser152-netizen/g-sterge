"""Winsorize (%1-%99, yil bazinda) fark testi: coine ozel - piyasa geneli; gune gore kumelenmis t; parite bazinda tutarlilik."""
import numpy as np, pandas as pd
df = pd.read_pickle("coin_vs_market.pkl")
for dname in ("gercek", "bvc"):
    for part in ("2025", "2026"):
        P = df[(df.delta == dname) & (df.part == part)].copy()
        out = []
        for pre in ("f", "h"):
            for hz in (5, 15, 30):
                col = f"{pre}{hz}"
                x = P[col].to_numpy(float); ok = np.isfinite(x)
                lo, hi = np.percentile(x[ok], [1, 99]); P["w"] = np.clip(x, lo, hi)
                a = P[(P.cls == "coine ozel")].dropna(subset=[col]); b = P[(P.cls == "piyasa geneli")].dropna(subset=[col])
                # regresyon w ~ 1 + D(coine ozel), yalniz iki sinif, gune gore kumelenmis SE
                Q = pd.concat([a, b]); y = Q.w.to_numpy(); d = (Q.cls == "coine ozel").to_numpy(float)
                X = np.c_[np.ones(len(y)), d]; XtX = np.linalg.inv(X.T @ X); beta = XtX @ X.T @ y; e = y - X @ beta
                S = pd.DataFrame(X * e[:, None]).groupby(Q.day.to_numpy()).sum().to_numpy(); G = len(S)
                V = XtX @ (S.T @ S) @ XtX * G / (G - 1)
                # parite bazinda: coine ozel ort > piyasa geneli ort olan parite orani
                pa = a.groupby("sym").w.mean(); pb = b.groupby("sym").w.mean(); com = pa.index.intersection(pb.index)
                out.append(f"{'ham' if pre == 'f' else 'hdg'}{hz}: {beta[1]:+5.2f} (tG{beta[1] / np.sqrt(V[1, 1]):+4.1f}, parite%{(pa[com] > pb[com]).mean() * 100:3.0f})")
        print(dname, part, " | ".join(out))
