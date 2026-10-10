"""TradingView topluluk gostergelerinin AL/SAT sinyalleri: on kayitli islem testi (22 Binance USDT-M paritesi, 2025 kesif / 2026 dogrulama).

Kullanici, TradingView "en iyiler" kategorisindeki en yuksek puanli gostergelerin kodlarini gonderdi; isimize yarayan kisimlarin VSP'ye
eklenmesini istedi. VSP'ye AL/SAT sinyali geri geldigi icin her gostergenin sinyali ayni islem motoruyla sinanir (sinyal_v6.py ile ayni kurallar).
Lisans: Bu dosya gostergelerin kodunu icermez; her birinin algilama mantigi spesifikasyon olarak okunup bastan yazildi. Mantik uyarlamalari
yalnizca arastirma icindir. Kaynaklar ve lisanslari asagidaki listede. VSP.pine bu dosyayi kullanmaz.

ON KAYIT (sonuclardan once yazildi):
  Adaylar (varsayilan girdiler; sinyal yalnizca kapanmis mumda, repaint yok):
    ST   Supertrend (10, 3, hl2, RMA ATR) [TradingView]: trend -1 -> 1 AL, 1 -> -1 SAT.
    SQZ  Squeeze Momentum [LazyBear]: sikisma biter (sqzOn[1] ve sqzOn degil), momentum val > 0 AL, < 0 SAT.
         Kod yazildigi gibi: BB sapmasi KC carpaniyla (1,5) hesaplanir.
    MACD CM_MacD_Ult_MTF [ChrisMoody] (12, 26, sinyal SMA 9): MACD sinyali yukari keser AL, asagi keser SAT.
    WVF  CM_Williams_Vix_Fix [ChrisMoody] (22, 20, 2, 50, 0,85): yesil cubugun ilk mumu AL (yalnizca AL).
    SRB  Support and Resistance Levels with Breaks [LuxAlgo] (15, 15, hacim osc > 20): direnc kirilimi AL, destek kirilimi SAT (alarm tanimi).
    MSB  Market Structure Break & Order Block [EmreKb] (zigzag 9, fib 0,33): market 1'e doner AL, -1'e doner SAT.
    WT   WaveTrend [LazyBear] (10, 21): wt1 wt2'yi yukari keser ve wt1 <= -53 AL; asagi keser ve wt1 >= 53 SAT.
    UT   UT Bot Alerts (1, 10, kapanis): Buy AL, Sell SAT.
    TLB  Trendlines with Breaks [LuxAlgo] (14, ATR, 1): yukari kirilim AL, asagi kirilim SAT.
    SRC  Support Resistance Channels [LonesomeTheBlue] (10, High/Low, %5, 1, 6, 290): direnc kirildi AL, destek kirildi SAT (ayni mumda ikisi: yok).
    DMI  ADX and DI [BeikabuOyaji] (14, 20): DI+ DI-'yi yukari keser ve ADX > 20 AL; asagi keser ve ADX > 20 SAT.
    HVB  Support and Resistance (High Volume Boxes) [ChartPrime] (20, 2, 1): kirilim; direnc kutusu kirilimi AL, destek kutusu kirilimi SAT.
    HVH  Ayni gosterge, tutma: destek tutar AL, direnc tutar SAT.
    KZ   ICT Killzones & Pivots [TFO] (Asya 20-00, Londra 02-05, NYAM 09:30-11, NYPM 13:30-16 ET): biten son seansin tepesi ilk kez
         kirilinca AL, dibi ilk kez kirilinca SAT (devam; gostergenin "Broke High/Low" alarmi).
    Test edilmeyenler: Smart Money Concepts [LuxAlgo] (BULGULAR bolum 12'de iki bagimsiz portla test edildi), Sessions [LuxAlgo]
    (sinyal yok; seans tepe/dip ve VWAP seviyeleri bolum 7 ve 9'daki seviye testleriyle ayni sinif).
  Islem motoru (sinyal_v6.py ile ayni): izgara k {1; 1,5; 2} x R {1; 1,5; 2} x H {5; 15; 30} x giris {P, L}; engeller: zamanlanmis olay ufukta/suruyor
    ve hareket / maliyet < 1; acik islem varken yeni sinyal yok. Maliyet VIP 0 ana senaryo, dusuk ucret ek.
  Yerel cikis (gostergenin kendi kullanimi; engel yok, piyasa giris/cikis, en fazla 240 mum):
    ST, UT, MACD, MSB: ters sinyale kadar tut. SQZ: momentum donunce (AL'de val < val[1]) cik. WT, DMI: ters kesisimde (seviye/ADX sarti yok) cik.
    Kirilim adaylarinin ve WVF'nin yerel cikisi yok.
  Secim: her aday icin 2025'te VIP 0 ortalama net R'si en yuksek izgara ayari. Dogrulama: ayni ayarin 2026 sonucu.
  Basari kurali (13 aday, coklu test): 2025'te net R > 0 ve t >= 2, 2026'da net R > 0 ve t >= 3 (gun kumelenmis). Yerel cikista ayni kural, net bp ile.
  Karar: Kurali gecen aday VSP'ye AL/SAT olarak eklenir. Hicbiri gecmezse VSP'nin AL/SAT'i sinyal_v6.py'deki geri donus sinyali olur.

Kullanim: VSP_VERI=<klasor> python3 arastirma/topluluk_sinyal.py
"""
import math, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6

