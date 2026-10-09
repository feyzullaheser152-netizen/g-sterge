"""Aday 3 (v5.7 arastirmasi): Maliyet gercekciligi - tick tabani, olay ani makasi, EDGE.

Kullanim:
    python3 -I arastirma/makas.py dogrula   # Mart 2024: aggTrades olcutu <-> gercek bookTicker kotasyonu
    python3 -I arastirma/makas.py topla     # 2025-01..2026-09 orneklemi: aggTrades -> dakika ozetleri
    python3 -I arastirma/makas.py analiz    # K1, K2, K3 ve parite tablolari

ON KAYIT (2026-10-08, hicbir sonuc gorulmeden yazildi; tasarim: arastirma lideri secim raporu, Aday 3)
------------------------------------------------------------------------------------------------
Olcut makas s (aggTrades): agg_trade_id sirasinda ardisik iki islem zit yonluyse ve aralarindaki sure <= 100 ms ise
  p_a = alicinin saldirgan oldugu islemin fiyati (is_buyer_maker = false), p_b = saticinin saldirgan oldugu islemin fiyati;
  s = (p_a - p_b) / ((p_a + p_b) / 2), bp. Cift, ikinci islemin dakikasina yazilir. Negatif s atilmaz, kirpilmaz.
  Saatlik s = saatteki ciftlerin ortalamasi (en az 20 cift; yoksa bos). Dakikalik s_m = dakikadaki ciftlerin ortalamasi (>= 1 cift).

On dogrulama (Mart 2024, bookTicker arsivinin son ayi):
  Gunler: 2024-03-05, 03-12 (CPI), 03-15, 03-20 (FOMC), 03-24 (Pazar). Pariteler: BTC, ETH, SOL, XRP, DOGE, WIF, 1000PEPE, ZEC.
  HYPE Mart 2024'te Binance vadelide yoktu; yerine ZEC (o donem dusuk likidite) alindi. Dosya boyutu sorun degil: tasarimdaki 5 gun x 8 parite.
  Gercek kotasyon makasi q = (ask - bid) / orta, bp; saat icinde zaman agirlikli (100 ms izgarada son gecerli kotasyon; ask <= bid atilir).
  Olcutler: parite icinde saatlik Spearman(s, q) ve duzey orani L = medyan_saat(s / q).
  Kapi: Spearman >= 0,7 ve 0,8 <= L <= 1,25, ikisi birden paritelerin en az %80'inde (8'in 7'si). Tutmazsa aday durur:
  K1/K2 karara baglanmaz, yalnizca tanimlayici tablolar verilir. (Tasarim "parite ici ... olmali" diyor; %80 esigi K1 ile tutarlilik icin.)
  Kapi disi ek bilgi: islem anindaki kotasyon, gercek etkin yari makas (islem fiyati - islemden hemen onceki orta, isaretli), EDGE <-> q.

Ana orneklem (yalnizca tam aylar 2025-01..2026-09; gunler UTC):
  A: 22 parite x her ayin 15'i (21 gun; HYPE yalnizca listelenme 2025-05-30 sonrasi).
  B: 8 parite (BTC, ETH, SOL, XRP, DOGE, WIF, 1000PEPE, HYPE) x FOMC, CPI ve NFP gunleri (asagidaki listeler).
  E (tasarima ek, yalnizca Pazar olayi icin): ayni 8 parite x her ayin ilk Pazari (21 gun). A orneklemi Pazar 18:00 icin
    yalnizca 1 (2025) ve 2 (2026) gun iceriyor; karar verilebilmesi icin eklendi. Tasarimdan sapmadir, acikca raporlanir.

K1 (EDGE): Her saat icin EDGE, o saatin 60 adet 1 dk mumu uzerinde (Binance 1 dk mumlari; edge.py degistirilmeden, sign=False).
  Parite ve yil icinde, s'nin gecerli oldugu saatlerde: Spearman(EDGE, s) >= 0,5 ve medyan_saat(EDGE / s) 0,67-1,5.
  Ikisi birden paritelerin en az %80'inde -> o yil K1 tutar. Iki yilda da tutarsa: kayma = max(girdi, EDGE / 2).
K2 (olay ani makasi): Olay pencereleri VSP.pine ile ayni (NY saati): 08:30 Sal-Cum; 09:30-09:43 Pzt-Cum; 10:00-10:08 Pzt-Cum;
  Pazar 18:00-18:07; FOMC gunu 13:59-14:44 (14:00-14:05 alt pencere ayrica raporlanir). Orneklem gunlerinde tatil yok (kontrol edilir).
  Oran = medyan_{olay dakikasi m} [ s_m / B(saat(m)) ]; B(h) = ayni parite, ayni yil, ayni NY saati h'deki olaysiz dakikalarin s_m medyani
  (tum orneklem gunleri; olaysiz = hicbir VSP penceresinde degil). Birincil: tum gunler (tasarimin harfi). Ikincil: ayni gun tipi
  (hafta ici olaylar icin Pzt-Cum, Pazar olayi icin Pazar).
  Bir olay tipi icin karar: iki yilda da parite medyani oran >= 2 ise tutar. Bir yilda o tipte 3'ten az olay gunu varsa "karar yok".
  Carpan: tutan tiplerin iki yildaki parite medyani oranlarinin en kucugu, 0,5'lik adimla asagi yuvarlanir; tek sabit.
  Uygulama bicimi (tasarim taslagindan sapma, sonuclardan once bildirildi): tasarim "kayma x carpan" diyor; bu, kullanicinin girdisinin
  gercek yari makasa esit oldugunu varsayar. Iki bicim de raporlanir: (i) slipSide x k, (ii) max(slipSide, k x 0,5 tick / fiyat).
  Hangisinin onerilecegi: paritelerin olay penceresindeki olculen ortalama yari makasina (s/2, cift agirlikli) medyan mutlak log hatasi
  daha kucuk olan.
K3 (tick tabani): test yok (mantiksal alt sinir: makas >= 1 tick, yari makas >= 0,5 tick). Raporlanir: tick / fiyat (bp),
  s'nin tam 1 tick oldugu ciftlerin orani, dakika medyaninin 1 tick oldugu dakikalarin orani.
Tanimlayici tablolar (karar disi): parite basina medyan kotasyon yari makasi (s_m / 2) ve etkin yari makas (saatlik EDGE / 2),
  genel ve UTC saat gruplarinda: hafta ici ABD seansi (Pzt-Cum 13:00-20:59 UTC), hafta ici Asya seansi (Pzt-Cum 00:00-07:59 UTC),
  hafta sonu (Cmt-Paz). Olay dakikalari ve ayni saatteki olaysiz dakikalar.
"""
import os, sys, glob, time, zipfile, hashlib, subprocess, datetime as dt
from multiprocessing import Pool
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from makas_edge import edge  # noqa: E402

