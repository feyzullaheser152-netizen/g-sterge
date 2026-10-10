"""RSI Signals Entries [Michael_Fx_Trader] mantik uyarlamasi.

Lisans: kaynakta "All rights reserved" yaziyor, acik lisans yok. RSI (Wilder) genel bir yontem; bu modul yalnizca arastirma icin mantigi yeniden
uygular. Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir. Kaynak: kullanicinin mesaji (Ekim 2026), scratchpad/k5_kaynak/R_rsise.pine.
Varsayilanlar: RSI 14 (close), mum kapanisinda onay, Over Buy 79.90, Resistance 67.90, Support 34.90, Over Sold 19.90, guclu mum: govde >=
1.2 x SMA(govde, 20).
Pine anlamina uyum:
  - ta.rsi: RMA(14) ile kazanc/kayip (ilk deger 14 degisimin SMA'si), Pine'daki gibi: kayip 0 ise 100, kazanc 0 ise 0.
  - ta.sma(govde, 20): ilk 19 mumda na -> guclu mum kosulu yanlis.
  - Bolge durumu: overbought = rsi >= 79.9; resistance = 67.9 <= rsi < 79.9; support = 19.9 < rsi <= 34.9; oversold = rsi <= 19.9.
  - "fired" bayraklari bolgeden cikinca (mumun basinda) sifirlanir; sinyal bolgede kalindigi surece bir kez. RSI na iken bolge yok.
  - Sinyaller yalnizca mum kapanisinda (gecmis mumlarda her zaman onayli).
  - Gostergenin pip tabanli giris/stop/hedefi (70/80 pip, pip 0.0001) kripto fiyatlarina uymadigi icin sinanmadi.
Ciktilar (katki_testi5 on kaydi):
  S RSISE : finalBuySignal AL / finalSellSignal SAT (ayni mumda ikisi olamaz).
  S RSIX  : yalnizca asiri bolge sinyalleri (buySignalExtreme AL / sellSignalExtreme SAT).
  S RSIZ  : yalnizca bolge + guclu mum sinyalleri (buySignalZone AL / sellSignalZone SAT).
  D "RSI bölgesi (destek bölgesi +)": +1 rsi <= 34.9, -1 rsi >= 67.9, yoksa 0.
"""
import math
import numpy as np
from numba import njit


@njit(cache=True)
def _rsi(c, n):
    m = len(c)
    out = np.full(m, np.nan)
    if m <= n:
        return out
    g = 0.0
    lo = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]
        g += max(d, 0.0)
        lo += max(-d, 0.0)
    g /= n
    lo /= n
    out[n] = 100.0 if lo == 0 else (0.0 if g == 0 else 100.0 - 100.0 / (1.0 + g / lo))
    for i in range(n + 1, m):
        d = c[i] - c[i - 1]
        g = (g * (n - 1) + max(d, 0.0)) / n
        lo = (lo * (n - 1) + max(-d, 0.0)) / n
        out[i] = 100.0 if lo == 0 else (0.0 if g == 0 else 100.0 - 100.0 / (1.0 + g / lo))
    return out


@njit(cache=True)
def _sinyal(o, c, rsi, ob, rs, sp, os_, blen, bmul):
    n = len(c)
    xb = np.zeros(n, np.bool_)
    xs = np.zeros(n, np.bool_)
    zb = np.zeros(n, np.bool_)
    zs = np.zeros(n, np.bool_)
    body = np.abs(c - o)
    obf = False
    rsf = False
    spf = False
    osf = False
    acc = 0.0
    for i in range(n):
        acc += body[i]
        if i >= blen:
            acc -= body[i - blen]
        avgb = acc / blen if i >= blen - 1 else np.nan
        r = rsi[i]
        valid = not math.isnan(r)
        in_ob = valid and r >= ob
        in_rs = valid and r >= rs and r < ob
        in_sp = valid and r <= sp and r > os_
        in_os = valid and r <= os_
        if not in_ob:
            obf = False
        if not in_rs:
            rsf = False
        if not in_sp:
            spf = False
        if not in_os:
            osf = False
        strong_ok = not math.isnan(avgb)
        sbear = strong_ok and c[i] < o[i] and body[i] >= avgb * bmul
        sbull = strong_ok and c[i] > o[i] and body[i] >= avgb * bmul
        s_ext = in_ob and not obf
        s_zon = in_rs and sbear and not rsf
        b_ext = in_os and not osf
        b_zon = in_sp and sbull and not spf
        if s_ext:
            obf = True
        if s_zon:
            rsf = True
        if b_ext:
            osf = True
        if b_zon:
            spf = True
        xb[i] = b_ext
        xs[i] = s_ext
        zb[i] = b_zon
        zs[i] = s_zon
    return xb, xs, zb, zs


def hesapla(z):
    o, c = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("o", "c"))
    rsi = _rsi(c, 14)
    xb, xs, zb, zs = _sinyal(o, c, rsi, 79.90, 67.90, 34.90, 19.90, 20, 1.2)
    al, sat = xb | zb, xs | zs
    d = np.where(rsi <= 34.90, 1, np.where(rsi >= 67.90, -1, 0)).astype(np.int64)
    return {"S": {"RSISE": (al & ~sat, sat & ~al), "RSIX": (xb, xs), "RSIZ": (zb, zs)}, "D": {"RSI bölgesi (destek bölgesi +)": d},
            "U": {}, "X": {}, "STOPS": {}, "NATIVE": {}}
