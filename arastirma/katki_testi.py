"""Topluluk gostergelerinin VSP'ye katkisi: sinyal, filtre ve bilgi olarak (1 dk; 22 Binance USDT-M paritesi; 2025 kesif / 2026 dogrulama).

Kullanici: "Ozgun bir gosterge olusturuyoruz; katkisi olacak her seyi kullanmamiz gerekir. AL/SAT disinda bilmem gereken seyleri de gormek isterim."
Komisyon: kullanicinin karariyla sifir (BULGULAR 14b). Makas bu olculere dahil degil.
Lisans: gostergelerin kodu kopyalanmadi; algilama mantiklari spesifikasyon olarak okunup bastan yazildi, yalnizca arastirma icindir.

ON KAYIT (sonuclardan once yazildi):
 A) Sinyal: Yeni adaylar topluluk_sinyal.py motoruyla (izgara 54 ayar, komisyon 0, olay engeli acik, hareket/maliyet engeli yok) sinanir.
    Adaylar: LQS Liquidity Swings [LuxAlgo] (14; salinim bolgesine giris: dip bolgesi AL, tepe bolgesi SAT),
             OBF Order Block Finder [wugamlo] (5; son OB bolgesine ilk donus), OBD Order Block Detector [LuxAlgo] (5; hacim OB bolgesine ilk giris),
             CMT CM Ultimate MA (SMA 20, yumusatma 2) yon donusu, CMC fiyatin SMA 20'yi mum icinde kesmesi, CMX SMA 20 / 50 kesisimi,
             TLS TMA Overlay 3 Line Strike, ENG TMA yutan mum, TRF TMA EMA 2 / SMMA 200 kesisimi,
             LOR Lorentzian Classification [jdehorty] (varsayilanlar; canli grafikte oldugu gibi komsu penceresi 2000-3000 mum geride),
             NWE Nadaraya-Watson Envelope [LuxAlgo] (8, 3; repaint kapali uc nokta yontemi: alt bandi asagi kesince AL, ust bandi yukari kesince SAT).
    Yerel cikis: CMT, CMC, CMX, TRF ters sinyalde; LOR 4 mum sonra (gostergenin kendi cikisi).
    Secim: 2025'te en yuksek ortalama R. Basari: 2025 R > 0 ve t >= 2; 2026 R > 0 ve t >= 3.
 B) Filtre: VSP'nin AL/SAT islemleri (v6.1 varsayilanlari: piyasa girisi, stop 2 sigma15, hedef 2R, 5 dk; komisyon 0) sinyal mumundaki durumlara gore ayrilir.
    Yonlu durumlar (+1 boga / -1 ayi) islem yonuyle ayni ise "uyumlu"; yonsuz durumlar dogru/yanlis.
    Olcu: durum dogru (uyumlu) islemlerin brut bp ortalamasi eksi digerlerinin. Gun kumelenmis t (iki grup farki).
    Kabul: iki yilda ayni isaret, |fark| >= 1 bp, 2025 t >= 2 ve 2026 t >= 3, durumun islemlerin en az %20'sini kapsamasi.
    Kabul edilen durum ya "guclu sinyal" isareti (fark pozitif) ya da "zayif sinyal" isareti (fark negatif) olur.
 C) Bilgi: Sonraki 15 dk gerceklesen oynakligi (log) EWMA tahminine ek olarak aciklama gucu. Her 15. mum (ortusmesiz).
    Kabul: R2 artisi iki yilda da >= 0,005 (BULGULAR 6 ile ayni esik).

Kullanim: VSP_VERI=<klasor> python3 arastirma/katki_testi.py
"""
import math, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
from topluluk_sinyal import rma, ema, sma, stdev, highest, lowest, cross_up, cross_dn, true_range, pivot