SP = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
RAW = f"{SP}/dl_makas/raw"
OUT = f"{SP}/bt/v57"
DK = f"{OUT}/dk"
DG = f"{OUT}/dogrula"
NPZ = f"{SP}/data_bn/npz"
URL = "https://data.binance.vision/data/futures/um/daily"

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT", "SUIUSDT", "1000PEPEUSDT", "WIFUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "UNIUSDT", "ENAUSDT", "HYPEUSDT", "ZECUSDT"]
SYM8 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "WIFUSDT", "1000PEPEUSDT", "HYPEUSDT"]
VAL_SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "WIFUSDT", "1000PEPEUSDT", "ZECUSDT"]
VAL_DAYS = ["2024-03-05", "2024-03-12", "2024-03-15", "2024-03-20", "2024-03-24"]
LISTED = {"HYPEUSDT": "2025-05-30"}

FOMC = ["2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"]
# CPI ve Istihdam Raporu (NFP) aciklama gunleri, 08:30 ET. Kapanma kaymalari dahil (Eylul 2025 CPI 24 Ekim; Ekim 2025 CPI/NFP yayimlanmadi;
# Eylul NFP 20 Kasim, Kasim NFP 16 Aralik, Kasim CPI 18 Aralik; Ocak 2026 NFP 11 Subat, CPI 13 Subat).
CPI = ["2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13", "2025-06-11", "2025-07-15", "2025-08-12", "2025-09-11", "2025-10-24", "2025-12-18", "2026-01-13", "2026-02-13", "2026-03-11", "2026-04-10", "2026-05-12", "2026-06-10", "2026-07-14", "2026-08-12", "2026-09-11"]
NFP = ["2025-01-10", "2025-02-07", "2025-03-07", "2025-04-04", "2025-05-02", "2025-06-06", "2025-07-03", "2025-08-01", "2025-09-05", "2025-11-20", "2025-12-16", "2026-01-09", "2026-02-11", "2026-03-06", "2026-04-03", "2026-05-08", "2026-06-05", "2026-07-02", "2026-08-07", "2026-09-04"]
# 2025-01..2026-09 tatilleri, VSP.pine'daki gibi iki ayri liste: NYSE (09:30 acilisi yok) ve federal veri tatili (08:30 / 10:00 verisi yok).
# Uygulama notu (2026-10-09, sonuclar gorulmeden): on kayittaki "orneklemde tatil yok" denetimi 2026-04-03'te (Kutsal Cuma, NFP gunu) tutmuyor.
# O gun NYSE kapali ama veri gunu; VSP gibi 09:30 penceresi o gun yok, 08:30 ve 10:00 var. Diger orneklem gunlerinde tatil yok.
NYHOL = {"2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"}
DATAHOL = {"2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-10-13", "2025-11-11", "2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"}
HOL = NYHOL | DATAHOL


