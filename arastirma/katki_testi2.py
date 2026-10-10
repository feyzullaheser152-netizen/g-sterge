"""Katki testi, ikinci grup ve tum katmanlar (1 dk; 22 Binance USDT-M paritesi; 2025 kesif / 2026 dogrulama).

Kullanici: "1 dakikalik grafikte gorulmesi gereken tum katmanlarda tum kodlari ele al; karar vermek icin gorulmesi gereken her seyi gor."
Komisyon sifir (kullanici karari, BULGULAR 14b). Makas dahil degil. Gosterge kodlari kopyalanmadi; mantiklar spesifikasyon olarak okunup bastan yazildi.

Yeni gostergeler (varsayilan girdiler):
  CDL  Candlestick Patterns Identified [repo32]: yukselis formasyonlari (harami, yutan, piercing, belt, kicker, sabah yildizi) AL; dusus (harami, yutan,
       kicker, asili adam, aksam yildizi, kayan yildiz) SAT; doji, cekic, ters cekic durum. (Fitil oranlarindaki 0.001 sabiti koddaki gibi.)
  FBB  Fibonacci Bollinger Bands (200, hlc3, 3): alt bandi (-1) asagi kesince AL, ust bandi yukari kesince SAT.
  SMBC Smart Money Breakout Channels [AlgoAlpha] (100, 14, guclu kapanis): kanal kirilimi yukari AL, asagi SAT.
  BPRB Breakout Probability [Zeiierman]: onceki mum rengine gore yeni tepe / yeni dip sikligi (kayan 5000 mum); egilim durum olarak.
  MLST Machine Learning Adaptive SuperTrend [AlgoAlpha] (10, 3, 100; k-ortalamalar): yon donusu AL/SAT. (Bos kume: onceki ortalama korunur.)
  ICT  ICT Concepts [LuxAlgo]: MSS (zigzag 5) AL/SAT; displacement, hacim dengesizligi (VI), FVG durum; Londra acilis/kapanis killzone durum.
  DIV  Divergence for Many Indicators v4 [LonesomeTheBlue] (5, kapanis, normal uyumsuzluk, 10 gosterge): ilk pozitif uyumsuzluk AL, negatif SAT.
  BSL  Buyside & Sellside Liquidity [LuxAlgo] (7, 6.9): likidite seviyesi asilinca; BSLR donus (alim tarafi asildi SAT), BSLC devam (alim tarafi asildi AL).
  STAI SuperTrend AI (Clustering) [LuxAlgo] (10, 1-5 adim 0,5, 10; en iyi kume): yon donusu AL/SAT.
  OBB  Order Blocks & Breaker Blocks [LuxAlgo] (10): aktif OB bolgesine ilk donus AL/SAT; OBBK breaker bolgesine ilk donus (boga breaker SAT, ayi breaker AL).
  SLG  CM SlingShot System (EMA 38/62): muhafazakar giris AL/SAT; trend ve geri cekilme durum.
  Birinci gruptaki tum durumlar (katki_testi.py) filtre, yon ve cikis katmanlarinda yeniden kullanilir.

ON KAYIT (sonuclardan once yazildi):
 1) Sinyal: yeni adaylar katki_testi.py A ile ayni (izgara 54, komisyon 0, olay engeli acik). Basari: 2025 R > 0, t >= 2; 2026 R > 0, t >= 3.
 2) Filtre: VSP AL/SAT islemlerinde (v6.1 varsayilanlari) durum dogru/uyumlu olanlarin brutu eksi digerleri. Kabul: iki yilda ayni isaret, |fark| >= 1 bp,
    2025 |t| >= 2, 2026 |t| >= 3, kapsam %20-80.
 3) Oynaklik bilgisi: sonraki 15 dk gerceklesen oynaklikta EWMA'ya ek R2 artisi iki yilda >= 0,005.
 4) Yon bilgisi: yonlu durum +1 iken -1'e gore sonraki 15 dk getiri farki (bp; her 15. mum). Kabul: iki yilda ayni isaret, |fark| >= 1 bp, 2025 |t| >= 2, 2026 |t| >= 3.
 5) Seviyeler: bolge/seviye gostergelerinin dokunus sinyalleri (LQS, OBF, OBD, OBB, OBBK, FBB, NWE, BSL, SRC, HVH, KZ) 1. katmanda sinanir.
 6) Cikis: VSP AL/SAT olaylarinin hepsi (ust uste binme serbest, eslestirilmis karsilastirma). Temel: mevcut cikis (stop 2 sigma, hedef 2R, 5 dk).
    Alternatif: ayni stop, hedef yok, gosterge isleme karsi donunce sonraki acilista cik, en fazla 30 mum. Gostergeler: Supertrend, UT Bot, SuperTrend AI,
    ML Adaptive SuperTrend, SMA20 yonu, SlingShot trendi, Lorentzian cekirdek egimi. Ayrica "yalnizca 30 mum sabit" referansi.
    Kabul: alternatif - temel (ayni islemler) iki yilda >= +0,5 bp ve 2026 t >= 3.
Kullanim: VSP_VERI=<klasor> python3 arastirma/katki_testi2.py
"""
import math, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
import katki_testi as K1
from topluluk_sinyal import rma, ema, sma, stdev, highest, lowest, cross_up, cross_dn, true_range, pivot

KS, RS, HS = sinyal_v6.KS, sinyal_v6.RS, sinyal_v6.HS
YENI = ["CDL", "FBB", "SMBC", "MLST", "ICT", "DIV", "BSLR", "BSLC", "STAI", "OBB", "OBBK", "SLG"]