KS, RS, HS = sinyal_v6.KS, sinyal_v6.RS, sinyal_v6.HS
YENI = ["LQS", "OBF", "OBD", "CMT", "CMC", "CMX", "TLS", "ENG", "TRF", "LOR", "NWE"]
YEREL = {"CMT": "ters", "CMC": "ters", "CMX": "ters", "TRF": "ters", "LOR": "4"}


# ------------------------------------------------------------------ yeni gostergeler
@njit(cache=True)
def liq_swings(o, h, l, c, ph, pl, L):
    """Liquidity Swings: aktif tepe/dip bolgesi; bolgeye giris sinyali ve bolge icinde olma durumu."""
    n = len(c)
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    inz = np.zeros(n, np.int64)
    pt = np.nan
    pb = np.nan
    pc = True
    lt = np.nan
    lb = np.nan
    lcx = True
    for i in range(1, n):
        if not math.isnan(ph[i]):
            pt = h[i - L]
            pb = max(c[i - L], o[i - L])
            pc = False
        elif not math.isnan(pt) and c[i] > pt:
            pc = True
        if not math.isnan(pl[i]):
            lt = min(c[i - L], o[i - L])
            lb = l[i - L]
            lcx = False
        elif not math.isnan(lb) and c[i] < lb:
            lcx = True
        if (not pc) and math.isnan(ph[i]):
            if h[i] >= pb and c[i] <= pt:
                inz[i] = -1
                if h[i - 1] < pb:
                    sat[i] = True
        if (not lcx) and math.isnan(pl[i]):
            if l[i] <= lt and c[i] >= lb:
                inz[i] = 1 if inz[i] == 0 else 0
                if l[i - 1] > lt:
                    al[i] = True
    return al, sat, inz


@njit(cache=True)
def ob_finder(o, h, l, c, P):
    n = len(c)
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    bh = np.nan
    bl = np.nan
    bu = True
    sh = np.nan
    sl = np.nan
    su = True
    for i in range(P + 1, n):
        # once mevcut bolgeye donus (bu mumda yeni OB tespit edilse bile eski bolge once kontrol edilir)
        if not bu:
            if l[i] <= bh:
                if c[i] >= bl:
                    al[i] = True
                bu = True
        if not su:
            if h[i] >= sl:
                if c[i] <= sh:
                    sat[i] = True
                su = True
        up = 0
        dn = 0
        for k in range(1, P + 1):
            if c[i - k] > o[i - k]:
                up += 1
            if c[i - k] < o[i - k]:
                dn += 1
        j = i - P - 1
        if c[j] < o[j] and up == P:
            bh = o[j]
            bl = l[j]
            bu = False
        if c[j] > o[j] and dn == P:
            sl = o[j]
            sh = h[j]
            su = False
    return al, sat


@njit(cache=True)
def ob_detector(h, l, v, hl2, phv, L):
    n = len(h)
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    inz = np.zeros(n, np.int64)
    M = 50
    bt = np.full(M, np.nan)
    bb = np.full(M, np.nan)
    bus = np.zeros(M, np.bool_)
    st = np.full(M, np.nan)
    sb = np.full(M, np.nan)
    sus = np.zeros(M, np.bool_)
    nb = 0
    ns = 0
    os_ = 0
    for i in range(L, n):
        up = h[i]
        lo = l[i]
        for k in range(1, L):
            up = max(up, h[i - k])
            lo = min(lo, l[i - k])
        if h[i - L] > up:
            os_ = 0
        elif l[i - L] < lo:
            os_ = 1
        if not math.isnan(phv[i]):
            if os_ == 1:
                if nb == M:
                    nb -= 1
                for k in range(nb, 0, -1):
                    bt[k] = bt[k - 1]
                    bb[k] = bb[k - 1]
                    bus[k] = bus[k - 1]
                bt[0] = hl2[i - L]
                bb[0] = l[i - L]
                bus[0] = False
                nb += 1
            else:
                if ns == M:
                    ns -= 1
                for k in range(ns, 0, -1):
                    st[k] = st[k - 1]
                    sb[k] = sb[k - 1]
                    sus[k] = sus[k - 1]
                st[0] = h[i - L]
                sb[0] = hl2[i - L]
                sus[0] = False
                ns += 1
        # gecersizlesme (fitil): son L mumun dibi bolgenin altina inerse
        k = 0
        while k < nb:
            if lo < bb[k]:
                for m in range(k, nb - 1):
                    bt[m] = bt[m + 1]
                    bb[m] = bb[m + 1]
                    bus[m] = bus[m + 1]
                nb -= 1
            else:
                k += 1
        k = 0
        while k < ns:
            if up > st[k]:
                for m in range(k, ns - 1):
                    st[m] = st[m + 1]
                    sb[m] = sb[m + 1]
                    sus[m] = sus[m + 1]
                ns -= 1
            else:
                k += 1
        for k in range(nb):
            if l[i] <= bt[k]:
                inz[i] = 1
                if (not bus[k]) and l[i - 1] > bt[k]:
                    al[i] = True
                    bus[k] = True
        for k in range(ns):
            if h[i] >= sb[k]:
                inz[i] = -1 if inz[i] == 0 else 0
                if (not sus[k]) and h[i - 1] < sb[k]:
                    sat[i] = True
                    sus[k] = True
    return al, sat, inz


