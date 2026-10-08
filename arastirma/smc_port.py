# LuxAlgo Smart Money Concepts mantiginin bagimsiz Python uygulamasi; yalnizca arastirma/test icin.
# Lisans: Algilama mantigi LuxAlgo'nun "Smart Money Concepts" betigine (c) LuxAlgo, CC BY-NC-SA 4.0 dayanir.
# Bu dosya o mantigin bir uyarlamasi olarak ayni lisansla (CC BY-NC-SA 4.0, ticari olmayan kullanim) paylasilir.
# https://creativecommons.org/licenses/by-nc-sa/4.0/ . VSP.pine bu dosyayi kullanmaz.
"""smc_port.py - SMC (LuxAlgo) algilama mantiginin kanonik Python uygulamasi.

LuxAlgo kodu kopyalanmadi; davranis, betigin algilama mantigi spesifikasyon olarak okunup
bastan yazildi. Iki bagimsiz portun (A, B) olay olay uzlastirilmasindan sonra tek kaynak budur.

Varsayilan girdiler (orijinaldeki gibi):
  swing boyu 50, ic (internal) boyu 5, EQH/EQL boyu 3 ve esik 0.1*ATR(200),
  ic OB acik (liste en fazla 100), swing OB kapali, OB filtresi ATR, OB gecersizlesme High/Low,
  ic yapida "confluence" filtresi kapali.
  FVG orijinalde varsayilan KAPALIDIR; burada "acik olsaydi" diye hesaplanir
  (grafik zaman dilimi, otomatik esik).

Pine anlamsal kurallari (uzlastirmada dogrulandi):
  * Karsilastirma islecleri float isleneni 9 ondalik basamaga yuvarlar (Pine belgesi, Type system).
    Fiyatlar bundan etkilenmez; etkisi ATR'ye ve FVG esigine dayali karsilastirmalardadir.
  * leg(): high[boy] > ta.highest(boy) (son 'boy' bar, icinde bulunulan bar dahil); tepe onceliklidir.
  * ta.crossover(close, seviye): onceki barin seviyesiyle karsilastirir; 'crossed' bayragi yeni
    pivotta sifirlanir; bir barda once ic, sonra swing yapisi; her birinde once boga, sonra ayi.
  * "for [i, x] in dizi" icinde dizi.remove(i): indeks her turda artar, boyut yeniden okunur;
    silinen ogenin hemen ardindaki oge o gecis icin kontrol edilmez.
  * Bar sirasi: trailing guncelle -> FVG sil -> pivotlar (50, 5, 3) -> ic yapi (+OB) -> swing yapi
    -> ic OB sil -> yeni FVG.

Disari acilan islev:
  olaylar(npz_yolu) -> (olay DataFrame'i, bar DataFrame'i)
    olay sutunlari: kind, bar, bar_ts, level, prev_level, pivot_ts, prev_pivot_ts, top, bottom,
                    ob_ts, created_ts, bias
    bar sutunlari : bar_ts, internal_bias, swing_bias, trailing_top, trailing_bottom (bar sonu durumu)
  bar_ts = mumun ACILIS zamani (unix sn, UTC); olay o mumun kapanisinda olusur.

Oz-sinama (hizli surum == harfi harfine bar-bar surum):
  python3 arastirma/smc_port.py --oz-sina VERI.npz [BAR_SAYISI]
"""
import math
import sys
import time

import numpy as np
import pandas as pd

SWING_BOY = 50
IC_BOY = 5
ESIT_BOY = 3
ESIT_ESIK = 0.1
ATR_BOY = 200
OB_SINIR = 100
BOGA = 1
AYI = -1

TURLER = ['swing_pivot_high', 'swing_pivot_low', 'internal_pivot_high', 'internal_pivot_low', 'EQH', 'EQL',
          'BOS_swing_bull', 'BOS_swing_bear', 'CHoCH_swing_bull', 'CHoCH_swing_bear',
          'BOS_int_bull', 'BOS_int_bear', 'CHoCH_int_bull', 'CHoCH_int_bear',
          'OB_int_new', 'OB_int_mitigated', 'FVG_new', 'FVG_filled']
