"""K3 / G2: seviyeler ve kirilimlar (1 dk; 22 Binance USDT-M paritesi). Topluluk gostergelerinin sinyal ve durum dizileri.

Kaynak gostergeler (varsayilan girdilerle):
  SRD   Support Resistance - Dynamic v2, LonesomeTheBlue, MPL 2.0. Pivot 10, High/Low, en fazla 20 pivot, kanal genisligi %10,
        en fazla 5 S/R, en az guc 2.
  BOF   Breakout Finder, LonesomeTheBlue, MPL 2.0. Periyot 5, en uzun kirilim 200, esik %3, en az 2 test.
  TLB2  Trend Lines v2, LonesomeTheBlue, MPL 2.0. Pivot 20, 3 pivot noktasi, en fazla 3 cizgi (baslangic tarihi filtresi: hep acik).
Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir.

Ciktilar:
  S  SRD  : (crossed_over, crossed_under) = alarmlardaki "Resistance Broken" / "Support Broken"; orta seviye = (ust + alt) / 2
            (round_to_mintick yok: tik boyu bilinmiyor, ham deger kullanildi).
     BOF  : (breakout, breakdown).
     TLB2 : gostergenin kendi sinyali yok; on kayitli "cizgi kirilimi" tanimi: t-1 mumunda gecerli cizgiler betikteki gibi hesaplanir
            (en fazla 3 yukselen, 3 dusen). Her cizgi bir mum ileri (t'ye) uzatilir. close[t] gecerli herhangi bir yukselen cizginin
            t degerinin altindaysa SAT, gecerli herhangi bir dusen cizginin t degerinin ustundeyse AL; ikisi birden ise hicbiri.
            Cizginin t degeri, betigin dogrulama dongusundeki ardisik toplamdir (hline; = t-1 degeri + diff), yani betik t mumunda
            dizi degismezse ayni kapanisi ayni degerle karsilastirir.
  D  "Trend çizgisi durumu": t mumunda en az bir gecerli yukselen cizgi var ve dusen yok +1; tersi -1; aksi 0.
  U  "S/R kanalında": close[t], SRD'nin o anki S/R bolgelerinden birinin [alt, ust] araliginda.

Pine anlamina uyum notlari:
  - Pivotlar topluluk_sinyal.pivot ile (sol taraf kesin, sag taraf esitlige izin verir); pivot bilgisi onay mumunda (pivot mumundan R sonra)
    kullanilir. Her deger yalnizca t ve oncesi mumlarin verisiyle hesaplanir (repaint yok).
  - SRD: 'if ph or pl' (v5 float -> bool: na yanlis); ikisi ayni mumda ise pivotvals'e ph eklenir. prdhighest/prdlowest = ta.highest/lowest(300)
    (ilk 299 mumda na -> cwidth na -> genislik karsilastirmasi yanlis -> guc 0). cwidth = (hh - ll) * 10 / 100 (Pine sirasiyla).
    get_sr_vals genislik kurali 'cpp <= lo ? hi - cpp : cpp - lo' ve lo/hi dongu icinde guncellenerek. sr_strength 'var' degil (her mum bos),
    sr_up_level/sr_dn_level 'var'; ancak sr_strength yalnizca pivot mumundaki yeniden hesapta, uc dizi birlikte temizlendikten sonra kullanilir.
    check_sr: ilk kesisen bolgede (mevcut bolgenin ust ya da alt ucu [lo, hi] icinde) guc >= ise o bolge silinir, degilse ret = yanlis; break.
    find_loc: sondan basa 'strength <= sr_strength[i]' olunca break. 'for i = na to 0' ve 'for x = 0 to na' donguleri calismaz (bos dizi).
  - BOF: lll = max(min(bar_index, 300), 1); h_/l_ = ta.highest/lowest(lll) (degisken uzunluk; ilk 300 mumda pencere 1..bar_index mumlari).
    chwidth = (h_ - l_) * (3 / 100). Temizlik dongusu 'for x = size - 1 to 1' asagi sayar ve array.pop SON elemani siler (0. eleman hic silinmez).
    hgst = ta.highest(5)[1], lwst = ta.lowest(5)[1]. breakout = not na(bomax) and num >= 2 (ilk kosul tutup ic kosul tutmazsa num = 0 -> yanlis).
  - TLB2: diziler na ile baslar (na karsilastirmalari yanlis); konumlar onay mumu indeksidir (pivot mumu = konum - prd).
    'for p2 = PPnum - 1 to p1 + 1' asagi sayar; ilk gecerli p2'de break. Dogrulama dongusu x = pos2 + 1 - prd .. bar_index kapanislari, hline ardisik
    toplamla (hline := hline + diff). Sayac kontrolleri (countline <= maxline / < maxline) aynen; PPnum = 3 ile p1 yalnizca 0 ve 1 oldugundan
    pratikte en fazla 2 yukselen ve 2 dusen cizgi olusur. max_bars_back = 4000 siniri (Pine'da cok eski pivotta calisma hatasi) uygulanmadi.
"""
import math, os, sys
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topluluk_sinyal import rma, ema, sma, stdev, highest, lowest, cross_up, cross_dn, true_range, pivot

