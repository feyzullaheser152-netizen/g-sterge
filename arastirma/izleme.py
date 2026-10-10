"""VSP izleme (yeniden dogrulama). Piyasa degisir: gostergenin dayandigi bulgular her ay yeni veriyle yeniden sinanir.

Kullanim:
  python3 arastirma/izleme.py guncelle   # data.binance.vision'dan eksik 1 dk mumlari indirir, npz dosyalarina ekler
  python3 arastirma/izleme.py rapor      # aylik olcumleri hesaplar, arastirma/IZLEME.md dosyasini yazar
Veri klasoru: VSP_VERI ortam degiskeni. Yoksa bu oturumun scratchpad/data_bn klasoru, o da yoksa ~/vsp_veri.
Izleme verisi npz_izleme/ altinda tutulur; ilk calismada npz/ kopyalanir, o da yoksa 2025-01'den indirilir.
Arastirma betiklerinin kullandigi npz/ klasorune dokunulmaz (eski sonuclar yeniden uretilebilir kalsin).

Olcumler (22 Binance USDT-M paritesi, takvim ayi bazinda; tanimlar VSP.pine v5.6 ve BULGULAR bolum 10 ile ayni):
  1) Beklenen hareket: 15 dk %50 (0,61) ve %80 (1,23) bantlarinin kapsamasi. Hedef 50 / 80.
     Ayrica sari anlarda (08:30, 09:30, Pazar 18:00 ya da FOMC ufukta; NY acilisi 09:30-09:43) %80 kapsamasi.
  2) Turuncu (sert satis sonrasi): ilk mumda SHORT acanin 5 ve 15 dk ortalama kaybi (bp), gun kumelenmis t. Karsilastirma: LONG.
  3) Mor / kirmizi (olagandisi oynaklik): olay pencereleri (CPI/NFP gunleri arastirma/takvim.py listesinden), asiri mumdan sonraki 4 mum (olay bazli, taban spike mumunda sabit),
     iki yonde sert akis. x = |r1| / sigma_taban (onceki 1440 mumun std'si, bir mum gecikmeli);
     'x normal' = kategori ortalamasi / ayni aylarin tum mumlarinin ortalamasi.
  4) Izlenen ama gostergede olmayanlar: LONG kovalama, fonlama dakikalari (-3..+2 dk, 8 saatlik takvim).
  5) Bekleyen on kayitli test (BULGULAR 10d): karisim var = 0,8 ewVar + 0,2 sigma_taban^2, katsayilar 0,575 / 1,152.
     Yalnizca tam 2026-10, 2026-11, 2026-12 aylariyla, bir kez degerlendirilir (sonraki aylar eklenmez).
Durum yalnizca tam aylardan hesaplanir. Pencereler: kapsama ve mor icin son 3 tam ay; turuncu ve FOMC icin son 12 tam ay.
Kaldirma kurali: iki ardisik tam ay penceresinde (bu ay ve bir onceki ay biten pencere) BOZULDU."""
import io, os, shutil, subprocess, sys, zipfile
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import takvim  # CPI / NFP gunleri (iki kaynakla dogrulanmis, dondurulmus liste)