SUTUNLAR = ['kind', 'bar', 'bar_ts', 'level', 'prev_level', 'pivot_ts', 'prev_pivot_ts', 'top', 'bottom',
            'ob_ts', 'created_ts', 'bias']
TAMSAYI = ['pivot_ts', 'prev_pivot_ts', 'ob_ts', 'created_ts', 'bias']


# ------------------------------------------------------------------------------------------------
# temel yardimcilar
# ------------------------------------------------------------------------------------------------
def _y9(x):
    """Pine karsilastirma kurali: float isleneni 9 ondalik basamaga yuvarla (NaN korunur)."""
    return np.round(x, 9)


def _atr(h, l, c, boy=ATR_BOY):
    """ta.atr(boy): gercek araligin RMA'si. Ilk bar TR = high-low; ilk deger ilk 'boy' TR'nin ortalamasi."""
    n = len(h)
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum(np.maximum(h[1:] - l[1:], np.abs(h[1:] - c[:-1])), np.abs(l[1:] - c[:-1]))
    sonuc = np.full(n, np.nan)
    if n < boy:
        return sonuc
    trl = tr.tolist()
    toplam = 0.0
    for x in trl[:boy]:
        toplam += x
    deger = toplam / boy
    a = 1.0 / boy
    b = 1.0 - a
    cikti = [deger]
    for x in trl[boy:]:
        deger = a * x + b * deger
        cikti.append(deger)
    sonuc[boy - 1:] = cikti
    return sonuc


def _pivot_tespit(hk, lk, boy):
    """leg(boy) + ta.change: (tepe pivotu tespit barlari, dip pivotu tespit barlari).
    Pivot bari = tespit bari - boy."""
    n = len(hk)
    tepe = np.zeros(n, bool)
    dip = np.zeros(n, bool)
    if n > boy:
        ust = pd.Series(hk).rolling(boy).max().to_numpy()   # ta.highest(boy): [t-boy+1, t]
        alt = pd.Series(lk).rolling(boy).min().to_numpy()
        tepe[boy:] = hk[:-boy] > ust[boy:]
        dip[boy:] = lk[:-boy] < alt[boy:]
    kod = np.full(n, -1, np.int8)
    kod[dip] = 1          # boga bacagi
    kod[tepe] = 0         # ayi bacagi (ikisi birden olursa tepe kazanir)
    son = np.where(kod >= 0, np.arange(n), -1)
    np.maximum.accumulate(son, out=son)
    bacak = np.where(son >= 0, kod[np.maximum(son, 0)], 0).astype(np.int8)   # var leg = 0
    degisim = np.diff(bacak, prepend=bacak[:1])                             # ilk bar: degisim yok
    return np.flatnonzero(degisim == -1), np.flatnonzero(degisim == 1)


def _pivot_durumu(n, tespit, boy, kaynak):
    """Pivot nesnesinin bar sonu durumu: seviye, pivot bari, segment no (0 = henuz pivot yok)."""
    segment = np.zeros(n, np.int64)
    segment[tespit] = 1
    segment = np.cumsum(segment)
    sira = segment - 1
    var_mi = sira >= 0
    seviye = np.full(n, np.nan)
    pbar = np.full(n, -1, np.int64)
    seviye[var_mi] = kaynak[tespit - boy][sira[var_mi]]
    pbar[var_mi] = (tespit - boy)[sira[var_mi]]
    return seviye, pbar, segment


def _kirilim(ck, seviye_k, segment, ek_kosul, yukari):
    """crossover/crossunder(close, seviye) and not crossed and ek_kosul.
    'crossed' yeni pivotta sifirlandigi icin her segmentte yalnizca ilk aday gecerlidir."""
    onceki_c = np.r_[np.nan, ck[:-1]]
    onceki_s = np.r_[np.nan, seviye_k[:-1]]
    with np.errstate(invalid='ignore'):
        if yukari:
            aday = (ck > seviye_k) & (onceki_c <= onceki_s)
        else:
            aday = (ck < seviye_k) & (onceki_c >= onceki_s)
    if ek_kosul is not None:
        aday &= ek_kosul
    idx = np.flatnonzero(aday & (segment > 0))
    if len(idx) == 0:
        return idx
    s = segment[idx]
    ilk = np.r_[True, s[1:] != s[:-1]]
    return idx[ilk]


