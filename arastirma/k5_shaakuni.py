"""K5: Shaakuni - Liquidity Levels & Order Blocks v1.4.0 (Pine Script v6), yazar: Shaakuni, lisans: Mozilla Public License 2.0.
Yalnizca Order Block / POI kismi uyarlandi (yapi kirilimi + ATR itki mumu + tazelik kurali + ilk dokunus). Onceki gun/hafta uclari, EQ (%50)
cizgileri ve bilgi paneli daha once sinandi (BULGULAR 7, 9, 10e) ya da yalnizca canli mumda degerlendirilir; uyarlanmadi.
Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir. Kaynak alinti: scratchpad/k5_kaynak/S_shaakuni_ob.pine.

Varsayilan girdiler: showOB = true, Zone Lookback = Auto (1 dk grafik: timeframe.in_seconds <= 60 -> zoneLB = 2000), OB yapi geriye bakisi
obSwingLen = 10, itki carpani impMult = 0,7, ATR_PERIOD = 14, OB_MIN_HOFF = 3.

Ciktilar (katki_testi5 sozlesmesi):
  S "SOBY" : bu mumda boga OB bolgesi eklendi (pushZone tip 5) AL; ayi OB bolgesi (tip 6) eklendi SAT; ikisi birden ise hicbiri.
             Tarih = olusum mumu (bar_index = yapi kirilimi mumu), OB mumu degil. Ikisinin ayni mumda olmasi imkansiz (boga: close > max(high[1..10]),
             ayi: close < min(low[1..10]) ve max(high) >= min(low)); kural yine de kodlandi.
  S "SOBM" : bu mumda en az bir taze boga (tip 5) bolgesi mitige oldu (ilk temas) AL; en az bir ayi (tip 6) bolgesi SAT; ikisi birden ise hicbiri.
  U "Shaakuni taze OB içinde" : bu mumun butun islemlerinden (ekleme, mitigasyon, budama) sonra close, mitige olmamis herhangi bir bolgenin
             [bot, top] araliginda. UYARI: bu durum yapisi geregi HEP yanlistir. Onceki mumlarda olusmus bir bolge bu mum sonunda hala taze ise
             high < bot ya da low > top demektir, close [low, high] icinde oldugundan araliga giremez. Bu mumda eklenen boga bolgesinin top'u
             <= hh < close, ayi bolgesinin bot'u >= ll > close. On kayitli tanim aynen uygulandi (kapsam %0 cikar).
  STOPS "Shaakuni OB" : (uzun, kisa). Uzun = top'u close'un altinda olan taze boga bolgelerinden top'u close'a en yakin (en buyuk top) olanin
             bot'u; kisa = bot'u close'un ustunde olan taze ayi bolgelerinden bot'u en yakin (en kucuk bot) olanin top'u. Bu mumda eklenen bolgeler
             dahil (islemlerden sonra). Esitlikte en son eklenen bolge secilir. Yoksa nan.
  D, X, NATIVE: bos.

Pine anlamina uyum kararlari:
  - ta.atr(14) = ta.rma(ta.tr(true), 14): ilk TR = high - low (onceki kapanis na), sonra max(h - l, |h - c[1]|, |l - c[1]|). RMA tohumu ilk 14 TR'nin
    SMA'si (0 tabanli 13. mumda), sonra alpha * tr + (1 - alpha) * onceki, alpha = 1/14. 0-12. mumlarda na.
  - 'barstate.isconfirmed and not na(atrVal) and bar_index > obSwingLen + 2': gecmis mumlarin hepsi onayli; kosul bar_index >= 13 demektir.
    Her sey mum kapanisinda, yalnizca t ve onceki mumlarla hesaplanir (repaint yok). bar_index = npz'deki sira (verinin ilk mumu 0).
  - Pine for dongusu 'for x = a to b' b < a ise ASAGI sayar: butun dongulerde adim = (b >= a ? +1 : -1), uclar dahil (_adim). Pratikte:
    'for i = 2 to hOff - 1' hOff >= 3 ile hep yukari; 'for k = 0 to mnOff - 1' mnOff >= 1 ile hep yukari; 'for j = dOff + 1 to mnOff' de hep
    yukari, cunku o = mnOff - 1 - k ile dOff en fazla mnOff - 1 olur (dOff + 1 <= mnOff); 'for k = 0 to obOff - 2' obOff >= 2 korumali.
    Genel adim yine de uygulandi.
  - Yapi aramalarinda kesin esitsizlik (high[i] > hh, low[i] < mnLow ...): esitlikte daha yakin (kucuk ofsetli) mum kalir.
  - Itki mumu: (close[o] - open[o]) >= atrVal * impMult; atrVal bu mumun ATR'si (gecmis mumun degil), Pine'daki carpim sirasi korundu.
    k dongusu o = mnOff - 1 ... 0 sirasiyla (dibe en yakin itki mumundan bugune) ilk uyani alir, break.
  - OB mumu: j = dOff + 1 ... mnOff, ilk ters renkli mum (boga icin close < open), yoksa obOff = mnOff.
  - Tazelik: obOff >= 2 ise k = 0 ... obOff - 2 (bu mum dahil, OB'den hemen sonraki mum haric) her mumda low[k] > high[obOff] (ayi: high[k] < low[obOff]);
    obOff = 1 ise kontrol yok (taze).
  - Tekrar engeli: obBar = bar_index - obOff, tip basina son eklenen OB mumu (lastBullObBar / lastBearObBar) ile ayniysa eklenmez; yalnizca
    eklendiginde guncellenir.
  - Bolge: top = high[obOff], bot = low[obOff], olusum = bar_index, durum 0.
  - Mitigasyon (eklemeden sonra, ayni mumda): olusum < bar_index ve durum 0 olan bolge 'high >= bot and low <= top' ise durum 2. Pine sondan basa
    gezer; sira ciktilari etkilemez. Mitige bolgeler bir daha taze olmaz ve hicbir ciktida kullanilmaz; bu yuzden ic listeden hemen silinir (esdeger).
  - Budama mitigasyondan SONRA: olusum < bar_index - zoneLB olan bolgeler silinir (durumdan bagimsiz). Yani olusum = bar_index - 2001 olan bir bolge
    bu mumda once mitige olabilir (SOBM sayilir), sonra silinir. Taze bolgeler olusum ∈ [bar_index - 2000, bar_index] araliginda yasar.
  - zBox / box.new ve max_boxes_count = 500 yalnizca cizimdir: Pine en eski kutuyu silse de diziler degismez; mantiga etkisi yok, uyarlanmadi.
"""
import math, os, sys, time
import numpy as np
from numba import njit