KS, RS, HS = sinyal_v6.KS, sinyal_v6.RS, sinyal_v6.HS
SEN = sinyal_v6.SEN
NATIVE_MAX = 240
GUN0 = 20089  # 2025-01-01 (unix gun)
NGUN = 700
ADAYLAR = ["V6", "ST", "SQZ", "MACD", "WVF", "SRB", "MSB", "WT", "UT", "TLB", "SRC", "DMI", "HVB", "HVH", "KZ"]
YEREL = {"ST": "ters", "UT": "ters", "MACD": "ters", "MSB": "ters", "SQZ": "kosul", "WT": "kosul", "DMI": "kosul"}


# ------------------------------------------------------------------ yardimcilar
def rma(x, n):
    return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(alpha=2 / (n + 1), adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def stdev(x, n):
    return pd.Series(x).rolling(n).std(ddof=0).to_numpy()


def highest(x, n):
    return pd.Series(x).rolling(n).max().to_numpy()


def lowest(x, n):
    return pd.Series(x).rolling(n).min().to_numpy()


def cross_up(a, b):
    a1, b1 = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    return np.nan_to_num((a > b) & (a1 <= b1)).astype(bool)


def cross_dn(a, b):
    a1, b1 = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    return np.nan_to_num((a < b) & (a1 >= b1)).astype(bool)


def true_range(h, l, c):
    c1 = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - c1), np.abs(l - c1)))
    tr[0] = h[0] - l[0]
    return tr


@njit(cache=True)
def pivot(src, L, R, high):
    """ta.pivothigh/pivotlow(src, L, R): i. mumda, i-R mumunun degeri (yoksa nan). Sol taraf kesin, sag taraf esitlige izin verir."""
    n = len(src)
    out = np.full(n, np.nan)
    for i in range(L + R, n):
        p = i - R
        v = src[p]
        ok = True
        for k in range(1, L + 1):
            if (high and src[p - k] >= v) or ((not high) and src[p - k] <= v):
                ok = False
                break
        if ok:
            for k in range(1, R + 1):
                if (high and src[p + k] > v) or ((not high) and src[p + k] < v):
                    ok = False
                    break
        if ok:
            out[i] = v
    return out


def fixnan(x):
    return pd.Series(x).ffill().to_numpy()


# ------------------------------------------------------------------ gostergeler
@njit(cache=True)
def supertrend(src, c, atr, m):
    n = len(c)
    tr = np.ones(n, np.int64)
    upf = np.empty(n)
    dnf = np.empty(n)
    for i in range(n):
        up = src[i] - m * atr[i]
        dn = src[i] + m * atr[i]
        up1 = upf[i - 1] if i > 0 and not math.isnan(upf[i - 1]) else up
        dn1 = dnf[i - 1] if i > 0 and not math.isnan(dnf[i - 1]) else dn
        if i > 0 and c[i - 1] > up1:
            up = max(up, up1)
        if i > 0 and c[i - 1] < dn1:
            dn = min(dn, dn1)
        upf[i] = up
        dnf[i] = dn
        t = tr[i - 1] if i > 0 else 1
        if t == -1 and c[i] > dn1:
            t = 1
        elif t == 1 and c[i] < up1:
            t = -1
        tr[i] = t
    return tr