# varsayilan girdiler
SRD_PRD, SRD_MAXPP, SRD_CHW, SRD_MAXSR, SRD_MINST = 10, 20, 10, 5, 2
BOF_PRD, BOF_BOLEN, BOF_CW, BOF_MINTEST = 5, 200, 3.0, 2
TL_PRD, TL_PPNUM, TL_MAXLINE = 20, 3, 3


# ------------------------------------------------------------------ Support Resistance - Dynamic v2
@njit(cache=True)
def _srd(c, ph, pl, cwidth, maxnumpp, maxnumsr, min_strength):
    n = len(c)
    pv = np.empty(maxnumpp + 2)
    npv = 0
    up = np.empty(maxnumsr + 2)
    dn = np.empty(maxnumsr + 2)
    st = np.empty(maxnumsr + 2)
    nsr = 0
    co = np.zeros(n, np.bool_)
    cu = np.zeros(n, np.bool_)
    ink = np.zeros(n, np.bool_)
    for i in range(n):
        isph = not math.isnan(ph[i])
        ispl = not math.isnan(pl[i])
        if isph or ispl:
            # array.unshift(pivotvals, ph ? ph : pl); boyut > maxnumpp ise pop (son)
            for k in range(npv, 0, -1):
                pv[k] = pv[k - 1]
            pv[0] = ph[i] if isph else pl[i]
            npv += 1
            if npv > maxnumpp:
                npv -= 1
            # array.clear x3
            nsr = 0
            cw = cwidth[i]
            for x in range(npv):
                # get_sr_vals(x)
                lo = pv[x]
                hi = lo
                numpp = 0
                for y in range(npv):
                    cpp = pv[y]
                    wdth = hi - cpp if cpp <= lo else cpp - lo
                    if wdth <= cw:
                        if cpp <= hi:
                            lo = min(lo, cpp)
                        else:
                            hi = max(hi, cpp)
                        numpp += 1
                strength = float(numpp)
                # check_sr(hi, lo, strength)
                ret = True
                for j in range(nsr):
                    if (up[j] >= lo and up[j] <= hi) or (dn[j] >= lo and dn[j] <= hi):
                        if strength >= st[j]:
                            for k in range(j, nsr - 1):
                                st[k] = st[k + 1]
                                up[k] = up[k + 1]
                                dn[k] = dn[k + 1]
                            nsr -= 1
                        else:
                            ret = False
                        break
                if ret:
                    # find_loc(strength)
                    loc = nsr
                    for j in range(nsr - 1, -1, -1):
                        if strength <= st[j]:
                            break
                        loc = j
                    if loc < maxnumsr and strength >= min_strength:
                        for k in range(nsr, loc, -1):
                            st[k] = st[k - 1]
                            up[k] = up[k - 1]
                            dn[k] = dn[k - 1]
                        st[loc] = strength
                        up[loc] = hi
                        dn[loc] = lo
                        nsr += 1
                        if nsr > maxnumsr:
                            nsr -= 1
        # f_crossed_over / f_crossed_under (her mum, guncel bolgelerle) ve kanal ici durumu
        for j in range(nsr):
            mid = (up[j] + dn[j]) / 2
            if i > 0:
                if c[i - 1] <= mid and c[i] > mid:
                    co[i] = True
                if c[i - 1] >= mid and c[i] < mid:
                    cu[i] = True
            if c[i] >= dn[j] and c[i] <= up[j]:
                ink[i] = True
    return co, cu, ink


def srd(h, l, c):
    ph = pivot(h, SRD_PRD, SRD_PRD, True)
    pl = pivot(l, SRD_PRD, SRD_PRD, False)
    cwidth = (highest(h, 300) - lowest(l, 300)) * SRD_CHW / 100
    return _srd(c, ph, pl, cwidth, SRD_MAXPP, SRD_MAXSR, SRD_MINST)


