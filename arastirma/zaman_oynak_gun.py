"""Test 2 asama 1b: secili dakikalarda gun bazinda normalize hareket (x) ve gunun ortalama x'i.
Iki saat sistemi: yerel tarih ve dakika (UTC / America/New_York). Cikti: zaman_oynak_gun.pkl"""
import os, pickle
import numpy as np, pandas as pd
from multiprocessing import Pool
from zaman_oynak import SRC, SYMS

OUT = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/zaman_oynak_gun.pkl"
SEL = {
    "et": ["08:28", "08:29", "08:30", "08:31", "08:32", "08:33", "08:35", "09:28", "09:29", "09:30", "09:31", "09:32", "09:33", "09:35", "09:44", "09:45", "09:46", "09:58", "09:59", "10:00", "10:01", "10:02", "10:03", "10:05", "10:29", "10:30", "10:31", "13:58", "13:59", "14:00", "14:01", "14:02", "14:03", "14:05", "14:29", "14:30", "14:31", "14:32", "14:35", "15:59", "16:00", "16:01", "16:02", "17:59", "18:00", "18:01", "18:02", "18:03"],
    "utc": ["23:58", "23:59", "00:00", "00:01", "00:02", "00:03", "07:59", "08:00", "08:01", "08:02", "15:59", "16:00", "16:01", "16:02", "21:59", "22:00", "22:01", "22:02", "12:29", "12:30", "12:31", "13:29", "13:30", "13:31", "19:59", "20:00", "20:01"],
}


def tomin(s):
    a, b = s.split(":")
    return int(a) * 60 + int(b)


def run(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, h, l, c = z["ts"], z["h"], z["l"], z["c"]
    lc = np.log(c)
    r1 = np.concatenate([[np.nan], np.diff(lc)])
    ew = pd.Series(r1 * r1).ewm(span=1440, adjust=False, min_periods=1440).mean().to_numpy()
    sig = np.concatenate([[np.nan], np.sqrt(ew[:-1])])
    ok = np.isfinite(sig) & (sig > 0) & np.isfinite(r1)
    ok[:1440] = False
    x = np.where(ok, np.abs(r1) / np.where(ok, sig, 1), np.nan)
    xr = np.where(ok, ((h - l) / c) / np.where(ok, sig, 1), np.nan)
    t = pd.DatetimeIndex(pd.to_datetime(ts, unit="s", utc=True))
    loc = t.tz_convert("America/New_York").tz_localize(None)
    off = ((loc - t.tz_localize(None)).total_seconds()).to_numpy().astype(np.int64)
    res = {}
    for sysn, tt in (("utc", ts), ("et", ts + off)):
        day = tt // 86400
        mnt = (tt // 60) % 1440
        df = pd.DataFrame({"day": day, "m": mnt, "x": x, "xr": xr})
        dm = df.groupby("day")[["x", "xr"]].mean()
        dn = df.groupby("day")["x"].count()
        sel = [tomin(s) for s in SEL[sysn]]
        sub = df[df.m.isin(sel)]
        px = sub.pivot(index="day", columns="m", values="x")
        pr = sub.pivot(index="day", columns="m", values="xr")
        res[sysn] = {"dm": dm, "dn": dn, "px": px, "pr": pr}
    return sym, res


if __name__ == "__main__":
    with Pool(4) as p:
        out = dict(p.map(run, SYMS))
    pickle.dump(out, open(OUT, "wb"))
    print("tamam")