def months():
    out = []
    for y in (2025, 2026):
        for m in range(1, 13):
            if y == 2026 and m > 9:
                break
            out.append((y, m))
    return out


def sample_tasks():
    """(sym, gun, orneklem) listesi; ayni (sym, gun) bir kez."""
    seen, tasks = set(), []
    def add(sym, d, tag):
        if sym in LISTED and d < LISTED[sym]:
            return
        if (sym, d) in seen:
            return
        seen.add((sym, d)); tasks.append((sym, d, tag))
    for y, m in months():
        for s in SYMS:
            add(s, f"{y}-{m:02d}-15", "A")
    for d in sorted(set(FOMC + CPI + NFP)):
        for s in SYM8:
            add(s, d, "B")
    for y, m in months():
        d = dt.date(y, m, 1)
        while d.weekday() != 6:
            d += dt.timedelta(1)
        for s in SYM8:
            add(s, d.isoformat(), "E")
    return tasks


# ---------------------------------------------------------------- indirme ve okuma
def indir(kind, sym, day):
    fn = f"{sym}-{kind}-{day}.zip"
    url = f"{URL}/{kind}/{sym}/{fn}"
    d = os.path.join(RAW, f"{sym}_{kind}_{day}")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, fn)
    for _ in range(4):
        r = subprocess.run(["curl", "-sS", "-f", "--retry", "3", "-o", path, url], capture_output=True, text=True)
        if r.returncode == 22:
            return None
        if r.returncode == 0:
            ck = subprocess.run(["curl", "-sS", "-f", url + ".CHECKSUM"], capture_output=True, text=True)
            if ck.returncode != 0:
                return path
            want = ck.stdout.split()[0].strip().lower()
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for b in iter(lambda: f.read(1 << 22), b""):
                    h.update(b)
            if h.hexdigest() == want:
                return path
        time.sleep(5)
    return None


def sil(path):
    if path and os.path.exists(path):
        os.remove(path)
        try:
            os.rmdir(os.path.dirname(path))
        except OSError:
            pass


def _header(path):
    with zipfile.ZipFile(path) as z:
        nm = z.namelist()[0]
        with z.open(nm) as f:
            first = f.readline()
    return nm, first[:1].isalpha()


