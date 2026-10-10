"""Buyers & Sellers Profile + Dynamic S/R [Zeiierman] — yazar: Zeiierman — lisans: CC BY-NC-SA 4.0
(https://creativecommons.org/licenses/by-nc-sa/4.0/; ticari olmayan kullanım, atıf, aynı lisansla paylaşım).
Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir.

Kaynak: scratchpad/k5_kaynak/Z_profil_sr.pine (kullanıcının gönderdiği Pine v6 kodu). Varsayılan girdiler:
  Lookback 600, Rows 72, Swing Length 5, Search ATR 1,20, Min Node 0,08, Min Evidence 0,22, Profile Pull 0,85, Min Score 30,
  Max Levels 20, Merge ATR 0,16, Break ATR 0,10; sabitler VOL_LEN 40, ABS_RAD min(3, swingLen) = 3, PIV_VOL_X 2,2,
  ABS_BODY_MAX 0,40, ABS_VOL_X 1,5. Çizim kodu (çizgiler, etiketler, sağdaki profil histogramı) sinyali etkilemez, uyarlanmadı.

Çıktılar (katki_testi5 ön kaydı):
  S  ZNEW : (newSup, newRes) — onay mumunda (pivot mumundan swingLen = 5 sonra) seviye eklendi ya da birleşip yerini aldı (store_lvl true).
     ZBRK : (resBreak, supBreak) — manage_breaks; aynı mumda ikisi birden ise ikisi de yanlış.
     ZTCH : göstergede tanımlı değil (ön kayıt): t-1 mumunun SONUNDAKİ aktif seviyelerle (t mumunun pivot/kırılım/kırpma işlemlerinden önce)
            herhangi bir destek p için low <= p ve close > p -> AL; herhangi bir direnç p için high >= p ve close < p -> SAT; ikisi birden ise yok.
  D  "Profil S/R konumu (en yakın seviye destek +)": t mumunun sonundaki aktif seviyeler içinde close'a en yakın seviye destekse +1,
     dirençse -1, seviye yoksa 0. Eşit uzaklıkta ilk eklenen (dizideki ilk) seviye seçilir (kesin '<' taraması).
  U  "Profil seviyesine yakın (≤ 0,5 ATR)": close ile en yakın aktif seviye arasındaki uzaklık <= 0,5 * ta.atr(14) (ATR na ya da seviye yoksa yanlış).
  STOPS "Profil destek/direnç": uzun = close'un KESİN altındaki en yakın aktif destek - breakAtr * atr; kısa = close'un KESİN üstündeki en yakın
     aktif direnç + breakAtr * atr; yoksa nan. (Kırılım tamponu: destek close < p - tampon olana dek aktif kalır, yani close'un biraz üstünde
     aktif destek olabilir; bu seviyeler uzun stopu olarak kullanılmaz.)
  X, NATIVE: boş (göstergenin kendi pozisyon/çıkış mantığı yok).

Pine anlamına uyum kararları:
  - Mum sırası betikteki gibi: (1) ready ve pl -> pivot_eval(destek); (2) ready ve ph -> pivot_eval(direnç); (3) manage_breaks;
    (4) trim_lvls. update_lvls yalnızca çizim. Aynı mumda hem pl hem ph varsa önce destek değerlendirilir.
  - ready = bar_index > VOL_LEN + swingLen*2 + 5 = 55 (dizi indeksi = bar_index; veri ilk mumdan başlar).
  - Pivotlar topluluk_sinyal.pivot ile (ta.pivothigh/pivotlow(5, 5); sol taraf kesin, sağ taraf eşitliğe izin verir; VSP ile aynı kural).
    Pivot bilgisi onay mumunda (i) kullanılır; raw = low[5] / high[5].
  - avgVol = ta.sma(volume, 40) (ilk 39 mum na; pandas rolling, toplama sırası farkı ~1e-15 göreli). atr = ta.atr(14) = ta.rma(ta.tr(true), 14):
    ilk mum TR = high - low, 13. mumda (0 tabanlı) ilk 14 TR'nin basit ortalaması, sonra alpha*tr + (1 - alpha)*önceki (alpha = 1/14).
  - FONKSİYON PARAMETRESİ GEÇMİŞİ (CAGRI_GECMISI = True, varsayılan): pivot_eval yalnızca 'if ready and not na(pl/ph)' içinde çağrılır.
    Pine'da bir fonksiyon parametresinin [] geçmişi, o çağrı yerinin ÖNCEKİ ÇAĞRILARINDA aldığı değerlerdir, grafik mumları değil
    (TradingView belgesi, uyarı CW10003: koşullu çağrılan 'previousValue(source) => source[1]' son çağrının değerini döndürür).
    Bu yüzden pivot_eval içindeki atr[swingLen] ve pivot_features içindeki avgVol[swingLen], avgVol[o] (o = 2..8) değerleri, AYNI çağrı
    yerinin (destek ve direnç ayrı ayrı) 5 ve o önceki çağrısının mumundaki global atr / avgVol değerleridir. Yeterli önceki çağrı yoksa na:
    atrP = max(nz(na, mintick), mintick) = mintick; vb = volume[5]; base = v[o] (nz yedekleri). high/low/open/close/volume/time gibi yerleşik
    seriler fonksiyon içinde de gerçek mum geçmişidir (profile döngüsü ve draw_profile'ın son mumdaki çağrısı buna dayanır).
    CAGRI_GECMISI = False ya da hesapla(z, cagri=False): yazarın olası niyeti olan mum geçmişi (atr[i-5], avgVol[i-5], avgVol[i-o]).
  - profile(newest = swingLen, oldest = swingLen + bars - 1): bars = max(1, min(600, bar_index - swingLen + 1)); mumlar i-5'ten geriye
    i-5-bars+1'e kadar, Pine'daki sırayla (yeniden eskiye) toplanır (kayan nokta toplama sırası korunur). span = max(hi - lo, mintick*rows),
    bot = lo - (span - (hi - lo))*0,5, step = span / rows. row_id = max(0, min(rows-1, int(floor((p - bot) / step)))).
    'for j = r0 to r1': l <= h olduğundan r0 <= r1 (yine de Pine'ın ters sayma kuralı kodda var). r = 0 ise ov = step, frac = 1, bf = 0,5.
    volume nz/negatif kırpma aynen (veride na yok).
  - profile_node: mx = max(array.max(tot), 1e-7); rad = max(atrP*srchAtr, step*2); satır merkezi bot + (r + 0,5)*step; d <= rad;
    komşu satırlar kenarda kendisi; e = 0,50*str + 0,20*pk + 0,20*dir + 0,10*prox (soldan sağa toplama); 'e > bestE' kesin (ilk en iyi satır).
  - pivot_features: Pine ifadeleri aynen (clip = max(0, min(1, x)); pr ve cr tabanı mintick; 'for n = 0 to ABS_RAD*2', o = swingLen - ABS_RAD + n).
  - pivot_eval: ok = nStr >= nodeMin ve evid >= evidMin; pull = ok ? pullMax*clip(evid/0,65) : 0; p = raw + (node - raw)*pull;
    sc = 100*(0,50*evid + 0,20*aSc + 0,15*vSc + 0,15*wSc); stored = ok ve sc >= scoreMin ? store_lvl(...) : false.
  - store_lvl/nearby: tol = max(atrP*mergeAtr, mintick); aynı taraftaki seviyeler dizi sırasıyla, d <= tol ve d < best (eşitlikte ilk);
    bulunduysa yalnızca sc > eski sc ise p ve sc değişir (dizi indeksi korunur) ve true; bulunmadıysa sona eklenir ve true. Aksi false.
  - manage_breaks: barstate.isconfirmed geçmiş mumlarda true; dizi sondan başa taranır; tampon = max(nz(atr, 0)*breakAtr, 0);
    destek close < p - tampon, direnç close > p + tampon ise silinir (silme dizinin kalan sırasını korur).
  - trim_lvls: boyut > maxLvl iken en küçük sc'li İLK indeks (kesin '<' taraması, 0. elemandan başlayarak) silinir.
  - syminfo.mintick veride yok: parite başına bir kez, kapanış fiyatlarının sıralı benzersiz değerleri arasındaki en küçük pozitif fark;
    12 anlamlı basamağa yuvarlanır, ardından kayan nokta gürültüsü için 6 anlamlı basamağa yapıştırılır (BTC: 0.0999999999913 -> 0.1).
    Tahmin = verinin en ince tiki (SOL 0.001 ve DOT 4e-05 verir; TradingView'in bugünkü değeri SOL 0.01, DOT 0.0001; DOT'ta 4e-05
    tek bir ızgara dışı fiyattan gelir). mintick yalnızca taban olarak kullanılır (span, pr, cr, atrP, tol); etkisi duman testinde ölçüldü.
    hesapla(z, mintick=...) ile değiştirilebilir.
  - Pine zamanı milisaniyedir (ts*1000); born/time yalnızca çizimde kullanılır, çıktıları etkilemez.
  - Her çıktı t mumunda yalnızca <= t verisiyle hesaplanır; sinyaller mum kapanışında, repaint yok.
"""
import math, os, sys
import numpy as np
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topluluk_sinyal import sma, true_range, pivot

