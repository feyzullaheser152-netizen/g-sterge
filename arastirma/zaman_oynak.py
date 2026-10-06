"""Test 2: Gun ici zamanlanmis oynaklik dakikalari (UTC ve America/New_York).
Asama 1: her parite icin normalize 1 dk hareket x = |r1| / sigma_prev ve aralik xr = (h-l)/c / sigma_prev.
sigma_prev: r1^2'nin EWMA ortalamasi (span 1440), bir mum geciktirilmis (yalnizca onceki mumlar).
Toplamlar anahtar = (yil, ABD yaz saati, haftanin gunu, dakika) bazinda iki saat sisteminde biriktirilir.
Cikti: zaman_oynak.pkl"""
import os, sys, pickle
import numpy as np, pandas as pd
from multiprocessing import Pool

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
OUT = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/zaman_oynak.pkl"
SYMS = "BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT AVAXUSDT LINKUSDT LTCUSDT DOTUSDT NEARUSDT SUIUSDT AAVEUSDT UNIUSDT ENAUSDT 1000PEPEUSDT WIFUSDT ARBUSDT OPUSDT ZECUSDT HYPEUSDT".split()
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
NK = 2 * 2 * 7 * 1440


def run(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, h, l, c = z["ts"], z["h"], z["l"], z["c"]
    lc = np.log(c)
    r1 = np.concatenate([[np.nan], np.diff(lc)])
    ew = pd.Series(r1 * r1).ewm(span=1440, adjust=False, min_periods=1440).mean().to_numpy()
    sig = np.concatenate([[np.nan], np.sqrt(ew[:-1])])  # yalnizca t-1'e kadarki getiriler
    ok = np.isfinite(sig) & (sig > 0) & np.isfinite(r1)
    ok[:1440] = False  # isinma
    x = np.abs(r1) / np.where(ok, sig, np.nan)
    xr = ((h - l) / c) / np.where(ok, sig, np.nan)
    yi = (ts >= CUT).astype(np.int64)
    # ABD saati
    t = pd.DatetimeIndex(pd.to_datetime(ts, unit="s", utc=True))
    loc = t.tz_convert("America/New_York").tz_localize(None)
    off = ((loc - t.tz_localize(None)).total_seconds()).to_numpy().astype(np.int64)
    dst = (off == -4 * 3600).astype(np.int64)
    lts = ts + off
    res = {"sym": sym, "n": int(ok.sum())}
    q = {}
    for y in (0, 1):
        m = ok & (yi == y)
        q[y] = (np.nanquantile(x[m], 0.90), np.nanquantile(xr[m], 0.90), np.nanquantile(x[m], 0.999), np.nanquantile(xr[m], 0.999))
    res["q"] = q
    q90x = np.where(yi == 0, q[0][0], q[1][0]); q90r = np.where(yi == 0, q[0][1], q[1][1])
    capx = np.where(yi == 0, q[0][2], q[1][2]); capr = np.where(yi == 0, q[0][3], q[1][3])
    xs = np.where(ok, x, 0.0); xrs = np.where(ok, xr, 0.0)
    xc = np.minimum(xs, capx); xrc = np.minimum(xrs, capr)
    hx = (ok & (x > q90x)).astype(float); hr = (ok & (xr > q90r)).astype(float)
    for sysn, tt in (("utc", ts), ("et", lts)):
        mnt = (tt // 60) % 1440
        dow = ((tt // 86400) + 3) % 7  # Pazartesi = 0
        key = ((yi * 2 + dst) * 7 + dow) * 1440 + mnt
        kk = key[ok]
        d = {}
        d["cnt"] = np.bincount(kk, minlength=NK)
        d["sx"] = np.bincount(kk, weights=xs[ok], minlength=NK)
        d["sxc"] = np.bincount(kk, weights=xc[ok], minlength=NK)
        d["sr"] = np.bincount(kk, weights=xrs[ok], minlength=NK)
        d["src"] = np.bincount(kk, weights=xrc[ok], minlength=NK)
        d["hx"] = np.bincount(kk, weights=hx[ok], minlength=NK)
        d["hr"] = np.bincount(kk, weights=hr[ok], minlength=NK)
        # medyan: (yil, hafta ici/sonu, dakika)
        wk = (dow >= 5).astype(np.int64)
        gk = (yi * 2 + wk) * 1440 + mnt
        df = pd.DataFrame({"g": gk[ok], "x": x[ok], "xr": xr[ok]})
        med = df.groupby("g").median()
        mx = np.full(2 * 2 * 1440, np.nan); mr = np.full(2 * 2 * 1440, np.nan)
        mx[med.index.to_numpy()] = med["x"].to_numpy(); mr[med.index.to_numpy()] = med["xr"].to_numpy()
        d["medx"] = mx; d["medr"] = mr
        res[sysn] = d
    return res


if __name__ == "__main__":
    with Pool(4) as p:
        out = p.map(run, SYMS)
    pickle.dump({r["sym"]: r for r in out}, open(OUT, "wb"))
    print("tamam", [(r["sym"], r["n"]) for r in out])
