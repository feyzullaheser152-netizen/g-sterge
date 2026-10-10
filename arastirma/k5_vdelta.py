"""K5 / vdelta: Volume Delta Pivot Matrix [BigBeluga] (1 dk; 22 Binance USDT-M paritesi). Sinyal, durum ve stop dizileri.

Kaynak gösterge: Volume Delta Pivot Matrix [BigBeluga], yazar BigBeluga, lisans CC BY-NC-SA 4.0
(https://creativecommons.org/licenses/by-nc-sa/4.0/). Varsayılan girdiler: Pivot Swing Length 5 (sol = sağ = 5),
Max Active Levels to Plot 10, Minimum Delta % Filter 20.
Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir. VSP.pine bu dosyayı kullanmaz.

Gösterge mantığı (her mumda, betik sırasıyla):
  1) Pivot tepe onaylandıysa (pivot mumu = bar_index - 5): wdlta = SUM_{i=0..10} delta(i), i ŞU ANKİ (onay) mumdan geriye sayılır
     (betikteki gibi; yani pivot mumunun 5 öncesinden 5 sonrasına 11 mum). delta(i): range = high[i] - low[i] > 0 ise
     volume[i] * ((close[i] - low[i]) / range * 2 - 1), değilse close[i] >= open[i] ? volume[i] : -volume[i].
     Direnç seviyesi (lvl = pivot tepe, dlta = wdlta) dizinin SONUNA eklenir.
  2) Aynısı pivot dip için -> destek. İkisi aynı mumda ise önce direnç, sonra destek eklenir (ikisinin wdlta'sı aynıdır).
  3) Kırılım denetimi (sondan başa): destek close <= lvl ise, direnç close >= lvl ise silinir (geçmişte barstate.isconfirmed doğru).
     Aynı mumda eklenen seviye de denetlenir (yalnızca eşitlikte silinebilir: pivot dip için close >= low >= lvl).

Çıktılar (sözleşme: katki_testi5.py):
  S "VDPB" : bu mumun kırılım denetiminde en az bir direnç silindiyse AL, en az bir destek silindiyse SAT; ikisi birden ise hiçbiri.
  S "VDPT" : ÖNCEKİ mumun sonundaki aktif seviyelerle (bu mumun eklemelerinden ve silmelerinden önce): herhangi bir destek için
             low <= lvl ve close > lvl -> AL; herhangi bir direnç için high >= lvl ve close < lvl -> SAT; ikisi birden ise hiçbiri.
  S "VDPTD": VDPT, yalnızca çizilecek seviyelerle (ön kayıttaki tanım): önceki mumun sonundaki aktif seviyelerden
             mdelt = max(0,0001, max |dlta|); en yeniden en eskiye, |dlta| / mdelt * 100 < 20 olanlar atlanır, en fazla 10 seviye alınır.
  D "Delta pivot konumu (en yakın seviye destek +)": bu mumun sonundaki aktif seviyelerden kapanışa en yakını destekse +1, dirençse -1,
             seviye yoksa 0. Eşit uzaklıkta bir destek ve bir direnç varsa 0.
  U "Delta pivot seviyesine yakın (≤ 0,5 ATR)": kapanışın en yakın aktif seviyeye uzaklığı <= 0,5 * ta.atr(14).
  STOPS "Delta pivot": uzun = kapanışın kesin altındaki en yakın aktif destek, kısa = kesin üstündeki en yakın aktif direnç; yoksa nan.
  X ve NATIVE boş (göstergenin kendi giriş/çıkış ya da stop kuralı yok).

Pine anlamına uyum kararları:
  - ta.pivothigh(high, 5, 5) / ta.pivotlow(low, 5, 5): topluluk_sinyal.pivot (sol taraf kesin, sağ taraf eşitliğe izin verir; sınanmış kural).
    Değer onay mumunda (pivot mumundan 5 sonra) bilinir ve o mumda kullanılır; her çıktı yalnızca t ve önceki mumlarla hesaplanır (repaint yok).
  - wdlta döngüsü 'for i = 0 to (lbars + rbars)' (dahil, 11 mum) ve geçmiş başvurusu onay mumundan; pivot ilk kez t = 10'da onaylanabildiği
    için high[10] vb. hiç na olmaz. Veride na yok (range > 0 karşılaştırması ve close >= open aynen).
  - Kırılım koşulu her seviye için bağımsızdır (yalnızca o mumun kapanışı ve seviyenin kendisi); bu nedenle sondan başa array.remove ile
    sıra korunarak tek geçişte sıkıştırma aynı sonucu verir.
  - Yalnızca son mumda çalışan kısım (barstate.islast: dizinin en eski seviyeleri silinerek mxlvl = 10'a indirilmesi ve %20 delta süzgeci)
    geçmiş duruma UYGULANMADI; parr yalnızca kırılımlarla küçülür. İç depolama sınırsızdır (kapasite dolunca ikiye katlanır; hiçbir seviye
    atılmaz, dolayısıyla depolama sınırı sonucu değiştirmez). Pine dizisinin 100.000 eleman sınırı veride aşılmıyor (sınama çıktısında en
    büyük boyut verilir).
  - calc_bars_count = 5000 ve max_bars_back = 5000 uygulanmadı: araştırma bütün geçmişle çalışır (spesifikasyon). Bir seviyenin akıbeti
    yalnızca kendisinden sonraki kapanışlara bağlı olduğundan calc_bars_count, grafiğin ilk hesaplanan mumundan önce eklenen seviyelerin
    atılmasına eşdeğerdir; sınama çıktısında aktif seviyelerin ne kadarının 5000 mumdan eski olduğu ve 5000 mumluk pencereyle sayımlar
    bilgi olarak verilir (_hesapla(..., pencere=5000)).
  - VDPTD: ön kayıttaki tanım aynen uygulandı (mdelt BÜTÜN aktif seviyelerin en büyük |dlta|'si). Göstergenin son mumdaki çizimi ise önce
    diziyi en yeni 10 seviyeye indirir, mdelt'i bu 10 seviyeden alır, sonra %20 süzgecini uygular. İki tanım aktif seviye 10'dan fazlayken
    ayrılabilir; sınama çıktısında "önce kırp" türünün sayımı yalnızca bilgi olarak verilir (modül çıktısı değil).
  - Kesirli işlem sırası Pine'daki gibi: (close - low) / range * 2 - 1 ve |dlta| / mdelt * 100.
  - Kırılım kuralı gereği mum sonunda bütün aktif destekler kapanışın kesin altında, dirençler kesin üstündedir; en yakın destek = en yüksek
    destek, en yakın direnç = en düşük direnç.
  - ta.atr(14): gerçek aralık (ilk mumda high - low), Pine RMA (ilk 14 değerin SMA'sıyla tohumlanır, sonra alfa = 1/14). ATR na iken
    (ilk 13 mum) ve aktif seviye yokken U yanlış.
  - Hacim: npz'deki v (taban hacim; TradingView'daki Binance vadeli hacmiyle aynı birim).
"""
import math, os, sys
import numpy as np
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topluluk_sinyal import pivot

