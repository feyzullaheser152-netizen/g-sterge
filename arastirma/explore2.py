import pickle, numpy as np, pandas as pd
from sim import DEFAULT, precompute
f = pickle.load(open("feat_btc.pkl", "rb"))
c, h, l = f["c"], f["h"], f["l"]; n = len(c)
ts = pd.read_csv("../data_btc/btc_latest.csv", usecols=["timestamp"])["timestamp"].to_numpy()
cut = np.searchsorted(ts, pd.Timestamp("2026-01-01", tz="UTC").timestamp())
def fwd(hz):
    out = np.full(n, np.nan); out[:-hz] = np.log(c[hz:] / c[:-hz]) * 1e4; return out
F = {hz: fwd(hz) for hz in (15, 30, 60, 120, 240)}
def report(name, mask, sign):
    rows = []
    for part, rng in (("2025", slice(0, cut)), ("2026", slice(cut, n))):
        m = np.zeros(n, bool); m[rng] = mask[rng]; k = m.sum()
        s = " ".join(f"{hz}:{np.nanmean(F[hz][m]*sign[m] if hasattr(sign,'__len__') else F[hz][m]*sign):+6.1f}" for hz in (15, 30, 60, 120, 240)) if k else ""
        rows.append(f"{part} n={k:5d} {s}")
    print(f"{name:48s} | " + " || ".join(rows))
g = precompute(f, dict(DEFAULT))
print("Süpürme olayları (seviye geri alındı), dönüş yönünde ileri getiri (bp):")
report("Süpürme LONG (dip süpürüldü)", g["sValidL"], 1)
report("Süpürme SHORT (tepe süpürüldü)", g["sValidS"], -1)
report("Süpürme LONG, üst ZD yukarı", g["sValidL"] & g["htfUp"], 1)
report("Süpürme LONG, üst ZD aşağı", g["sValidL"] & g["htfDn"], 1)
report("Süpürme SHORT, üst ZD aşağı", g["sValidS"] & g["htfDn"], -1)
report("Süpürme SHORT, üst ZD yukarı", g["sValidS"] & g["htfUp"], -1)
# Kirilim: onceki gun yuksek/dusuk ilk kez kapanisla gecildi
pdh, pdl = f["pdh"], f["pdl"]
brkU = (c > pdh) & (np.roll(c, 1) <= np.roll(pdh, 1)) & (f["lowF"] < pdh)
brkD = (c < pdl) & (np.roll(c, 1) >= np.roll(pdl, 1)) & (f["highF"] > pdl)
report("Önceki gün tepesi kapanışla kırıldı (long)", brkU, 1)
report("Önceki gün dibi kapanışla kırıldı (short)", brkD, -1)
rh, rl = f["rngHi"], f["rngLo"]
report("4 saatlik tepe kapanışla kırıldı (long)", (c > rh) & (np.roll(c,1) <= np.roll(rh,1)), 1)
report("4 saatlik dip kapanışla kırıldı (short)", (c < rl) & (np.roll(c,1) >= np.roll(rl,1)), -1)
print("\nSaate göre 60 dk ileri getiri (bp, yalnızca saat başı mum):")
hr = f["hour"]; mn = f["minute"]
for H in range(24):
    m = (hr == H) & (mn == 0)
    a = np.nanmean(F[60][:cut][m[:cut]]); b = np.nanmean(F[60][cut:][m[cut:]])
    sa = np.nanstd(F[60][:cut][m[:cut]]) / np.sqrt(m[:cut].sum()); sb = np.nanstd(F[60][cut:][m[cut:]]) / np.sqrt(m[cut:].sum())
    print(f"{H:02d}:00 UTC  2025 {a:+6.1f} (t {a/sa:+.1f})   2026 {b:+6.1f} (t {b/sb:+.1f})")