# ------------------------------------------------------------------ Breakout Finder
@njit(cache=True)
def _bof(o, c, ph, pl, h_, l_, hgst, lwst, prd, bo_len, cwidthu, mintest):
    n = len(c)
    cap = 64
    phval = np.empty(cap)
    phloc = np.empty(cap, np.int64)
    plval = np.empty(cap)
    plloc = np.empty(cap, np.int64)
    nph = 0
    npl = 0
    bo = np.zeros(n, np.bool_)
    bd = np.zeros(n, np.bool_)
    for i in range(n):
        chwidth = (h_[i] - l_[i]) * cwidthu
        if not math.isnan(ph[i]):
            if nph + 1 >= cap or npl + 1 >= cap:
                cap2 = cap * 2
                a = np.empty(cap2); a[:nph] = phval[:nph]; phval = a
                b = np.empty(cap2, np.int64); b[:nph] = phloc[:nph]; phloc = b
                a2 = np.empty(cap2); a2[:npl] = plval[:npl]; plval = a2
                b2 = np.empty(cap2, np.int64); b2[:npl] = plloc[:npl]; plloc = b2
                cap = cap2
            for k in range(nph, 0, -1):
                phval[k] = phval[k - 1]
                phloc[k] = phloc[k - 1]
            phval[0] = ph[i]
            phloc[0] = i - prd
            nph += 1
            if nph > 1:
                for x in range(nph - 1, 0, -1):  # for x = size - 1 to 1 (asagi)
                    if i - phloc[x] > bo_len:
                        nph -= 1  # array.pop: SON eleman
        if not math.isnan(pl[i]):
            if nph + 1 >= cap or npl + 1 >= cap:
                cap2 = cap * 2
                a = np.empty(cap2); a[:nph] = phval[:nph]; phval = a
                b = np.empty(cap2, np.int64); b[:nph] = phloc[:nph]; phloc = b
                a2 = np.empty(cap2); a2[:npl] = plval[:npl]; plval = a2
                b2 = np.empty(cap2, np.int64); b2[:npl] = plloc[:npl]; plloc = b2
                cap = cap2
            for k in range(npl, 0, -1):
                plval[k] = plval[k - 1]
                plloc[k] = plloc[k - 1]
            plval[0] = pl[i]
            plloc[0] = i - prd
            npl += 1
            if npl > 1:
                for x in range(npl - 1, 0, -1):
                    if i - plloc[x] > bo_len:
                        npl -= 1
        # yukselis kirilimi
        bomax = np.nan
        num = 0
        if nph >= mintest and c[i] > o[i] and c[i] > hgst[i]:
            bomax = phval[0]
            xx = 0
            for x in range(nph):
                if phval[x] >= c[i]:
                    break
                xx = x
                bomax = max(bomax, phval[x])
            if xx >= mintest and o[i] <= bomax:
                for x in range(xx + 1):
                    if phval[x] <= bomax and phval[x] >= bomax - chwidth:
                        num += 1
                if num < mintest or hgst[i] >= bomax:
                    bomax = np.nan
        bo[i] = (not math.isnan(bomax)) and num >= mintest
        # dusus kirilimi
        bomin = np.nan
        num1 = 0
        if npl >= mintest and c[i] < o[i] and c[i] < lwst[i]:
            bomin = plval[0]
            xx = 0
            for x in range(npl):
                if plval[x] <= c[i]:
                    break
                xx = x
                bomin = min(bomin, plval[x])
            if xx >= mintest and o[i] >= bomin:
                for x in range(xx + 1):
                    if plval[x] >= bomin and plval[x] <= bomin + chwidth:
                        num1 += 1
                if num1 < mintest or lwst[i] <= bomin:
                    bomin = np.nan
        bd[i] = (not math.isnan(bomin)) and num1 >= mintest
    return bo, bd


def _degisken_uc(x, maxlen, yuksek):
    """ta.highest/lowest(x, lll), lll = max(min(bar_index, maxlen), 1)."""
    n = len(x)
    out = highest(x, maxlen) if yuksek else lowest(x, maxlen)
    m = min(n, maxlen)
    if n > 0:
        out[0] = x[0]
    if m > 1:
        out[1:m] = (np.maximum if yuksek else np.minimum).accumulate(x[1:m])
    return out


def bof(o, h, l, c):
    ph = pivot(h, BOF_PRD, BOF_PRD, True)
    pl = pivot(l, BOF_PRD, BOF_PRD, False)
    h_ = _degisken_uc(h, 300, True)
    l_ = _degisken_uc(l, 300, False)
    hgst = np.r_[np.nan, highest(h, BOF_PRD)[:-1]]
    lwst = np.r_[np.nan, lowest(l, BOF_PRD)[:-1]]
    return _bof(o, c, ph, pl, h_, l_, hgst, lwst, BOF_PRD, BOF_BOLEN, BOF_CW / 100, BOF_MINTEST)