def _egilim(n, boga, ayi):
    """Kirilimlari zaman sirasina dizer (ayni barda once boga), CHoCH etiketini ve bar sonu egilimini verir."""
    zaman = np.r_[boga, ayi].astype(np.int64)
    yon = np.r_[np.full(len(boga), BOGA), np.full(len(ayi), AYI)].astype(np.int8)
    sira = np.lexsort((-yon, zaman))
    zaman = zaman[sira]
    yon = yon[sira]
    onceki = np.r_[np.int8(0), yon[:-1]]
    choch = onceki == -yon                       # onceki egilim ters yondeyse CHoCH, degilse BOS
    k = np.searchsorted(zaman, np.arange(n), side='right') - 1
    seri = np.zeros(n, np.int8)
    if len(zaman):
        seri[k >= 0] = yon[k[k >= 0]]
    return zaman, yon, choch, seri


def _uc_seri(kaynak, tespit, seviye, n, en_buyuk):
    """trailing.top / bottom: swing pivot tespitinde pivot seviyesine kurulur, sonra kumulatif max/min.
    Ilk swing pivotundan once na (math.max(x, na) = na)."""
    sonuc = np.full(n, np.nan)
    if len(tespit) == 0:
        return sonuc
    dizi = kaynak.astype(float).copy()
    dizi[tespit] = seviye
    grup = np.zeros(n, np.int64)
    grup[tespit] = 1
    grup = np.cumsum(grup)
    b0 = tespit[0]
    s = pd.Series(dizi[b0:]).groupby(grup[b0:])
    sonuc[b0:] = (s.cummax() if en_buyuk else s.cummin()).to_numpy()
    return sonuc


def _bolge_listesi(n, hk, lk, ekleme, ust, alt, yon, once_ekle, sinir=None):
    """OB / FVG dizisinin bar bar yurutulmesi (en yeni basta; unshift).
    ekleme: artan sirali ekleme barlari (kimlik = dizideki sira). once_ekle=True: OB (ekle, sonra sil);
    False: FVG (sil, sonra ekle). Silme gecisi Pine 'for [i, x] in dizi' + remove(i) davranisidir.
    Doner: silinmeler [(bar, kimlik)], sinir nedeniyle dusurulen sayisi, son dizi."""
    eb = ekleme.tolist()
    ul = ust.tolist()
    al = alt.tolist()
    yl = yon.tolist()
    hl = hk.tolist()
    ll = lk.tolist()
    m = len(eb)
    j = 0
    siradaki = eb[0] if m else n
    dizi = []
    silinen = []
    dusen = 0
    INF = math.inf
    ayi_alt_sinir = INF     # ayi bolgelerinin en dusuk ust kenari
    boga_ust_sinir = -INF   # boga bolgelerinin en yuksek alt kenari

    def sinirlar():
        a, b = INF, -INF
        for k in dizi:
            if yl[k] == AYI:
                if ul[k] < a:
                    a = ul[k]
            elif al[k] > b:
                b = al[k]
        return a, b

    def ekle(t):
        nonlocal j, siradaki, dusen, ayi_alt_sinir, boga_ust_sinir
        while j < m and eb[j] == t:
            if sinir is not None and len(dizi) >= sinir:
                dizi.pop()                  # en eskisi duser
                dusen += 1
                ayi_alt_sinir, boga_ust_sinir = sinirlar()
            dizi.insert(0, j)
            if yl[j] == AYI:
                ayi_alt_sinir = min(ayi_alt_sinir, ul[j])
            else:
                boga_ust_sinir = max(boga_ust_sinir, al[j])
            j += 1
        siradaki = eb[j] if j < m else n

    for t in range(n):
        if once_ekle and t == siradaki:
            ekle(t)
        ht = hl[t]
        lt = ll[t]
        if ht > ayi_alt_sinir or lt < boga_ust_sinir:
            i = 0
            while i < len(dizi):
                k = dizi[i]
                if (yl[k] == AYI and ht > ul[k]) or (yl[k] == BOGA and lt < al[k]):
                    del dizi[i]
                    silinen.append((t, k))
                i += 1                      # silmeden sonra da artar: ardindaki oge atlanir
            ayi_alt_sinir, boga_ust_sinir = sinirlar()
        if (not once_ekle) and t == siradaki:
            ekle(t)
    return silinen, dusen, dizi


