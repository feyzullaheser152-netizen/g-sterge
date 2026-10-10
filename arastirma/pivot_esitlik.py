"""Duyarlilik: pivot esitlik kurali (Ekim 2026 Pine denetimi; BULGULAR 17).

Testlerdeki topluluk_sinyal.pivot: solda esit deger pivotu iptal eder, sagda etmez. Ucuncu taraf kaynaklara gore (LuxAlgo/PineTS PR #322,
TradingView ciktisindan alinmis test) TradingView ta.pivothigh/pivotlow tersini uygular: solda esitlik serbest, sagda esitlik pivotu iptal eder.
VSP v6.4.1'den itibaren Pine'da testteki kurali birebir uygulayan kendi pivot fonksiyonunu kullanir; bu betik yalnizca bilgi icindir (karar degistirmez):
Trend cizgisi kirilimi ve uyumsuzluk, secilmis ayarlarla (piyasa, k 1, R 2, H 30), iki kuralla 2025 / 2026 brut bp ve t.
Kullanim: VSP_VERI=<klasor> python3 arastirma/pivot_esitlik.py
"""
import os, sys, math
from multiprocessing import Pool
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
import katki_testi as K1
import katki_testi2 as K2
import k3_seviye
from topluluk_sinyal import sma, ema, highest, lowest, pivot


@njit(cache=True)
def pivot_tv(src, L, R, high):
    """TradingView kurali (ucuncu taraf kaynaga gore): solda yalnizca kesin ustun deger, sagda esit deger de pivotu iptal eder."""
    n = len(src)
    out = np.full(n, np.nan)
    for i in range(L + R, n):
        p = i - R
        v = src[p]
        ok = True
        for k in range(1, L + 1):
            if (high and src[p - k] > v) or ((not high) and src[p - k] < v):
                ok = False
                break
        if ok:
            for k in range(1, R + 1):
                if (high and src[p + k] >= v) or ((not high) and src[p + k] <= v):
                    ok = False
                    break
        if ok:
            out[i] = v
    return out


def parite(s):
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    o, h, l, c, v = (np.ascontiguousarray(x, dtype=np.float64) for x in (o, h, l, c, v))
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    gec = (t >= 5000) & (t < n - TS.NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
    yil = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    sh = lambda x, k: np.r_[np.full(k, np.nan), x[:-k]]
    rsi14 = K1.rsi(c, 14)
    macd = ema(c, 12) - ema(c, 26)
    hist = macd - ema(macd, 9)
    rng = highest(h, 14) - lowest(l, 14)
    stk = sma(100 * (c - lowest(l, 14)) / np.where(rng > 0, rng, np.nan), 3)
    obv = np.cumsum(np.sign(np.r_[0, np.diff(c)]) * v)
    sv12, sv26, sv21 = sma(v, 12), sma(v, 26), sma(v, 21)
    vwm = sma(c * v, 12) / np.where(sv12 > 0, sv12, np.nan) - sma(c * v, 26) / np.where(sv26 > 0, sv26, np.nan)
    cmfm = ((c - l) - (h - c)) / np.where(h - l > 0, h - l, np.nan)
    cmf = sma(np.nan_to_num(cmfm) * v, 21) / np.where(sv21 > 0, sv21, np.nan)
    M = np.ascontiguousarray(np.column_stack([macd, hist, rsi14, stk, K1.cci(c, 10), c - sh(c, 10), obv, vwm, cmf, K2.mfi(h, l, c, v, 14)]))
    rows = []
    for kural, pf in (("test (sol kesin)", pivot), ("TradingView (sag kesin)", pivot_tv)):
        tl_al, tl_sat, _ = k3_seviye._tl(c, pf(h, 20, 20, True), pf(l, 20, 20, False), 20, 3, 3)
        pos, neg = K2.divergences(M, c, pf(c, 5, 5, True), pf(c, 5, 5, False), 5, 10, 100)
        pa, na_ = pos > 0, neg > 0
        div = (pa & ~np.r_[False, pa[:-1]] & ~na_, na_ & ~np.r_[False, na_[:-1]] & ~pa)
        for ad, (al, sat) in (("Trend çizgisi kırılımı", (tl_al, tl_sat)), ("Uyumsuzluk", div)):
            ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
            y = np.where(al[ix], 1, -1).astype(np.int64)
            oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ix, y, sigall[ix], engel[ix], 1.0, 2.0, 30, False, 0.0, 0.0, 0.0, False)
            rows.append(pd.DataFrame({"kural": kural, "sinyal": ad, "sym": s, "yil": yil[oi], "gun": ts[oi] // 86400, "yon": oy, "brut": ob * 1e4, "R": orr}))
    print(s, "tamam", flush=True)
    return pd.concat(rows)


def kume_t(x, gun):
    m = x.mean()
    psi = (x - m).groupby(gun).sum()
    se = math.sqrt((psi ** 2).sum()) / len(x)
    return m, m / se


def main():
    with Pool(4) as p:
        D = pd.concat(p.map(parite, izleme.SYMS), ignore_index=True)
    out = []
    for (kural, ad, yl), d in D.groupby(["kural", "sinyal", "yil"]):
        mb, tb = kume_t(d.brut, d.gun)
        mr, tr_ = kume_t(d.R, d.gun)
        out.append(dict(sinyal=ad, kural=kural, yil=yl, n=len(d), brut_bp=mb, R=mr, t=tr_, AL_bp=d.brut[d.yon > 0].mean(), SAT_bp=d.brut[d.yon < 0].mean()))
    pd.set_option("display.width", 200)
    print(pd.DataFrame(out).round(3).to_string())


if __name__ == "__main__":
    main()