def rolling_norm(x, w=5000):
    """MLExtensions.normalize: grafik basindan beri min/max; ucretsiz planda grafik ~5000 mum oldugu icin kayan 5000 mum."""
    s = pd.Series(x)
    mn = s.rolling(w, min_periods=1).min().to_numpy()
    mx = s.rolling(w, min_periods=1).max().to_numpy()
    return (x - mn) / np.maximum(mx - mn, 1e-9)


def rsi(c, n):
    d = np.r_[np.nan, np.diff(c)]
    up = rma(np.nan_to_num(np.maximum(d, 0)), n)
    dn = rma(np.nan_to_num(np.maximum(-d, 0)), n)
    return np.where(dn > 0, 100 - 100 / (1 + up / np.where(dn > 0, dn, 1)), 100.0)


@njit(cache=True)
def _meandev(c, n):
    out = np.full(len(c), np.nan)
    for t in range(n - 1, len(c)):
        m = 0.0
        for k in range(n):
            m += c[t - k]
        m /= n
        d = 0.0
        for k in range(n):
            d += abs(c[t - k] - m)
        out[t] = d / n
    return out


def cci(c, n):
    m = sma(c, n)
    md = _meandev(c, n)
    return (c - m) / (0.015 * np.where(md > 0, md, np.nan))


@njit(cache=True)
def regime(src, h, l):
    n = len(src)
    v1 = 0.0
    v2 = 0.0
    k = 0.0
    out = np.zeros(n)
    prev = src[0]
    pk = src[0]
    for i in range(n):
        s1 = src[i - 1] if i > 0 else src[i]
        v1 = 0.2 * (src[i] - s1) + 0.8 * v1
        v2 = 0.1 * (h[i] - l[i]) + 0.8 * v2
        om = abs(v1 / v2) if v2 != 0 else 0.0
        al = (-om * om + math.sqrt(om ** 4 + 16 * om * om)) / 8
        pk = k
        k = al * src[i] + (1 - al) * k
        out[i] = abs(k - pk)
    return out


@njit(cache=True)
def lorentzian(F, y, K, lo, hi):
    """ANN: her mumda komsular i = b-lo ... b-hi (azalan sira), i % 4 != 0; tahmin ve uzaklik dizileri mumlar arasi kalici."""
    n = F.shape[0]
    nf = F.shape[1]
    pred = np.zeros(n)
    pv = np.zeros(K + 1)
    dv = np.zeros(K + 1)
    cnt = 0
    for b in range(hi, n):
        last = -1.0
        for i in range(b - lo, b - hi - 1, -1):
            if i % 4 == 0:
                continue
            d = 0.0
            for f in range(nf):
                d += math.log(1 + abs(F[b, f] - F[i, f]))
            if d >= last:
                last = d
                dv[cnt] = d
                pv[cnt] = y[i]
                cnt += 1
                if cnt > K:
                    last = dv[int(round(K * 3 / 4))]
                    for m in range(cnt - 1):
                        dv[m] = dv[m + 1]
                        pv[m] = pv[m + 1]
                    cnt -= 1
        s = 0.0
        for m in range(cnt):
            s += pv[m]
        pred[b] = s
    return pred