# varsayilan girdiler ve sabitler
PROF_LB, PROF_ROWS, SWING = 600, 72, 5
SRCH_ATR, NODE_MIN, EVID_MIN, PULL_MAX, SCORE_MIN = 1.20, 0.08, 0.22, 0.85, 30.0
MAX_LVL, MERGE_ATR, BREAK_ATR = 20, 0.16, 0.10
VOL_LEN, ABS_RAD, PIV_VOL_X, ABS_BODY_MAX, ABS_VOL_X = 40, min(3, SWING), 2.2, 0.40, 1.5
ATR_LEN = 14
CAGRI_GECMISI = True

D_AD = "Profil S/R konumu (en yakın seviye destek +)"
U_AD = "Profil seviyesine yakın (≤ 0,5 ATR)"
STOP_AD = "Profil destek/direnç"


def mintick_tahmin(c):
    """syminfo.mintick tahmini: sirali benzersiz kapanislar arasindaki en kucuk pozitif fark (12 anlamli basamak, sonra 6 anlamli basamaga yapistirma)."""
    u = np.unique(np.asarray(c, dtype=np.float64))
    d = np.diff(u)
    d = d[d > 0]
    if len(d) == 0:
        return 1e-8
    m12 = float("%.12g" % float(d.min()))
    m6 = float("%.6g" % m12)
    return m6 if abs(m6 - m12) <= 1e-8 * m6 else m12