def _tablo(tur, bar, ts, **alanlar):
    m = len(bar)
    d = {'kind': np.full(m, tur, dtype=object), 'bar': np.asarray(bar, np.int64), 'bar_ts': ts[bar]}
    for s in SUTUNLAR[3:]:
        d[s] = np.asarray(alanlar[s], float) if s in alanlar else np.full(m, np.nan)
    return pd.DataFrame(d, columns=SUTUNLAR)


# ------------------------------------------------------------------------------------------------
# hizli (vektorel + olay odakli) hesap
# ------------------------------------------------------------------------------------------------
def hesapla(ts, o, h, l, c):
    """Tum barlar icin SMC olaylari ve bar sonu durum serileri."""
    ts = np.asarray(ts, np.int64)
    o, h, l, c = (np.asarray(x, np.float64) for x in (o, h, l, c))
    n = len(c)
    hk, lk, ck = _y9(h), _y9(l), _y9(c)          # karsilastirma kopyalari (fiyatlarda kimlik donusumu)
    atr = _atr(h, l, c)
    with np.errstate(invalid='ignore'):
        oynak = _y9(h - l) >= _y9(2.0 * atr)       # highVolatilityBar (ATR na iken False)
    p_ust = np.where(oynak, l, h)                  # parsedHigh
    p_alt = np.where(oynak, h, l)                  # parsedLow
    tablolar = []

    # pivotlar
    sw_t, sw_d = _pivot_tespit(hk, lk, SWING_BOY)
    ic_t, ic_d = _pivot_tespit(hk, lk, IC_BOY)
    es_t, es_d = _pivot_tespit(hk, lk, ESIT_BOY)
    for tur, tespit, boy, kaynak in (('swing_pivot_high', sw_t, SWING_BOY, h), ('swing_pivot_low', sw_d, SWING_BOY, l),
                                     ('internal_pivot_high', ic_t, IC_BOY, h), ('internal_pivot_low', ic_d, IC_BOY, l)):
        tablolar.append(_tablo(tur, tespit, ts, level=kaynak[tespit - boy], pivot_ts=ts[tespit - boy]))

    # EQH / EQL: ayni yondeki bir onceki boy-3 pivotuna uzaklik < 0.1 * ATR (o barin ATR'si)
    for tur, tespit, kaynak in (('EQH', es_t, h), ('EQL', es_d, l)):
        sev = kaynak[tespit - ESIT_BOY]
        onceki = np.r_[np.nan, sev[:-1]]
        onceki_ts = np.r_[np.nan, ts[tespit - ESIT_BOY][:-1].astype(float)]
        with np.errstate(invalid='ignore'):
            uygun = _y9(np.abs(onceki - sev)) < _y9(ESIT_ESIK * atr[tespit])
        b = tespit[uygun]
        tablolar.append(_tablo(tur, b, ts, level=sev[uygun], prev_level=onceki[uygun], pivot_ts=ts[b - ESIT_BOY],
                               prev_pivot_ts=onceki_ts[uygun]))

    # pivot nesnelerinin bar sonu durumlari
    SH, SHp, SHs = _pivot_durumu(n, sw_t, SWING_BOY, h)
    SL, SLp, SLs = _pivot_durumu(n, sw_d, SWING_BOY, l)
    IH, IHp, IHs = _pivot_durumu(n, ic_t, IC_BOY, h)
    IL, ILp, ILs = _pivot_durumu(n, ic_d, IC_BOY, l)
    SHk, SLk, IHk, ILk = _y9(SH), _y9(SL), _y9(IH), _y9(IL)

    # ic yapi: ek kosul ic seviye != swing seviye (na karsilastirmasi yanlis sayilir)
    with np.errstate(invalid='ignore'):
        ek_ust = ~np.isnan(IH) & ~np.isnan(SH) & (IHk != SHk)
        ek_alt = ~np.isnan(IL) & ~np.isnan(SL) & (ILk != SLk)
    kir = {
        'int': (_kirilim(ck, IHk, IHs, ek_ust, True), _kirilim(ck, ILk, ILs, ek_alt, False), IH, IL, IHp, ILp),
        'swing': (_kirilim(ck, SHk, SHs, None, True), _kirilim(ck, SLk, SLs, None, False), SH, SL, SHp, SLp),
    }
    seriler = {}
    ob_bar = ob_k = ob_yon = None
    for kapsam, (boga, ayi, ust_sev, alt_sev, ust_p, alt_p) in kir.items():
        zaman, yon, choch, seri = _egilim(n, boga, ayi)
        seriler[kapsam] = seri
        for yn, ad in ((BOGA, 'bull'), (AYI, 'bear')):
            sev = ust_sev if yn == BOGA else alt_sev
            pb = ust_p if yn == BOGA else alt_p
            for etiket, sec in (('BOS', ~choch), ('CHoCH', choch)):
                b = zaman[(yon == yn) & sec]
                tablolar.append(_tablo('%s_%s_%s' % (etiket, kapsam, ad), b, ts, level=sev[b], pivot_ts=ts[pb[b]],
                                       bias=np.full(len(b), yn)))
        if kapsam == 'int':
            # ic OB: boga kirilimi -> [ic tepe pivot bari, kirilim bari) araliginda en kucuk parsedLow'un bari;
            # ayi kirilimi -> [ic dip pivot bari, kirilim bari) araliginda en buyuk parsedHigh'in bari (ilk esit)
            ob_bar = zaman
            ob_yon = yon
            ob_k = np.empty(len(zaman), np.int64)
            for i, (t, yn) in enumerate(zip(zaman.tolist(), yon.tolist())):
                if yn == BOGA:
                    p = int(IHp[t])
                    ob_k[i] = p + int(np.argmin(p_alt[p:t]))
                else:
                    p = int(ILp[t])
                    ob_k[i] = p + int(np.argmax(p_ust[p:t]))

    # ic OB listesi (ekle -> sil), en fazla 100
    ob_ust = p_ust[ob_k]
    ob_alt = p_alt[ob_k]
    silinen, ob_dusen, ob_son = _bolge_listesi(n, hk, lk, ob_bar, _y9(ob_ust), _y9(ob_alt), ob_yon, True, OB_SINIR)
    tablolar.append(_tablo('OB_int_new', ob_bar, ts, top=ob_ust, bottom=ob_alt, ob_ts=ts[ob_k], created_ts=ts[ob_bar],
                           bias=ob_yon))
    if silinen:
        sb, sk = (np.array(x, np.int64) for x in zip(*silinen))
        tablolar.append(_tablo('OB_int_mitigated', sb, ts, top=ob_ust[sk], bottom=ob_alt[sk], ob_ts=ts[ob_k[sk]],
                               created_ts=ts[ob_bar[sk]], bias=ob_yon[sk]))

    # FVG (grafik zaman dilimi; otomatik esik = 2 * ortalama |onceki mum degisimi %|)
    yuzde = np.full(n, np.nan)
    yuzde[1:] = (c[:-1] - o[:-1]) / (o[:-1] * 100)
    mutlak = np.abs(yuzde)
    mutlak[0] = 0.0                                # ta.cum na'yi atlar
    esik = np.full(n, np.nan)
    esik[1:] = np.cumsum(mutlak)[1:] / np.arange(1, n) * 2
    boga = np.zeros(n, bool)
    ayi = np.zeros(n, bool)
    with np.errstate(invalid='ignore'):
        boga[2:] = (lk[2:] > hk[:-2]) & (ck[1:-1] > hk[:-2]) & (_y9(yuzde[2:]) > _y9(esik[2:]))
        ayi[2:] = (hk[2:] < lk[:-2]) & (ck[1:-1] < lk[:-2]) & (_y9(-yuzde[2:]) > _y9(esik[2:]))
    fv_bar = np.flatnonzero(boga | ayi)            # ayni barda ikisi birden olamaz
    fv_yon = np.where(boga[fv_bar], BOGA, AYI).astype(np.int8)
    fv_ust = np.where(boga[fv_bar], l[fv_bar], h[fv_bar])
    fv_alt = np.where(boga[fv_bar], h[fv_bar - 2], l[fv_bar - 2])
    fsil, _, fv_son = _bolge_listesi(n, hk, lk, fv_bar, _y9(fv_ust), _y9(fv_alt), fv_yon, False)
    tablolar.append(_tablo('FVG_new', fv_bar, ts, top=fv_ust, bottom=fv_alt, created_ts=ts[fv_bar], bias=fv_yon))
    if fsil:
        sb, sk = (np.array(x, np.int64) for x in zip(*fsil))
        tablolar.append(_tablo('FVG_filled', sb, ts, top=fv_ust[sk], bottom=fv_alt[sk], created_ts=ts[fv_bar[sk]],
                               bias=fv_yon[sk]))

    olay = pd.concat([t for t in tablolar if len(t)], ignore_index=True)
    olay = olay.sort_values(['bar', 'kind'], kind='mergesort').reset_index(drop=True)
    for s in TAMSAYI:
        olay[s] = olay[s].round().astype('Int64')
    olay.attrs['istatistik'] = {'yuksek_oynak_bar': int(oynak.sum()), 'ob_sinir_dusen': ob_dusen,
                                'ob_acik_son': len(ob_son), 'fvg_acik_son': len(fv_son)}
    barlar = pd.DataFrame({'bar_ts': ts, 'internal_bias': seriler['int'], 'swing_bias': seriler['swing'],
                           'trailing_top': _uc_seri(h, sw_t, h[sw_t - SWING_BOY], n, True),
                           'trailing_bottom': _uc_seri(l, sw_d, l[sw_d - SWING_BOY], n, False)})
    return olay, barlar