@njit(cache=True)
def lor_signal(pred, filt, kbull, kbear):
    n = len(pred)
    sig = np.zeros(n, np.int64)
    al = np.zeros(n, np.bool_)
    sat = np.zeros(n, np.bool_)
    s = 0
    for i in range(n):
        p = s
        if pred[i] > 0 and filt[i]:
            s = 1
        elif pred[i] < 0 and filt[i]:
            s = -1
        sig[i] = s
        if s != p:
            if s == 1 and kbull[i]:
                al[i] = True
            if s == -1 and kbear[i]:
                sat[i] = True
    return al, sat, sig


def gostergeler(z):
    """Yeni adaylarin sinyalleri ve filtre/bilgi testi icin durumlar."""
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    tr = true_range(h, l, c)
    S, D, U = {}, {}, {}  # sinyaller, yonlu durumlar, yonsuz durumlar
    # LQS
    a, b, inz = liq_swings(o, h, l, c, pivot(h, 14, 14, True), pivot(l, 14, 14, False), 14)
    S["LQS"] = (a, b)
    D["LQS bölgede (dip +, tepe -)"] = inz
    # OBF
    S["OBF"] = ob_finder(o, h, l, c, 5)
    # OBD
    a, b, inz = ob_detector(h, l, v, (h + l) / 2, pivot(v, 5, 5, True), 5)
    S["OBD"] = (a, b)
    D["OBD bölgede (boğa +, ayı -)"] = inz
    # CM MA
    s20, s50 = sma(c, 20), sma(c, 50)
    mup = np.nan_to_num(s20 >= np.r_[np.full(2, np.nan), s20[:-2]]).astype(bool)
    mup1 = np.r_[False, mup[:-1]]
    S["CMT"] = (mup & ~mup1, ~mup & mup1)
    S["CMC"] = (np.nan_to_num((o < s20) & (c > s20)).astype(bool), np.nan_to_num((o > s20) & (c < s20)).astype(bool))
    S["CMX"] = (cross_up(s20, s50), cross_dn(s20, s50))
    D["SMA20 yönü"] = np.where(mup, 1, -1)
    D["Fiyat SMA20 üstü"] = np.where(c > s20, 1, -1)
    # TMA
    def sh(x, k):
        return np.r_[np.full(k, np.nan), x[:-k]]
    red = (c < o).astype(float)
    grn = (c > o).astype(float)
    S["TLS"] = (np.nan_to_num((sh(red, 3) == 1) & (sh(red, 2) == 1) & (sh(red, 1) == 1) & (c > sh(o, 1))).astype(bool),
                np.nan_to_num((sh(grn, 3) == 1) & (sh(grn, 2) == 1) & (sh(grn, 1) == 1) & (c < sh(o, 1))).astype(bool))
    o1, c1 = np.r_[np.nan, o[:-1]], np.r_[np.nan, c[:-1]]
    S["ENG"] = (np.nan_to_num((o <= c1) & (o < o1) & (c > o1)).astype(bool), np.nan_to_num((o >= c1) & (o > o1) & (c < o1)).astype(bool))
    smma200 = rma(c, 200)
    e2 = ema(c, 2)
    S["TRF"] = (cross_up(e2, smma200), cross_dn(e2, smma200))
    D["TMA trend (EMA2 > SMMA200)"] = np.where(e2 > smma200, 1, -1)
    D["SMMA 21 > 50 > 100 > 200 dizilimi"] = np.where((rma(c, 21) > rma(c, 50)) & (rma(c, 50) > rma(c, 100)) & (rma(c, 100) > smma200), 1,
                                                       np.where((rma(c, 21) < rma(c, 50)) & (rma(c, 50) < rma(c, 100)) & (rma(c, 100) < smma200), -1, 0))
    # NWE (uc nokta)
    w = np.exp(-(np.arange(500) ** 2) / (2 * 64.0))
    out = np.convolve(c, w / w.sum(), mode="full")[:n]
    out[:499] = np.nan
    mae = sma(np.abs(c - out), 499) * 3
    S["NWE"] = (cross_dn(c, out - mae), cross_up(c, out + mae))
    D["NWE bant dışı (alt +, üst -)"] = np.where(c < out - mae, 1, np.where(c > out + mae, -1, 0))
    # LOR
    hlc3 = (h + l + c) / 3
    e1 = ema(hlc3, 10)
    e2w = ema(np.abs(hlc3 - e1), 10)
    ci = (hlc3 - e1) / (0.015 * np.where(e2w > 0, e2w, np.nan))
    wt1 = ema(np.nan_to_num(ci), 11)
    wt2 = sma(wt1, 4)
    dip, dim, dx = TS.dmi(h, l, c, 20.0)
    F = np.column_stack([rsi(c, 14) / 100, rolling_norm(np.nan_to_num(wt1 - wt2)), rolling_norm(np.nan_to_num(cci(c, 20))), np.nan_to_num(rma(np.nan_to_num(dx), 20)) / 100, rsi(c, 9) / 100])
    c4 = np.r_[np.full(4, np.nan), c[:-4]]
    ylab = np.where(c4 < c, -1.0, np.where(c4 > c, 1.0, 0.0))
    pred = lorentzian(np.ascontiguousarray(np.nan_to_num(F)), ylab, 8, 2000, 3000)
    volf = rma(tr, 1) > rma(tr, 10)
    acs = regime((o + h + l + c) / 4, h, l)
    ea = ema(acs, 200)
    regf = (acs - ea) / np.where(ea > 0, ea, np.nan) >= -0.1
    filt = volf & np.nan_to_num(regf).astype(bool)
    wq = (1 + (np.arange(27) ** 2) / (64 * 2 * 8.0)) ** -8.0
    yhat = np.convolve(c, wq / wq.sum(), mode="full")[:n]
    yhat[:26] = np.nan
    yh1 = np.r_[np.nan, yhat[:-1]]
    kb = np.nan_to_num(yh1 < yhat).astype(bool)
    ks = np.nan_to_num(yh1 > yhat).astype(bool)
    a, b, lsig = lor_signal(pred, filt, kb, ks)
    S["LOR"] = (a, b)
    D["Lorentzian tahmini (+/-)"] = np.sign(pred).astype(np.int64)
    D["Lorentzian çekirdek eğimi"] = np.where(kb, 1, np.where(ks, -1, 0))
    # onceki turdaki gostergelerin durumlari
    st = TS.supertrend((h + l) / 2, c, rma(tr, 10), 3.0)
    D["Supertrend yönü"] = st
    tsu = TS.utbot(c, rma(tr, 10))
    D["UT Bot konumu"] = np.where(c > tsu, 1, -1)
    macd = ema(c, 12) - ema(c, 26)
    D["MACD > sinyal"] = np.where(macd > sma(macd, 9), 1, -1)
    D["WaveTrend wt1 > wt2"] = np.where(wt1 > wt2, 1, -1)
    D["WaveTrend aşırı bölge (satım +, alım -)"] = np.where(wt1 <= -53, 1, np.where(wt1 >= 53, -1, 0))
    dip14, dim14, dx14 = TS.dmi(h, l, c, 14.0)
    D["DI+ > DI-"] = np.where(dip14 > dim14, 1, -1)
    D["MSB yapısı"] = TS.msb(h, l, 9, 0.33)
    basis = sma(c, 20)
    dev = 1.5 * stdev(c, 20)
    rng = sma(tr, 20)
    sqzOn = np.nan_to_num((basis - dev > basis - rng * 1.5) & (basis + dev < basis + rng * 1.5)).astype(bool)
    val = TS.linreg0(c - ((highest(h, 20) + lowest(l, 20)) / 2 + basis) / 2, 20)
    D["Squeeze momentum (+/-)"] = np.sign(np.nan_to_num(val)).astype(np.int64)
    hc = highest(c, 22)
    wvf = (hc - l) / hc * 100
    D["Vix Fix yeşil (korku)"] = np.where(np.nan_to_num((wvf >= sma(wvf, 20) + 2 * stdev(wvf, 20)) | (wvf >= highest(wvf, 50) * 0.85)).astype(bool), 1, 0)
    U["Squeeze açık (sıkışma)"] = sqzOn
    U["ADX > 20"] = np.nan_to_num(sma(dx14, 14) > 20).astype(bool)
    U["Oynaklık artıyor (ATR1 > ATR10)"] = volf
    U["Rejim filtresi (Lorentzian)"] = np.nan_to_num(regf).astype(bool)
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    em = (et.hour * 60 + et.minute).to_numpy()
    U["Asya killzone (20-24 ET)"] = em >= 1200
    U["Londra killzone (02-05 ET)"] = (em >= 120) & (em < 300)
    U["NY sabah killzone (09:30-11 ET)"] = (em >= 570) & (em < 660)
    U["NY öğleden sonra (13:30-16 ET)"] = (em >= 810) & (em < 960)
    U["OBD bölgesinde (her iki yön)"] = D["OBD bölgede (boğa +, ayı -)"] != 0
    U["LQS bölgesinde (her iki yön)"] = D["LQS bölgede (dip +, tepe -)"] != 0
    U["NWE bant dışı (her iki yön)"] = D["NWE bant dışı (alt +, üst -)"] != 0
    U["Lorentzian |tahmin| >= 6"] = np.abs(pred) >= 6
    U["Vix Fix yeşil"] = D["Vix Fix yeşil (korku)"] == 1
    return S, D, U