@njit(cache=True)
def linreg0(y, n):
    """ta.linreg(y, n, 0): pencerede en kucuk kareler dogrusunun son noktadaki degeri."""
    N = len(y)
    out = np.full(N, np.nan)
    sx = n * (n - 1) / 2.0
    sxx = (n - 1) * n * (2 * n - 1) / 6.0
    for t in range(n - 1, N):
        sy = 0.0
        sxy = 0.0
        bad = False
        for k in range(n):
            v = y[t - n + 1 + k]
            if math.isnan(v):
                bad = True
                break
            sy += v
            sxy += k * v
        if bad:
            continue
        slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        icpt = (sy - slope * sx) / n
        out[t] = icpt + slope * (n - 1)
    return out


@njit(cache=True)
def msb(h, l, zl, fib):
    n = len(h)
    hh = np.full(n, np.nan)
    ll = np.full(n, np.nan)
    for i in range(zl - 1, n):
        mx = h[i]
        mn = l[i]
        for k in range(1, zl):
            mx = max(mx, h[i - k])
            mn = min(mn, l[i - k])
        hh[i] = mx
        ll[i] = mn
    market = np.ones(n, np.int64)
    trend = 1
    last_up = -1
    last_dn = -1
    hp = [np.nan] * 5
    lp = [np.nan] * 5
    last_l0 = np.nan
    last_h0 = np.nan
    for i in range(n):
        to_up = (not math.isnan(hh[i])) and h[i] >= hh[i]
        to_dn = (not math.isnan(ll[i])) and l[i] <= ll[i]
        # barssince(to_up[1]) / barssince(to_down[1]); last_up/last_dn = son to_up/to_down indeksi (i-1'e kadar)
        Lu = (i - (last_up + 1)) if last_up >= 0 else 0
        Ld = (i - (last_dn + 1)) if last_dn >= 0 else 0
        Lu = Lu if Lu > 0 else 1
        Ld = Ld if Ld > 0 else 1
        lowv = l[i]
        for k in range(1, Lu):
            if i - k >= 0:
                lowv = min(lowv, l[i - k])
        highv = h[i]
        for k in range(1, Ld):
            if i - k >= 0:
                highv = max(highv, h[i - k])
        newt = trend
        if trend == 1 and to_dn:
            newt = -1
        elif trend == -1 and to_up:
            newt = 1
        if newt != trend:
            if newt == 1:
                lp.append(lowv)
            else:
                hp.append(highv)
        trend = newt
        h0, h1 = hp[-1], hp[-2]
        l0, l1 = lp[-1], lp[-2]
        prev = market[i - 1] if i > 0 else 1
        # ta.change(market) burada bir onceki mumun degisimini gorur (degisken bu satirda henuz guncellenmedi)
        chg = i > 1 and market[i - 1] != market[i - 2]
        if chg:
            last_l0 = l0
            last_h0 = h0
        m = prev
        if not (last_l0 == l0 or last_h0 == h0):
            if prev == 1 and l0 < l1 and l0 < l1 - abs(h0 - l1) * fib:
                m = -1
            elif prev == -1 and h0 > h1 and h0 > h1 + abs(h1 - l0) * fib:
                m = 1
        market[i] = m
        if to_up:
            last_up = i
        if to_dn:
            last_dn = i
    return market


@njit(cache=True)
def utbot(src, nloss):
    n = len(src)
    ts = np.zeros(n)
    for i in range(n):
        p = ts[i - 1] if i > 0 else 0.0
        s1 = src[i - 1] if i > 0 else np.nan
        if src[i] > p and s1 > p:
            ts[i] = max(p, src[i] - nloss[i])
        elif src[i] < p and s1 < p:
            ts[i] = min(p, src[i] + nloss[i])
        elif src[i] > p:
            ts[i] = src[i] - nloss[i]
        else:
            ts[i] = src[i] + nloss[i]
    return ts


@njit(cache=True)
def trendlines(c, ph, pl, slope, length):
    n = len(c)
    upos = np.zeros(n, np.int64)
    dnos = np.zeros(n, np.int64)
    upper = 0.0
    lower = 0.0
    sph = 0.0
    spl = 0.0
    u = 0
    d = 0
    for i in range(n):
        isph = not math.isnan(ph[i])
        ispl = not math.isnan(pl[i])
        if isph:
            sph = slope[i]
        if ispl:
            spl = slope[i]
        upper = ph[i] if isph else upper - sph
        lower = pl[i] if ispl else lower + spl
        if isph:
            u = 0
        elif c[i] > upper - sph * length:
            u = 1
        if ispl:
            d = 0
        elif c[i] < lower + spl * length:
            d = 1
        upos[i] = u
        dnos[i] = d
    return upos, dnos


