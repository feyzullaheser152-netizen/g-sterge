import pickle, numpy as np, pandas as pd
f = pickle.load(open("feat_btc.pkl", "rb"))
c, h, l, o, v = f["c"], f["h"], f["l"], f["o"], f["v"]; n = len(c)
ts = pd.read_csv("../data_btc/btc_latest.csv", usecols=["timestamp"])["timestamp"].to_numpy()
cut = np.searchsorted(ts, pd.Timestamp("2026-01-01", tz="UTC").timestamp())
def fwd(hz):
    out = np.full(n, np.nan); out[:-hz] = np.log(c[hz:] / c[:-hz]) * 1e4; return out
F = {hz: fwd(hz) for hz in (30, 60, 120, 240, 480)}
def thin(mask, gap=60):
    idx = np.flatnonzero(mask); keep = []; last = -10**9
    for i in idx:
        if i - last >= gap: keep.append(i); last = i
    m = np.zeros(n, bool); m[keep] = True; return m
def report(name, mask, sign):
    mask = thin(mask)
    rows = []
    for part, rng in (("2025", slice(0, cut)), ("2026", slice(cut, n))):
        m = np.zeros(n, bool); m[rng] = mask[rng]; k = m.sum()
        cells = []
        for hz in (30, 60, 120, 240, 480):
            x = F[hz][m] * (sign[m] if isinstance(sign, np.ndarray) else sign); x = x[~np.isnan(x)]
            t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else 0
            cells.append(f"{hz}:{x.mean():+6.1f}({t:+.1f})")
        rows.append(f"{part} n={k:4d} " + " ".join(cells))
    print(f"{name:40s}\n   " + "\n   ".join(rows))
s = pd.Series(c)
r1 = np.log(s / s.shift(1))
rv60 = r1.rolling(60).std().to_numpy()
pct = pd.Series(rv60).rolling(60 * 24 * 14, min_periods=5000).rank(pct=True).to_numpy()
hi60 = pd.Series(h).rolling(60).max().shift(1).to_numpy(); lo60 = pd.Series(l).rolling(60).min().shift(1).to_numpy()
squeeze = np.roll(pct, 1) <= 0.10
print("Olaylar arası en az 60 dk; parantez içi t-değeri. Getiri işlem yönünde, baz puan.\n")
report("Sıkışma (oynaklık %10 dilim) sonrası 60dk tepe kırılımı LONG", squeeze & (c > hi60), 1)
report("Sıkışma sonrası 60dk dip kırılımı SHORT", squeeze & (c < lo60), -1)
atr = f["atr"]; vma = f["volMa"]
big = (h - l) > 5 * np.roll(atr, 1)
report("Dev mum (>5 ATR) yükseliş -> DÖNÜŞ (short)", big & (c > o), -1)
report("Dev mum (>5 ATR) düşüş -> DÖNÜŞ (long)", big & (c < o), 1)
c1h = s.iloc[::1]
ema1h = pd.Series(c).ewm(span=60 * 50, adjust=False).mean().to_numpy()
mom24 = np.full(n, np.nan); mom24[1440:] = np.log(c[1440:] / c[:-1440])
up = (c > ema1h) & (mom24 > 0); dn = (c < ema1h) & (mom24 < 0)
report("Saatlik trend: fiyat>EMA50(1s) ve 24s getiri>0 -> LONG", up & (f["minute"] == 0), 1)
report("Saatlik trend: fiyat<EMA50(1s) ve 24s getiri<0 -> SHORT", dn & (f["minute"] == 0), -1)
report("Tüm saat başları LONG (taban çizgisi)", f["minute"] == 0, 1)