def sh(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


# ------------------------------------------------------------------ gostergeler
def candles(o, h, l, c):
    o1, c1, h1, l1 = sh(o, 1), sh(c, 1), sh(h, 1), sh(l, 1)
    o2, c2, h2 = sh(o, 2), sh(c, 2), sh(h, 2)
    o5 = sh(o, 5)
    b = np.abs(o - c)
    rg = h - l
    f = lambda x: np.nan_to_num(x).astype(bool)
    bearH = f((c1 > o1) & (o > c) & (o <= c1) & (o1 <= c) & ((o - c) < (c1 - o1)) & (o5 < o))
    bullH = f((o1 > c1) & (c > o) & (c <= o1) & (c1 <= o) & ((c - o) < (o1 - c1)) & (o5 > o))
    bearE = f((c1 > o1) & (o > c) & (o >= c1) & (o1 >= c) & ((o - c) > (c1 - o1)) & (o5 < o))
    bullE = f((o1 > c1) & (c > o) & (c >= o1) & (c1 >= o) & ((c - o) > (o1 - c1)) & (o5 > o))
    pierc = f((c1 < o1) & (o < l1) & (c > c1 + (o1 - c1) / 2) & (c < o1) & (o5 > o))
    low10 = sh(lowest(l, 10), 1)
    belt = f((l == o) & (o < low10) & (o < c) & (c > (h1 - l1) / 2 + l1) & (o5 > o))
    bullK = f((o1 > c1) & (o >= o1) & (c > o) & (o5 > o))
    bearK = f((o1 < c1) & (o <= o1) & (c <= o) & (o5 < o))
    hang = f((rg > 4 * b) & ((c - l) / (0.001 + rg) >= 0.75) & ((o - l) / (0.001 + rg) >= 0.75) & (o5 < o) & (h1 < o) & (h2 < o))
    eve = f((c2 > o2) & (np.minimum(o1, c1) > c2) & (o < np.minimum(o1, c1)) & (c < o))
    morn = f((c2 < o2) & (np.maximum(o1, c1) < c2) & (o > np.maximum(o1, c1)) & (c > o))
    shoot = f((o1 < c1) & (o > c1) & (h - np.maximum(o, c) >= b * 3) & (np.minimum(c, o) - l <= b))
    hammer = f((rg > 3 * b) & ((c - l) / (0.001 + rg) > 0.6) & ((o - l) / (0.001 + rg) > 0.6))
    inv = f((rg > 3 * b) & ((h - c) / (0.001 + rg) > 0.6) & ((h - o) / (0.001 + rg) > 0.6))
    doji = b <= rg * 0.05
    bull = bullH | bullE | pierc | belt | bullK | morn
    bear = bearH | bearE | bearK | hang | eve | shoot
    return bull, bear, doji, hammer, inv


@njit(cache=True)
def smbc(o, h, l, c, upper, lower, dur, hh, ll):
    n = len(c)
    M = 20
    bt = np.zeros(M)
    bb = np.zeros(M)
    nb = 0
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    inch = np.zeros(n, np.bool_)
    for i in range(1, n):
        if upper[i] > lower[i] and upper[i - 1] <= lower[i - 1] and dur[i] > 10:
            ok = True
            for j in range(nb):
                if hh[i] > bb[j] and ll[i] < bt[j]:
                    ok = False
                    break
            if ok and nb < M:
                for j in range(nb, 0, -1):
                    bt[j] = bt[j - 1]
                    bb[j] = bb[j - 1]
                bt[0] = hh[i]
                bb[0] = ll[i]
                nb += 1
        mid = (c[i] + o[i]) / 2
        j = 0
        while j < nb:
            if mid > bt[j]:
                al[i] = True
                for m in range(j, nb - 1):
                    bt[m] = bt[m + 1]
                    bb[m] = bb[m + 1]
                nb -= 1
            elif mid < bb[j]:
                sat[i] = True
                for m in range(j, nb - 1):
                    bt[m] = bt[m + 1]
                    bb[m] = bb[m + 1]
                nb -= 1
            else:
                inch[i] = True
                j += 1
    return al, sat, inch


def bars_since(mask):
    idx = np.where(mask, np.arange(len(mask)), -1)
    last = np.maximum.accumulate(idx)
    return np.where(last >= 0, np.arange(len(mask)) - last, -1)


@njit(cache=True)
def _hb(x, n, hi):
    N = len(x)
    out = np.full(N, np.nan)
    for t in range(n - 1, N):
        best = x[t]
        off = 0
        ok = not math.isnan(best)
        for k in range(1, n):
            v = x[t - k]
            if math.isnan(v):
                ok = False
                break
            if (hi and v > best) or ((not hi) and v < best):
                best = v
                off = -k
        if ok:
            out[t] = off
    return out


@njit(cache=True)
def _roll_ext(x, w, hi):
    N = len(x)
    out = np.empty(N)
    for t in range(N):
        a = max(0, t - w + 1)
        b = x[a]
        for k in range(a + 1, t + 1):
            if (hi and x[k] > b) or ((not hi) and x[k] < b):
                b = x[k]
        out[t] = b
    return out


def smbc_all(o, h, l, c):
    ll100, hh100 = lowest(l, 100), highest(h, 100)
    npr = (c - ll100) / np.where(hh100 - ll100 > 0, hh100 - ll100, np.nan)
    vol = stdev(npr, 14)
    up = (_hb(vol, 15, True) + 14) / 14
    lo = (_hb(vol, 15, False) + 14) / 14
    xo = np.nan_to_num((lo > up) & (sh(lo, 1) <= sh(up, 1))).astype(bool)
    bs = bars_since(xo)
    dur = np.maximum(np.where(bs >= 0, bs, 0), 1)
    # ta.highest(duration): degisken uzunluk
    hh = _var_ext(h, dur, True)
    ll = _var_ext(l, dur, False)
    return smbc(o, h, l, c, np.nan_to_num(up, nan=-1.0), np.nan_to_num(lo, nan=-1.0), dur, hh, ll)


@njit(cache=True)
def _var_ext(x, L, hi):
    N = len(x)
    out = np.empty(N)
    for t in range(N):
        b = x[t]
        for k in range(1, min(L[t], t + 1)):
            v = x[t - k]
            if (hi and v > b) or ((not hi) and v < b):
                b = v
        out[t] = b
    return out


@njit(cache=True)
def bprob(o, h, l, c, W):
    """Onceki mum yesilken/kirmiziyken yeni tepe ve yeni dip sikligi (son W mum); t mumunun kapanisinda t+1 icin egilim (+1 boga, -1 ayi)."""
    n = len(c)
    gh = np.zeros(n)
    gl = np.zeros(n)
    rh = np.zeros(n)
    rl = np.zeros(n)
    gt = np.zeros(n)
    rt = np.zeros(n)
    for i in range(2, n):
        g = c[i - 1] > o[i - 1]
        r = c[i - 1] < o[i - 1]
        hh = h[i] >= h[i - 1]
        ll_ = l[i] <= l[i - 1]
        gt[i] = 1.0 if g else 0.0
        rt[i] = 1.0 if r else 0.0
        gh[i] = 1.0 if (g and hh) else 0.0
        gl[i] = 1.0 if (g and ll_) else 0.0
        rh[i] = 1.0 if (r and hh) else 0.0
        rl[i] = 1.0 if (r and ll_) else 0.0
    cg = np.cumsum(gh)
    cgl = np.cumsum(gl)
    crh = np.cumsum(rh)
    crl = np.cumsum(rl)
    bias = np.zeros(n, np.int64)
    for i in range(W, n):
        a = i - W
        g = c[i] > o[i]
        r = c[i] < o[i]
        if g:
            bias[i] = 1 if (cg[i] - cg[a]) >= (cgl[i] - cgl[a]) else -1
        elif r:
            bias[i] = 1 if (crh[i] - crh[a]) >= (crl[i] - crl[a]) else -1
    return bias


@njit(cache=True)
def kmeans_atr(atr, T, phv, pmv, plv):
    n = len(atr)
    cen = np.full(n, np.nan)
    clu = np.full(n, -1, np.int64)
    for t in range(T - 1, n):
        if not (atr[t] > 0):
            continue
        mx = atr[t]
        mn = atr[t]
        bad = False
        for k in range(T):
            v = atr[t - k]
            if math.isnan(v):
                bad = True
                break
            mx = max(mx, v)
            mn = min(mn, v)
        if bad:
            continue
        a = mn + (mx - mn) * phv
        b = mn + (mx - mn) * pmv
        cc = mn + (mx - mn) * plv
        for it in range(100):
            sa = 0.0
            na_ = 0
            sb = 0.0
            nb_ = 0
            sc = 0.0
            nc = 0
            for k in range(T):
                v = atr[t - k]
                d1 = abs(v - a)
                d2 = abs(v - b)
                d3 = abs(v - cc)
                if d1 < d2 and d1 < d3:
                    sa += v
                    na_ += 1
                if d2 < d1 and d2 < d3:
                    sb += v
                    nb_ += 1
                if d3 < d1 and d3 < d2:
                    sc += v
                    nc += 1
            a2 = sa / na_ if na_ > 0 else a
            b2 = sb / nb_ if nb_ > 0 else b
            c2 = sc / nc if nc > 0 else cc
            if a2 == a and b2 == b and c2 == cc:
                break
            a, b, cc = a2, b2, c2
        d = np.array([abs(atr[t] - a), abs(atr[t] - b), abs(atr[t] - cc)])
        j = int(np.argmin(d))
        clu[t] = j
        cen[t] = a if j == 0 else (b if j == 1 else cc)
    return cen, clu


@njit(cache=True)
def pine_supertrend(hl2, c, atr, f):
    """ta.supertrend; yon -1 = yukselis."""
    n = len(c)
    d = np.ones(n, np.int64)
    st = np.full(n, np.nan)
    pl = 0.0
    pu = 0.0
    pst = np.nan
    for i in range(n):
        ub = hl2[i] + f * atr[i]
        lb = hl2[i] - f * atr[i]
        if math.isnan(atr[i]):
            pl = 0.0
            pu = 0.0
            continue
        c1 = c[i - 1] if i > 0 else c[i]
        if not (lb > pl or c1 < pl):
            lb = pl
        if not (ub < pu or c1 > pu):
            ub = pu
        if i == 0 or math.isnan(atr[i - 1]):
            dd = 1
        elif pst == pu:
            dd = -1 if c[i] > ub else 1
        else:
            dd = 1 if c[i] < lb else -1
        s = lb if dd == -1 else ub
        d[i] = dd
        st[i] = s
        pst = s
        pl = lb
        pu = ub
    return st, d


@njit(cache=True)
def supertrend_ai(hl2, c, atr, ema_abs):
    nf = 9
    n = len(c)
    up_ = np.full(nf, hl2[0])
    lo_ = np.full(nf, hl2[0])
    out = np.full(nf, np.nan)
    perf = np.zeros(nf)
    tr_ = np.zeros(nf, np.int64)
    facs = np.array([1.0 + 0.5 * k for k in range(nf)])
    os_ = np.zeros(n, np.int64)
    pidx = np.zeros(n)
    U = hl2[0]
    L = hl2[0]
    o = 0
    tf = np.nan
    alpha = 2.0 / 11.0
    for i in range(1, n):
        if math.isnan(atr[i]):
            continue
        for k in range(nf):
            up = hl2[i] + atr[i] * facs[k]
            dn = hl2[i] - atr[i] * facs[k]
            if c[i] > up_[k]:
                tr_[k] = 1
            elif c[i] < lo_[k]:
                tr_[k] = 0
            up_[k] = min(up, up_[k]) if c[i - 1] < up_[k] else up
            lo_[k] = max(dn, lo_[k]) if c[i - 1] > lo_[k] else dn
            diff = 0.0
            if not math.isnan(out[k]):
                diff = np.sign(c[i - 1] - out[k])
            perf[k] += alpha * ((c[i] - c[i - 1]) * diff - perf[k])
            out[k] = lo_[k] if tr_[k] == 1 else up_[k]
        # k-ortalamalar (3 kume), baslangic: ceyrekler
        srt = np.sort(perf)
        cen = np.zeros(3)
        for j in range(3):
            r_ = (25.0 * (j + 1)) / 100.0 * (nf - 1)
            lo_i = int(math.floor(r_))
            hi_i = min(lo_i + 1, nf - 1)
            cen[j] = srt[lo_i] + (srt[hi_i] - srt[lo_i]) * (r_ - lo_i)
        asg = np.zeros(nf, np.int64)
        for it in range(1000):
            for k in range(nf):
                bd = 1e300
                bj = 0
                for j in range(3):
                    dd = abs(perf[k] - cen[j])
                    if dd < bd:
                        bd = dd
                        bj = j
                asg[k] = bj
            nc = cen.copy()
            for j in range(3):
                s = 0.0
                m = 0
                for k in range(nf):
                    if asg[k] == j:
                        s += perf[k]
                        m += 1
                nc[j] = s / m if m > 0 else np.nan
            same = True
            for j in range(3):
                if not (nc[j] == cen[j]):
                    same = False
            if same:
                break
            cen = nc
        s = 0.0
        m = 0
        sp = 0.0
        for k in range(nf):
            if asg[k] == 2:
                s += facs[k]
                sp += perf[k]
                m += 1
        if m > 0:
            tf = s / m
            pidx[i] = max(sp / m, 0.0) / ema_abs[i] if ema_abs[i] > 0 else 0.0
        else:
            pidx[i] = pidx[i - 1]
        if math.isnan(tf):
            continue
        up = hl2[i] + atr[i] * tf
        dn = hl2[i] - atr[i] * tf
        U = min(up, U) if c[i - 1] < U else up
        L = max(dn, L) if c[i - 1] > L else dn
        if c[i] > U:
            o = 1
        elif c[i] < L:
            o = 0
        os_[i] = o
    return os_, pidx


@njit(cache=True)
def zigzag_liq(h, l, ph, pl, atr, mar, mode_ict):
    """Zigzag (pivot sol L, sag 1). BSL: likidite seviyeleri ve asilma; ICT: MSS yonu."""
    n = len(h)
    M = 50
    d = np.zeros(M, np.int64)
    x = np.zeros(M, np.int64)
    y = np.full(M, np.nan)
    V = 3
    bt = np.full(V, np.nan)
    bb = np.full(V, np.nan)
    bl = np.full(V, -1, np.int64)
    bbr = np.ones(V, np.bool_)
    st_ = np.full(V, np.nan)
    sb_ = np.full(V, np.nan)
    sl_ = np.full(V, -1, np.int64)
    sbr = np.ones(V, np.bool_)
    buy_br = np.zeros(n, np.bool_)
    sell_br = np.zeros(n, np.bool_)
    for i in range(1, n):
        x2 = i - 1
        m = atr[i] / mar if not math.isnan(atr[i]) else np.nan
        if not math.isnan(ph[i]):
            y2 = h[i - 1]
            if d[0] < 1:
                for k in range(M - 1, 0, -1):
                    d[k] = d[k - 1]
                    x[k] = x[k - 1]
                    y[k] = y[k - 1]
                d[0] = 1
                x[0] = x2
                y[0] = y2
            elif d[0] == 1 and ph[i] > y[0]:
                x[0] = x2
                y[0] = y2
            if not mode_ict and not math.isnan(m):
                cnt = 0
                stB = 0
                stP = 0.0
                mxP = 0.0
                mnP = 1e300
                for k in range(M):
                    if d[k] == 1:
                        if y[k] > ph[i] + m:
                            break
                        elif y[k] > ph[i] - m and y[k] < ph[i] + m:
                            cnt += 1
                            stB = x[k]
                            stP = y[k]
                            mxP = max(mxP, y[k])
                            mnP = min(mnP, y[k])
                if cnt > 2:
                    if stB == bl[0]:
                        bt[0] = (mxP + mnP) / 2 + m
                        bb[0] = (mxP + mnP) / 2 - m
                    else:
                        for k in range(V - 1, 0, -1):
                            bt[k] = bt[k - 1]
                            bb[k] = bb[k - 1]
                            bl[k] = bl[k - 1]
                            bbr[k] = bbr[k - 1]
                        bt[0] = (mxP + mnP) / 2 + m
                        bb[0] = (mxP + mnP) / 2 - m
                        bl[0] = stB
                        bbr[0] = False
        if not math.isnan(pl[i]):
            y2 = l[i - 1]
            if d[0] > -1:
                for k in range(M - 1, 0, -1):
                    d[k] = d[k - 1]
                    x[k] = x[k - 1]
                    y[k] = y[k - 1]
                d[0] = -1
                x[0] = x2
                y[0] = y2
            elif d[0] == -1 and pl[i] < y[0]:
                x[0] = x2
                y[0] = y2
            if not mode_ict and not math.isnan(m):
                cnt = 0
                stB = 0
                mxP = 0.0
                mnP = 1e300
                for k in range(M):
                    if d[k] == -1:
                        if y[k] < pl[i] - m:
                            break
                        elif y[k] > pl[i] - m and y[k] < pl[i] + m:
                            cnt += 1
                            stB = x[k]
                            mxP = max(mxP, y[k])
                            mnP = min(mnP, y[k])
                if cnt > 2:
                    if stB == sl_[0]:
                        st_[0] = (mxP + mnP) / 2 + m
                        sb_[0] = (mxP + mnP) / 2 - m
                    else:
                        for k in range(V - 1, 0, -1):
                            st_[k] = st_[k - 1]
                            sb_[k] = sb_[k - 1]
                            sl_[k] = sl_[k - 1]
                            sbr[k] = sbr[k - 1]
                        st_[0] = (mxP + mnP) / 2 + m
                        sb_[0] = (mxP + mnP) / 2 - m
                        sl_[0] = stB
                        sbr[0] = False
        if not mode_ict:
            for k in range(V):
                if not bbr[k] and not math.isnan(bt[k]) and h[i] > bt[k]:
                    bbr[k] = True
                    buy_br[i] = True
                if not sbr[k] and not math.isnan(sb_[k]) and l[i] < sb_[k]:
                    sbr[k] = True
                    sell_br[i] = True
    return buy_br, sell_br


@njit(cache=True)
def ict_mss(h, l, c, ph, pl):
    n = len(c)
    M = 50
    d = np.zeros(M, np.int64)
    y = np.full(M, np.nan)
    mdir = 0
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    dirs = np.zeros(n, np.int64)
    for i in range(1, n):
        if not math.isnan(ph[i]):
            y2 = h[i - 1]
            if d[0] < 1:
                for k in range(M - 1, 0, -1):
                    d[k] = d[k - 1]
                    y[k] = y[k - 1]
                d[0] = 1
                y[0] = y2
            elif d[0] == 1 and ph[i] > y[0]:
                y[0] = y2
        if not math.isnan(pl[i]):
            y2 = l[i - 1]
            if d[0] > -1:
                for k in range(M - 1, 0, -1):
                    d[k] = d[k - 1]
                    y[k] = y[k - 1]
                d[0] = -1
                y[0] = y2
            elif d[0] == -1 and pl[i] < y[0]:
                y[0] = y2
        iH = 2 if d[2] == 1 else 1
        iL = 2 if d[2] == -1 else 1
        if (not math.isnan(y[iH])) and c[i] > y[iH] and d[iH] == 1 and mdir < 1:
            mdir = 1
            al[i] = True
        elif (not math.isnan(y[iL])) and c[i] < y[iL] and d[iL] == -1 and mdir > -1:
            mdir = -1
            sat[i] = True
        dirs[i] = mdir
    return al, sat, dirs


@njit(cache=True)
def divergences(S, c, ph, pl, prd, maxpp, maxbars):
    """LonesomeTheBlue v4, normal uyumsuzluk, kaynak kapanis, onay bekle. S: (n, k) gosterge matrisi. Cikti: pozitif ve negatif sayilar."""
    n, K = S.shape
    php = np.zeros(20, np.int64)
    phv = np.zeros(20)
    plp = np.zeros(20, np.int64)
    plv = np.zeros(20)
    pos = np.zeros(n, np.int64)
    neg = np.zeros(n, np.int64)
    for t in range(1, n):
        if not math.isnan(ph[t]):
            for k in range(19, 0, -1):
                php[k] = php[k - 1]
                phv[k] = phv[k - 1]
            php[0] = t
            phv[0] = ph[t]
        if not math.isnan(pl[t]):
            for k in range(19, 0, -1):
                plp[k] = plp[k - 1]
                plv[k] = plv[k - 1]
            plp[0] = t
            plv[0] = pl[t]
        for j in range(K):
            src = S[:, j]
            if math.isnan(src[t]) or math.isnan(src[t - 1]):
                continue
            # pozitif normal
            if src[t] > src[t - 1] or c[t] > c[t - 1]:
                for x in range(maxpp):
                    L = t - plp[x] + prd
                    if plp[x] == 0 or L > maxbars:
                        break
                    if L > 5 and t - L >= 0 and src[t - 1] > src[t - L] and c[t - 1] < plv[x]:
                        s1 = (src[t - 1] - src[t - L]) / (L - 1)
                        v1 = src[t - 1] - s1
                        s2 = (c[t - 1] - c[t - L]) / (L - 1)
                        v2 = c[t - 1] - s2
                        ok = True
                        for yy in range(2, L):
                            if src[t - yy] < v1 or c[t - yy] < v2:
                                ok = False
                                break
                            v1 -= s1
                            v2 -= s2
                        if ok:
                            pos[t] += 1
                            break
            if src[t] < src[t - 1] or c[t] < c[t - 1]:
                for x in range(maxpp):
                    L = t - php[x] + prd
                    if php[x] == 0 or L > maxbars:
                        break
                    if L > 5 and t - L >= 0 and src[t - 1] < src[t - L] and c[t - 1] > phv[x]:
                        s1 = (src[t - 1] - src[t - L]) / (L - 1)
                        v1 = src[t - 1] - s1
                        s2 = (c[t - 1] - c[t - L]) / (L - 1)
                        v2 = c[t - 1] - s2
                        ok = True
                        for yy in range(2, L):
                            if src[t - yy] > v1 or c[t - yy] > v2:
                                ok = False
                                break
                            v1 -= s1
                            v2 -= s2
                        if ok:
                            neg[t] += 1
                            break
    return pos, neg


@njit(cache=True)
def ob_breaker(o, h, l, c, L):
    """LuxAlgo Order Blocks & Breaker Blocks (fitil): aktif OB'ye ilk donus ve breaker bolgesine ilk donus."""
    n = len(c)
    M = 60
    bt = np.zeros(M)
    bb = np.zeros(M)
    bbrk = np.zeros(M, np.bool_)
    bu1 = np.zeros(M, np.bool_)
    bu2 = np.zeros(M, np.bool_)
    nb = 0
    st = np.zeros(M)
    sb = np.zeros(M)
    sbrk = np.zeros(M, np.bool_)
    su1 = np.zeros(M, np.bool_)
    su2 = np.zeros(M, np.bool_)
    ns = 0
    os_ = 0
    topy = np.nan
    topx = -1
    topc = True
    btmy = np.nan
    btmx = -1
    btmc = True
    a_ob = np.zeros(n, np.bool_)
    s_ob = np.zeros(n, np.bool_)
    a_bk = np.zeros(n, np.bool_)
    s_bk = np.zeros(n, np.bool_)
    for i in range(L, n):
        up = h[i]
        lo = l[i]
        for k in range(1, L):
            up = max(up, h[i - k])
            lo = min(lo, l[i - k])
        prev = os_
        if h[i - L] > up:
            os_ = 0
        elif l[i - L] < lo:
            os_ = 1
        if os_ == 0 and prev != 0:
            topy = h[i - L]
            topx = i - L
            topc = False
        if os_ == 1 and prev != 1:
            btmy = l[i - L]
            btmx = i - L
            btmc = False
        # boga OB
        if (not topc) and (not math.isnan(topy)) and c[i] > topy:
            topc = True
            mi = h[i - 1]
            ma = l[i - 1]
            for k in range(1, i - topx):
                if l[i - k] < mi:
                    mi = l[i - k]
                    ma = h[i - k]
                elif l[i - k] == mi:
                    ma = h[i - k]
            if nb == M:
                nb -= 1
            for k in range(nb, 0, -1):
                bt[k] = bt[k - 1]
                bb[k] = bb[k - 1]
                bbrk[k] = bbrk[k - 1]
                bu1[k] = bu1[k - 1]
                bu2[k] = bu2[k - 1]
            bt[0] = ma
            bb[0] = mi
            bbrk[0] = False
            bu1[0] = False
            bu2[0] = False
            nb += 1
        k = nb - 1
        while k >= 0:
            if not bbrk[k]:
                if min(c[i], o[i]) < bb[k]:
                    bbrk[k] = True
                elif (not bu1[k]) and l[i] <= bt[k] and l[i - 1] > bt[k]:
                    a_ob[i] = True
                    bu1[k] = True
            else:
                if c[i] > bt[k]:
                    for m in range(k, nb - 1):
                        bt[m] = bt[m + 1]
                        bb[m] = bb[m + 1]
                        bbrk[m] = bbrk[m + 1]
                        bu1[m] = bu1[m + 1]
                        bu2[m] = bu2[m + 1]
                    nb -= 1
                elif (not bu2[k]) and h[i] >= bb[k] and h[i - 1] < bb[k]:
                    s_bk[i] = True
                    bu2[k] = True
            k -= 1
        # ayi OB
        if (not btmc) and (not math.isnan(btmy)) and c[i] < btmy:
            btmc = True
            ma = h[i - 1]
            mi = l[i - 1]
            for k in range(1, i - btmx):
                if h[i - k] > ma:
                    ma = h[i - k]
                    mi = l[i - k]
                elif h[i - k] == ma:
                    mi = l[i - k]
            if ns == M:
                ns -= 1
            for k in range(ns, 0, -1):
                st[k] = st[k - 1]
                sb[k] = sb[k - 1]
                sbrk[k] = sbrk[k - 1]
                su1[k] = su1[k - 1]
                su2[k] = su2[k - 1]
            st[0] = ma
            sb[0] = mi
            sbrk[0] = False
            su1[0] = False
            su2[0] = False
            ns += 1
        k = ns - 1
        while k >= 0:
            if not sbrk[k]:
                if max(c[i], o[i]) > st[k]:
                    sbrk[k] = True
                elif (not su1[k]) and h[i] >= sb[k] and h[i - 1] < sb[k]:
                    s_ob[i] = True
                    su1[k] = True
            else:
                if c[i] < sb[k]:
                    for m in range(k, ns - 1):
                        st[m] = st[m + 1]
                        sb[m] = sb[m + 1]
                        sbrk[m] = sbrk[m + 1]
                        su1[m] = su1[m + 1]
                        su2[m] = su2[m + 1]
                    ns -= 1
                elif (not su2[k]) and l[i] <= st[k] and l[i - 1] > st[k]:
                    a_bk[i] = True
                    su2[k] = True
            k -= 1
    return a_ob, s_ob, a_bk, s_bk


def mfi(h, l, c, v, n):
    """ta.mfi(close, n): kodda kaynak kapanis."""
    tp = c
    d = np.r_[0, np.diff(tp)]
    mf = tp * v
    pos = pd.Series(np.where(d > 0, mf, 0.0)).rolling(n).sum().to_numpy()
    neg = pd.Series(np.where(d < 0, mf, 0.0)).rolling(n).sum().to_numpy()
    return 100 - 100 / (1 + pos / np.where(neg > 0, neg, np.nan))


def gostergeler2(z):
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    tr = true_range(h, l, c)
    S, D, U = {}, {}, {}
    hl2 = (h + l) / 2
    # CDL
    bull, bear, doji, ham, inv = candles(o, h, l, c)
    S["CDL"] = (bull & ~bear, bear & ~bull)
    D["Mum formasyonu (yükseliş +, düşüş -)"] = np.where(bull & ~bear, 1, np.where(bear & ~bull, -1, 0))
    U["Doji"] = doji
    U["Çekiç"] = ham
    U["Ters çekiç"] = inv
    # FBB
    src = (h + l + c) / 3
    basis = sma(src * v, 200) / np.where(sma(v, 200) > 0, sma(v, 200), np.nan)
    dev = 3 * stdev(src, 200)
    S["FBB"] = (cross_dn(c, basis - dev), cross_up(c, basis + dev))
    zf = (src - basis) / np.where(dev > 0, dev, np.nan)
    D["Fib Bollinger konumu (0,618 altı +, üstü -)"] = np.where(zf < -0.618, 1, np.where(zf > 0.618, -1, 0))
    U["Fib Bollinger 0,618 dışı"] = np.nan_to_num(np.abs(zf) > 0.618).astype(bool)
    # SMBC
    a, b, inch = smbc_all(o, h, l, c)
    S["SMBC"] = (a, b)
    U["AlgoAlpha kanal içinde"] = inch
    # BPRB
    D["Breakout Probability eğilimi"] = bprob(o, h, l, c, 5000)
    # MLST
    atr10 = rma(tr, 10)
    cen, clu = kmeans_atr(atr10, 100, 0.75, 0.5, 0.25)
    st, dd = pine_supertrend(hl2, c, cen, 3.0)
    d1 = np.r_[1, dd[:-1]]
    S["MLST"] = ((dd == -1) & (d1 == 1), (dd == 1) & (d1 == -1))
    D["ML Adaptive SuperTrend yönü"] = np.where(dd == -1, 1, -1)
    U["ML oynaklık kümesi yüksek"] = clu == 0
    U["ML oynaklık kümesi düşük"] = clu == 2
    # ICT
    a, b, mdir = ict_mss(h, l, c, pivot(h, 5, 1, True), pivot(l, 5, 1, False))
    S["ICT"] = (a, b)
    D["ICT MSS yönü"] = mdir
    mx, mn = np.maximum(c, o), np.minimum(c, o)
    body = np.abs(c - o)
    Lb = ((h - mx) < body * 0.36) & ((mn - l) < body * 0.36)
    mb = sma(body, 5)
    dup = np.nan_to_num((body > mb) & Lb & (c > o)).astype(bool)
    ddn = np.nan_to_num((body > mb) & Lb & (c < o)).astype(bool)
    D["ICT displacement mumu"] = np.where(dup, 1, np.where(ddn, -1, 0))
    c1, o1, h1, l1 = sh(c, 1), sh(o, 1), sh(h, 1), sh(l, 1)
    vib = np.nan_to_num((o > c1) & (h1 > l) & (c > c1) & (o > o1) & (h1 < mn)).astype(bool)
    vis = np.nan_to_num((o < c1) & (l1 < h) & (c < c1) & (o < o1) & (l1 > mx)).astype(bool)
    D["ICT hacim dengesizliği (VI)"] = np.where(vib, 1, np.where(vis, -1, 0))
    fu = np.r_[False, dup[:-1]] & np.nan_to_num(l > sh(h, 2)).astype(bool)
    fd = np.r_[False, ddn[:-1]] & np.nan_to_num(h < sh(l, 2)).astype(bool)
    D["ICT FVG (displacement)"] = np.where(fu, 1, np.where(fd, -1, 0))
    lon = pd.to_datetime(ts, unit="s", utc=True).tz_convert("Europe/London")
    lm = (lon.hour * 60 + lon.minute).to_numpy()
    U["ICT Londra açılış (07-10 Londra)"] = (lm >= 420) & (lm < 600)
    U["ICT Londra kapanış (15-17 Londra)"] = (lm >= 900) & (lm < 1020)
    # DIV
    rsi14 = K1.rsi(c, 14)
    macd = ema(c, 12) - ema(c, 26)
    hist = macd - ema(macd, 9)
    stk = sma(100 * (c - lowest(l, 14)) / np.where(highest(h, 14) - lowest(l, 14) > 0, highest(h, 14) - lowest(l, 14), np.nan), 3)
    cci10 = K1.cci(c, 10)
    mom = c - sh(c, 10)
    obv = np.cumsum(np.sign(np.r_[0, np.diff(c)]) * v)
    vwm = sma(c * v, 12) / np.where(sma(v, 12) > 0, sma(v, 12), np.nan) - sma(c * v, 26) / np.where(sma(v, 26) > 0, sma(v, 26), np.nan)
    cmfm = ((c - l) - (h - c)) / np.where(h - l > 0, h - l, np.nan)
    cmf = sma(np.nan_to_num(cmfm) * v, 21) / np.where(sma(v, 21) > 0, sma(v, 21), np.nan)
    M = np.column_stack([macd, hist, rsi14, stk, cci10, mom, obv, vwm, cmf, mfi(h, l, c, v, 14)])
    pos, neg = divergences(np.ascontiguousarray(M), c, pivot(c, 5, 5, True), pivot(c, 5, 5, False), 5, 10, 100)
    pa, na_ = pos > 0, neg > 0
    S["DIV"] = (pa & ~np.r_[False, pa[:-1]] & ~na_, na_ & ~np.r_[False, na_[:-1]] & ~pa)
    D["Uyumsuzluk (pozitif +, negatif -)"] = np.where(pa & ~na_, 1, np.where(na_ & ~pa, -1, 0))
    # BSL
    bbr, sbr = zigzag_liq(h, l, pivot(h, 7, 1, True), pivot(l, 7, 1, False), rma(tr, 10), 10 / 6.9, False)
    S["BSLR"] = (sbr & ~bbr, bbr & ~sbr)
    S["BSLC"] = (bbr & ~sbr, sbr & ~bbr)
    # STAI
    os_, pidx = supertrend_ai(hl2, c, atr10, ema(np.abs(np.r_[0, np.diff(c)]), 10))
    o1s = np.r_[0, os_[:-1]]
    S["STAI"] = ((os_ == 1) & (o1s == 0), (os_ == 0) & (o1s == 1))
    D["SuperTrend AI yönü"] = np.where(os_ == 1, 1, -1)
    U["SuperTrend AI performans >= 5"] = pidx * 10 >= 5
    # OBB
    a1, s1, a2, s2 = ob_breaker(o, h, l, c, 10)
    S["OBB"] = (a1 & ~s1, s1 & ~a1)
    S["OBBK"] = (a2 & ~s2, s2 & ~a2)
    # SLG
    ef, es = ema(c, 38), ema(c, 62)
    S["SLG"] = (np.nan_to_num((ef > es) & (sh(c, 1) < ef) & (c > ef)).astype(bool), np.nan_to_num((ef < es) & (sh(c, 1) > ef) & (c < ef)).astype(bool))
    D["SlingShot trendi (EMA38 > EMA62)"] = np.where(ef > es, 1, -1)
    D["SlingShot geri çekilme (alım +, satım -)"] = np.where((ef > es) & (c < ef), 1, np.where((ef < es) & (c > ef), -1, 0))
    return S, D, U, {"STAI": os_, "MLST": dd}


# ------------------------------------------------------------------ cikis katmani
@njit(cache=True)
def exits(o, h, l, c, ix, y, sg, flip, maxh):
    """Her olay bagimsiz. Temel: stop 2 sigma, hedef 2R, 5 mum. Alternatif: stop 2 sigma, hedef yok, flip[j]*y < 0 olunca sonraki acilis, en fazla maxh."""
    m = len(ix)
    n = len(c)
    base = np.full(m, np.nan)
    alt = np.full(m, np.nan)
    for q in range(m):
        i = ix[q]
        if i + maxh + 2 >= n:
            break
        yy = y[q]
        ent = o[i + 1]
        d = 2.0 * sg[q]
        stop = ent * math.exp(-yy * d)
        tgt = ent * math.exp(yy * 2.0 * d)
        px = c[i + 5]
        for j in range(5):
            b = i + 1 + j
            hs = l[b] <= stop if yy > 0 else h[b] >= stop
            ht = h[b] > tgt if yy > 0 else l[b] < tgt
            if hs:
                px = min(stop, o[b]) if yy > 0 else max(stop, o[b])
                break
            if ht:
                px = tgt
                break
        base[q] = yy * (math.log(px) - math.log(ent))
        px = c[i + maxh]
        for j in range(maxh):
            b = i + 1 + j
            hs = l[b] <= stop if yy > 0 else h[b] >= stop
            if hs:
                px = min(stop, o[b]) if yy > 0 else max(stop, o[b])
                break
            if flip[b] * yy < 0 and j < maxh - 1:
                px = o[b + 1]
                break
        alt[q] = yy * (math.log(px) - math.log(ent))
    return base, alt


def parite_isle(s):
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c = z["ts"], z["o"], z["h"], z["l"], z["c"]
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    yilb = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    gunb = (ts // 86400 - TS.GUN0).astype(np.int64)
    S1, D1, U1 = K1.gostergeler(z)
    S2, D2, U2, X = gostergeler2(z)
    D = {**D1, **D2}
    U = {**U1, **U2}
    gec = (t >= 5000) & (t < n - TS.NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
    out = {"A": {}}
    # 1) sinyal
    for ad in YENI:
        al, sat = S2[ad]
        ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
        y = np.where(al[ix], 1, -1).astype(np.int64)
        sg, blk = sigall[ix], engel[ix]
        for giris in ("P", "L"):
            for k in KS:
                for R in RS:
                    for H in HS:
                        res = TS.sim_izgara(o, h, l, c, ix, y, sg, blk, k, R, H, giris == "L", 0.0, 0.0, 0.0, False)
                        out["A"][(ad, "izgara", giris, k, R, H)] = TS.toplam(yilb, gunb, *res)
        if ad in ("MLST", "STAI", "ICT", "SLG"):
            res = TS.sim_yerel(o, c, ix, y, sg, sat, al, 0.0, 0.0, TS.NATIVE_MAX)
            out["A"][(ad, "yerel", "P", 0, 0, 0)] = TS.toplam(yilb, gunb, *res)
    # 2) filtre ve 6) cikis: VSP olaylari
    E = sinyal_v6.olaylar(s)
    ixv = np.searchsorted(ts, E["ts"])
    m = (ixv >= 5000) & (ixv < n - 40)
    ixv, yv, sgv = ixv[m], E["yon"][m].astype(np.int64), E["sig"][m]
    oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ixv, yv, sgv, np.zeros(len(ixv), bool), 2.0, 2.0, 5, False, 0.0, 0.0, 0.0, False)
    B = pd.DataFrame({"sym": s, "gun": ts[oi] // 86400, "yil": yilb[oi], "yon": oy, "brut": ob * 1e4})
    for ad, d in D.items():
        B["D:" + ad] = d[oi] * oy > 0
    for ad, u in U.items():
        B["U:" + ad] = u[oi]
    out["B"] = B
    flips = {
        "Supertrend (10, 3)": D["Supertrend yönü"].astype(float),
        "UT Bot": D["UT Bot konumu"].astype(float),
        "SuperTrend AI": D["SuperTrend AI yönü"].astype(float),
        "ML Adaptive SuperTrend": D["ML Adaptive SuperTrend yönü"].astype(float),
        "SMA20 yönü": D["SMA20 yönü"].astype(float),
        "SlingShot trendi": D["SlingShot trendi (EMA38 > EMA62)"].astype(float),
        "Lorentzian çekirdek eğimi": D["Lorentzian çekirdek eğimi"].astype(float),
        "Yalnızca 30 mum sabit": np.zeros(n),
    }
    F = pd.DataFrame({"sym": s, "gun": ts[ixv] // 86400, "yil": yilb[ixv], "yon": yv})
    for ad, fl in flips.items():
        base, alt = exits(o, h, l, c, ixv, yv, sgv, fl, 30)
        F["base"] = base * 1e4
        F["X:" + ad] = alt * 1e4
    out["F"] = F
    # 3) oynaklik ve 4) yon bilgisi
    r2 = np.nan_to_num(r * r)
    cs = np.r_[0, np.cumsum(r2)]
    fut = np.sqrt(cs[np.minimum(t + 16, n)] - cs[np.minimum(t + 1, n)])
    idx = np.flatnonzero(gec & (t % 15 == 0) & (fut > 0))
    C = pd.DataFrame({"yil": yilb[idx], "gun": ts[idx] // 86400, "y": np.log(fut[idx]), "x0": np.log(sigall[idx]), "f15": (lc[np.minimum(idx + 15, n - 1)] - lc[idx]) * 1e4})
    for ad, u in U.items():
        C["U:" + ad] = u[idx].astype(float)
    for ad, d in D.items():
        C["D:" + ad] = d[idx].astype(float)
    out["C"] = C
    print(s, "tamam", flush=True)
    return out


def yon_farki(df, kol):
    a = df[df[kol] > 0]
    b = df[df[kol] < 0]
    if len(a) < 100 or len(b) < 100:
        return np.nan, np.nan
    fa, fb = a["f15"].mean(), b["f15"].mean()
    g = df[df[kol] != 0].copy()
    g["ra"] = np.where(g[kol] > 0, g["f15"] - fa, 0.0)
    g["rb"] = np.where(g[kol] < 0, g["f15"] - fb, 0.0)
    gg = g.groupby("gun").agg(ra=("ra", "sum"), rb=("rb", "sum"))
    va = (gg["ra"] ** 2).sum() / len(a) ** 2
    vb = (gg["rb"] ** 2).sum() / len(b) ** 2
    cov = (gg["ra"] * gg["rb"]).sum() / (len(a) * len(b))
    se = math.sqrt(max(va + vb - 2 * cov, 1e-12))
    return fa - fb, (fa - fb) / se


def main():
    A, B, C, F = {}, [], [], []
    with Pool(4) as p:
        for parca in p.imap_unordered(parite_isle, izleme.SYMS):
            A = TS.birlestir([A, parca["A"]]) if A else TS.birlestir([parca["A"]])
            B.append(parca["B"])
            C.append(parca["C"])
            F.append(parca["F"])
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 40)
    rows = []
    for key, yl in A.items():
        for y in (2025, 2026):
            rows.append(dict(aday=key[0], tur=key[1], giris=key[2], k=key[3], R=key[4], H=key[5], yil=y, **TS.ozet(yl[y])))
    DA = pd.DataFrame(rows)
    DA.to_csv(os.path.join(izleme.VERI, "katki2_A.csv"), index=False)
    kar = []
    for ad in YENI:
        for tur in ("izgara", "yerel"):
            d = DA[(DA["aday"] == ad) & (DA["tur"] == tur)]
            if len(d) == 0:
                continue
            a25 = d[d["yil"] == 2025].sort_values("netR", ascending=False).iloc[0]
            sel = d[(d["giris"] == a25["giris"]) & (d["k"] == a25["k"]) & (d["R"] == a25["R"]) & (d["H"] == a25["H"])]
            r25, r26 = sel[sel["yil"] == 2025].iloc[0], sel[sel["yil"] == 2026].iloc[0]
            gecti = r25["netR"] > 0 and r26["netR"] > 0 and r25["t"] >= 2 and r26["t"] >= 3
            kar.append(dict(aday=ad, tur=tur, ayar=f"{a25['giris']} k{a25['k']} R{a25['R']} H{a25['H']}", n25=r25["n"], n26=r26["n"],
                            R25=r25["netR"], t25=r25["t"], R26=r26["netR"], t26=r26["t"], bp25=r25["brut_bp"], bp26=r26["brut_bp"],
                            AL26=r26["brutAL_bp"], SAT26=r26["brutSAT_bp"], karar="GECTI" if gecti else "gecmedi"))
    print("=== 1) Sinyal (komisyon 0) ===")
    print(pd.DataFrame(kar).round(3).to_string())
    DB = pd.concat(B, ignore_index=True)
    print("\n=== 2) VSP AL/SAT filtre ===")
    fr = []
    for kol in [k for k in DB.columns if k.startswith("D:") or k.startswith("U:")]:
        res = {yl: K1.iki_grup(DB[DB["yil"] == yl], kol) for yl in (2025, 2026)}
        f25, t25, p25 = res[2025]
        f26, t26, p26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3 and min(p25, p26) >= 0.2 and max(p25, p26) <= 0.8
        fr.append(dict(durum=kol, pay25=p25, fark25=f25, t25=t25, pay26=p26, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(fr).round(3).to_string())
    DC = pd.concat(C, ignore_index=True)
    print("\n=== 3) Oynaklik bilgisi (R2 artisi) ===")
    cr = []
    for kol in [k for k in DC.columns if k.startswith("U:")] + [k for k in DC.columns if k.startswith("D:")]:
        tmp = DC.copy()
        if kol.startswith("D:"):
            tmp[kol] = (tmp[kol] != 0).astype(float)
        a = K1.r2_artis(tmp, kol)
        cr.append(dict(ozellik=kol, r2_25=a[2025], r2_26=a[2026], karar="KABUL" if min(a.values()) >= 0.005 else ""))
    print(pd.DataFrame(cr).round(4).to_string())
    print("\n=== 4) Yon bilgisi (sonraki 15 dk, +1 eksi -1, bp) ===")
    yr = []
    for kol in [k for k in DC.columns if k.startswith("D:")]:
        res = {yl: yon_farki(DC[DC["yil"] == yl], kol) for yl in (2025, 2026)}
        f25, t25 = res[2025]
        f26, t26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3
        yr.append(dict(durum=kol, fark25=f25, t25=t25, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(yr).round(3).to_string())
    DF = pd.concat(F, ignore_index=True)
    print("\n=== 6) Cikis (VSP olaylari, alternatif - temel, bp) ===")
    xr = []
    for kol in [k for k in DF.columns if k.startswith("X:")]:
        rr = {}
        for yl in (2025, 2026):
            d = DF[DF["yil"] == yl].dropna(subset=["base", kol])
            df_ = d[kol] - d["base"]
            g = (df_ - df_.mean()).groupby(d["gun"]).sum()
            se = math.sqrt((g ** 2).sum()) / len(d)
            rr[yl] = (d["base"].mean(), d[kol].mean(), df_.mean(), df_.mean() / se)
        ok = rr[2025][2] >= 0.5 and rr[2026][2] >= 0.5 and rr[2026][3] >= 3
        xr.append(dict(cikis=kol, temel25=rr[2025][0], alt25=rr[2025][1], fark25=rr[2025][2], t25=rr[2025][3], temel26=rr[2026][0], alt26=rr[2026][1], fark26=rr[2026][2], t26=rr[2026][3], karar="KABUL" if ok else ""))
    print(pd.DataFrame(xr).round(3).to_string())


if __name__ == "__main__":
    main()