def olaylar(npz_yolu):
    """npz (ts, o, h, l, c) -> (olay DataFrame'i, bar DataFrame'i). Tum barlar hesaplanir."""
    z = np.load(npz_yolu)
    return hesapla(z['ts'], z['o'], z['h'], z['l'], z['c'])


# ------------------------------------------------------------------------------------------------
# harfi harfine bar-bar surum (yalnizca oz-sinama; yavas)
# ------------------------------------------------------------------------------------------------
def _referans(ts, o, h, l, c):
    T, O, H, L, C = (np.asarray(x).tolist() for x in (ts, o, h, l, c))
    n = len(C)
    nan = math.nan
    isn = math.isnan

    def y(x):
        return x if isn(x) else round(x * 1e9) / 1e9

    def buyuk(a, b):
        return (not isn(a)) and (not isn(b)) and y(a) > y(b)

    def kucuk(a, b):
        return (not isn(a)) and (not isn(b)) and y(a) < y(b)

    def bk(a, b):
        return (not isn(a)) and (not isn(b)) and y(a) >= y(b)

    def kk(a, b):
        return (not isn(a)) and (not isn(b)) and y(a) <= y(b)

    piv = {k: {'sev': nan, 'gecti': False, 'ts': None, 'bar': None} for k in ('sH', 'sL', 'iH', 'iL', 'eH', 'eL')}
    egilim = {'int': 0, 'swing': 0}
    bacak = {SWING_BOY: 0, IC_BOY: 0, ESIT_BOY: 0}
    onceki_bacak = {SWING_BOY: None, IC_BOY: None, ESIT_BOY: None}
    onceki_sev = {}
    ust_uc, alt_uc = nan, nan
    pu, pa = [], []
    obs, fvgs = [], []
    atr, tr_ilk, toplam_yuzde = nan, [], 0.0
    E, B = [], []

    def yaz(tur, t, **k):
        r = dict.fromkeys(SUTUNLAR, nan)
        r.update(kind=tur, bar=t, bar_ts=T[t], **k)
        E.append(r)

    for t in range(n):
        tr = H[t] - L[t] if t == 0 else max(H[t] - L[t], abs(H[t] - C[t - 1]), abs(L[t] - C[t - 1]))
        if t < ATR_BOY:
            tr_ilk.append(tr)
            if t == ATR_BOY - 1:
                s = 0.0
                for x in tr_ilk:
                    s += x
                atr = s / ATR_BOY
        else:
            atr = (1.0 / ATR_BOY) * tr + (1.0 - 1.0 / ATR_BOY) * atr
        oyn = bk(H[t] - L[t], 2 * atr)
        pu.append(L[t] if oyn else H[t])
        pa.append(H[t] if oyn else L[t])
        ust_uc = nan if isn(ust_uc) else max(H[t], ust_uc)
        alt_uc = nan if isn(alt_uc) else min(L[t], alt_uc)
        i = 0                                                          # FVG silme
        while i < len(fvgs):
            g = fvgs[i]
            if (g['yon'] == BOGA and kucuk(L[t], g['alt'])) or (g['yon'] == AYI and buyuk(H[t], g['ust'])):
                fvgs.pop(i)
                yaz('FVG_filled', t, top=g['ust'], bottom=g['alt'], created_ts=g['ts'], bias=g['yon'])
            i += 1
        for boy, ad in ((SWING_BOY, 's'), (IC_BOY, 'i'), (ESIT_BOY, 'e')):     # pivotlar
            if t >= boy:
                if buyuk(H[t - boy], max(H[t - boy + 1:t + 1])):
                    bacak[boy] = 0
                elif kucuk(L[t - boy], min(L[t - boy + 1:t + 1])):
                    bacak[boy] = 1
            once = onceki_bacak[boy]
            onceki_bacak[boy] = bacak[boy]
            if once is None or once == bacak[boy]:
                continue
            dip_mi = bacak[boy] - once == 1
            p = piv[ad + ('L' if dip_mi else 'H')]
            sev = L[t - boy] if dip_mi else H[t - boy]
            if ad == 'e' and kucuk(abs(p['sev'] - sev), ESIT_ESIK * atr):
                yaz('EQL' if dip_mi else 'EQH', t, level=sev, prev_level=p['sev'], pivot_ts=T[t - boy], prev_pivot_ts=p['ts'])
            p.update(sev=sev, gecti=False, ts=T[t - boy], bar=t - boy)
            if ad != 'e':
                yaz(('swing' if ad == 's' else 'internal') + ('_pivot_low' if dip_mi else '_pivot_high'), t, level=sev,
                    pivot_ts=T[t - boy])
            if ad == 's':
                if dip_mi:
                    alt_uc = sev
                else:
                    ust_uc = sev
        for ad, kapsam in (('i', 'int'), ('s', 'swing')):                     # yapi: once ic, sonra swing
            for yn, uc in ((BOGA, 'H'), (AYI, 'L')):
                p = piv[ad + uc]
                anahtar = ad + uc
                lp = onceki_sev.get(anahtar, nan)
                onceki_sev[anahtar] = p['sev']
                if t == 0:
                    continue
                if yn == BOGA:
                    kesisim = buyuk(C[t], p['sev']) and kk(C[t - 1], lp)
                else:
                    kesisim = kucuk(C[t], p['sev']) and bk(C[t - 1], lp)
                if ad == 'i':
                    a, b = piv['i' + uc]['sev'], piv['s' + uc]['sev']
                    ek = (not isn(a)) and (not isn(b)) and y(a) != y(b)
                else:
                    ek = True
                if kesisim and not p['gecti'] and ek:
                    etiket = 'CHoCH' if egilim[kapsam] == -yn else 'BOS'
                    p['gecti'] = True
                    egilim[kapsam] = yn
                    yaz('%s_%s_%s' % (etiket, kapsam, 'bull' if yn == BOGA else 'bear'), t, level=p['sev'],
                        pivot_ts=p['ts'], bias=yn)
                    if ad == 'i':
                        dilim = pa[p['bar']:t] if yn == BOGA else pu[p['bar']:t]
                        k = p['bar'] + dilim.index(min(dilim) if yn == BOGA else max(dilim))
                        if len(obs) >= OB_SINIR:
                            obs.pop()
                        obs.insert(0, {'ust': pu[k], 'alt': pa[k], 'yon': yn, 'obts': T[k], 'ts': T[t]})
                        yaz('OB_int_new', t, top=pu[k], bottom=pa[k], ob_ts=T[k], created_ts=T[t], bias=yn)
        i = 0                                                          # ic OB silme
        while i < len(obs):
            x = obs[i]
            if (x['yon'] == AYI and buyuk(H[t], x['ust'])) or (x['yon'] == BOGA and kucuk(L[t], x['alt'])):
                obs.pop(i)
                yaz('OB_int_mitigated', t, top=x['ust'], bottom=x['alt'], ob_ts=x['obts'], created_ts=x['ts'], bias=x['yon'])
            i += 1
        if t >= 1:                                                     # yeni FVG
            yzd = (C[t - 1] - O[t - 1]) / (O[t - 1] * 100)
            toplam_yuzde += abs(yzd)
            esik = toplam_yuzde / t * 2
            if t >= 2:
                if buyuk(L[t], H[t - 2]) and buyuk(C[t - 1], H[t - 2]) and buyuk(yzd, esik):
                    fvgs.insert(0, {'ust': L[t], 'alt': H[t - 2], 'yon': BOGA, 'ts': T[t]})
                    yaz('FVG_new', t, top=L[t], bottom=H[t - 2], created_ts=T[t], bias=BOGA)
                if kucuk(H[t], L[t - 2]) and kucuk(C[t - 1], L[t - 2]) and buyuk(-yzd, esik):
                    fvgs.insert(0, {'ust': H[t], 'alt': L[t - 2], 'yon': AYI, 'ts': T[t]})
                    yaz('FVG_new', t, top=H[t], bottom=L[t - 2], created_ts=T[t], bias=AYI)
        B.append((T[t], egilim['int'], egilim['swing'], ust_uc, alt_uc))
    olay = pd.DataFrame(E, columns=SUTUNLAR).sort_values(['bar', 'kind'], kind='mergesort').reset_index(drop=True)
    for s in TAMSAYI:
        olay[s] = olay[s].astype(float).round().astype('Int64')
    barlar = pd.DataFrame(B, columns=['bar_ts', 'internal_bias', 'swing_bias', 'trailing_top', 'trailing_bottom'])
    return olay, barlar