@njit(cache=True)
def srchannels(h, l, c, ph, pl, cw, loopback, maxnumsr):
    n = len(c)
    pv = np.zeros(4096)
    pls = np.zeros(4096, np.int64)
    npv = 0
    sr = np.zeros(20)
    rb = np.zeros(n, np.bool_)
    sb = np.zeros(n, np.bool_)
    for i in range(n):
        isph = not math.isnan(ph[i])
        ispl = not math.isnan(pl[i])
        if isph or ispl:
            # unshift
            for k in range(npv, 0, -1):
                pv[k] = pv[k - 1]
                pls[k] = pls[k - 1]
            pv[0] = ph[i] if isph else pl[i]
            pls[0] = i
            npv += 1
            while npv > 0 and i - pls[npv - 1] > loopback:
                npv -= 1
            # kanallar
            sup = np.zeros(npv * 3)
            for x in range(npv):
                lo = pv[x]
                hi = lo
                num = 0
                for y in range(npv):
                    cpp = pv[y]
                    w = hi - cpp if cpp <= hi else cpp - lo
                    if w <= cw[i]:
                        if cpp <= hi:
                            lo = min(lo, cpp)
                        else:
                            hi = max(hi, cpp)
                        num += 20
                sup[x * 3] = num
                sup[x * 3 + 1] = hi
                sup[x * 3 + 2] = lo
            for x in range(npv):
                hx = sup[x * 3 + 1]
                lx = sup[x * 3 + 2]
                s = 0
                for y in range(loopback + 1):
                    if i - y < 0:
                        break
                    if (h[i - y] <= hx and h[i - y] >= lx) or (l[i - y] <= hx and l[i - y] >= lx):
                        s += 1
                sup[x * 3] += s
            for k in range(20):
                sr[k] = 0.0
            stren = np.zeros(10)
            src = 0
            for x in range(npv):
                stv = -1.0
                stl = -1
                for y in range(npv):
                    if sup[y * 3] > stv and sup[y * 3] >= 20:
                        stv = sup[y * 3]
                        stl = y
                if stl >= 0:
                    hh = sup[stl * 3 + 1]
                    lll = sup[stl * 3 + 2]
                    sr[src * 2] = hh
                    sr[src * 2 + 1] = lll
                    stren[src] = sup[stl * 3]
                    for y in range(npv):
                        a = sup[y * 3 + 1]
                        b = sup[y * 3 + 2]
                        if (a <= hh and a >= lll) or (b <= hh and b >= lll):
                            sup[y * 3] = -1
                    src += 1
                    if src >= 10:
                        break
            # orijinaldeki siralama (stren[x] guncellenmez; aynen korunur)
            for x in range(9):
                for y in range(x + 1, 10):
                    if stren[y] > stren[x]:
                        stren[y] = stren[x]
                        t0 = sr[y * 2]
                        sr[y * 2] = sr[x * 2]
                        sr[x * 2] = t0
                        t1 = sr[y * 2 + 1]
                        sr[y * 2 + 1] = sr[x * 2 + 1]
                        sr[x * 2 + 1] = t1
        m = min(9, maxnumsr)
        inch = False
        for x in range(m + 1):
            if c[i] <= sr[x * 2] and c[i] >= sr[x * 2 + 1]:
                inch = True
        if not inch and i > 0:
            for x in range(m + 1):
                if c[i - 1] <= sr[x * 2] and c[i] > sr[x * 2]:
                    rb[i] = True
                if c[i - 1] >= sr[x * 2 + 1] and c[i] < sr[x * 2 + 1]:
                    sb[i] = True
    return rb, sb


@njit(cache=True)
def dmi(h, l, c, ln):
    n = len(c)
    dip = np.full(n, np.nan)
    dim = np.full(n, np.nan)
    dx = np.full(n, np.nan)
    st = 0.0
    sp = 0.0
    sm = 0.0
    for i in range(n):
        c1 = c[i - 1] if i > 0 else 0.0
        h1 = h[i - 1] if i > 0 else 0.0
        l1 = l[i - 1] if i > 0 else 0.0
        trr = max(max(h[i] - l[i], abs(h[i] - c1)), abs(l[i] - c1))
        up = h[i] - h1
        dn = l1 - l[i]
        pdm = max(up, 0.0) if up > dn else 0.0
        mdm = max(dn, 0.0) if dn > up else 0.0
        st = st - st / ln + trr
        sp = sp - sp / ln + pdm
        sm = sm - sm / ln + mdm
        if st > 0:
            dip[i] = sp / st * 100
            dim[i] = sm / st * 100
            if dip[i] + dim[i] > 0:
                dx[i] = abs(dip[i] - dim[i]) / (dip[i] + dim[i]) * 100
    return dip, dim, dx