# varsayılan girdiler
LBARS = 5
RBARS = LBARS
MXLVL = 10
MDPCT = 20.0
ATR_N = 14
YAKIN_ATR = 0.5
ESKI = 5000  # yalnızca bilgi: calc_bars_count


@njit(cache=True)
def pine_atr(h, l, c, n_):
    N = len(c)
    out = np.full(N, np.nan)
    a = 1.0 / n_
    s = 0.0
    for i in range(N):
        if i == 0:
            tr = h[i] - l[i]
        else:
            tr = max(h[i] - l[i], max(abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
        if i < n_:
            s += tr
            if i == n_ - 1:
                out[i] = s / n_
        else:
            out[i] = a * tr + (1.0 - a) * out[i - 1]
    return out


@njit(cache=True)
def _vdelta(o, h, l, c, v, ph, pl, atr, lb, rb, mxlvl, mdpct, yakin, pencere, eski):
    n = len(c)
    cap = 256
    lv = np.empty(cap)
    dl = np.empty(cap)
    sp = np.empty(cap, np.bool_)
    pb = np.empty(cap, np.int64)  # ekleme (onay) mumu
    m = 0
    b_al = np.zeros(n, np.bool_)
    b_sat = np.zeros(n, np.bool_)
    t_al = np.zeros(n, np.bool_)
    t_sat = np.zeros(n, np.bool_)
    d_al = np.zeros(n, np.bool_)
    d_sat = np.zeros(n, np.bool_)
    k_al = np.zeros(n, np.bool_)  # bilgi: "önce kırp" VDPTD türü
    k_sat = np.zeros(n, np.bool_)
    dur = np.zeros(n, np.int64)
    yak = np.zeros(n, np.bool_)
    st_l = np.full(n, np.nan)
    st_s = np.full(n, np.nan)
    aktif = np.zeros(n, np.int64)
    n_eski = np.zeros(n, np.int64)
    maxm = 0
    for t in range(n):
        cl = c[t]
        lo = l[t]
        hi = h[t]
        # --- dokunuşlar: önceki mumun sonundaki aktif seviyeler
        if m > 0:
            ta_ = False
            ts_ = False
            md = 0.0001
            for k in range(m):
                lk = lv[k]
                if sp[k]:
                    if lo <= lk and cl > lk:
                        ta_ = True
                elif hi >= lk and cl < lk:
                    ts_ = True
                a = abs(dl[k])
                if a > md:
                    md = a
            if ta_ != ts_:
                t_al[t] = ta_
                t_sat[t] = ts_
            da = False
            ds = False
            cnt = 0
            for k in range(m - 1, -1, -1):
                if abs(dl[k]) / md * 100.0 < mdpct:
                    continue
                lk = lv[k]
                if sp[k]:
                    if lo <= lk and cl > lk:
                        da = True
                elif hi >= lk and cl < lk:
                    ds = True
                cnt += 1
                if cnt >= mxlvl:
                    break
            if da != ds:
                d_al[t] = da
                d_sat[t] = ds
            # bilgi: önce en yeni mxlvl seviyeye kırp, mdelt'i onlardan al, sonra süz
            k0 = m - mxlvl if m > mxlvl else 0
            md2 = 0.0001
            for k in range(k0, m):
                a = abs(dl[k])
                if a > md2:
                    md2 = a
            ka = False
            ks = False
            for k in range(m - 1, k0 - 1, -1):
                if abs(dl[k]) / md2 * 100.0 < mdpct:
                    continue
                lk = lv[k]
                if sp[k]:
                    if lo <= lk and cl > lk:
                        ka = True
                elif hi >= lk and cl < lk:
                    ks = True
            if ka != ks:
                k_al[t] = ka
                k_sat[t] = ks
        # --- pivot seviyeleri: önce direnç, sonra destek
        yph = not math.isnan(ph[t])
        ypl = not math.isnan(pl[t])
        if yph or ypl:
            wd = 0.0
            for i in range(lb + rb + 1):
                j = t - i
                rg = h[j] - l[j]
                if rg > 0:
                    wd += v[j] * ((c[j] - l[j]) / rg * 2 - 1)
                else:
                    wd += v[j] if c[j] >= o[j] else -v[j]
            if m + 2 > cap:
                cap2 = cap * 2
                lv2 = np.empty(cap2)
                dl2 = np.empty(cap2)
                sp2 = np.empty(cap2, np.bool_)
                pb2 = np.empty(cap2, np.int64)
                lv2[:m] = lv[:m]
                dl2[:m] = dl[:m]
                sp2[:m] = sp[:m]
                pb2[:m] = pb[:m]
                lv, dl, sp, pb, cap = lv2, dl2, sp2, pb2, cap2
            if yph:
                lv[m] = ph[t]
                dl[m] = wd
                sp[m] = False
                pb[m] = t
                m += 1
            if ypl:
                lv[m] = pl[t]
                dl[m] = wd
                sp[m] = True
                pb[m] = t
                m += 1
        if m > maxm:
            maxm = m
        # --- kırılım denetimi (sıra korunarak sıkıştırma) ve mum sonu durumu
        brs = False
        brr = False
        w = 0
        bs = -np.inf
        br = np.inf
        ne = 0
        for k in range(m):
            if pencere > 0 and pb[k] <= t - pencere:
                continue
            if sp[k]:
                if cl <= lv[k]:
                    brs = True
                    continue
                if lv[k] > bs:
                    bs = lv[k]
            else:
                if cl >= lv[k]:
                    brr = True
                    continue
                if lv[k] < br:
                    br = lv[k]
            if pb[k] <= t - eski:
                ne += 1
            if w != k:
                lv[w] = lv[k]
                dl[w] = dl[k]
                sp[w] = sp[k]
                pb[w] = pb[k]
            w += 1
        m = w
        if brr != brs:
            b_al[t] = brr
            b_sat[t] = brs
        aktif[t] = m
        n_eski[t] = ne
        if m > 0:
            dsup = cl - bs
            dres = br - cl
            if bs > -np.inf:
                st_l[t] = bs
            if br < np.inf:
                st_s[t] = br
            if dsup < dres:
                dur[t] = 1
            elif dres < dsup:
                dur[t] = -1
            yk = dsup if dsup < dres else dres
            if not math.isnan(atr[t]) and yk <= yakin * atr[t]:
                yak[t] = True
    return b_al, b_sat, t_al, t_sat, d_al, d_sat, k_al, k_sat, dur, yak, st_l, st_s, aktif, n_eski, maxm


def _hesapla(z, pencere=0):
    o, h, l, c, v = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("o", "h", "l", "c", "v"))
    ph = pivot(h, LBARS, RBARS, True)
    pl = pivot(l, LBARS, RBARS, False)
    atr = pine_atr(h, l, c, ATR_N)
    return _vdelta(o, h, l, c, v, ph, pl, atr, LBARS, RBARS, MXLVL, MDPCT, YAKIN_ATR, pencere, ESKI)


def hesapla(z):
    b_al, b_sat, t_al, t_sat, d_al, d_sat, _ka, _ks, dur, yak, st_l, st_s, _akt, _ne, _mx = _hesapla(z)
    return {
        "S": {"VDPB": (b_al, b_sat), "VDPT": (t_al, t_sat), "VDPTD": (d_al, d_sat)},
        "D": {"Delta pivot konumu (en yakın seviye destek +)": dur},
        "U": {"Delta pivot seviyesine yakın (≤ 0,5 ATR)": yak},
        "X": {},
        "STOPS": {"Delta pivot": (st_l, st_s)},
        "NATIVE": {},
    }
