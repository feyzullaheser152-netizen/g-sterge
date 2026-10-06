"""coin_vs_market.pkl uzerinde dayaniklilik: %1-%99 winsorize ortalama, medyan, isabet orani, en kalabalik 10 gun haric."""
import numpy as np, pandas as pd
df = pd.read_pickle("coin_vs_market.pkl")
CLS = ["piyasa geneli", "karisik", "coine ozel"]
def wins(x):
    x = x[np.isfinite(x)]
    lo, hi = np.percentile(x, [1, 99])
    return np.clip(x, lo, hi)
def tw(x):
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
for dname in ("gercek", "bvc"):
    D = df[df.delta == dname]
    print("=" * 20, dname, "=" * 20)
    for pre, lab in (("f", "ham"), ("h", "hedge")):
        print(f"-- {lab}: winsorize ort (t) / medyan / isabet% --")
        for part in ("2025", "2026"):
            P = D[D.part == part]
            for cl in CLS:
                g = P[P.cls == cl]
                cells = []
                for hz in (5, 15, 30):
                    x = g[f"{pre}{hz}"].to_numpy(float); x = x[np.isfinite(x)]
                    # winsorize sinirlari yilin tum olaylarindan (sinif bagimsiz)
                    allx = P[f"{pre}{hz}"].to_numpy(float); allx = allx[np.isfinite(allx)]
                    lo, hi = np.percentile(allx, [1, 99]); w = np.clip(x, lo, hi)
                    cells.append(f"{hz}dk {w.mean():+5.2f}(t{tw(w):+4.1f}) md{np.median(x):+5.2f} %{(x > 0).mean() * 100:4.1f}")
                print(f"{part} {cl:14s} n={len(g):5d} | " + " | ".join(cells))
    print("-- En kalabalik 10 gun (olay sayisina gore) cikarilinca 15 dk ham / hedge ortalama --")
    for part in ("2025", "2026"):
        P = D[D.part == part]
        top = P.day.value_counts().index[:10]
        Q = P[~P.day.isin(top)]
        print(part, "cikarilan olay:", int(P.day.isin(top).sum()), "|", " | ".join(f"{cl}: n={len(Q[Q.cls == cl])} ham {Q[Q.cls == cl].f15.mean():+.2f} hedge {Q[Q.cls == cl].h15.mean():+.2f}" for cl in CLS))
    print("-- Sinif paylari --")
    print(D.groupby(["part", "cls"]).size().unstack().round(0).to_string())
    print()
E = pd.read_pickle("btc_burst.pkl")
print("== BTC patlamasi: winsorize ort / medyan (olay ortalamalari) ==")
for dname in ("gercek", "bvc"):
    for part in ("2025", "2026"):
        g = E[(E.delta == dname) & (E.part == part)]
        cells = []
        for hz in (5, 15, 30):
            x = g[f"alt{hz}"].to_numpy(float); w = wins(x)
            h = g[f"ah{hz}"].to_numpy(float); hw = wins(h)
            cells.append(f"{hz}dk alt {w.mean():+5.2f}(t{tw(w):+4.1f}) md{np.median(x[np.isfinite(x)]):+5.2f} hedge {hw.mean():+5.2f}(t{tw(hw):+4.1f})")
        print(f"{dname:6s} {part} n={len(g)} | " + " | ".join(cells))