@njit(cache=True)
def hvboxes(o, c, h, l, v, phc, plc, atr200, width):
    n = len(c)
    vol = np.zeros(n)
    isbuy = True
    for i in range(n):
        if c[i] > o[i]:
            isbuy = True
        elif c[i] < o[i]:
            isbuy = False
        vol[i] = v[i] if isbuy else -v[i]
    S = np.full(n, np.nan)
    S1 = np.full(n, np.nan)
    Rr = np.full(n, np.nan)
    R1 = np.full(n, np.nan)
    s = np.nan
    s1 = np.nan
    r = np.nan
    r1 = np.nan
    for i in range(n):
        vh = vol[i] / 2.5
        vl = vol[i] / 2.5
        if i > 0:
            vh = max(vh, vol[i - 1] / 2.5)
            vl = min(vl, vol[i - 1] / 2.5)
        if (not math.isnan(plc[i])) and vol[i] > vh:
            s = plc[i]
            s1 = s - atr200[i] * width
        if (not math.isnan(phc[i])) and vol[i] < vl:
            r = phc[i]
            r1 = r + atr200[i] * width
        S[i] = s
        S1[i] = s1
        Rr[i] = r
        R1[i] = r1
    return S, S1, Rr, R1


def killzones(ts, h, l):
    """TFO Killzones: her seans (ET) bitince tepe/dip; bir sonraki ayni seans baslayana kadar ilk kirilim."""
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    em = (et.hour * 60 + et.minute).to_numpy()
    seans = [(1200, 1440), (120, 300), (570, 660), (810, 960)]
    n = len(h)
    al = np.zeros(n, bool)
    sat = np.zeros(n, bool)
    for a, b in seans:
        ins = (em >= a) & (em < b)
        _kz_kirilim(ins, h, l, al, sat)
    return al, sat


@njit(cache=True)
def _kz_kirilim(ins, h, l, al, sat):
    n = len(h)
    hi = np.nan
    lo = np.nan
    vh = False
    vl = False
    for i in range(n):
        if ins[i]:
            if i == 0 or not ins[i - 1]:
                hi = h[i]
                lo = l[i]
                vh = True
                vl = True
            else:
                hi = max(hi, h[i])
                lo = min(lo, l[i])
        else:
            if vh and h[i] > hi:
                al[i] = True
                vh = False
            if vl and l[i] < lo:
                sat[i] = True
                vl = False


