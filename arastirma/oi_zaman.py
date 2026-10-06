"""OI kaydinin zaman damgasi testi: create_time T'deki OI degisimi (T-5 -> T), hangi 5 dakikalik penceredeki fiyat hareketi ve hacimle ilgili?
Pencere k: [T + 5k, T + 5k + 5) dakikadaki mumlar (k=-1: T'den onceki 5 dk, k=0: T'den sonraki 5 dk)."""
import sys
sys.argv = ["x"]
import numpy as np, pandas as pd
exec(open("oi_vol.py").read().split("def main")[0])
out = []
for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"):
    k = np.load(f"{SRC}/npz/{s}.npz")
    idx = pd.to_datetime(k["ts"], unit="s")
    c = pd.Series(k["c"], index=idx); v = pd.Series(k["v"], index=idx)
    r = np.log(c).diff()
    # 5 dk pencereler: etiket = pencere baslangici
    absr5 = (r * r).resample("5min", label="left", closed="left").sum() ** 0.5
    vol5 = v.resample("5min", label="left", closed="left").sum()
    oi = np.log(load_oi(s))
    doi = (oi - oi.shift(1)).abs()
    row = {"sym": s}
    for kk in (-2, -1, 0, 1, 2):
        a = absr5.shift(-kk).reindex(doi.index); b = vol5.shift(-kk).reindex(doi.index)
        m = doi.notna() & a.notna() & b.notna()
        row[f"rv k={kk}"] = np.corrcoef(doi[m].rank(), a[m].rank())[0, 1]
        row[f"hacim k={kk}"] = np.corrcoef(doi[m].rank(), b[m].rank())[0, 1]
    out.append(row)
print("Spearman korelasyon: |ΔOI(T-5→T)| ile [T+5k, T+5k+5) penceresi")
print(pd.DataFrame(out).set_index("sym").round(3).T.to_string())