_SCR = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn"
VERI = os.environ.get("VSP_VERI", _SCR if os.path.isdir(_SCR) else os.path.expanduser("~/vsp_veri"))
NPZ = os.path.join(VERI, "npz_izleme")
KAYNAK = os.path.join(VERI, "npz")
INDIR = os.path.join(VERI, "zip_yeni")
CIKTI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IZLEME.md")
SYMS = "BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT AVAXUSDT LINKUSDT LTCUSDT DOTUSDT NEARUSDT SUIUSDT AAVEUSDT UNIUSDT ENAUSDT 1000PEPEUSDT WIFUSDT ARBUSDT OPUSDT ZECUSDT HYPEUSDT".split()
URL = "https://data.binance.vision/data/futures/um"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
FOMC = {"2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09", "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09", "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08", "2028-01-26"}
# VSP.pine ile ayni tatil listeleri (YYYYMMDD, New York tarihi)
NYHOL = {20261126, 20261225, 20270101, 20270118, 20270215, 20270326, 20270531, 20270618, 20270705, 20270906, 20271125, 20271224, 20280117, 20280221, 20280414, 20280529, 20280619, 20280704, 20280904, 20281123, 20281225}
DATAHOL = {20261012, 20261111, 20261126, 20261225, 20270101, 20270118, 20270215, 20270531, 20270618, 20270705, 20270906, 20271011, 20271111, 20271125, 20271224, 20271231, 20280117, 20280221, 20280529, 20280619, 20280704, 20280904, 20281009, 20281110, 20281123, 20281225}
KARISIM_AYLAR = ["2026-10", "2026-11", "2026-12"]
H = 15
ADAYS = sorted(takvim.tarih_kumeleri()["A"] | set(takvim.GELECEK))  # CPI ve NFP gunleri (New York tarihi)
KATS = ["CPI/NFP 08:30", "CPI/NFP 08:30–08:38", "Diğer Sal–Cum 08:30", "NY açılışı 09:30–09:43", "ABD verisi 10:00–10:08", "Pazar 18:00–18:07", "FOMC 14:00–14:05", "FOMC 13:59–14:44", "Aşırı mum sonrası 4 mum", "İki yönde sert akış", "Fonlama −3..+2 dk"]


# ---------------------------------------------------------------- guncelle
def indir(url, hedef):
    if os.path.exists(hedef):
        return True
    tmp = hedef + ".part"
    r = subprocess.run(["curl", "-sSf", "--retry", "3", "-o", tmp, url], capture_output=True)
    if r.returncode != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        return False
    os.replace(tmp, hedef)
    return True


def oku_zip(f):
    with zipfile.ZipFile(f) as z:
        raw = z.read(z.namelist()[0])
    bas = raw[:20].decode(errors="ignore").startswith("open_time")
    d = pd.read_csv(io.BytesIO(raw), header=0 if bas else None)
    d.columns = COLS
    return d