# ------------------------------------------------------------------ parite isleme
def parite_isle(s):
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c = z["ts"], z["o"], z["h"], z["l"], z["c"]
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    yilb = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    gunb = (ts // 86400 - TS.GUN0).astype(np.int64)
    S, D, U = gostergeler(z)
    gec = (t >= 4000) & (t < n - TS.NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
    sonuc = {"A": {}, "B": [], "C": []}
    # A) sinyal
    for ad in YENI:
        al, sat = S[ad]
        ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
        y = np.where(al[ix], 1, -1).astype(np.int64)
        sg, blk = sigall[ix], engel[ix]
        for giris in ("P", "L"):
            for k in KS:
                for R in RS:
                    for H in HS:
                        res = TS.sim_izgara(o, h, l, c, ix, y, sg, blk, k, R, H, giris == "L", 0.0, 0.0, 0.0, False)
                        sonuc["A"][(ad, "izgara", giris, k, R, H)] = TS.toplam(yilb, gunb, *res)
        if ad in YEREL:
            if YEREL[ad] == "ters":
                res = TS.sim_yerel(o, c, ix, y, sg, sat, al, 0.0, 0.0, TS.NATIVE_MAX)
            else:
                res = TS.sim_yerel(o, c, ix, y, sg, np.zeros(n, bool), np.zeros(n, bool), 0.0, 0.0, 4)
            sonuc["A"][(ad, "yerel", "P", 0, 0, 0)] = TS.toplam(yilb, gunb, *res)
    # B) filtre: VSP v6.1 islemleri
    E = sinyal_v6.olaylar(s)
    ixv = np.searchsorted(ts, E["ts"])
    m = ixv >= 4000
    ixv, yv, sgv = ixv[m], E["yon"][m].astype(np.int64), E["sig"][m]
    oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ixv, yv, sgv, np.zeros(len(ixv), bool), 2.0, 2.0, 5, False, 0.0, 0.0, 0.0, False)
    tr_df = pd.DataFrame({"sym": s, "gun": ts[oi] // 86400, "yil": yilb[oi], "yon": oy, "brut": ob * 1e4})
    for ad, d in D.items():
        tr_df["D:" + ad] = d[oi] * oy > 0
    for ad, u in U.items():
        tr_df["U:" + ad] = u[oi]
    sonuc["B"] = tr_df
    # C) bilgi: sonraki 15 dk gerceklesen oynaklik
    r2 = np.nan_to_num(r * r)
    cs = np.r_[0, np.cumsum(r2)]
    fut = np.sqrt(cs[np.minimum(t + 16, n)] - cs[np.minimum(t + 1, n)])
    idx = np.flatnonzero(gec & (t % 15 == 0) & (fut > 0))
    cdf = pd.DataFrame({"yil": yilb[idx], "y": np.log(fut[idx]), "x0": np.log(sigall[idx])})
    for ad, u in U.items():
        cdf["U:" + ad] = u[idx].astype(float)
    for ad, d in D.items():
        cdf["|D|:" + ad] = (d[idx] != 0).astype(float)
    sonuc["C"] = cdf
    print(s, "tamam", flush=True)
    return sonuc


def iki_grup(df, kol):
    """Durum dogru/yanlis islemlerin brut farki; gun kumelenmis t."""
    a = df[df[kol]]
    b = df[~df[kol]]
    if len(a) < 50 or len(b) < 50:
        return np.nan, np.nan, len(a) / max(len(df), 1)
    fa, fb = a["brut"].mean(), b["brut"].mean()
    # gun kumelenmis fark: gunluk toplamlar uzerinden
    g = df.assign(x=np.where(df[kol], 1.0, 0.0))
    g["ra"] = np.where(g[kol], g["brut"] - fa, 0.0)
    g["rb"] = np.where(~g[kol], g["brut"] - fb, 0.0)
    gg = g.groupby("gun").agg(ra=("ra", "sum"), rb=("rb", "sum"))
    va = (gg["ra"] ** 2).sum() / len(a) ** 2
    vb = (gg["rb"] ** 2).sum() / len(b) ** 2
    cov = (gg["ra"] * gg["rb"]).sum() / (len(a) * len(b))
    se = math.sqrt(max(va + vb - 2 * cov, 1e-12))
    return fa - fb, (fa - fb) / se, len(a) / len(df)


def r2_artis(df, kol):
    out = {}
    for yl in (2025, 2026):
        d = df[df["yil"] == yl]
        y = d["y"].to_numpy()
        X0 = np.column_stack([np.ones(len(d)), d["x0"].to_numpy()])
        X1 = np.column_stack([X0, d[kol].to_numpy()])
        def r2(X):
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            e = y - X @ beta
            return 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
        out[yl] = r2(X1) - r2(X0)
    return out


def main():
    A, B, C = {}, [], []
    with Pool(4) as p:
        for parca in p.imap_unordered(parite_isle, izleme.SYMS):
            A = TS.birlestir([A, parca["A"]]) if A else TS.birlestir([parca["A"]])
            B.append(parca["B"])
            C.append(parca["C"])
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 40)
    # A
    rows = []
    for key, yl in A.items():
        for y in (2025, 2026):
            rows.append(dict(aday=key[0], tur=key[1], giris=key[2], k=key[3], R=key[4], H=key[5], yil=y, **TS.ozet(yl[y])))
    DA = pd.DataFrame(rows)
    DA.to_csv(os.path.join(izleme.VERI, "katki_A.csv"), index=False)
    kar = []
    for ad in YENI:
        for tur in ("izgara", "yerel"):
            d = DA[(DA["aday"] == ad) & (DA["tur"] == tur)]
            if len(d) == 0:
                continue
            a25 = d[d["yil"] == 2025].sort_values("netR", ascending=False).iloc[0]
            sel = d[(d["giris"] == a25["giris"]) & (d["k"] == a25["k"]) & (d["R"] == a25["R"]) & (d["H"] == a25["H"])]
            r25, r26 = sel[sel["yil"] == 2025].iloc[0], sel[sel["yil"] == 2026].iloc[0]
            gecti = r25["netR"] > 0 and r26["netR"] > 0 and r25["t"] >= 2 and r26["t"] >= 3
            kar.append(dict(aday=ad, tur=tur, ayar=f"{a25['giris']} k{a25['k']} R{a25['R']} H{a25['H']}", n25=r25["n"], n26=r26["n"],
                            R25=r25["netR"], t25=r25["t"], R26=r26["netR"], t26=r26["t"], bp25=r25["brut_bp"], bp26=r26["brut_bp"],
                            AL26=r26["brutAL_bp"], SAT26=r26["brutSAT_bp"], karar="GECTI" if gecti else "gecmedi"))
    print("=== A) Sinyal (komisyon 0) ===")
    print(pd.DataFrame(kar).round(3).to_string())
    # B
    DB = pd.concat(B, ignore_index=True)
    print("\n=== B) VSP AL/SAT filtre (brut bp; v6.1 varsayilanlari, komisyon 0) ===")
    for yl in (2025, 2026):
        d = DB[DB["yil"] == yl]
        print(yl, "islem", len(d), "brut", round(d["brut"].mean(), 3), "AL", round(d[d["yon"] > 0]["brut"].mean(), 3), "SAT", round(d[d["yon"] < 0]["brut"].mean(), 3))
    fr = []
    for kol in [k for k in DB.columns if k.startswith("D:") or k.startswith("U:")]:
        res = {}
        for yl in (2025, 2026):
            res[yl] = iki_grup(DB[DB["yil"] == yl], kol)
        f25, t25, p25 = res[2025]
        f26, t26, p26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3 and min(p25, p26) >= 0.2 and max(p25, p26) <= 0.8
        fr.append(dict(durum=kol, pay25=p25, fark25=f25, t25=t25, pay26=p26, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(fr).round(3).to_string())
    # B ek: yon ayrimi (AL ve SAT ayri) - yalnizca bilgi
    fr2 = []
    for kol in [k for k in DB.columns if k.startswith("D:") or k.startswith("U:")]:
        for yn, ynad in ((1, "AL"), (-1, "SAT")):
            res = {yl: iki_grup(DB[(DB["yil"] == yl) & (DB["yon"] == yn)], kol) for yl in (2025, 2026)}
            fr2.append(dict(durum=kol, yon=ynad, fark25=res[2025][0], t25=res[2025][1], fark26=res[2026][0], t26=res[2026][1], pay26=res[2026][2]))
    F2 = pd.DataFrame(fr2)
    print("\n(yon ayrimi, yalnizca bilgi; |t| >= 2 iki yilda ayni isaret)")
    q = F2[(np.sign(F2["fark25"]) == np.sign(F2["fark26"])) & (F2["t25"].abs() >= 2) & (F2["t26"].abs() >= 2)]
    print(q.round(3).to_string())
    # C
    DC = pd.concat(C, ignore_index=True)
    print("\n=== C) Bilgi: sonraki 15 dk oynaklik, R2 artisi ===")
    cr = []
    for kol in [k for k in DC.columns if k.startswith("U:") or k.startswith("|D|:")]:
        a = r2_artis(DC, kol)
        cr.append(dict(ozellik=kol, r2_25=a[2025], r2_26=a[2026], karar="KABUL" if min(a.values()) >= 0.005 else ""))
    print(pd.DataFrame(cr).round(4).to_string())


if __name__ == "__main__":
    main()