def sinyaller(z):
    """Her aday icin (al, sat, yerel_cikis_long, yerel_cikis_short) dizileri."""
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    tr = true_range(h, l, c)
    S = {}
    # ST
    st = supertrend((h + l) / 2, c, rma(tr, 10), 3.0)
    st1 = np.r_[1, st[:-1]]
    S["ST"] = ((st == 1) & (st1 == -1), (st == -1) & (st1 == 1))
    # SQZ
    basis = sma(c, 20)
    dev = 1.5 * stdev(c, 20)
    rng = sma(tr, 20)
    sqzOn = np.nan_to_num((basis - dev > basis - rng * 1.5) & (basis + dev < basis + rng * 1.5)).astype(bool)
    val = linreg0(c - ((highest(h, 20) + lowest(l, 20)) / 2 + basis) / 2, 20)
    fire = np.r_[False, sqzOn[:-1]] & ~sqzOn
    val1 = np.r_[np.nan, val[:-1]]
    S["SQZ"] = (fire & (val > 0), fire & (val < 0), np.nan_to_num(val < val1).astype(bool), np.nan_to_num(val > val1).astype(bool))
    # MACD
    macd = ema(c, 12) - ema(c, 26)
    sig = sma(macd, 9)
    S["MACD"] = (cross_up(macd, sig), cross_dn(macd, sig))
    # WVF
    hc = highest(c, 22)
    wvf = (hc - l) / hc * 100
    up = sma(wvf, 20) + 2 * stdev(wvf, 20)
    rh = highest(wvf, 50) * 0.85
    g = np.nan_to_num((wvf >= up) | (wvf >= rh)).astype(bool)
    S["WVF"] = (g & ~np.r_[False, g[:-1]], np.zeros(n, bool))
    # SRB
    hp = fixnan(np.r_[np.nan, pivot(h, 15, 15, True)[:-1]])
    lp = fixnan(np.r_[np.nan, pivot(l, 15, 15, False)[:-1]])
    e5, e10 = ema(v, 5), ema(v, 10)
    osc = np.where(e10 > 0, 100 * (e5 - e10) / np.where(e10 > 0, e10, 1), 0)
    S["SRB"] = (cross_up(c, hp) & (osc > 20), cross_dn(c, lp) & (osc > 20))
    # MSB
    mk = msb(h, l, 9, 0.33)
    mk1 = np.r_[1, mk[:-1]]
    S["MSB"] = ((mk == 1) & (mk1 == -1), (mk == -1) & (mk1 == 1))
    # WT
    ap = (h + l + c) / 3
    esa = ema(ap, 10)
    d = ema(np.abs(ap - esa), 10)
    ci = (ap - esa) / (0.015 * np.where(d > 0, d, np.nan))
    wt1 = ema(np.nan_to_num(ci), 21)
    wt2 = sma(wt1, 4)
    cu, cd = cross_up(wt1, wt2), cross_dn(wt1, wt2)
    S["WT"] = (cu & (wt1 <= -53), cd & (wt1 >= 53), cd, cu)
    # UT
    tsu = utbot(c, rma(tr, 10) * 1.0)
    S["UT"] = ((c > tsu) & cross_up(c, tsu), (c < tsu) & cross_dn(c, tsu))
    # TLB
    ph14 = pivot(h, 14, 14, True)
    pl14 = pivot(l, 14, 14, False)
    upos, dnos = trendlines(c, ph14, pl14, rma(tr, 14) / 14 * 1.0, 14)
    S["TLB"] = (upos > np.r_[0, upos[:-1]], dnos > np.r_[0, dnos[:-1]])
    # SRC
    cw = (highest(h, 300) - lowest(l, 300)) * 5 / 100
    rb, sbk = srchannels(h, l, c, pivot(h, 10, 10, True), pivot(l, 10, 10, False), np.nan_to_num(cw), 290, 5)
    S["SRC"] = (rb & ~sbk, sbk & ~rb)
    # DMI
    dip, dim, dx = dmi(h, l, c, 14.0)
    adx = sma(dx, 14)
    du, dd = cross_up(dip, dim), cross_dn(dip, dim)
    S["DMI"] = (du & (adx > 20), dd & (adx > 20), dd, du)
    # HVB / HVH
    Sx, S1x, Rx, R1x = hvboxes(o, c, h, l, v, pivot(c, 20, 20, True), pivot(c, 20, 20, False), rma(tr, 200), 1.0)
    S["HVB"] = (cross_up(l, R1x), cross_dn(h, S1x))
    S["HVH"] = (cross_up(l, Sx), cross_dn(h, Rx))
    # KZ
    S["KZ"] = killzones(ts, h, l)
    return S


# ------------------------------------------------------------------ islem motorlari
@njit(cache=True)
def sim_izgara(o, h, l, c, ix, y, sg, blk, k, R, H, lim, mk, tk, sl, kapi):
    """sinyal_v6.islem ile ayni kurallar (indeks tabanli). Cikti: kabul edilen islemlerin sinyal indeksi, yon, brut, net, R."""
    n = len(c)
    m = len(ix)
    oi = np.empty(m, np.int64)
    oy = np.empty(m, np.int64)
    ob = np.empty(m)
    on = np.empty(m)
    orr = np.empty(m)
    cnt = 0
    free = -1
    for q in range(m):
        i = ix[q]
        if i < free or blk[q]:
            continue
        if i + 1 + H >= n:
            break
        yy = y[q]
        if lim:
            ent = c[i]
            fin = mk
            if yy > 0:
                filled = l[i + 1] < ent
            else:
                filled = h[i + 1] > ent
        else:
            ent = o[i + 1]
            fin = tk + sl
            filled = True
        if not filled:
            continue
        if kapi and 0.61 * sg[q] < fin + tk + sl:
            continue
        d = k * sg[q]
        stop = ent * math.exp(-yy * d)
        tgt = ent * math.exp(yy * R * d)
        px = c[i + H]
        fout = tk + sl
        jj = H - 1
        for j in range(H):
            b = i + 1 + j
            if yy > 0:
                hs = l[b] <= stop
                ht = h[b] > tgt
            else:
                hs = h[b] >= stop
                ht = l[b] < tgt
            if lim and j == 0:
                ht = False
            if hs:
                po = ent if (lim and j == 0) else o[b]
                px = min(stop, po) if yy > 0 else max(stop, po)
                fout = tk + sl
                jj = j
                break
            if ht:
                px = tgt
                fout = mk
                jj = j
                break
        br = yy * (math.log(px) - math.log(ent))
        nt = br - fin - fout
        oi[cnt] = i
        oy[cnt] = yy
        ob[cnt] = br
        on[cnt] = nt
        orr[cnt] = nt / (d + fin + tk + sl)
        cnt += 1
        free = i + 1 + jj + 1
    return oi[:cnt], oy[:cnt], ob[:cnt], on[:cnt], orr[:cnt]


