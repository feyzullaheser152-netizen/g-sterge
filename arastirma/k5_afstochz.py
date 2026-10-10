"""AF_StochZ_Overlay mantik uyarlamasi.

Lisans: kaynakta lisans ya da yazar satiri yok (kullanicinin mesaji, Ekim 2026; scratchpad/k5_kaynak/A_afstochz.pine). Mantık uyarlaması; kod
kopyalanmadı, yalnızca araştırma içindir.
Varsayilanlar: Min/Max Length 8/34, ER 10, %K 3, %D 3, %K/%D teyidi kapali, Z 20, osilator pivotu 1/1, esikler -1/+1, fiyat pivotu sol 3 sag 2,
osilator pivotundan sonra en fazla 5 mum, EMA trend filtresi kapali, normal ve gizli uyumsuzluk acik, uyumsuzluk arama 5-60 mum.
Pine anlamina uyum:
  - ER = |close - close[10]| / (SMA(|close - close[1]|, 10) * 10); payda na ya da 0 ise 0 (v6'da na karsilastirmasi false).
    Uyarlanabilir boy = max(8, min(34, round(34 - ER * 26))) (math.round: yarim yukari).
  - %K = SMA(ham stokastik, 3); ham = (close - en dusuk) / (en yuksek - en dusuk) * 100, aralik 0 ise 50. En yuksek/en dusuk o mumun uyarlanabilir
    boyuyla (bu mum dahil). Isinma: pencere veri basini asarsa mevcut mumlarla (Pine'da ilk mumlar farkli olabilir; ilk 300 mum karsilastirilmaz).
  - Fisher = 0,5 ln((1+x)/(1-x)), x = (%K - 50)/50, +-0,998 ile sinirli. Z = (Fisher - SMA20) / stdev20 (ta.stdev: populasyon); stdev 0 ya da na ise 0.
  - Pivotlar topluluk_sinyal.pivot ile (sol kesin, sag esitlige izin verir; VSP ve onceki testlerle ayni kural, BULGULAR 17).
  - Osilator pivotu (1/1) Z < -1 (dip) ya da Z > 1 (tepe) ise son gecerli osilator dibi/tepesi = pivot mumu. Bu, fiyat kontrolunden ONCE guncellenir.
  - Lider AL: fiyat pivot dibi (3/2) onaylandiginda, pivot mumu - son gecerli osilator dibi 0..5 ve bu osilator dibi daha once sinyal vermediyse.
    Lider SAT simetrik.
  - Uyumsuzluk: fiyat pivot dibi onay mumunda, 5..60 mum onceki onaylarda en yakin pivot dibi aranir. Normal: dip daha alcak ve Z daha yuksek;
    gizli: dip daha yuksek ve Z daha alcak. Kosulu saglamayan pivotun ustunden atlanip aramaya devam edilir (betikteki gibi; ilk saglayanda durur).
  - Etiketler pivot mumuna (2 mum geriye) cizilir, ama sinyal onay mumunun kapanisinda bilinir; test onay mumunda tarihlenir.
Ciktilar (katki_testi5 on kaydi):
  S AFLD : lider sinyal (StochZ Lead BUY AL / SELL SAT; ayni mumda ikisi birden ise yok).
  S AFRD : normal uyumsuzluk (R-Bull AL / R-Bear SAT; ikisi birden ise yok).
  S AFHD : gizli uyumsuzluk (H-Bull AL / H-Bear SAT; ikisi birden ise yok).
  S AFLB : gostergenin butun etiketleri (herhangi bir boga etiketi AL / ayi etiketi SAT; ikisi birden ise yok).
  D "StochZ bölgesi (aşırı satım +)": +1 Z < -1, -1 Z > 1, yoksa 0.
"""
import math
import os
import sys
import numpy as np
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topluluk_sinyal as TS