@njit(cache=True)
def atr_pine(tr, n):
    """ta.atr(n) = ta.rma(ta.tr(true), n): n-1. mumda ilk n TR'nin SMA'si, sonra alpha*tr + (1-alpha)*onceki."""
    m = len(tr)
    out = np.full(m, np.nan)
    if m < n:
        return out
    s = 0.0
    for i in range(n):
        s += tr[i]
    out[n - 1] = s / n
    alpha = 1.0 / n
    for i in range(n, m):
        out[i] = alpha * tr[i] + (1.0 - alpha) * out[i - 1]
    return out


@njit(cache=True)
def _clip(x):
    return max(0.0, min(1.0, x))


@njit(cache=True)
def _row_id(p, bot, step, rows):
    return max(0, min(rows - 1, int(math.floor((p - bot) / step))))


@njit(cache=True)
def _profile(h, l, c, v, newest, oldest, rows, mintick, tot, buy):
    """profile(newest, oldest, rows): newest/oldest MUTLAK mum indeksleri (newest >= oldest); Pine sirasi (yeniden eskiye)."""
    lo = l[newest]
    hi = h[newest]
    for b in range(newest, oldest - 1, -1):
        lo = min(lo, l[b])
        hi = max(hi, h[b])
    span = max(hi - lo, mintick * rows)
    bot = lo - (span - (hi - lo)) * 0.5
    step = span / rows
    for j in range(rows):
        tot[j] = 0.0
        buy[j] = 0.0
    for b in range(newest, oldest - 1, -1):
        lb = l[b]
        hb = h[b]
        r = hb - lb
        vv = v[b]
        if math.isnan(vv):
            vv = 0.0
        vv = max(vv, 0.0)
        bf = _clip((c[b] - lb) / r) if r > 0 else 0.5
        r0 = _row_id(lb, bot, step, rows)
        r1 = _row_id(hb, bot, step, rows)
        dj = 1 if r1 >= r0 else -1
        j = r0
        while True:
            rl = bot + j * step
            ov = max(0.0, min(hb, rl + step) - max(lb, rl)) if r > 0 else step
            frac = ov / r if r > 0 else 1.0
            if frac > 0:
                av = vv * frac
                tot[j] = tot[j] + av
                buy[j] = buy[j] + av * bf
            if j == r1:
                break
            j += dj
    return bot, step