OB_SWING, IMP_MULT, ATR_LEN, OB_MIN_HOFF, ZONE_LB = 10, 0.7, 14, 3, 2000


@njit(cache=True)
def atr_pine(h, l, c, length):
    """ta.atr(length): RMA(ta.tr(true)), SMA tohumlu; ilk length-1 mum nan."""
    n = len(c)
    out = np.full(n, np.nan)
    if n < length:
        return out
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(max(h[i] - l[i], abs(h[i] - c[i - 1])), abs(l[i] - c[i - 1]))
    s = 0.0
    for i in range(length):
        s += tr[i]
    prev = s / length
    out[length - 1] = prev
    alpha = 1.0 / length
    for i in range(length, n):
        prev = alpha * tr[i] + (1.0 - alpha) * prev
        out[i] = prev
    return out


@njit(inline="always")
def _adim(a, b):
    """Pine 'for x = a to b': b < a ise asagi sayar."""
    return 1 if b >= a else -1


@njit(cache=True)
def _shaakuni_ob(o, h, l, c, atr, swing, imp, min_hoff, zlb):
    n = len(c)
    cap = 2 * zlb + 16  # tip basina mum basina en fazla 1 ekleme, taze bolge en fazla zlb + 1 mum yasar
    zty = np.empty(cap, np.int64)
    ztop = np.empty(cap)
    zbot = np.empty(cap)
    zcb = np.empty(cap, np.int64)
    nz = 0
    last_bull = -1
    last_bear = -1
    yb = np.zeros(n, np.bool_)
    ys = np.zeros(n, np.bool_)
    mb = np.zeros(n, np.bool_)
    ms = np.zeros(n, np.bool_)
    ins = np.zeros(n, np.bool_)
    lst = np.full(n, np.nan)
    sst = np.full(n, np.nan)
    for bi in range(n):
        if (not math.isnan(atr[bi])) and bi > swing + 2:
            av = atr[bi]
            # ---- boga OB
            hh = h[bi - 1]
            hoff = 1
            st = _adim(2, swing)
            for i in range(2, swing + st, st):
                if h[bi - i] > hh:
                    hh = h[bi - i]
                    hoff = i
            if c[bi] > hh and hoff >= min_hoff:
                mnlow = l[bi - 1]
                mnoff = 1
                e = hoff - 1
                st = _adim(2, e)
                for i in range(2, e + st, st):
                    if l[bi - i] < mnlow:
                        mnlow = l[bi - i]
                        mnoff = i
                doff = -1
                e = mnoff - 1
                st = _adim(0, e)
                for k in range(0, e + st, st):
                    oo = mnoff - 1 - k
                    if c[bi - oo] > o[bi - oo] and (c[bi - oo] - o[bi - oo]) >= av * imp:
                        doff = oo
                        break
                if doff >= 0:
                    oboff = mnoff
                    a = doff + 1
                    st = _adim(a, mnoff)
                    for j in range(a, mnoff + st, st):
                        if c[bi - j] < o[bi - j]:
                            oboff = j
                            break
                    fresh = True
                    if oboff >= 2:
                        e = oboff - 2
                        st = _adim(0, e)
                        for k in range(0, e + st, st):
                            if l[bi - k] <= h[bi - oboff]:
                                fresh = False
                                break
                    obbar = bi - oboff
                    if fresh and obbar != last_bull:
                        last_bull = obbar
                        zty[nz] = 5
                        ztop[nz] = h[bi - oboff]
                        zbot[nz] = l[bi - oboff]
                        zcb[nz] = bi
                        nz += 1
                        yb[bi] = True
            # ---- ayi OB
            ll = l[bi - 1]
            loff = 1
            st = _adim(2, swing)
            for i in range(2, swing + st, st):
                if l[bi - i] < ll:
                    ll = l[bi - i]
                    loff = i
            if c[bi] < ll and loff >= min_hoff:
                mxhigh = h[bi - 1]
                mxoff = 1
                e = loff - 1
                st = _adim(2, e)
                for i in range(2, e + st, st):
                    if h[bi - i] > mxhigh:
                        mxhigh = h[bi - i]
                        mxoff = i
                doff = -1
                e = mxoff - 1
                st = _adim(0, e)
                for k in range(0, e + st, st):
                    oo = mxoff - 1 - k
                    if c[bi - oo] < o[bi - oo] and (o[bi - oo] - c[bi - oo]) >= av * imp:
                        doff = oo
                        break
                if doff >= 0:
                    oboff = mxoff
                    a = doff + 1
                    st = _adim(a, mxoff)
                    for j in range(a, mxoff + st, st):
                        if c[bi - j] > o[bi - j]:
                            oboff = j
                            break
                    fresh = True
                    if oboff >= 2:
                        e = oboff - 2
                        st = _adim(0, e)
                        for k in range(0, e + st, st):
                            if h[bi - k] >= l[bi - oboff]:
                                fresh = False
                                break
                    obbar = bi - oboff
                    if fresh and obbar != last_bear:
                        last_bear = obbar
                        zty[nz] = 6
                        ztop[nz] = h[bi - oboff]
                        zbot[nz] = l[bi - oboff]
                        zcb[nz] = bi
                        nz += 1
                        ys[bi] = True
        # ---- mitigasyon (bu mumda eklenenler haric); mitige olan ic listeden cikar
        w = 0
        for q in range(nz):
            keep = True
            if bi > zcb[q] and h[bi] >= zbot[q] and l[bi] <= ztop[q]:
                keep = False
                if zty[q] == 5:
                    mb[bi] = True
                else:
                    ms[bi] = True
            if keep:
                zty[w] = zty[q]
                ztop[w] = ztop[q]
                zbot[w] = zbot[q]
                zcb[w] = zcb[q]
                w += 1
        nz = w
        # ---- budama (mitigasyondan sonra)
        cutoff = bi - zlb
        w = 0
        for q in range(nz):
            if zcb[q] >= cutoff:
                zty[w] = zty[q]
                ztop[w] = ztop[q]
                zbot[w] = zbot[q]
                zcb[w] = zcb[q]
                w += 1
        nz = w
        # ---- durum ve stoplar (islemlerden sonra)
        cc = c[bi]
        btop = -np.inf
        bbot = np.nan
        sbot = np.inf
        stop_ = np.nan
        for q in range(nz):
            if zbot[q] <= cc and cc <= ztop[q]:
                ins[bi] = True
            if zty[q] == 5:
                if ztop[q] < cc and ztop[q] >= btop:
                    btop = ztop[q]
                    bbot = zbot[q]
            else:
                if zbot[q] > cc and zbot[q] <= sbot:
                    sbot = zbot[q]
                    stop_ = ztop[q]
        lst[bi] = bbot
        sst[bi] = stop_
    return yb, ys, mb, ms, ins, lst, sst


