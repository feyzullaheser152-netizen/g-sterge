"""Trinity Reversal Pattern [AlgoAlpha] (MPL 2.0) mantik uyarlamasi.

Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir. Kaynak (mantik, birebir): scratchpad/k5_kaynak/T_trinity.pine.
Varsayilanlar: Strength Lookback 100, Minimum Strength 0 (butun formasyonlar), Level Expiry 100 mum, Confirm on Close acik, EMA trend filtresi kapali,
Maximum Stored Levels 500.
Pine anlamina uyum:
  - strength = govde / (son 100 govdenin, bu mum dahil, en buyugu) * 100, en fazla 100; filtre 0 oldugu icin sinyali etkilemez (yine de hesaplanir).
  - bull = close > open, high > high[2], low[1] < low[2], high[1] < high[2], close[1] < open[1], close[2] < open[2]; bear simetrik. bar_index >= 2.
  - Seviyeler her mum, yeni sinyal eklenmeden ONCE, sondan basa taranir: yas > 0 ise boga seviyesi icin low <= seviye, ayi icin high >= seviye
    dokunus; yas >= 100 ve mum onayli ise sure dolar. Dokunulan ya da suresi dolan seviye "inaktif" listeye gecer.
  - Yeni sinyalde aktif + inaktif >= 500 iken once en eski inaktif, inaktif yoksa en eski aktif seviye silinir (betikteki gibi).
  - Boga seviyesi = formasyonun en dusugu (3 mum), ayi seviyesi = en yuksegi.
Ciktilar (katki_testi5 on kaydi):
  S TRIN  : bullSignal AL / bearSignal SAT (ayni mumda ikisi olamaz: biri close > open, digeri close < open ister).
  S TRINT : "Bullish Trinity Level Touched" AL / "Bearish Trinity Level Touched" SAT; ikisi birden ise yok.
  STOPS "Trinity seviyesi": uzun = bu mumun islemesinden sonra kapanisin altinda kalan en yakin aktif boga seviyesi; kisa = ustteki en yakin aktif ayi
  seviyesi; yoksa nan.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _trinity(o, h, l, c, lookback, expiry, maxlv):
    n = len(c)
    sig_al = np.zeros(n, np.bool_)
    sig_sat = np.zeros(n, np.bool_)
    t_al = np.zeros(n, np.bool_)
    t_sat = np.zeros(n, np.bool_)
    st_l = np.full(n, np.nan)
    st_s = np.full(n, np.nan)
    cap = maxlv + 5
    lv = np.empty(cap)
    dr = np.empty(cap, np.int64)
    sb = np.empty(cap, np.int64)
    na_ = 0
    ninact = 0
    body = np.abs(c - o)
    for i in range(n):
        # strength (filtre 0: yalnizca bilgi)
        s0 = max(0, i - lookback + 1)
        mx = 0.0
        for k in range(s0, i + 1):
            if body[k] > mx:
                mx = body[k]
        strength = min(100.0, body[i] / mx * 100.0) if mx > 0 else 0.0
        bull = False
        bear = False
        if i >= 2:
            bull = c[i] > o[i] and h[i] > h[i - 2] and l[i - 1] < l[i - 2] and h[i - 1] < h[i - 2] and c[i - 1] < o[i - 1] and c[i - 2] < o[i - 2]
            bear = c[i] < o[i] and l[i] < l[i - 2] and h[i - 1] > h[i - 2] and l[i - 1] > l[i - 2] and c[i - 1] > o[i - 1] and c[i - 2] > o[i - 2]
        bsig = bull and strength >= 0.0
        ssig = bear and strength >= 0.0
        # seviye taramasi (sondan basa)
        bt = False
        st = False
        j = na_ - 1
        while j >= 0:
            age = i - sb[j]
            if age > 0:
                wick = l[i] <= lv[j] if dr[j] == 1 else h[i] >= lv[j]
                expd = age >= expiry
                if wick or expd:
                    if wick and dr[j] == 1:
                        bt = True
                    if wick and dr[j] == -1:
                        st = True
                    for k in range(j, na_ - 1):
                        lv[k] = lv[k + 1]
                        dr[k] = dr[k + 1]
                        sb[k] = sb[k + 1]
                    na_ -= 1
                    ninact += 1
            j -= 1
        if bsig or ssig:
            while na_ + ninact >= maxlv:
                if ninact > 0:
                    ninact -= 1
                else:
                    for k in range(0, na_ - 1):
                        lv[k] = lv[k + 1]
                        dr[k] = dr[k + 1]
                        sb[k] = sb[k + 1]
                    na_ -= 1
            if bsig:
                lvl = min(l[i], l[i - 1], l[i - 2])
                d = 1
            else:
                lvl = max(h[i], h[i - 1], h[i - 2])
                d = -1
            lv[na_] = lvl
            dr[na_] = d
            sb[na_] = i
            na_ += 1
        sig_al[i] = bsig
        sig_sat[i] = ssig
        t_al[i] = bt and not st
        t_sat[i] = st and not bt
        bl = np.nan
        bs = np.nan
        for k in range(na_):
            if dr[k] == 1 and lv[k] < c[i]:
                if np.isnan(bl) or lv[k] > bl:
                    bl = lv[k]
            if dr[k] == -1 and lv[k] > c[i]:
                if np.isnan(bs) or lv[k] < bs:
                    bs = lv[k]
        st_l[i] = bl
        st_s[i] = bs
    return sig_al, sig_sat, t_al, t_sat, st_l, st_s


def hesapla(z):
    o, h, l, c = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("o", "h", "l", "c"))
    a, s, ta_, ts_, sl, ss = _trinity(o, h, l, c, 100, 100, 500)
    return {"S": {"TRIN": (a, s), "TRINT": (ta_, ts_)}, "D": {}, "U": {}, "X": {}, "STOPS": {"Trinity seviyesi": (sl, ss)}, "NATIVE": {}}