def read_agg(path):
    nm, hdr = _header(path)
    with zipfile.ZipFile(path) as z, z.open(nm) as f:
        df = pd.read_csv(f, header=None, skiprows=1 if hdr else 0, names=["id", "p", "q", "f", "l", "t", "m"], usecols=["id", "p", "q", "t", "m"], dtype={"id": np.int64, "p": np.float64, "q": np.float64, "t": np.int64, "m": str})
    if not df["id"].is_monotonic_increasing:
        df = df.sort_values("id", kind="stable")
    m = df["m"].str.strip().str.lower().to_numpy()
    assert np.isin(m, ["true", "false"]).all()
    t = df["t"].to_numpy()
    if t.max() > 1e14:
        t = t // 1000
    return t, df["p"].to_numpy(), df["q"].to_numpy(), m == "false"


def infer_tick(p):
    """Fiyat izgarasi: islemlerin en az %95'inin tam katinda oldugu en buyuk aday (1, 2, 5 x 10^k).
    Uygulama notu (2026-10-09, sonuclar gorulmeden): ilk surum en kucuk fiyat farkini aliyordu; Binance'te az sayida (%0,2)
    tick-alti islem var (ornek SOLUSDT 187,261; makasin icinde), bu yuzden SOL'da tick 0,001 cikiyordu. Tick-alti islemler
    olcutten atilmaz; yalnizca tick tahmini duzeltildi."""
    p = np.asarray(p, dtype=np.float64)
    if len(p) > 200000:
        p = p[np.random.default_rng(0).choice(len(p), 200000, replace=False)]
    best = None
    for e in range(-10, 4):
        for m in (1, 2, 5):
            tk = m * 10.0 ** e
            k = p / tk
            if np.mean((k >= 1) & (np.abs(p - np.rint(k) * tk) <= 1e-7 * p)) >= 0.95:
                best = tk
    return float(f"{best:.3g}")


def ciftler(t, p, buy, tick):
    chg = buy[:-1] != buy[1:]
    i = np.flatnonzero(chg & ((t[1:] - t[:-1]) <= 100))
    pa = np.where(buy[i], p[i], p[i + 1])
    pb = np.where(buy[i], p[i + 1], p[i])
    s = (pa - pb) / ((pa + pb) / 2) * 1e4
    nt = np.rint((pa - pb) / tick).astype(np.int64)
    return t[i + 1], s, nt


def dakika_ozet(t, p, q, buy, tick, d0):
    """Gunun 1440 dakikasi icin cift ve islem ozetleri."""
    tt, s, nt = ciftler(t, p, buy, tick)
    mi = (tt - d0) // 60000
    k = (mi >= 0) & (mi < 1440)
    mi, s, nt = mi[k], s[k], nt[k]
    o = {}
    o["n"] = np.bincount(mi, minlength=1440)
    o["ssum"] = np.bincount(mi, weights=s, minlength=1440)
    o["s2sum"] = np.bincount(mi, weights=s * s, minlength=1440)
    o["n1"] = np.bincount(mi, weights=(nt == 1), minlength=1440)
    o["nle0"] = np.bincount(mi, weights=(nt <= 0), minlength=1440)
    med = pd.Series(s).groupby(mi).median()
    o["smed"] = med.reindex(range(1440)).to_numpy()
    # islemlerden 1 dk mum (kontrol icin)
    if not np.all(np.diff(t) >= 0):
        j = np.argsort(t, kind="stable"); t, p, q = t[j], p[j], q[j]
    tm = (t - d0) // 60000
    k = (tm >= 0) & (tm < 1440)
    t, p, q, tm = t[k], p[k], q[k], tm[k]
    oo = np.full((4, 1440), np.nan)
    st = np.flatnonzero(np.r_[True, tm[1:] != tm[:-1]])
    en = np.r_[st[1:], len(tm)] - 1
    mm = tm[st]
    oo[0, mm] = p[st]; oo[3, mm] = p[en]
    oo[1, mm] = np.maximum.reduceat(p, st); oo[2, mm] = np.minimum.reduceat(p, st)
    o["ohlc"] = oo
    o["ntr"] = np.bincount(tm, minlength=1440)
    o["qv"] = np.bincount(tm, weights=p * q, minlength=1440)
    o["tick"] = np.array(tick)
    o["d0"] = np.array(d0)
    return o