@njit(cache=True)
def _node(raw, supp, atrP, bot, step, tot, buy, rows, srch):
    mx = tot[0]
    for r in range(1, rows):
        if tot[r] > mx:
            mx = tot[r]
    mx = max(mx, 0.0000001)
    rad = max(atrP * srch, step * 2.0)
    bestP = raw
    bestE = -1.0
    bestS = 0.0
    bestPk = 0.0
    bestDir = 0.5
    for r in range(rows):
        p = bot + (r + 0.5) * step
        d = abs(p - raw)
        if d <= rad:
            rv = tot[r]
            st = rv / mx
            lv = tot[r - 1] if r > 0 else rv
            rv2 = tot[r + 1] if r < rows - 1 else rv
            nAvg = max((lv + rv2) * 0.5, mx * 0.01)
            pk = _clip((rv / nAvg - 0.85) / 0.65)
            bSh = _clip(buy[r] / rv) if rv > 0 else 0.5
            dr = bSh if supp else 1.0 - bSh
            prox = 1.0 - d / rad
            e = 0.50 * st + 0.20 * pk + 0.20 * dr + 0.10 * prox
            if e > bestE:
                bestE = e
                bestP = p
                bestS = st
                bestPk = pk
                bestDir = dr
    return bestP, max(bestE, 0.0), bestS, bestPk, bestDir


@njit(cache=True)
def _features(i, supp, o, h, l, c, v, avh, sw, absrad, mintick, pivx, bodymax, absvx):
    """pivot_features; avh[k] = fonksiyon icindeki avgVol[k] (na ise nan)."""
    b = i - sw
    vb = avh[sw]
    if math.isnan(vb):
        vb = v[b]
    vol_b = v[b]
    if math.isnan(vol_b):
        vol_b = 0.0
    vr = vol_b / vb if vb > 0 else 1.0
    vSc = _clip((vr - 0.8) / (pivx - 0.8))
    pr = max(h[b] - l[b], mintick)
    wick = (min(o[b], c[b]) - l[b]) if supp else (h[b] - max(o[b], c[b]))
    wSc = _clip((wick / pr) / 0.50)
    absSc = 0.0
    for nn in range(0, absrad * 2 + 1):
        off = sw - absrad + nn
        bb = i - off
        cr = max(h[bb] - l[bb], mintick)
        vv = v[bb]
        if math.isnan(vv):
            vv = 0.0
        vv = max(vv, 0.0)
        base = avh[off]
        if math.isnan(base):
            base = vv
        vRat = vv / base if base > 0 else 1.0
        bRat = abs(c[bb] - o[bb]) / cr
        small = _clip((bodymax - bRat) / bodymax)
        av = _clip((vRat - 1.0) / (absvx - 1.0))
        absSc = max(absSc, math.sqrt(small * av))
    return vSc, wSc, absSc


