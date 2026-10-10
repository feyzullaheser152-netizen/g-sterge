"""K3 / G1: izleyen stoplar (1 dk; 22 Binance USDT-M paritesi). Topluluk gostergelerinin sinyal, yon ve stop dizileri.

Kaynak gostergeler (varsayilan girdilerle):
  CE    Chandelier Exit, Alex Orekhov (everget), GPL-3.0. ATR 22, carpan 3, useClose = true (en yuksek/en dusuk kapanis).
  PPST  Pivot Point SuperTrend, LonesomeTheBlue, MPL 2.0. Pivot periyodu 2, ATR carpani 3, ATR 10.
  AT    AlphaTrend, KivancOzbilgic, MPL 2.0. Carpan 1, periyot 14, kaynak kapanis, MFI kipi (hacim verisi var).
Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir.

Pine anlamina uyum notlari:
  - ta.atr = Wilder RMA (topluluk_sinyal.rma; ilk mumlardaki tohum farki kabul edilebilir). AlphaTrend'in ATR'si sma(ta.tr, 14) (RMA degil).
    ta.tr degiskeni ta.tr(false) demektir: ilk mumda na (ta.atr ise ta.tr(true) kullanir, ilk mum h-l). ta.sma na'yi yok sayip 14 gecerli
    deger ister; bu yuzden AlphaTrend ATR'si ilk kez 14. mumda (0 tabanli) olusur.
  - CE: longStopPrev = nz(longStop[1], longStop); longStop[1] guncellenmis (:=) son degerdir. dir 'var', baslangic 1; dir[1] ilk mumda na.
  - PPST: lastpp = ph ? ph : pl ? pl : na ve 'if lastpp' (na ya da 0 yanlis). Pivot bilgisi onay mumunda (pivot mumundan R = 2 sonra) kullanilir.
    TUp/TDown her mumda na ile baslar; TUp[1]/TDown[1] ilk mumda na, karsilastirmalar yanlis. Trend onceki mumun TDown[1]/TUp[1] degerini kullanir;
    nz(Trend[1], 1). max/min'e na girerse sonuc na.
  - AT: nz(AlphaTrend[1]) ilk mumda 0. ta.mfi(hlc3, 14): upper = sum(v * (change <= 0 ? 0 : src)), lower = sum(v * (change >= 0 ? 0 : src));
    ilk mumda change na oldugundan iki toplam da v*src alir (Pine'daki gibi). lower = 0 ise Pine'da bolme na verir -> mfi na -> 'mfi >= 50' yanlis
    (downT dali). color1: AT > AT[2] yesil, AT < AT[2] kirmizi, aksi halde AT[1] > AT[3] yesil, degilse kirmizi.
    BUY etiketi: buySignalk ve O1 > K2; SELL etiketi: sellSignalk ve O2 > K1 (ta.barssince; hic olmadiysa na -> yanlis).
  - Her deger yalnizca t ve oncesi mumlarin verisiyle hesaplanir (repaint yok); sinyaller mum kapanisinda.
"""
import math, os, sys
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topluluk_sinyal import rma, ema, sma, stdev, highest, lowest, cross_up, cross_dn, true_range, pivot


