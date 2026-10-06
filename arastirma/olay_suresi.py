"""Zamanlanmis olaylarin suresi: olay dakikasindan itibaren dakika dakika ortalama |r1| / sigma_base (22 parite, 2025 / 2026).
sigma_base: onceki 1440 mumun r1 standart sapmasi (bir mum gecikmeli). Olaylar: FOMC 14:00 ET (yalnizca FOMC gunleri),
Pazar 18:00 ET, NY acilisi 09:30 ET (is gunleri), ABD verisi 08:30 ET (Sal-Cum). Kontrol: ayni dakikalar diger gunlerde."""
import glob, os
import numpy as np, pandas as pd

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
FOMC = {"2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"}
OFF = np.arange(-5, 61)
acc = {}
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    z = np.load(f)
    ts, c = z["ts"], z["c"]
    r = np.r_[np.nan, np.diff(np.log(c))]
    sb = pd.Series(r).rolling(1440).std(ddof=0).shift(1).to_numpy()
    x = np.abs(r) / sb
    t = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    mins = (t.hour * 60 + t.minute).to_numpy(); dow = t.dayofweek.to_numpy(); d = np.asarray(t.strftime("%Y-%m-%d"))
    yr = np.where(ts < 1767225600, "2025", "2026")
    ev = {"FOMC 14:00": (mins == 840) & np.isin(d, list(FOMC)), "Pazar 18:00": (mins == 1080) & (dow == 6), "NY açılışı 09:30": (mins == 570) & (dow < 5), "ABD verisi 08:30": (mins == 510) & (dow >= 1) & (dow <= 4)}
    for nm, m in ev.items():
        for i in np.flatnonzero(m):
            if i < 3000 or i + OFF[-1] >= len(c):
                continue
            k = (nm, yr[i]); a = acc.setdefault(k, [np.zeros(len(OFF)), 0])
            a[0] += np.nan_to_num(x[i + OFF]); a[1] += 1
rows = {}
for (nm, y), (s, n) in sorted(acc.items()):
    rows[(nm, y)] = pd.Series(s / n, index=OFF)
P = pd.DataFrame(rows)
print("Olay dakikasina gore ortalama |r1| / sigma_base (0 = olay dakikasi)")
print(P.loc[[-2, -1, 0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 29, 30, 31, 35, 40, 45, 50, 55, 60]].round(2).to_string())
print("\nOlaydan sonra oranin >= 1,5 kaldigi son dakika (ardisik) ve n")
for k in P.columns:
    s = P[k].loc[0:]; last = 0
    for o, v in s.items():
        if v >= 1.5: last = o
        else: break
    print(k, "son dk:", last, "n:", acc[k][1])