def hesapla(z):
    o, h, l, c = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("o", "h", "l", "c"))
    atr = atr_pine(h, l, c, ATR_LEN)
    yb, ys, mb, ms, ins, lst, sst = _shaakuni_ob(o, h, l, c, atr, OB_SWING, IMP_MULT, OB_MIN_HOFF, ZONE_LB)
    both_y = yb & ys
    both_m = mb & ms
    return {
        "S": {"SOBY": (yb & ~both_y, ys & ~both_y), "SOBM": (mb & ~both_m, ms & ~both_m)},
        "D": {},
        "U": {"Shaakuni taze OB içinde": ins},
        "X": {},
        "STOPS": {"Shaakuni OB": (lst, sst)},
        "NATIVE": {},
    }


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import izleme
    for s in (sys.argv[1:] or ["BTCUSDT", "HYPEUSDT"]):
        z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
        t0 = time.time()
        R = hesapla(z)
        dt = time.time() - t0
        n = len(z["c"])
        g = np.arange(n) >= 5000
        parca = [f"{k}: AL {int((a & g).sum())} SAT {int((b & g).sum())}" for k, (a, b) in R["S"].items()]
        for k, u in R["U"].items():
            parca.append(f"U[{k}] {int((u & g).sum())}")
        for k, (ls, ss) in R["STOPS"].items():
            parca.append(f"STOP[{k}] uzun dolu %{100 * np.isfinite(ls[g]).mean():.1f} kisa dolu %{100 * np.isfinite(ss[g]).mean():.1f}")
        print(f"{s} n={n} sure={dt:.2f} sn | " + " | ".join(parca))