def sh(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


@njit(cache=True)
def _pmax(a, b):
    if math.isnan(a) or math.isnan(b):
        return np.nan
    return a if a > b else b


@njit(cache=True)
def _pmin(a, b):
    if math.isnan(a) or math.isnan(b):
        return np.nan
    return a if a < b else b


@njit(cache=True)
def _barssince(cond):
    n = len(cond)
    out = np.full(n, np.nan)
    last = -1
    for i in range(n):
        if cond[i]:
            last = i
        if last >= 0:
            out[i] = i - last
    return out


# ------------------------------------------------------------------ Chandelier Exit
@njit(cache=True)
def _ce(c, hc, lc, atr):
    n = len(c)
    lsf = np.empty(n)
    ssf = np.empty(n)
    d = np.empty(n, np.int64)
    dr = 1
    for i in range(n):
        ls = hc[i] - atr[i]
        ss = lc[i] + atr[i]
        lsp = lsf[i - 1] if i > 0 and not math.isnan(lsf[i - 1]) else ls
        ssp = ssf[i - 1] if i > 0 and not math.isnan(ssf[i - 1]) else ss
        if i > 0 and c[i - 1] > lsp:
            ls = _pmax(ls, lsp)
        if i > 0 and c[i - 1] < ssp:
            ss = _pmin(ss, ssp)
        lsf[i] = ls
        ssf[i] = ss
        if c[i] > ssp:
            dr = 1
        elif c[i] < lsp:
            dr = -1
        d[i] = dr
    return lsf, ssf, d


def chandelier(h, l, c, tr, length=22, mult=3.0, use_close=True):
    atr = mult * rma(tr, length)
    hc = highest(c, length) if use_close else highest(h, length)
    lc = lowest(c, length) if use_close else lowest(l, length)
    ls, ss, d = _ce(c, hc, lc, atr)
    d1 = np.r_[0, d[:-1]]
    return ls, ss, d, (d == 1) & (d1 == -1), (d == -1) & (d1 == 1)


# ------------------------------------------------------------------ Pivot Point SuperTrend
@njit(cache=True)
def _ppst(c, ph, pl, atr, factor):
    n = len(c)
    tu = np.empty(n)
    td = np.empty(n)
    t = np.empty(n, np.int64)
    center = np.nan
    for i in range(n):
        lastpp = np.nan
        if not math.isnan(ph[i]) and ph[i] != 0.0:
            lastpp = ph[i]
        elif not math.isnan(pl[i]) and pl[i] != 0.0:
            lastpp = pl[i]
        if not math.isnan(lastpp) and lastpp != 0.0:
            if math.isnan(center):
                center = lastpp
            else:
                center = (center * 2 + lastpp) / 3
        up = center - factor * atr[i]
        dn = center + factor * atr[i]
        tu1 = tu[i - 1] if i > 0 else np.nan
        td1 = td[i - 1] if i > 0 else np.nan
        c1 = c[i - 1] if i > 0 else np.nan
        tu[i] = _pmax(up, tu1) if c1 > tu1 else up
        td[i] = _pmin(dn, td1) if c1 < td1 else dn
        tr1 = t[i - 1] if i > 0 else 1
        if c[i] > td1:
            t[i] = 1
        elif c[i] < tu1:
            t[i] = -1
        else:
            t[i] = tr1
    return tu, td, t


def ppst(h, l, c, tr, prd=2, factor=3.0, pd_=10):
    ph = pivot(h, prd, prd, True)
    pl = pivot(l, prd, prd, False)
    tu, td, t = _ppst(c, ph, pl, rma(tr, pd_), factor)
    t1 = np.r_[0, t[:-1]]
    return tu, td, t, (t == 1) & (t1 == -1), (t == -1) & (t1 == 1)


# ------------------------------------------------------------------ AlphaTrend
@njit(cache=True)
def _at(cond, upT, downT):
    n = len(cond)
    at = np.empty(n)
    for i in range(n):
        p = at[i - 1] if i > 0 and not math.isnan(at[i - 1]) else 0.0
        if cond[i]:
            at[i] = p if upT[i] < p else upT[i]
        else:
            at[i] = p if downT[i] > p else downT[i]
    return at


def pine_mfi(src, v, n):
    ch = np.r_[np.nan, np.diff(src)]
    up_t = np.where(ch <= 0, 0.0, src)  # ch na -> karsilastirma yanlis -> src
    dn_t = np.where(ch >= 0, 0.0, src)
    upper = pd.Series(v * up_t).rolling(n).sum().to_numpy()
    lower = pd.Series(v * dn_t).rolling(n).sum().to_numpy()
    lower = np.where(lower == 0, np.nan, lower)  # Pine: sifira bolme na
    return 100.0 - 100.0 / (1.0 + upper / lower)


def alphatrend(h, l, c, v, coeff=1.0, ap=14):
    tr_f = true_range(h, l, c)
    tr_f[0] = np.nan  # ta.tr degiskeni = ta.tr(false): onceki kapanis yokken na
    atr = sma(tr_f, ap)  # pandas rolling(ap) ap gecerli deger ister = Pine ta.sma'nin na'yi yok saymasi (yalnizca ilk mum na)
    upT = l - atr * coeff
    downT = h + atr * coeff
    m = pine_mfi((h + l + c) / 3.0, v, ap)
    with np.errstate(invalid="ignore"):
        cond = m >= 50
    at = _at(cond, upT, downT)
    at1, at2, at3 = sh(at, 1), sh(at, 2), sh(at, 3)
    with np.errstate(invalid="ignore"):
        gt, lt = at > at2, at < at2
        green = gt | (~gt & ~lt & (at1 > at3))
    buyk = cross_up(at, at2)
    sellk = cross_dn(at, at2)
    k1 = _barssince(buyk)
    k2 = _barssince(sellk)
    o1 = _barssince(np.r_[False, buyk[:-1]])
    o2 = _barssince(np.r_[False, sellk[:-1]])
    with np.errstate(invalid="ignore"):
        buy = buyk & (o1 > k2)
        sell = sellk & (o2 > k1)
    return at, np.where(green, 1, -1).astype(np.int64), buy, sell


# ------------------------------------------------------------------ sozlesme
def hesapla(z):
    o, h, l, c, v = (np.asarray(z[k], dtype=np.float64) for k in ("o", "h", "l", "c", "v"))
    tr = true_range(h, l, c)
    ce_ls, ce_ss, ce_d, ce_al, ce_sat = chandelier(h, l, c, tr)
    tu, td, pt, pp_al, pp_sat = ppst(h, l, c, tr)
    at, at_d, at_al, at_sat = alphatrend(h, l, c, v)
    return {
        "S": {"CE": (ce_al, ce_sat), "PPST": (pp_al, pp_sat), "AT": (at_al, at_sat)},
        "D": {"Chandelier Exit yönü": ce_d, "Pivot Point SuperTrend yönü": pt, "AlphaTrend yönü": at_d},
        "U": {},
        "X": {"Chandelier Exit": ce_d.astype(np.float64), "Pivot Point SuperTrend": pt.astype(np.float64), "AlphaTrend": at_d.astype(np.float64)},
        "STOPS": {"Chandelier": (ce_ls, ce_ss), "Pivot Point SuperTrend": (tu, td)},
    }