@njit(cache=True)
def _motor(o, h, l, c, v, avg, atr, ph, pl, mintick, cagri, prof_lb, rows, sw, srch, node_min, evid_min, pull_max, score_min,
           max_lvl, merge_atr, break_atr, vol_len, absrad, pivx, bodymax, absvx):
    n = len(c)
    cap = max_lvl + 8
    Lp = np.empty(cap)
    Lsc = np.empty(cap)
    Ls = np.zeros(cap, np.bool_)
    nl = 0
    new_sup = np.zeros(n, np.bool_)
    new_res = np.zeros(n, np.bool_)
    sup_brk = np.zeros(n, np.bool_)
    res_brk = np.zeros(n, np.bool_)
    tch_al = np.zeros(n, np.bool_)
    tch_sat = np.zeros(n, np.bool_)
    dpos = np.zeros(n, np.int64)
    near = np.full(n, np.nan)
    sup_alt = np.full(n, np.nan)
    res_ust = np.full(n, np.nan)
    nlv = np.zeros(n, np.int64)
    tot = np.zeros(rows)
    buy = np.zeros(rows)
    hmax = max(sw, absrad * 2 + sw - absrad) + 1
    avh = np.full(hmax, np.nan)
    calls = np.empty((2, n), np.int64)  # 0: destek cagri yeri, 1: direnc cagri yeri
    ncall = np.zeros(2, np.int64)
    ready_min = vol_len + sw * 2 + 5
    for i in range(n):
        # ZTCH: t-1 mumunun sonundaki seviyeler
        ta_ = False
        ts_ = False
        for k in range(nl):
            if Ls[k]:
                if l[i] <= Lp[k] and c[i] > Lp[k]:
                    ta_ = True
            else:
                if h[i] >= Lp[k] and c[i] < Lp[k]:
                    ts_ = True
        tch_al[i] = ta_ and not ts_
        tch_sat[i] = ts_ and not ta_
        ready = i > ready_min
        for side in range(2):
            supp = side == 0
            raw = pl[i] if supp else ph[i]
            if not ready or math.isnan(raw):
                continue
            # cagri gecmisi
            calls[side, ncall[side]] = i
            ncall[side] += 1
            kk = ncall[side] - 1
            for j in range(hmax):
                if cagri:
                    avh[j] = avg[calls[side, kk - j]] if kk - j >= 0 else np.nan
                else:
                    avh[j] = avg[i - j]
            if cagri:
                a5 = atr[calls[side, kk - sw]] if kk - sw >= 0 else np.nan
            else:
                a5 = atr[i - sw]
            # pivot_eval
            avail = i - sw + 1
            bars = max(1, min(prof_lb, avail))
            newest = i - sw
            oldest = i - (sw + bars - 1)
            bot, step = _profile(h, l, c, v, newest, oldest, rows, mintick, tot, buy)
            atrP = max(mintick if math.isnan(a5) else a5, mintick)
            node, evid, nStr, pk, dr = _node(raw, supp, atrP, bot, step, tot, buy, rows, srch)
            vSc, wSc, aSc = _features(i, supp, o, h, l, c, v, avh, sw, absrad, mintick, pivx, bodymax, absvx)
            ok = nStr >= node_min and evid >= evid_min
            pull = pull_max * _clip(evid / 0.65) if ok else 0.0
            p = raw + (node - raw) * pull
            sc = 100.0 * (0.50 * evid + 0.20 * aSc + 0.15 * vSc + 0.15 * wSc)
            stored = False
            if ok and sc >= score_min:
                # store_lvl
                tol = max(atrP * merge_atr, mintick)
                idx = -1
                best = 1e20
                for k in range(nl):
                    if Ls[k] == supp:
                        d = abs(Lp[k] - p)
                        if d <= tol and d < best:
                            best = d
                            idx = k
                if idx >= 0:
                    if sc > Lsc[idx]:
                        Lp[idx] = p
                        Lsc[idx] = sc
                        stored = True
                else:
                    Lp[nl] = p
                    Lsc[nl] = sc
                    Ls[nl] = supp
                    nl += 1
                    stored = True
            if supp:
                new_sup[i] = stored
            else:
                new_res[i] = stored
        # manage_breaks
        a0 = atr[i]
        if math.isnan(a0):
            a0 = 0.0
        buf = max(a0 * break_atr, 0.0)
        sb = False
        rb = False
        for k in range(nl - 1, -1, -1):
            if Ls[k]:
                broken = c[i] < Lp[k] - buf
            else:
                broken = c[i] > Lp[k] + buf
            if broken:
                if Ls[k]:
                    sb = True
                else:
                    rb = True
                for q in range(k, nl - 1):
                    Lp[q] = Lp[q + 1]
                    Lsc[q] = Lsc[q + 1]
                    Ls[q] = Ls[q + 1]
                nl -= 1
        sup_brk[i] = sb
        res_brk[i] = rb
        # trim_lvls
        while nl > max_lvl:
            weak = 0
            scm = Lsc[0]
            for k in range(1, nl):
                if Lsc[k] < scm:
                    scm = Lsc[k]
                    weak = k
            for q in range(weak, nl - 1):
                Lp[q] = Lp[q + 1]
                Lsc[q] = Lsc[q + 1]
                Ls[q] = Ls[q + 1]
            nl -= 1
        # mum sonu durumlari
        nlv[i] = nl
        best = np.inf
        side_n = 0
        sa = np.nan
        ru = np.nan
        for k in range(nl):
            d = abs(c[i] - Lp[k])
            if d < best:
                best = d
                side_n = 1 if Ls[k] else -1
            if Ls[k]:
                if Lp[k] < c[i] and (math.isnan(sa) or Lp[k] > sa):
                    sa = Lp[k]
            else:
                if Lp[k] > c[i] and (math.isnan(ru) or Lp[k] < ru):
                    ru = Lp[k]
        if nl > 0:
            dpos[i] = side_n
            near[i] = best
        sup_alt[i] = sa
        res_ust[i] = ru
    return new_sup, new_res, sup_brk, res_brk, tch_al, tch_sat, dpos, near, sup_alt, res_ust, nlv


