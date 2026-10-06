import pickle, numpy as np, pandas as pd
f = pickle.load(open("feat_btc.pkl", "rb"))
c, h, l, o, v = f["c"], f["h"], f["l"], f["o"], f["v"]
n = len(c)
ts = pd.read_csv("../data_btc/btc_latest.csv", usecols=["timestamp"])["timestamp"].to_numpy()
cut = np.searchsorted(ts, pd.Timestamp("2026-01-01", tz="UTC").timestamp())
def fwd(hz):
    out = np.full(n, np.nan); out[:-hz] = np.log(c[hz:] / c[:-hz]) * 1e4; return out  # baz puan
F = {hz: fwd(hz) for hz in (5, 15, 30, 60, 120)}
def past(k):
    out = np.full(n, np.nan); out[k:] = np.log(c[k:] / c[:-k]) * 1e4; return out
P15 = past(15)
def report(name, mask, sign=1):
    rows = []
    for part, rng in (("2025", slice(0, cut)), ("2026", slice(cut, n))):
        m = np.zeros(n, bool); m[rng] = mask[rng]
        k = m.sum()
        s = " ".join(f"{hz}dk:{np.nanmean(F[hz][m])*sign:+5.1f}" for hz in (5, 15, 30, 60, 120)) if k else ""
        rows.append(f"{part} n={k:6d} {s}")
    print(f"{name:55s} | " + " || ".join(rows))
print("İleri getiri, baz puan (1 bp = %0,01). Maliyet ~8-13 bp gidiş-dönüş.\n")
atrbp = f["atr"] / c * 1e4
print("Ortalama 1 dk ATR (bp):", np.nanmean(atrbp).round(1), " | 15 dk ortalama mutlak hareket (bp):", np.nanmean(np.abs(F[15])).round(1))
# 1) 15 dk ters donus: buyuk 15 dk hareketlerden sonra
z = f["z15"]
for thr in (1.5, 2.0, 2.5, 3.0):
    report(f"15dk z >= {thr} sonrası (short yönünde getiri)", z >= thr, -1)
    report(f"15dk z <= -{thr} sonrası (long yönünde getiri)", z <= -thr, 1)
# 2) VWAP sapmasi
dev = (c - f["vwap"]) / f["vwap"] * 1e4
band = (f["vwapU"] - f["vwap"]) / 2
for k in (1.5, 2.0, 2.5):
    report(f"VWAP +{k} sigma üstü (short yönü)", c > f["vwap"] + k * band, -1)
    report(f"VWAP -{k} sigma altı (long yönü)", c < f["vwap"] - k * band, 1)