# ------------------------------------------------------------------ Trend Lines v2
@njit(cache=True)
def _tl(c, ph, pl, prd, ppnum, maxline):
    n = len(c)
    tval = np.full(ppnum, np.nan)
    tpos = np.zeros(ppnum, np.int64)  # val na iken pos kullanilmaz (ikisi birlikte eklenir/silinir)
    bval = np.full(ppnum, np.nan)
    bpos = np.zeros(ppnum, np.int64)
    upj = np.full((n, maxline), np.nan)  # gecerli yukselen cizgilerin bir sonraki muma (i+1) uzatilmis degeri
    dnj = np.full((n, maxline), np.nan)
    nlo = np.zeros(n, np.int64)
    nhi = np.zeros(n, np.int64)
    for i in range(n):
        if not math.isnan(ph[i]):
            for k in range(ppnum - 1, 0, -1):
                tval[k] = tval[k - 1]
                tpos[k] = tpos[k - 1]
            tval[0] = ph[i]
            tpos[0] = i
        if not math.isnan(pl[i]):
            for k in range(ppnum - 1, 0, -1):
                bval[k] = bval[k - 1]
                bpos[k] = bpos[k - 1]
            bval[0] = pl[i]
            bpos[0] = i
        countlinelo = 0
        countlinehi = 0
        for p1 in range(ppnum - 1):
            up1 = 0
            up2 = 0
            uj = np.nan
            if countlinelo <= maxline:
                for p2 in range(ppnum - 1, p1, -1):
                    val1 = bval[p1]
                    val2 = bval[p2]
                    pos1 = bpos[p1]
                    pos2 = bpos[p2]
                    if val1 > val2:
                        diff = (val1 - val2) / (pos1 - pos2)
                        hline = val2 + diff
                        lloc = i
                        valid = True
                        for x in range(pos2 + 1 - prd, i + 1):
                            if c[x] < hline:
                                valid = False
                                break
                            lloc = x
                            hline = hline + diff
                        if valid:
                            up1 = lloc
                            up2 = pos2
                            uj = hline
                            break
            dp1 = 0
            dp2 = 0
            dj = np.nan
            if countlinehi <= maxline:
                for p2 in range(ppnum - 1, p1, -1):
                    val1 = tval[p1]
                    val2 = tval[p2]
                    pos1 = tpos[p1]
                    pos2 = tpos[p2]
                    if val1 < val2:
                        diff = (val2 - val1) / float(pos1 - pos2)
                        hline = val2 - diff
                        lloc = i
                        valid = True
                        for x in range(pos2 + 1 - prd, i + 1):
                            if c[x] > hline:
                                valid = False
                                break
                            lloc = x
                            hline = hline - diff
                        if valid:
                            dp1 = lloc
                            dp2 = pos2
                            dj = hline
                            break
            if up1 != 0 and up2 != 0 and countlinelo < maxline:
                upj[i, countlinelo] = uj
                countlinelo += 1
            if dp1 != 0 and dp2 != 0 and countlinehi < maxline:
                dnj[i, countlinehi] = dj
                countlinehi += 1
        nlo[i] = countlinelo
        nhi[i] = countlinehi
    # cizgi kirilimi: t-1'de gecerli cizgilerin t'ye uzatilmis degeri
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    for i in range(1, n):
        a = False
        s = False
        for k in range(maxline):
            if c[i] < upj[i - 1, k]:
                s = True
            if c[i] > dnj[i - 1, k]:
                a = True
        if a and not s:
            al[i] = True
        elif s and not a:
            sat[i] = True
    durum = np.zeros(n, np.int64)
    for i in range(n):
        if nlo[i] > 0 and nhi[i] == 0:
            durum[i] = 1
        elif nhi[i] > 0 and nlo[i] == 0:
            durum[i] = -1
    return al, sat, durum


def tlb2(h, l, c):
    ph = pivot(h, TL_PRD, TL_PRD, True)
    pl = pivot(l, TL_PRD, TL_PRD, False)
    return _tl(c, ph, pl, TL_PRD, TL_PPNUM, TL_MAXLINE)


# ------------------------------------------------------------------ sozlesme
def hesapla(z):
    o, h, l, c = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("o", "h", "l", "c"))
    sr_co, sr_cu, sr_in = srd(h, l, c)
    bo, bd = bof(o, h, l, c)
    tl_al, tl_sat, tl_d = tlb2(h, l, c)
    return {
        "S": {"SRD": (sr_co, sr_cu), "BOF": (bo, bd), "TLB2": (tl_al, tl_sat)},
        "D": {"Trend çizgisi durumu": tl_d},
        "U": {"S/R kanalında": sr_in},
        "X": {},
        "STOPS": {},
    }
