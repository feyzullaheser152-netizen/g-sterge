"""G3: SMC araçları ve fiyat hareketi mumları.

Kaynak göstergeler:
  - Super OrderBlock / FVG / BoS Tools — makuchaku & eFe (TradingView), lisans: Mozilla Public License 2.0.
    Girdiler: pivotLookup 1, BoS kapanışla (useHighLow... false), hacim EMA 12, çarpan 1,5.
  - CM_Price-Action-Bars — ChrisMoody (1-20-2014; Chris Capre / 2nd Skies Forex'e atıf), TradingView açık kaynak
    (lisans başlığı yok; TradingView kuralları gereği yazar anılarak yeniden kullanılır). Girdiler: 66 / 6 / 5.

Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir.

Notlar:
  - top = ta.valuewhen(pivothigh(high,1,1), high[1], 0): pivot doğrulama mumunda (pivot mumundan 1 sonra) bilinir; bottom simetrik.
    Dolayısıyla tüm çıktılar t mumunda yalnızca <= t verisini kullanır (repaint yok).
  - Kaynak Pine v5'te pivot değeri (float) bool olarak kullanılır: na -> false, fiyat > 0 -> true.
  - ta.ema(volume, 12) yardımcı ema ile (ilk mumlardaki tohum farkı kabul edildi).
  - Price-action: lowest(6)/highest(6) kaynaksız -> low/high, mevcut mum dahil.
  - Aynı mumda hem AL hem SAT çıkarsa ikisi de verilmez (PPDD, PPDDW, OBFVG, PIN'de mantıksal olarak imkânsız; BOS1'de top < bottom iken olabilir).
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topluluk_sinyal import ema, highest, lowest, cross_up, cross_dn, pivot


def _sh(x, k):
    """x[k] (Pine geçmiş operatörü); ilk k mum na."""
    return np.r_[np.full(k, np.nan), x[:-k]]


def _b(x):
    return np.nan_to_num(x).astype(bool)


def _ffill(x):
    idx = np.where(np.isnan(x), 0, np.arange(len(x)))
    np.maximum.accumulate(idx, out=idx)
    return x[idx]  # x[0] na ise ilk geçerli değere kadar na kalır


def _tek(al, sat):
    al, sat = _b(al), _b(sat)
    return al & ~sat, sat & ~al


def hesapla(z):
    o = np.asarray(z["o"], float)
    h = np.asarray(z["h"], float)
    l = np.asarray(z["l"], float)
    c = np.asarray(z["c"], float)
    v = np.asarray(z["v"], float)
    # ---------------------------------------------------------------- Super OrderBlock / FVG / BoS
    O = {k: _sh(o, k) for k in (1, 2)}
    C = {k: _sh(c, k) for k in (1, 2)}
    H = {k: _sh(h, k) for k in (1, 2)}
    Lw = {k: _sh(l, k) for k in (1, 2)}
    O[0], C[0], H[0], Lw[0] = o, c, h, l
    isUp = lambda i: C[i] > O[i]
    isDown = lambda i: C[i] < O[i]
    isObUp = lambda i: isDown(i + 1) & isUp(i) & (C[i] > H[i + 1])
    isObDown = lambda i: isUp(i + 1) & isDown(i) & (C[i] < Lw[i + 1])
    isFvgUp0 = l > H[2]
    isFvgDown0 = h < Lw[2]
    ph = pivot(h, 1, 1, True)
    pl = pivot(l, 1, 1, False)
    top = _ffill(np.where(np.isfinite(ph) & (ph != 0), H[1], np.nan))
    bottom = _ffill(np.where(np.isfinite(pl) & (pl != 0), Lw[1], np.nan))
    top1, bottom1 = _sh(top, 1), _sh(bottom, 1)
    bosBull = cross_up(c, top)
    bosBear = cross_dn(c, bottom)
    mx = np.maximum(h, H[1])
    mn = np.minimum(l, Lw[1])
    prem_kos = ((mx > top) & (c < top)) | ((mx > top1) & (c < top1))
    disc_kos = ((mn < bottom) & (c > bottom)) | ((mn < bottom1) & (c > bottom1))
    premiumPremium = _b(isObDown(0) & prem_kos)
    discountDiscount = _b(isObUp(0) & disc_kos)
    premiumPremium1 = _b(isUp(1) & isDown(0) & (c < O[1]) & prem_kos) & ~premiumPremium
    discountDiscount1 = _b(isDown(1) & isUp(0) & (c > O[1]) & disc_kos) & ~discountDiscount
    volEma = ema(v, 12)
    isHighVolume = _b(v > 1.5 * volEma)
    hvbBull = _b(isUp(0)) & isHighVolume
    hvbBear = _b(isDown(0)) & isHighVolume
    obfvgBear = _b(isFvgDown0 & isObDown(1))
    obfvgBull = _b(isFvgUp0 & isObUp(1))
    # ---------------------------------------------------------------- CM Price Action Bars
    pctCp = 66 * .01
    pctCPO = 1 - pctCp
    pctCs = 5 * .01
    rng = h - l
    pBarUp = _b((o > h - rng * pctCPO) & (c > h - rng * pctCPO) & (l <= lowest(l, 6)))
    pBarDn = _b((o < h - rng * pctCp) & (c < h - rng * pctCp) & (h >= highest(h, 6)))
    sBarUp = _b(c >= h - rng * pctCs)
    sBarDown = _b(c <= l + rng * pctCs)
    insideBar = _b((h <= H[1]) & (l >= Lw[1]))
    outsideBar = _b((h > H[1]) & (l < Lw[1]))
    # ---------------------------------------------------------------- çıktı
    S = {
        "PPDD": _tek(discountDiscount, premiumPremium),
        "PPDDW": _tek(discountDiscount1, premiumPremium1),
        "OBFVG": _tek(obfvgBull, obfvgBear),
        "BOS1": _tek(bosBull, bosBear),
        "PIN": _tek(pBarUp, pBarDn),
    }
    i8 = np.int64
    D = {
        "Yüksek hacim mumu (HVB) yönü": hvbBull.astype(i8) - hvbBear.astype(i8),
        "Traşlı mum (shaved)": (sBarUp & ~sBarDown).astype(i8) - (sBarDown & ~sBarUp).astype(i8),
        "Pin bar": (pBarUp & ~pBarDn).astype(i8) - (pBarDn & ~pBarUp).astype(i8),
    }
    U = {
        "Yüksek hacim mumu": isHighVolume,
        "İç mum (inside)": insideBar,
        "Dış mum (outside)": outsideBar,
    }
    return {"S": S, "D": D, "U": U, "X": {}, "STOPS": {}}