def gun_ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 1_000_000)


# ---------------------------------------------------------------- 1) dogrulama (Mart 2024)
def dogrula_bir(sym, day):
    outp = f"{DG}/{sym}_{day}.npz"
    if os.path.exists(outp):
        return outp
    d0 = gun_ms(day)
    pa = indir("aggTrades", sym, day)
    if pa is None:
        print("aggTrades yok", sym, day, flush=True); return None
    t, p, q, buy = read_agg(pa)
    sil(pa)
    tick = infer_tick(p)
    o = dakika_ozet(t, p, q, buy, tick, d0)
    pb = indir("bookTicker", sym, day)
    if pb is None:
        print("bookTicker yok", sym, day, flush=True); return None
    nm, hdr = _header(pb)
    G = d0 + 100 * np.arange(864000, dtype=np.int64)
    gq = np.full(864000, np.nan); g1 = np.zeros(864000, dtype=bool)
    sgn = np.where(buy, 1.0, -1.0)
    eff = np.full(len(t), np.nan); qt = np.full(len(t), np.nan); age = np.full(len(t), np.nan)
    prev = None; gdone = 0; tdone = 0; nonmono = 0; nrow = 0; ncross = 0
    with zipfile.ZipFile(pb) as z, z.open(nm) as f:
        rd = pd.read_csv(f, header=None, skiprows=1 if hdr else 0, names=["u", "bp", "bq", "ap", "aq", "tt", "et"], usecols=["bp", "ap", "tt"], dtype={"bp": np.float64, "ap": np.float64, "tt": np.int64}, chunksize=2_000_000)
        for ch in rd:
            tq = ch["tt"].to_numpy(); b = ch["bp"].to_numpy(); a = ch["ap"].to_numpy()
            nrow += len(tq)
            if not np.all(np.diff(tq) >= 0):
                nonmono += 1; j = np.argsort(tq, kind="stable"); tq, b, a = tq[j], b[j], a[j]
            if prev is not None:
                tq = np.r_[prev[0], tq]; b = np.r_[prev[1], b]; a = np.r_[prev[2], a]
            ok = a > b
            ncross += int((~ok).sum())
            mid = (a + b) / 2
            spb = np.where(ok, (a - b) / mid * 1e4, np.nan)
            one = ok & (np.rint((a - b) / tick) == 1)
            thi = tq[-1]
            gend = np.searchsorted(G, thi, side="right")
            if gend > gdone:
                gg = G[gdone:gend]
                ix = np.searchsorted(tq, gg, side="right") - 1
                v = ix >= 0
                gq[gdone:gend][v] = spb[ix[v]]; g1[gdone:gend][v] = one[ix[v]]
                gdone = gend
            tend = np.searchsorted(t, thi, side="right")
            if tend > tdone:
                ix = np.searchsorted(tq, t[tdone:tend], side="left") - 1
                v = ix >= 0
                sl = np.arange(tdone, tend)[v]
                m_ = mid[ix[v]]
                eff[sl] = np.where(ok[ix[v]], sgn[sl] * (p[sl] - m_) / m_ * 1e4, np.nan)
                qt[sl] = spb[ix[v]]
                age[sl] = t[sl] - tq[ix[v]]
                tdone = tend
            prev = (tq[-1:], b[-1:], a[-1:])
    sil(pb)
    if gdone < 864000 and prev is not None and prev[2][0] > prev[1][0]:
        m_ = (prev[2][0] + prev[1][0]) / 2
        gq[gdone:] = (prev[2][0] - prev[1][0]) / m_ * 1e4; g1[gdone:] = np.rint((prev[2][0] - prev[1][0]) / tick) == 1
    if tdone < len(t) and prev is not None and prev[2][0] > prev[1][0]:
        m_ = (prev[2][0] + prev[1][0]) / 2; sl = np.arange(tdone, len(t))
        eff[sl] = sgn[sl] * (p[sl] - m_) / m_ * 1e4; qt[sl] = (prev[2][0] - prev[1][0]) / m_ * 1e4; age[sl] = t[sl] - prev[0][0]
    gm = np.arange(864000) // 600
    vg = np.isfinite(gq)
    o["q_tw"] = np.bincount(gm[vg], weights=gq[vg], minlength=1440) / np.maximum(np.bincount(gm[vg], minlength=1440), 1)
    o["q_tw"][np.bincount(gm[vg], minlength=1440) == 0] = np.nan
    o["q1_frac"] = np.bincount(gm[vg], weights=g1[vg], minlength=1440) / np.maximum(np.bincount(gm[vg], minlength=1440), 1)
    tm = (t - d0) // 60000
    v = np.isfinite(eff) & (tm >= 0) & (tm < 1440)
    nt_ = p[v] * q[v]
    o["eff_n"] = np.bincount(tm[v], minlength=1440)
    o["eff_sum"] = np.bincount(tm[v], weights=eff[v], minlength=1440)
    o["eff_vw"] = np.bincount(tm[v], weights=eff[v] * nt_, minlength=1440)
    o["notional"] = np.bincount(tm[v], weights=nt_, minlength=1440)
    o["qt_sum"] = np.bincount(tm[v], weights=qt[v], minlength=1440)
    o["age_med"] = np.array(np.nanmedian(age))
    o["meta"] = np.array([nrow, nonmono, ncross])
    np.savez_compressed(outp, **o)
    print(f"dogrula {sym} {day}: tick {tick}, kotasyon satiri {nrow}, ters {ncross}, sirasiz parca {nonmono}", flush=True)
    return outp