@njit(cache=True)
def sim_yerel(o, c, ix, y, sg, exL, exS, tk, sl, maxh):
    """Gostergenin kendi cikisi: kosul i+1..i+maxh mumlarindan birinin kapanisinda olusursa sonraki acilista cik."""
    n = len(c)
    m = len(ix)
    oi = np.empty(m, np.int64)
    oy = np.empty(m, np.int64)
    ob = np.empty(m)
    on = np.empty(m)
    orr = np.empty(m)
    cnt = 0
    free = -1
    for q in range(m):
        i = ix[q]
        if i < free:
            continue
        if i + maxh + 2 >= n:
            break
        yy = y[q]
        ent = o[i + 1]
        px = c[i + maxh]
        nf = i + maxh + 1
        for j in range(i + 1, i + maxh):
            if (yy > 0 and exL[j]) or (yy < 0 and exS[j]):
                px = o[j + 1]
                nf = j
                break
        br = yy * (math.log(px) - math.log(ent))
        nt = br - 2 * (tk + sl)
        oi[cnt] = i
        oy[cnt] = yy
        ob[cnt] = br
        on[cnt] = nt
        orr[cnt] = nt / (1.5 * sg[q] + 2 * (tk + sl))
        cnt += 1
        free = nf
    return oi[:cnt], oy[:cnt], ob[:cnt], on[:cnt], orr[:cnt]


def toplam(yilb, gunb, oi, oy, ob, on, orr):
    """Yil bazinda toplamlar (gun kumelenmis t icin gunluk R toplamlari). yilb/gunb: mum basina yil ve gun indeksi."""
    out = {}
    gun = gunb[oi]
    yil = yilb[oi]
    for yl in (2025, 2026):
        m = yil == yl
        g = gun[m]
        out[yl] = dict(n=int(m.sum()), sR=float(orr[m].sum()), sN=float(on[m].sum()), sB=float(ob[m].sum()),
                       gR=np.bincount(g, orr[m], NGUN), gn=np.bincount(g, None, NGUN),
                       nAL=int((m & (oy > 0)).sum()), sRAL=float(orr[m & (oy > 0)].sum()), sBAL=float(ob[m & (oy > 0)].sum()),
                       sBSAT=float(ob[m & (oy < 0)].sum()))
    return out


