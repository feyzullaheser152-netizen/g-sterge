"""Bagimsiz dogrulama, asama 1: her parite icin dakika bazinda olculer.
ET donusumu elle (ABD kurali: Mart 2. Pazar 02:00 yerel -> Kasim 1. Pazar 02:00 yerel), zoneinfo ile capraz kontrol.
Olculer (hepsi yalnizca onceki mumlarla normalize):
  xa: |r1| / sqrt(EWMA_1440(r1^2))[t-1]                (analizdeki tanimin bagimsiz yeniden yazimi)
  xb: |r1| / rolling_std_1440(r1)[t-1]                  (Pine sd1, bir mum geciktirilmis)
  xc: |r1| / ort(|r1|, onceki 10080 mum)                (haftalik taban: 'tipik bir hafta dakikasina gore')
Cikti: parite basina feather benzeri npz (ts, etmin, etdow, etday, xa, xb, xc)."""
import os, sys
import numpy as np, pandas as pd
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
OUT = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/dogrula/feat"
SYMS = "BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT AVAXUSDT LINKUSDT LTCUSDT DOTUSDT NEARUSDT SUIUSDT AAVEUSDT UNIUSDT ENAUSDT 1000PEPEUSDT WIFUSDT ARBUSDT OPUSDT ZECUSDT HYPEUSDT".split()


def us_dst_bounds(year):
    # 2. Pazar Mart 02:00 EST = 07:00 UTC ; 1. Pazar Kasim 02:00 EDT = 06:00 UTC
    d = datetime(year, 3, 1, tzinfo=timezone.utc)
    first_sun = d + timedelta(days=(6 - d.weekday()) % 7)
    start = first_sun + timedelta(days=7, hours=7)
    d = datetime(year, 11, 1, tzinfo=timezone.utc)
    first_sun = d + timedelta(days=(6 - d.weekday()) % 7)
    end = first_sun + timedelta(hours=6)
    return int(start.timestamp()), int(end.timestamp())


def et_offset(ts):
    off = np.full(len(ts), -5 * 3600, dtype=np.int64)
    for y in range(2024, 2028):
        s, e = us_dst_bounds(y)
        off[(ts >= s) & (ts < e)] = -4 * 3600
    return off


def roll_mean_prev(a, n):
    c = np.cumsum(np.insert(np.nan_to_num(a), 0, 0.0))
    cnt = np.cumsum(np.insert(np.isfinite(a).astype(float), 0, 0.0))
    out = np.full(len(a), np.nan)
    # t icin ortalama a[t-n .. t-1]
    s = c[n:-1] - c[:-n - 1]; k = cnt[n:-1] - cnt[:-n - 1]
    out[n:] = s / np.maximum(k, 1)
    return out


def run(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts = z["ts"].astype(np.int64); c = z["c"].astype(float)
    gaps = np.unique(np.diff(ts))
    off = et_offset(ts)
    # zoneinfo capraz kontrol (orneklem)
    ny = ZoneInfo("America/New_York")
    idx = np.linspace(0, len(ts) - 1, 4000).astype(int)
    idx = np.unique(np.concatenate([idx, np.flatnonzero(np.diff(off) != 0), np.flatnonzero(np.diff(off) != 0) + 1]))
    bad = 0
    for i in idx:
        o = datetime.fromtimestamp(int(ts[i]), tz=timezone.utc).astimezone(ny).utcoffset().total_seconds()
        bad += int(o != off[i])
    lt = ts + off
    etmin = ((lt // 60) % 1440).astype(np.int16)
    etday = (lt // 86400).astype(np.int32)
    etdow = ((etday + 3) % 7).astype(np.int8)  # 0=Pzt
    r1 = np.full(len(c), np.nan); r1[1:] = np.diff(np.log(c))
    a = np.abs(r1)
    # EWMA (adjust=False) elle: v_t = (1-al) v_{t-1} + al r_t^2 ; sigma_prev[t] = sqrt(v_{t-1})
    al = 2.0 / (1440 + 1)
    r2 = np.nan_to_num(r1 * r1)
    v = pd.Series(r2).ewm(alpha=al, adjust=False).mean().to_numpy()
    sa = np.full(len(c), np.nan); sa[1:] = np.sqrt(v[:-1]); sa[:2881] = np.nan
    # rolling std 1440 (Pine stdev: populasyon std), bir mum geciktirilmis
    s = pd.Series(r1)
    sd = s.rolling(1440).std(ddof=0).to_numpy()
    sb = np.full(len(c), np.nan); sb[1:] = sd[:-1]
    # haftalik |r1| tabani
    sc = roll_mean_prev(a, 10080)
    sc[:10080] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        xa = a / sa; xb = a / sb; xc = a / sc
    for x in (xa, xb, xc):
        x[~np.isfinite(x)] = np.nan
    np.savez(os.path.join(OUT, f"{sym}.npz"), ts=ts, etmin=etmin, etday=etday, etdow=etdow, xa=xa.astype(np.float32), xb=xb.astype(np.float32), xc=xc.astype(np.float32), off=off.astype(np.int32))
    return sym, len(ts), gaps.tolist()[:5], bad, len(idx)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    from multiprocessing import Pool
    with Pool(6) as p:
        for r in p.imap_unordered(run, SYMS):
            print(r, flush=True)