def _kanonik(ev):
    e = ev[SUTUNLAR].copy()
    for s in SUTUNLAR[1:]:
        e[s] = pd.to_numeric(e[s], errors='coerce').astype(float)
    return e.sort_values(SUTUNLAR, kind='mergesort').reset_index(drop=True)


def oz_sina(npz_yolu, bar_sayisi=200000):
    z = np.load(npz_yolu)
    k = slice(0, bar_sayisi)
    veri = [z[a][k] for a in ('ts', 'o', 'h', 'l', 'c')]
    t0 = time.time()
    e1, b1 = hesapla(*veri)
    t1 = time.time()
    e2, b2 = _referans(*veri)
    t2 = time.time()
    a, b = _kanonik(e1), _kanonik(e2)
    olay_ayni = a.shape == b.shape and bool((a['kind'] == b['kind']).all()) and all(
        np.array_equal(a[s].to_numpy(), b[s].to_numpy(), equal_nan=True) for s in SUTUNLAR[1:])
    seri_ayni = all(np.array_equal(b1[s].to_numpy(float), b2[s].to_numpy(float), equal_nan=True) for s in b1.columns)
    print('%s bar=%d hizli=%.1fs referans=%.1fs olay=%d/%d olaylar_ayni=%s seriler_ayni=%s' % (
        npz_yolu, len(veri[0]), t1 - t0, t2 - t1, len(a), len(b), olay_ayni, seri_ayni))
    return olay_ayni and seri_ayni


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--oz-sina':
        ok = oz_sina(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 200000)
        print('OZ-SINAMA', 'GECTI' if ok else 'BASARISIZ')
        sys.exit(0 if ok else 1)
    for yol in sys.argv[1:]:
        t0 = time.time()
        ev, br = olaylar(yol)
        print(yol, 'bar=%d olay=%d sure=%.1fs' % (len(br), len(ev), time.time() - t0), ev.attrs['istatistik'])
        print(ev.groupby('kind').size().reindex(TURLER, fill_value=0).to_string())