def parite_isle(s):
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c = z["ts"], z["o"], z["h"], z["l"], z["c"]
    n = len(c)
    E = sinyal_v6.olaylar(s)  # v6 olaylari (engel uygulanmis)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    yilb = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    gunb = (ts // 86400 - GUN0).astype(np.int64)
    S = sinyaller(z)
    ix_v6 = np.searchsorted(ts, E["ts"])
    S["V6"] = (np.isin(t, ix_v6[E["yon"] > 0]), np.isin(t, ix_v6[E["yon"] < 0]))
    sonuc = {}
    for ad in ADAYLAR:
        al, sat = S[ad][0], S[ad][1]
        gec = (t >= 3000) & (t < n - NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
        ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
        y = np.where(al[ix], 1, -1).astype(np.int64)
        sg = sigall[ix]
        blk = engel[ix]
        for giris in ("P", "L"):
            for k in KS:
                for R in RS:
                    for H in HS:
                        for sen, (mk_, tk_, sl_) in SEN.items():
                            res = sim_izgara(o, h, l, c, ix, y, sg, blk, k, R, H, giris == "L", mk_, tk_, sl_, True)
                            sonuc[(ad, "izgara", giris, k, R, H, sen)] = toplam(yilb, gunb, *res)
        if ad in YEREL:
            if YEREL[ad] == "ters":
                exL, exS = sat, al
            else:
                exL, exS = S[ad][2], S[ad][3]
            for sen, (mk_, tk_, sl_) in SEN.items():
                res = sim_yerel(o, c, ix, y, sg, exL, exS, tk_, sl_, NATIVE_MAX)
                sonuc[(ad, "yerel", "P", 0, 0, 0, sen)] = toplam(yilb, gunb, *res)
    print(s, "tamam", flush=True)
    return sonuc


def birlestir(parcalar):
    T = {}
    for p in parcalar:
        for key, yl in p.items():
            if key not in T:
                T[key] = {y: {kk: (vv.copy() if isinstance(vv, np.ndarray) else vv) for kk, vv in d.items()} for y, d in yl.items()}
            else:
                for y, d in yl.items():
                    for kk, vv in d.items():
                        T[key][y][kk] = T[key][y][kk] + vv
    return T


def ozet(d):
    n = d["n"]
    if n == 0:
        return dict(n=0, netR=np.nan, t=np.nan, net_bp=np.nan, brut_bp=np.nan, nAL=0, brutAL_bp=np.nan, brutSAT_bp=np.nan)
    m = d["sR"] / n
    e = d["gR"] - m * d["gn"]
    se = np.sqrt((e ** 2).sum()) / n
    nAL = d["nAL"]
    nS = n - nAL
    return dict(n=n, netR=m, t=m / se if se > 0 else np.nan, net_bp=d["sN"] / n * 1e4, brut_bp=d["sB"] / n * 1e4, nAL=nAL,
                brutAL_bp=d["sBAL"] / nAL * 1e4 if nAL else np.nan, brutSAT_bp=d["sBSAT"] / nS * 1e4 if nS else np.nan)


def main():
    T = {}
    with Pool(4) as p:
        for parca in p.imap_unordered(parite_isle, izleme.SYMS):
            T = birlestir([T, parca]) if T else birlestir([parca])
    rows = []
    for key, yl in T.items():
        for y in (2025, 2026):
            rows.append(dict(aday=key[0], tur=key[1], giris=key[2], k=key[3], R=key[4], H=key[5], sen=key[6], yil=y, **ozet(yl[y])))
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(izleme.VERI, "topluluk_sinyal.csv"), index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 40)
    kar = []
    for ad in ADAYLAR:
        for tur in ("izgara", "yerel"):
            d = D[(D["aday"] == ad) & (D["tur"] == tur) & (D["sen"] == "VIP0")]
            if len(d) == 0:
                continue
            a25 = d[d["yil"] == 2025].sort_values("netR", ascending=False).iloc[0]
            key = (a25["giris"], a25["k"], a25["R"], a25["H"])
            sel = D[(D["aday"] == ad) & (D["tur"] == tur) & (D["giris"] == key[0]) & (D["k"] == key[1]) & (D["R"] == key[2]) & (D["H"] == key[3])]
            r25 = sel[(sel["yil"] == 2025) & (sel["sen"] == "VIP0")].iloc[0]
            r26 = sel[(sel["yil"] == 2026) & (sel["sen"] == "VIP0")].iloc[0]
            d25 = sel[(sel["yil"] == 2025) & (sel["sen"] == "Dusuk")].iloc[0]
            d26 = sel[(sel["yil"] == 2026) & (sel["sen"] == "Dusuk")].iloc[0]
            esik = 2.0 if ad == "V6" else 3.0
            olcu = "netR"
            gecti = r25[olcu] > 0 and r26[olcu] > 0 and r25["t"] >= 2 and r26["t"] >= esik
            kar.append(dict(aday=ad, tur=tur, ayar=f"{key[0]} k{key[1]} R{key[2]} H{key[3]}" if tur == "izgara" else "yerel",
                            n25=r25["n"], n26=r26["n"], brut25=r25["brut_bp"], brut26=r26["brut_bp"], net25=r25["net_bp"], net26=r26["net_bp"],
                            R25=r25["netR"], t25=r25["t"], R26=r26["netR"], t26=r26["t"], dusukR25=d25["netR"], dusukR26=d26["netR"],
                            brutAL26=r26["brutAL_bp"], brutSAT26=r26["brutSAT_bp"], karar="GECTI" if gecti else "gecmedi"))
    K = pd.DataFrame(kar)
    print(K.round(3).to_string())
    K.to_csv(os.path.join(izleme.VERI, "topluluk_karar.csv"), index=False)


if __name__ == "__main__":
    main()
