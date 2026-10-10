"""Aylik izleme: Gostergedeki sinyallerin brut sonucu (izleme.py rapor tarafindan cagrilir).

Sinyaller ve ayarlari, eklendikleri testteki secilmis ayarlarla aynidir (komisyon sifir, BULGULAR 14b, 15, 16):
  VSP AL / VSP SAT : v6.1 sinyali, piyasa girisi, stop 2 sigma15, hedef 2R, en fazla 5 mum (olay engeli uygulanmis).
  SMA20 donusu     : CM Ultimate MA, SMA20 yonu donunce; piyasa, k 1, R 2, H 15. v6.4.2'den beri gostergede ayrica gorunmuyor (SMA20 destek/direnc rengiyle
                     ciziliyor); izlenenler listesinde, son 12 ayda brut > 0 ve t >= 3 olursa yeniden gorunume alinmasi dusunulur.
  SMA20 kesisimi   : mum SMA20'yi icinde keser (acilis bir yanda, kapanis diger yanda); piyasa, k 1, R 2, H 15.
  Uyumsuzluk       : Divergence for Many Indicators v4 (10 gosterge); piyasa, k 1, R 2, H 30.
  Trend cizgisi    : Trend Lines v2 cizgi kirilimi (k3_seviye.tlb2; BULGULAR 17); piyasa, k 1, R 2, H 30. Ayrica SAT oku ayri izlenir.
Izlenen aday (gostergede yok; BULGULAR 17, 7. katman): yapisal stop (son 10 mumun dibi/tepesi - 0,1 sigma15) ile 2 sigma15 stopun R farki, VSP olaylarinda.
  Son 12 tam ayda >= +0,01 R ve t >= 3 olursa on kayitli testle yeniden sinanir.
Durum kurali (ON KAYIT, sonuclardan once yazildi; son 12 tam ay, gun kumelenmis t):
  VSP AL ve VSP SAT: brut >= +1 bp ve t >= 2 TUTUYOR; brut > 0 ZAYIFLADI; brut <= 0 BOZULDU.
  SMA20 donusu, SMA20 kesisimi, Uyumsuzluk, Trend cizgisi (ve SAT oku): brut > 0 ve t >= 2 TUTUYOR; brut > 0 ZAYIFLADI; brut <= 0 BOZULDU.
"""
import os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
import katki_testi as K1
import katki_testi2 as K2
import k3_seviye
import katki_testi3 as K3
from topluluk_sinyal import sma, ema, highest, lowest, pivot

SINYALLER = [("VSP AL", 1.0), ("VSP SAT", 1.0), ("SMA20 kesişimi", 0.0), ("Uyumsuzluk", 0.0), ("Trend çizgisi kırılımı", 0.0), ("Trend çizgisi SAT oku", 0.0)]


