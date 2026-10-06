import glob, os, numpy as np, pandas as pd
from scipy.stats import norm
SRC = "../data_bn/npz"; CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
N = 15
rows = []; hitrows = []
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]; z = np.load(f)
    c, h, l, ts = z["c"], z["h"], z["l"], z["ts"]
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    r2 = pd.Series(r * r)
    vS = r2.ewm(span=30, adjust=False).mean().to_numpy()      # kisa (30 dk)
    vL = r2.ewm(span=1440, adjust=False).mean().to_numpy()    # uzun (1 gun)
    # mevsimsellik: saat-ici ortalama r^2, onceki gunlerden EWMA (ileriye bakma yok)
    t = pd.to_datetime(ts, unit="s", utc=True); hr = t.hour.to_numpy(); day = t.floor("D")
    hd = pd.DataFrame({"d": day, "h": hr, "r2": r * r}).groupby(["d", "h"]).r2.mean().unstack()
    seas = hd.ewm(span=20).mean().shift(1)            # her saat icin onceki 20 gunun EWMA'si
    seas = seas.div(seas.mean(axis=1), axis=0)        # gun ortalamasina oran
    sf = seas.stack().reindex(pd.MultiIndex.from_arrays([day, hr])).to_numpy()
    sf = np.where(np.isfinite(sf), sf, 1.0)
    models = {
        "A kısa EWMA": vS,
        "C karışım (HAR benzeri)": 0.5 * vS + 0.5 * vL,
        "D karışım + saat etkisi": 0.5 * vS + 0.5 * vL * sf,
    }
    fwd = np.r_[lc[N:] - lc[:-N], np.full(N, np.nan)]
    # ilk-gecis: sonraki N mumda en dusuk / en yuksek
    lowN = pd.Series(l[::-1]).rolling(N, min_periods=N).min().to_numpy()[::-1]
    highN = pd.Series(h[::-1]).rolling(N, min_periods=N).max().to_numpy()[::-1]
    lowN = np.r_[lowN[1:], np.nan]; highN = np.r_[highN[1:], np.nan]
    idx = np.arange(2000, len(c) - N - 1, 7)  # ornekleme
    part = np.where(ts[idx] < CUT, "2025", "2026")
    for name, v in models.items():
        sig = np.sqrt(v[idx] * N)
        x = np.abs(fwd[idx]) / sig
        rows.append(pd.DataFrame({"sym": s, "model": name, "part": part, "x": x, "lr": np.log(np.abs(fwd[idx]) + 1e-9), "lf": np.log(sig)}))
    sig = np.sqrt((0.5 * vS + 0.5 * vL * sf)[idx] * N)
    for k in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        hitL = np.log(lowN[idx] / c[idx]) <= -k * sig
        hitS = np.log(highN[idx] / c[idx]) >= k * sig
        hitrows.append(pd.DataFrame({"sym": s, "part": np.r_[part, part], "k": k, "hit": np.r_[hitL, hitS].astype(float)}))
R = pd.concat(rows); H = pd.concat(hitrows)
print(f"15 dk ileri |getiri| / öngörülen σ (ideal normal dağılım: %50 dilim 0.674, %80 dilim 1.282)")
for (m, p), g in R.groupby(["model", "part"]):
    x = g.x.dropna()
    ok = np.isfinite(g.lr) & np.isfinite(g.lf)
    corr = np.corrcoef(g.lr[ok], g.lf[ok])[0, 1]
    print(f"{m:26s} {p}: %50 dilim {x.quantile(.5):.3f} | %80 dilim {x.quantile(.8):.3f} | %95 dilim {x.quantile(.95):.3f} | log korelasyon {corr:.3f}")
print("\nStopun 15 dk içinde vurulma oranı (gerçek) ve Brown hareketi tahmini 2(1-Φ(k)):")
T = H.groupby(["k", "part"]).hit.mean().unstack()
T["Brown tahmini"] = [2 * (1 - norm.cdf(k)) for k in T.index]
print((T * 100).round(1).to_string())
sp = H[H.part == "2026"].groupby(["k", "sym"]).hit.mean().unstack(0)
print("\n2026 parite bazında vurulma oranı aralığı (%): ")
print((sp.quantile([0.1, 0.5, 0.9]) * 100).round(1).to_string())