def hesapla_ic(z, cagri=None, mintick=None):
    """Butun ara diziler (duman testi ve dogrulama icin). Sozlesme ciktisi: hesapla(z)."""
    o, h, l, c, v = (np.ascontiguousarray(z[k], dtype=np.float64) for k in ("o", "h", "l", "c", "v"))
    if cagri is None:
        cagri = CAGRI_GECMISI
    if mintick is None:
        mintick = mintick_tahmin(c)
    avg = sma(v, VOL_LEN)
    atr = atr_pine(true_range(h, l, c), ATR_LEN)
    ph = pivot(h, SWING, SWING, True)
    pl = pivot(l, SWING, SWING, False)
    r = _motor(o, h, l, c, v, avg, atr, ph, pl, float(mintick), bool(cagri), PROF_LB, PROF_ROWS, SWING, SRCH_ATR, NODE_MIN, EVID_MIN,
               PULL_MAX, SCORE_MIN, MAX_LVL, MERGE_ATR, BREAK_ATR, VOL_LEN, ABS_RAD, PIV_VOL_X, ABS_BODY_MAX, ABS_VOL_X)
    keys = ("new_sup", "new_res", "sup_brk", "res_brk", "tch_al", "tch_sat", "dpos", "near", "sup_alt", "res_ust", "nlv")
    R = dict(zip(keys, r))
    R.update(atr=atr, avg=avg, ph=ph, pl=pl, mintick=float(mintick))
    return R


def hesapla(z, cagri=None, mintick=None):
    R = hesapla_ic(z, cagri, mintick)
    atr = R["atr"]
    with np.errstate(invalid="ignore"):
        yakin = np.isfinite(R["near"]) & np.isfinite(atr) & (R["near"] <= 0.5 * atr)
        uzun = R["sup_alt"] - BREAK_ATR * atr
        kisa = R["res_ust"] + BREAK_ATR * atr
    sb, rb = R["sup_brk"], R["res_brk"]
    return {
        "S": {
            "ZNEW": (R["new_sup"], R["new_res"]),
            "ZBRK": (rb & ~sb, sb & ~rb),
            "ZTCH": (R["tch_al"], R["tch_sat"]),
        },
        "D": {D_AD: R["dpos"].astype(np.int64)},
        "U": {U_AD: yakin},
        "X": {},
        "STOPS": {STOP_AD: (np.where(np.isfinite(uzun), uzun, np.nan), np.where(np.isfinite(kisa), kisa, np.nan))},
        "NATIVE": {},
    }