def guncelle():
    os.makedirs(NPZ, exist_ok=True)
    os.makedirs(INDIR, exist_ok=True)
    for s in SYMS:
        if not os.path.exists(os.path.join(NPZ, f"{s}.npz")) and os.path.exists(os.path.join(KAYNAK, f"{s}.npz")):
            shutil.copy(os.path.join(KAYNAK, f"{s}.npz"), os.path.join(NPZ, f"{s}.npz"))
    dun = datetime.now(timezone.utc).date() - timedelta(days=1)
    bu_ay = dun.replace(day=1)
    for s in SYMS:
        f = os.path.join(NPZ, f"{s}.npz")
        eski = dict(np.load(f)) if os.path.exists(f) else None
        son = int(eski["ts"][-1]) if eski is not None else int(datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc).timestamp())
        gun = datetime.fromtimestamp(son + 60, timezone.utc).date()
        parcalar, eksik = [], None
        while gun <= dun:
            ay_sonu = (gun.replace(day=28) + timedelta(days=4)).replace(day=1)
            if gun.day == 1 and ay_sonu <= bu_ay:
                ad = f"{s}-1m-{gun:%Y-%m}.zip"
                h = os.path.join(INDIR, ad)
                if indir(f"{URL}/monthly/klines/{s}/1m/{ad}", h):
                    parcalar.append(h)
                    gun = ay_sonu
                    continue
            ad = f"{s}-1m-{gun:%Y-%m-%d}.zip"
            h = os.path.join(INDIR, ad)
            if not indir(f"{URL}/daily/klines/{s}/1m/{ad}", h):
                eksik = str(gun)  # ilk eksik gunde dur; aksi hâlde o gun kalici bosluk olarak kalir
                break
            parcalar.append(h)
            gun += timedelta(days=1)
        if not parcalar:
            print(s, "yeni veri yok", f"(ilk eksik gün: {eksik})" if eksik else "")
            continue
        d = pd.concat([oku_zip(p) for p in parcalar]).drop_duplicates("open_time").sort_values("open_time")
        yeni = {"ts": (d["open_time"].to_numpy() // 1000).astype(np.int64), "o": d["open"].to_numpy(float), "h": d["high"].to_numpy(float), "l": d["low"].to_numpy(float), "c": d["close"].to_numpy(float), "v": d["volume"].to_numpy(float), "tbv": d["taker_buy_volume"].to_numpy(float), "qv": d["quote_volume"].to_numpy(float)}
        m = yeni["ts"] > son
        out = {k: np.concatenate([eski[k], yeni[k][m]]) for k in yeni} if eski is not None else {k: yeni[k][m] for k in yeni}
        np.savez(f + ".tmp.npz", **out)
        os.replace(f + ".tmp.npz", f)
        bos = int(np.sum(np.diff(out["ts"]) != 60))
        print(s, "+", int(m.sum()), "mum; son:", datetime.fromtimestamp(int(out["ts"][-1]), timezone.utc).strftime("%Y-%m-%d %H:%M"), "| boşluk:", bos, f"| ilk eksik gün: {eksik}" if eksik else "")


# ---------------------------------------------------------------- rapor
def son_ind(mask):
    """Her t icin, t-1'e kadarki son True indeksi (yoksa -1e9)."""
    idx = np.where(mask, np.arange(len(mask)), -10**9)
    acc = np.maximum.accumulate(idx)
    return np.r_[-10**9, acc[:-1]]


def parite(s):
    z = np.load(os.path.join(NPZ, f"{s}.npz"))
    ts, h, l, c, v = z["ts"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    rs = pd.Series(r)
    sd1 = rs.rolling(1440).std(ddof=0).to_numpy()
    sb = rs.rolling(1440).std(ddof=0).shift(1).to_numpy()
    lc15 = np.r_[np.full(15, np.nan), lc[:-15]]
    z15 = np.where(sd1 > 0, (lc - lc15) / (sd1 * np.sqrt(15)), 0.0)
    dp = np.r_[np.nan, np.diff(c)]
    dps = pd.Series(dp).rolling(100).std(ddof=0).to_numpy()
    ok = dps > 0
    bf = np.where(ok, 1 / (1 + np.exp(-1.702 * np.nan_to_num(dp) / np.where(ok, dps, 1))), 0.5)
    sv = v * (2 * bf - 1)
    v15 = pd.Series(v).rolling(15).sum().to_numpy()
    imb = np.where(v15 > 0, pd.Series(sv).rolling(15).sum().to_numpy() / np.where(v15 > 0, v15, 1), 0.0)
    fUp = np.nan_to_num((z15 >= 3) & (imb >= 0.15)).astype(bool)
    fDn = np.nan_to_num((z15 <= -3) & (imb <= -0.15)).astype(bool)
    t = np.arange(n)
    dnAgo = (t - 1) - son_ind(fDn)
    upAgo = (t - 1) - son_ind(fUp)
    newDn = fDn & (dnAgo >= 15)
    newUp = fUp & (upAgo >= 15)
    twoWay = (upAgo < 15) & (dnAgo < 15)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[np.nan, c[:-1]]), np.abs(l - np.r_[np.nan, c[:-1]])))
    atr = pd.Series(np.nan_to_num(tr)).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    spike = np.nan_to_num((h - l) > 4 * np.r_[np.nan, atr[:-1]]).astype(bool)
    x = np.abs(r) / sb
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    em = (et.hour * 60 + et.minute).to_numpy()
    dow = et.dayofweek.to_numpy()  # 0 = Pazartesi
    gun = np.asarray(et.strftime("%Y-%m-%d"))
    ymd = (et.year * 10000 + et.month * 100 + et.day).to_numpy()
    fom = np.isin(gun, list(FOMC))
    hol = np.isin(ymd, list(NYHOL))
    dhol = np.isin(ymd, list(DATAHOL))
    wk = dow < 5
    big = np.isin(gun, ADAYS) & (dow >= 1) & (dow <= 4) & ~dhol
    utc = pd.to_datetime(ts, unit="s", utc=True)
    fmod = ((utc.hour * 60 + utc.minute).to_numpy()) % 480
    kat = {
        "CPI/NFP 08:30": big & (em == 510),
        "CPI/NFP 08:30–08:38": big & (em >= 510) & (em <= 518),
        "Diğer Sal–Cum 08:30": (em == 510) & (dow >= 1) & (dow <= 4) & ~dhol & ~np.isin(gun, ADAYS),
        "NY açılışı 09:30–09:43": wk & ~hol & (em >= 570) & (em <= 583),
        "ABD verisi 10:00–10:08": wk & ~dhol & (em >= 600) & (em <= 608),
        "Pazar 18:00–18:07": (dow == 6) & (em >= 1080) & (em <= 1087),
        "FOMC 14:00–14:05": fom & (em >= 840) & (em <= 845),
        "FOMC 13:59–14:44": fom & (em >= 839) & (em <= 884),
        "İki yönde sert akış": twoWay,
        "Fonlama −3..+2 dk": (fmod >= 477) | (fmod <= 2),
    }
    ay = np.asarray(utc.strftime("%Y-%m"))
    gecerli = np.isfinite(x) & (t >= 3000)
    vol = []
    for a in np.unique(ay[gecerli]):
        m = gecerli & (ay == a)
        row = {"ay": a, "sym": s, "tum_s": x[m].sum(), "tum_n": int(m.sum())}
        for k, kk in kat.items():
            mk = m & kk
            row[k + "_s"] = x[mk].sum()
            row[k + "_n"] = int(mk.sum())
        vol.append(row)
    V = pd.DataFrame(vol).set_index("ay")
    # asiri mum: olay bazli (BULGULAR 10a ile ayni), spike'tan sonraki 1..4. mum, taban spike mumunda sabit
    ix = np.flatnonzero(spike & (t >= 3000) & (t < n - 5) & np.isfinite(sb) & (sb > 0))
    xs = np.stack([np.abs(r[ix + j]) for j in range(1, 5)], 1) / sb[ix][:, None]
    sp = pd.DataFrame({"ay": ay[ix], "s": xs.sum(1), "n": 4}).groupby("ay").sum()
    V["Aşırı mum sonrası 4 mum_s"] = sp["s"].reindex(V.index).fillna(0)
    V["Aşırı mum sonrası 4 mum_n"] = sp["n"].reindex(V.index).fillna(0).astype(int)
    # kovalama olaylari
    ev = []
    for side, mask in (("SHORT", newDn), ("LONG", newUp)):
        ix = np.flatnonzero(mask & (t >= 3000) & (t < n - 16))
        sg = -1 if side == "SHORT" else 1
        for hh in (5, 15):
            ev.append(pd.DataFrame({"ay": ay[ix], "gun": ts[ix] // 86400, "sym": s, "yon": side, "h": hh, "kayip": -sg * (lc[ix + hh] - lc[ix]) * 1e4}))
    # sari beklenen hareket (VSP evInH): 08:30, 09:30, Pazar 18:00 ya da FOMC 14:00 sonraki H mumda baslar, ya da NY acilisi 09:30-09:43
    bas = ((em == 510) & (dow >= 1) & (dow <= 4) & ~dhol) | ((em == 570) & wk & ~hol) | ((dow == 6) & (em == 1080)) | (fom & (em == 840))
    cb = np.r_[0, np.cumsum(bas)]
    # kapsama (her 5 mumda bir)
    ix = np.arange(3000, n - H - 1, 5)
    ix = ix[np.isfinite(sb[ix]) & (sb[ix] > 0) & (ew[ix] > 0)]
    mv = np.abs(lc[ix + H] - lc[ix])
    sari = (cb[ix + H + 1] - cb[ix + 1] > 0) | kat["NY açılışı 09:30–09:43"][ix]
    kap = pd.DataFrame({"ay": ay[ix], "q": mv / np.sqrt(ew[ix] * H), "qb": mv / np.sqrt((0.8 * ew[ix] + 0.2 * sb[ix] ** 2) * H), "rho": np.sqrt(ew[ix]) / sb[ix], "hm": 0.61 * np.sqrt(ew[ix] * H) * 100 >= 0.08, "sari": sari})
    return V.reset_index(), pd.concat(ev), kap, int(ts[-1])


def kume_t(df):
    """Ortalama, gun kumelenmis standart hata ve t."""
    if len(df) < 2:
        return np.nan, np.nan, np.nan
    m = df.kayip.mean()
    psi = (df.kayip - m).groupby(df.gun).sum()
    se = np.sqrt((psi ** 2).sum()) / len(df)
    return m, se, m / se if se > 0 else np.nan


def durum(deger, iyi, zayif, ters=False):
    if deger is None or not np.isfinite(deger):
        return "veri yok"
    if ters:
        return "TUTUYOR" if deger <= iyi else "ZAYIFLADI" if deger <= zayif else "BOZULDU"
    return "TUTUYOR" if deger >= iyi else "ZAYIFLADI" if deger >= zayif else "BOZULDU"


def tr(x, d=2, isaret=False):
    if x is None or not np.isfinite(x):
        return "—"
    return (f"{x:+.{d}f}" if isaret else f"{x:.{d}f}").replace(".", ",")


def rapor():
    V, E, K, son_ts = [], [], [], 0
    for s in SYMS:
        if not os.path.exists(os.path.join(NPZ, f"{s}.npz")):
            continue
        a, b, c, lt = parite(s)
        V.append(a); E.append(b); K.append(c); son_ts = max(son_ts, lt)
        print("tamam", s, file=sys.stderr, flush=True)
    V, E, K = pd.concat(V), pd.concat(E), pd.concat(K)
    import izleme_sinyal as IS
    T = IS.hesapla()  # gostergedeki sinyallerin islemleri (brut bp)
    G = V.groupby("ay").sum(numeric_only=True)
    aylar = sorted(G.index)
    sonraki = lambda a: (pd.Period(a, "M") + 1).start_time.tz_localize("UTC").timestamp()
    tam = [a for a in aylar if sonraki(a) - 60 <= son_ts]
    eksik = [a for a in aylar if a not in tam]
    if len(tam) < 13:
        print("En az 13 tam ay gerekli", file=sys.stderr)
        return

    def hacim(ayl):
        g = G.loc[ayl].sum()
        tb = g["tum_s"] / g["tum_n"]
        return {k: ((g[k + "_s"] / g[k + "_n"]) / tb if g[k + "_n"] > 0 else np.nan, int(g[k + "_n"])) for k in KATS}, sum(1 for d in FOMC if d[:7] in ayl)

    def pencere(son_i):
        """son_i: tam aylar listesindeki son ay indeksi. Durum satirlarini dondurur."""
        w3, w12 = tam[son_i - 2: son_i + 1], tam[son_i - 11: son_i + 1]
        o3, _ = hacim(w3)
        o12, nf = hacim(w12)
        K3 = K[K.ay.isin(w3)]
        c50, c80 = (K3.q <= 0.61).mean() * 100, (K3.q <= 1.23).mean() * 100
        cs80, cd80 = (K3.q[K3.sari] <= 1.23).mean() * 100, (K3.q[~K3.sari] <= 1.23).mean() * 100
        E12, E3 = E[E.ay.isin(w12)], E[E.ay.isin(w3)]
        s5 = kume_t(E12[(E12.yon == "SHORT") & (E12.h == 5)])
        s15 = kume_t(E12[(E12.yon == "SHORT") & (E12.h == 15)])
        s5_3 = kume_t(E3[(E3.yon == "SHORT") & (E3.h == 5)])
        l5 = kume_t(E12[(E12.yon == "LONG") & (E12.h == 5)])
        ps = E12[(E12.yon == "SHORT") & (E12.h == 5)].groupby("sym").kayip.mean()
        sat = [
            ("Beklenen hareket %80 bandı (hedef 80)", f"%{tr(c80, 1)}", durum(abs(c80 - 80), 3, 6, ters=True), "son 3 tam ay; mutlak sapma ≤ 3 tutuyor, ≤ 6 zayıfladı"),
            ("Beklenen hareket %50 bandı (hedef 50)", f"%{tr(c50, 1)}", durum(abs(c50 - 50), 3, 6, ters=True), "son 3 tam ay; aynı"),
            ("Sarı beklenen hareket: %80 bandın sarı anlarda kapsaması", f"%{tr(cs80, 1)} (diğer anlar %{tr(cd80, 1)})", durum(cs80, 76, 78, ters=True), "son 3 tam ay; sarı uyarı, bant dar kaldığı sürece gerekli: ≤ %76 tutuyor, ≤ %78 zayıfladı, > %78 bozuldu (uyarı gereksiz)"),
            ("Turuncu: SHORT kovalama, 5 dk kayıp", f"{tr(s5[0], 2, True)} bp (t {tr(s5[2], 1)}; parite %{(ps > 0).mean() * 100:.0f}); son 3 ay {tr(s5_3[0], 2, True)}", durum(s5[0], 1.0, 0.0), "son 12 tam ay; ≥ +1 bp tutuyor, 0–1 zayıfladı, < 0 bozuldu"),
            ("Turuncu: SHORT kovalama, 15 dk kayıp", f"{tr(s15[0], 2, True)} bp (t {tr(s15[2], 1)})", durum(s15[0], 1.0, 0.0), "son 12 tam ay; aynı"),
        ]
        T12 = T[T.ay.isin(w12)]
        for ad, esik in IS.SINYALLER:
            x = T12[T12.sinyal == ad]
            mm, tt = IS.kume_t(x.brut, x.gun)
            kural = "≥ +1 bp ve t ≥ 2 tutuyor, > 0 zayıfladı, ≤ 0 bozuldu" if esik else "> 0 ve t ≥ 2 tutuyor, > 0 zayıfladı, ≤ 0 bozuldu"
            sat.append((f"Sinyal: {ad}, brüt bp / işlem", f"{tr(mm, 2, True)} bp (t {tr(tt, 1)}; n {len(x)})", IS.durum(mm, tt, esik), "son 12 tam ay; " + kural))
        for k in KATS:
            if k.startswith("Fonlama"):
                continue
            if k.startswith("FOMC") or k.startswith("CPI"):
                kr = k in ("FOMC 14:00–14:05", "CPI/NFP 08:30")
                v, nn = o12[k]
                esik = (3.0, 2.0) if kr else (1.5, 1.2)
                say = f"{nf} toplantı" if k.startswith("FOMC") else f"{sum(1 for d in ADAYS if d[:7] in w12)} gün"
                sat.append((("Kırmızı: " if kr else "Mor: ") + k, f"×{tr(v)} ({say})", durum(v, *esik), f"son 12 tam ay; ≥ ×{tr(esik[0], 1)} tutuyor, ≥ ×{tr(esik[1], 1)} zayıfladı"))
            else:
                v, nn = o3[k]
                sat.append(("Mor: " + k, f"×{tr(v)} (n {nn})", durum(v, 1.5, 1.2), "son 3 tam ay; ≥ ×1,5 tutuyor, ≥ ×1,2 zayıfladı"))
        izle = [
            ("LONG kovalama, 5 dk kayıp (göstergede yok)", f"{tr(l5[0], 2, True)} bp (t {tr(l5[2], 1)})", "yeniden test et" if l5[0] >= 1.0 and l5[2] >= 2 else "gerek yok", "son 12 tam ay; ≥ +1 bp ve t ≥ 2 olursa ön kayıtlı testle yeniden sına"),
            ("Fonlama −3..+2 dk (göstergede yok)", f"×{tr(o3['Fonlama −3..+2 dk'][0])}", "yeniden test et" if o3["Fonlama −3..+2 dk"][0] >= 1.5 else "gerek yok", "son 3 tam ay; ≥ ×1,5 olursa yeniden sına"),
        ]
        return w3, w12, sat, izle

    w3, w12, sat, izle = pencere(len(tam) - 1)
    _, _, sat_onceki, _ = pencere(len(tam) - 2)
    onceki = {a: c for a, _, c, _ in sat_onceki}
    # bekleyen on kayitli karisim testi: yalnizca tam 2026-10..12, bir kez
    if all(a in tam for a in KARISIM_AYLAR):
        KY = K[K.ay.isin(KARISIM_AYLAR)].copy()
        KY["dil"] = pd.qcut(KY.rho.rank(method="first"), 10, labels=False)
        cur = KY.groupby("dil").q.apply(lambda x: (x <= 1.23).mean() * 100)
        bl = KY.groupby("dil").qb.apply(lambda x: (x <= 1.152).mean() * 100)
        rms_c, rms_b = np.sqrt(((cur - 80) ** 2).mean()), np.sqrt(((bl - 80) ** 2).mean())
        g_c, g_b = abs((KY.q <= 1.23).mean() * 100 - 80), abs((KY.qb <= 1.152).mean() * 100 - 80)
        g50_c, g50_b = abs((KY.q <= 0.61).mean() * 100 - 50), abs((KY.qb <= 0.575).mean() * 100 - 50)
        gecti = rms_b < rms_c and g_b <= g_c + 0.5 and g50_b <= g50_c + 0.5
        karisim = f"Değerlendirildi (yalnızca {', '.join(KARISIM_AYLAR)}). Ondalık RMS: mevcut {tr(rms_c)}, karışım {tr(rms_b)}. Genel %80 sapması: {tr(g_c)} / {tr(g_b)}; %50: {tr(g50_c)} / {tr(g50_b)}. Sonuç: {'GEÇTİ, göstergeye alınmalı' if gecti else 'geçmedi, değişiklik yok'}."
    else:
        karisim = f"Veri birikiyor: {', '.join(KARISIM_AYLAR)} tam ayları gerekli; tamamlanan: {', '.join(a for a in KARISIM_AYLAR if a in tam) or 'yok'}."
    # aylik seri
    kap = K.groupby("ay").agg(k50=("q", lambda x: (x <= 0.61).mean() * 100), k80=("q", lambda x: (x <= 1.23).mean() * 100), hm=("hm", lambda x: x.mean() * 100))
    kap["ks80"] = K[K.sari].groupby("ay").q.apply(lambda x: (x <= 1.23).mean() * 100)
    kov = E.groupby(["ay", "yon", "h"]).kayip.mean().unstack(["yon", "h"])
    kovn = E[E.h == 5].groupby(["ay", "yon"]).size().unstack("yon")
    taban = G["tum_s"] / G["tum_n"]
    oran = pd.DataFrame({k: (G[k + "_s"] / G[k + "_n"].replace(0, np.nan)) / taban for k in KATS})
    seri = pd.DataFrame(index=aylar)
    seri["%50 kapsama"] = kap["k50"]
    seri["%80 kapsama"] = kap["k80"]
    seri["Sarı %80 kapsama"] = kap["ks80"]
    seri["SHORT kov. 5 dk"] = kov[("SHORT", 5)]
    seri["SHORT n"] = kovn["SHORT"]
    seri["LONG kov. 5 dk"] = kov[("LONG", 5)]
    for k, kisa in (("CPI/NFP 08:30", "CPI/NFP"), ("Diğer Sal–Cum 08:30", "08:30 diğer"), ("NY açılışı 09:30–09:43", "09:30"), ("ABD verisi 10:00–10:08", "10:00"), ("Pazar 18:00–18:07", "Pazar"), ("FOMC 13:59–14:44", "FOMC"), ("Aşırı mum sonrası 4 mum", "Aşırı mum"), ("İki yönde sert akış", "İki yön"), ("Fonlama −3..+2 dk", "Fonlama")):
        seri[kisa] = oran[k]
    seri["Hareket ≥ maliyet %"] = kap["hm"]
    tb = T.groupby(["ay", "sinyal"]).brut.mean().unstack("sinyal")
    for ad, kisa in (("VSP AL", "AL bp"), ("VSP SAT", "SAT bp"), ("SMA20 dönüşü", "SMA20 dön. bp"), ("SMA20 kesişimi", "SMA20 kes. bp"), ("Uyumsuzluk", "Uyumsuzluk bp"), ("Trend çizgisi kırılımı", "Trend ç. bp"), ("Trend çizgisi SAT oku", "Trend ç. SAT bp")):
        seri[kisa] = tb[ad] if ad in tb else np.nan
    bic = {"%50 kapsama": 1, "%80 kapsama": 1, "Sarı %80 kapsama": 1, "SHORT kov. 5 dk": 1, "SHORT n": 0, "LONG kov. 5 dk": 1, "Hareket ≥ maliyet %": 0}
    md = []
    md.append("# VSP İzleme (yeniden doğrulama)\n")
    md.append("Piyasa değişir; bir özellik zamanla güçlenebilir ya da bozulabilir. Bu dosya `arastirma/izleme.py` ile üretilir: Göstergenin dayandığı her bulgu ay ay yeniden ölçülür.\n")
    md.append(f"- **Son çalıştırma:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    md.append(f"- **Veri:** 22 Binance USDT-M paritesi, {aylar[0]} – {datetime.fromtimestamp(son_ts, timezone.utc):%Y-%m-%d}.")
    md.append(f"- **Durum pencereleri (yalnızca tam aylar):** son 3 tam ay ({w3[0]} – {w3[-1]}); turuncu uyarı ve FOMC için son 12 tam ay ({w12[0]} – {w12[-1]}).{' Eksik ay seride gösterilir, duruma girmez: ' + ', '.join(eksik) + '.' if eksik else ''}")
    md.append("- **Yenileme:** `python3 arastirma/izleme.py guncelle`, ardından `python3 arastirma/izleme.py rapor`. Her ay başında çalıştırılmalı.\n")
    md.append("## Göstergedeki özellikler: durum\n")
    md.append("| Özellik | Değer | Durum | Bir önceki pencere | Kural |")
    md.append("|---|---|---|---|---|")
    for a, b, c, d in sat:
        md.append(f"| {a} | {b} | **{c}** | {onceki.get(a, '—')} | {d} |")
    md.append("\n- **Kaldırma kuralı:** Bir özellik iki ardışık tam ay penceresinde (bu tabloda \"Durum\" ve \"Bir önceki pencere\") BOZULDU ise göstergeden çıkarılır. Tek pencerede bozuksa ön kayıtlı testle yeniden sınanır.")
    md.append("- Turuncu uyarı gürültülüdür: 3 aylık ortalamanın standart hatası 2–5 bp. Bu yüzden durumu 12 aylık pencereden verilir.\n")
    md.append("## İzlenen, göstergede olmayanlar\n")
    md.append("| Ölçü | Değer | Sonuç | Kural |")
    md.append("|---|---|---|---|")
    for a, b, c, d in izle:
        md.append(f"| {a} | {b} | {c} | {d} |")
    md.append("\n## Bekleyen ön kayıtlı test: karışım oynaklık tahmini (BULGULAR 10d)\n")
    md.append("- Kural: Ondalık RMS küçülmeli; genel %80 ve %50 kapsama sapması mevcut modelden en fazla 0,5 puan büyük olabilir.")
    md.append(f"- {karisim}\n")
    md.append("## Aylık seri\n")
    md.append("Oynaklık sütunları ×normal (ayın tüm mumlarına göre). Kovalama sütunları bp (pozitif = o yönde kovalayan ortalamada geride). Sinyal sütunları (AL, SAT, SMA20, Uyumsuzluk, Trend çizgisi) brüt bp / işlem; ayarlar `izleme_sinyal.py` başında. \"Hareket ≥ maliyet %\": 15 dk tipik hareketin %0,08 maliyeti (maker + taker + kayma) geçtiği anların oranı.\n")
    md.append("| Ay | " + " | ".join(seri.columns) + " |")
    md.append("|---" * (len(seri.columns) + 1) + "|")
    for a, row in seri.iterrows():
        hucre = [tr(vv, bic.get(k, 2)) if pd.notna(vv) else "" for k, vv in row.items()]
        md.append(f"| {a}{' (eksik)' if a in eksik else ''} | " + " | ".join(hucre) + " |")
    open(CIKTI, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    {"guncelle": guncelle, "rapor": rapor}[sys.argv[1] if len(sys.argv) > 1 else "rapor"]()