def dogrula():
    os.makedirs(DG, exist_ok=True)
    for day in VAL_DAYS:
        for sym in VAL_SYMS:
            try:
                dogrula_bir(sym, day)
            except Exception as e:  # noqa: BLE001
                print("HATA", sym, day, repr(e), flush=True)


# ---------------------------------------------------------------- 2) ana orneklem
def topla_bir(task):
    sym, day, tag = task
    outp = f"{DK}/{sym}_{day}.npz"
    if os.path.exists(outp):
        return outp
    try:
        pa = indir("aggTrades", sym, day)
        if pa is None:
            print("yok", sym, day, flush=True); return None
        t, p, q, buy = read_agg(pa)
        sil(pa)
        tick = infer_tick(p)
        o = dakika_ozet(t, p, q, buy, tick, gun_ms(day))
        o["tag"] = np.array(tag)
        np.savez_compressed(outp, **o)
        return outp
    except Exception as e:  # noqa: BLE001
        print("HATA", sym, day, repr(e), flush=True)
        return None


def topla():
    os.makedirs(DK, exist_ok=True)
    tasks = sample_tasks()
    tatil = sorted({x[1] for x in tasks} & HOL)
    print("orneklemdeki tatil gunleri (VSP gibi islenir):", tatil, flush=True)
    print("gorev:", len(tasks), {g: sum(1 for x in tasks if x[2] == g) for g in "ABE"}, flush=True)
    n = 0
    with Pool(2) as pl:
        for r in pl.imap_unordered(topla_bir, tasks):
            n += 1
            if n % 50 == 0:
                print(n, "/", len(tasks), time.strftime("%H:%M:%S"), flush=True)
    print("bitti", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dogrula":
        dogrula()
    elif cmd == "topla":
        topla()
    elif cmd == "analiz":
        import makas_analiz
        makas_analiz.main()
    else:
        print(__doc__)