def _sh(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


def parite(s):
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    gec = (t >= 4000) & (t < n - TS.NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
    ay = np.asarray(pd.to_datetime(ts, unit="s", utc=True).strftime("%Y-%m"))
    out = []

    def ekle(ad, oi, oy, ob):
        out.append(pd.DataFrame({"ay": ay[oi], "gun": ts[oi] // 86400, "sym": s, "sinyal": ad, "brut": ob * 1e4}))

    # VSP v6.1
    E = sinyal_v6.olaylar(s)
    ixv = np.searchsorted(ts, E["ts"])
    m = ixv >= 4000
    ixv, yv, sgv = ixv[m], E["yon"][m].astype(np.int64), E["sig"][m]
    oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ixv, yv, sgv, np.zeros(len(ixv), bool), 2.0, 2.0, 5, False, 0.0, 0.0, 0.0, False)
    ekle("VSP AL", oi[oy > 0], oy[oy > 0], ob[oy > 0])
    ekle("VSP SAT", oi[oy < 0], oy[oy < 0], ob[oy < 0])
    # izlenen aday: yapisal stop (katki_testi3 7. katman ile ayni)
    m2 = ixv < n - 40
    i2, y2, s2 = ixv[m2], yv[m2], sgv[m2]
    ent = o[i2 + 1]
    dd = np.where(y2 > 0, np.log(ent / (TS.lowest(l, 10)[i2] * np.exp(-0.1 * s2))), np.log(TS.highest(h, 10)[i2] * np.exp(0.1 * s2) / ent))
    _, r_t = K3.stop_varyant(o, h, l, c, i2, y2, s2, 2.0 * s2)
    _, r_y = K3.stop_varyant(o, h, l, c, i2, y2, s2, np.where(np.isfinite(dd), dd, np.nan))
    out.append(pd.DataFrame({"ay": ay[i2], "gun": ts[i2] // 86400, "sym": s, "sinyal": "Yapısal stop R farkı", "brut": r_y - r_t}))
    # SMA20 (katki_testi CMT, CMC)
    s20 = sma(c, 20)
    mup = np.nan_to_num(s20 >= _sh(s20, 2)).astype(bool)
    mup1 = np.r_[False, mup[:-1]]
    cmt = (mup & ~mup1, ~mup & mup1)
    cmc = (np.nan_to_num((o < s20) & (c > s20)).astype(bool), np.nan_to_num((o > s20) & (c < s20)).astype(bool))
    # Uyumsuzluk (katki_testi2 DIV)
    rsi14 = K1.rsi(c, 14)
    macd = ema(c, 12) - ema(c, 26)
    hist = macd - ema(macd, 9)
    rng = highest(h, 14) - lowest(l, 14)
    stk = sma(100 * (c - lowest(l, 14)) / np.where(rng > 0, rng, np.nan), 3)
    cci10 = K1.cci(c, 10)
    mom = c - _sh(c, 10)
    obv = np.cumsum(np.sign(np.r_[0, np.diff(c)]) * v)
    sv12, sv26, sv21 = sma(v, 12), sma(v, 26), sma(v, 21)
    vwm = sma(c * v, 12) / np.where(sv12 > 0, sv12, np.nan) - sma(c * v, 26) / np.where(sv26 > 0, sv26, np.nan)
    cmfm = ((c - l) - (h - c)) / np.where(h - l > 0, h - l, np.nan)
    cmf = sma(np.nan_to_num(cmfm) * v, 21) / np.where(sv21 > 0, sv21, np.nan)
    M = np.column_stack([macd, hist, rsi14, stk, cci10, mom, obv, vwm, cmf, K2.mfi(h, l, c, v, 14)])
    pos, neg = K2.divergences(np.ascontiguousarray(M), c, pivot(c, 5, 5, True), pivot(c, 5, 5, False), 5, 10, 100)
    pa, na_ = pos > 0, neg > 0
    div = (pa & ~np.r_[False, pa[:-1]] & ~na_, na_ & ~np.r_[False, na_[:-1]] & ~pa)
    tl_al, tl_sat, _ = k3_seviye.tlb2(np.ascontiguousarray(h, dtype=np.float64), np.ascontiguousarray(l, dtype=np.float64), np.ascontiguousarray(c, dtype=np.float64))
    for ad, (al, sat), H in (("SMA20 dönüşü", cmt, 15), ("SMA20 kesişimi", cmc, 15), ("Uyumsuzluk", div, 30), ("Trend çizgisi kırılımı", (tl_al, tl_sat), 30)):
        ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
        y = np.where(al[ix], 1, -1).astype(np.int64)
        oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ix, y, sigall[ix], engel[ix], 1.0, 2.0, H, False, 0.0, 0.0, 0.0, False)
        ekle(ad, oi, oy, ob)
        if ad == "Trend çizgisi kırılımı":
            ekle("Trend çizgisi SAT oku", oi[oy < 0], oy[oy < 0], ob[oy < 0])
    print("tamam (sinyal)", s, file=sys.stderr, flush=True)
    return pd.concat(out)


def hesapla():
    syms = [s for s in izleme.SYMS if os.path.exists(os.path.join(izleme.NPZ, f"{s}.npz"))]
    with Pool(min(4, os.cpu_count() or 1)) as p:
        return pd.concat(p.map(parite, syms))


def kume_t(x, gun):
    if len(x) < 2:
        return np.nan, np.nan
    m = x.mean()
    psi = (x - m).groupby(gun).sum()
    se = np.sqrt((psi ** 2).sum()) / len(x)
    return m, (m / se if se > 0 else np.nan)


def durum(m, tt, esik):
    if not np.isfinite(m):
        return "veri yok"
    if m >= esik and m > 0 and np.isfinite(tt) and tt >= 2:
        return "TUTUYOR"
    return "ZAYIFLADI" if m > 0 else "BOZULDU"