@njit(cache=True)
def _zstoch(h, l, c, minl, maxl, erl, sk, zl):
    n = len(c)
    raw = np.empty(n)
    ad = np.abs(np.diff(c))
    acc = 0.0
    for i in range(n):
        if i >= 1:
            acc += ad[i - 1]
        if i >= erl + 1:
            acc -= ad[i - 1 - erl]
        er = 0.0
        if i >= erl:
            vol = (acc / erl) * erl
            if vol != 0:
                er = abs(c[i] - c[i - erl]) / vol
        ln = int(math.floor(maxl - er * (maxl - minl) + 0.5))
        ln = max(minl, min(maxl, ln))
        hh = -np.inf
        ll = np.inf
        for k in range(max(0, i - ln + 1), i + 1):
            if h[k] > hh:
                hh = h[k]
            if l[k] < ll:
                ll = l[k]
        rng = hh - ll
        raw[i] = (c[i] - ll) / rng * 100.0 if rng != 0 else 50.0
    kk = np.full(n, np.nan)
    for i in range(sk - 1, n):
        s = 0.0
        for k in range(i - sk + 1, i + 1):
            s += raw[k]
        kk[i] = s / sk
    fis = np.full(n, np.nan)
    for i in range(n):
        if not math.isnan(kk[i]):
            x = max(min((kk[i] - 50.0) / 50.0, 0.998), -0.998)
            fis[i] = 0.5 * math.log((1 + x) / (1 - x))
    z = np.zeros(n)
    for i in range(n):
        if i - zl + 1 < 0 or math.isnan(fis[i - zl + 1]):
            continue
        m = 0.0
        for k in range(i - zl + 1, i + 1):
            m += fis[k]
        m /= zl
        v = 0.0
        for k in range(i - zl + 1, i + 1):
            v += (fis[k] - m) ** 2
        sd = math.sqrt(v / zl)
        z[i] = (fis[i] - m) / sd if sd != 0 else 0.0
    return kk, z


@njit(cache=True)
def _sinyal(l, h, z, opl, oph, ppl, pph, pr, ob, os_, lag, dmin, dmax):
    n = len(z)
    lb = np.zeros(n, np.bool_)
    ls = np.zeros(n, np.bool_)
    rb = np.zeros(n, np.bool_)
    rs = np.zeros(n, np.bool_)
    hb = np.zeros(n, np.bool_)
    hs = np.zeros(n, np.bool_)
    lastLo = -1
    lastHi = -1
    firedB = -1
    firedS = -1
    for i in range(n):
        if (not math.isnan(opl[i])) and opl[i] < os_:
            lastLo = i - 1
        if (not math.isnan(oph[i])) and oph[i] > ob:
            lastHi = i - 1
        pb = i - pr
        if (not math.isnan(ppl[i])) and lastLo >= 0:
            d = pb - lastLo
            if d >= 0 and d <= lag and firedB != lastLo:
                lb[i] = True
                firedB = lastLo
        if (not math.isnan(pph[i])) and lastHi >= 0:
            d = pb - lastHi
            if d >= 0 and d <= lag and firedS != lastHi:
                ls[i] = True
                firedS = lastHi
        if not math.isnan(ppl[i]):
            pl_ = l[pb]
            po = z[pb]
            for k in range(dmin, dmax + 1):
                if i - k < 0:
                    break
                if not math.isnan(ppl[i - k]):
                    q = pb - k
                    if pl_ < l[q] and po > z[q]:
                        rb[i] = True
                        break
                    if pl_ > l[q] and po < z[q]:
                        hb[i] = True
                        break
        if not math.isnan(pph[i]):
            ph_ = h[pb]
            po = z[pb]
            for k in range(dmin, dmax + 1):
                if i - k < 0:
                    break
                if not math.isnan(pph[i - k]):
                    q = pb - k
                    if ph_ > h[q] and po < z[q]:
                        rs[i] = True
                        break
                    if ph_ < h[q] and po > z[q]:
                        hs[i] = True
                        break
    return lb, ls, rb, rs, hb, hs


def _tek(a, s):
    return a & ~s, s & ~a


def hesapla(z):
    h, l, c = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("h", "l", "c"))
    _, zs = _zstoch(h, l, c, 8, 34, 10, 3, 20)
    opl = TS.pivot(zs, 1, 1, False)
    oph = TS.pivot(zs, 1, 1, True)
    ppl = TS.pivot(l, 3, 2, False)
    pph = TS.pivot(h, 3, 2, True)
    lb, ls, rb, rs, hb, hs = _sinyal(l, h, zs, opl, oph, ppl, pph, 2, 1.0, -1.0, 5, 5, 60)
    ab, as_ = lb | rb | hb, ls | rs | hs
    d = np.where(zs < -1.0, 1, np.where(zs > 1.0, -1, 0)).astype(np.int64)
    return {"S": {"AFLD": _tek(lb, ls), "AFRD": _tek(rb, rs), "AFHD": _tek(hb, hs), "AFLB": _tek(ab, as_)},
            "D": {"StochZ bölgesi (aşırı satım +)": d}, "U": {}, "X": {}, "STOPS": {}, "NATIVE": {}}
