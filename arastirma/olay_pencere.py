"""Zamanlanmis olaylarin DURUM penceresi (v5.6): olay dakikasina gore -10..+65 dk, dakika basina 'x normal'.
x = |r1| / sigma_base (onceki 1440 mumun std'si, bir mum gecikmeli); x normal = dakika ortalamasi / yilin kosulsuz ortalamasi
(2025: 0,725, 2026: 0,701; taban_oran.py). Kural: sari = iki yilda da >= 1,5; kirmizi = iki yilda da >= 3.
Olaylar: ABD verisi 08:30 ET (Sal-Cum, federal tatil haric degil; veri takvimi bilinmiyor), NY acilisi 09:30 ET (Pzt-Cum),
ABD verisi 10:00 ET, Pazar 18:00 ET, FOMC 14:00 ET (14 gun)."""
import glob
import numpy as np, pandas as pd

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
BASE = {"2025": 0.725, "2026": 0.701}
FOMC = {"2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"}
OFF = np.arange(-10, 66)
acc = {}
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    z = np.load(f)
    ts, c = z["ts"], z["c"]
    r = np.r_[np.nan, np.diff(np.log(c))]
    x = np.abs(r) / pd.Series(r).rolling(1440).std(ddof=0).shift(1).to_numpy()
    t = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    mins = (t.hour * 60 + t.minute).to_numpy(); dow = t.dayofweek.to_numpy(); d = np.asarray(t.strftime("%Y-%m-%d"))
    yr = np.where(ts < 1767225600, "2025", "2026")
    fom = np.isin(d, list(FOMC))
    ev = {"ABD verisi 08:30": (mins == 510) & (dow >= 1) & (dow <= 4) & ~fom, "NY açılışı 09:30": (mins == 570) & (dow < 5), "ABD verisi 10:00": (mins == 600) & (dow < 5), "Pazar 18:00": (mins == 1080) & (dow == 6), "FOMC 14:00": (mins == 840) & fom}
    for nm, m in ev.items():
        for i in np.flatnonzero(m):
            if i < 3000 or i + OFF[-1] >= len(c):
                continue
            a = acc.setdefault((nm, yr[i]), [np.zeros(len(OFF)), np.zeros(len(OFF)), 0])
            v = x[i + OFF]; ok = np.isfinite(v)
            a[0] += np.where(ok, v, 0); a[1] += ok; a[2] += 1
R = pd.DataFrame({k: pd.Series(s / n / BASE[k[1]], index=OFF) for k, (s, n, _) in acc.items()})
pd.set_option("display.width", 250)
print("Dakika basina x normal (satir: olay dakikasina gore ofset)")
print(R.round(2).to_string())
print("\nPencere ozeti (iki yilin minimumu):")
for nm in sorted({k[0] for k in acc}):
    mn = R[[(nm, "2025"), (nm, "2026")]].min(axis=1)
    def run(th, start):
        lo = hi = None
        for o in range(start, OFF[-1] + 1):
            if mn.loc[o] >= th:
                lo = o if lo is None else lo; hi = o
            elif lo is not None:
                break
        return lo, hi
    pre = [o for o in range(-10, 0) if mn.loc[o] >= 1.5]
    print(f"{nm}: n={acc[(nm,'2025')][2]}/{acc[(nm,'2026')][2]} | >=1,5 ardisik (0'dan): {run(1.5, 0)} | >=3 ardisik: {run(3.0, 0)} | olay oncesi >=1,5 dk: {pre}")
for nm, (a, b) in (("NY açılışı 09:30", (0, 59)), ("FOMC 14:00", (0, 44)), ("FOMC 14:00", (5, 44)), ("FOMC 14:00", (-5, -1)), ("Pazar 18:00", (0, 5)), ("ABD verisi 08:30", (0, 1))):
    print(f"{nm} ortalama [{a},{b}]:", R.loc[a:b, [(nm, '2025'), (nm, '2026')]].mean().round(2).to_dict())
