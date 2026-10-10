"""VSP v6.0 AL/SAT sinyali: on kayitli islem testi (22 Binance USDT-M paritesi, 2025 kesif / 2026 dogrulama).

Kullanicinin istegiyle AL/SAT, stop ve pozisyon onerisi geri geliyor. Sinyal, arastirmada tutarli cikan tek yon etkisine dayanir
(BULGULAR 3 ve 10c): saldirgan akisla gelen sert 15 dk hareketten sonra kisa vadeli geri donus.

ON KAYIT (sonuclardan once yazildi):
  Sinyal (VSP.pine ile ayni tanim; yalnizca kapanmis mumlar):
    AL  = yeni sert satis mumu: z15 <= -3 ve imb15 <= -0,15, onceki 15 mumda sert satis yok.
    SAT = yeni sert alis mumu:  z15 >= +3 ve imb15 >= +0,15, onceki 15 mumda sert alis yok.
    Engeller: (a) zamanlanmis olay ufukta (15 dk) ya da olay penceresi suruyor (stop/hedef olcegi orada guvenilmez; bant %30-75 kapsiyor);
              (b) hareket / maliyet < 1 (tipik 15 dk hareket maliyeti karsilamiyor); (c) acik islem varken yeni sinyal yok (parite bazinda).
  Giris: (P) piyasa emri, sinyal mumundan sonraki mumun acilisi, taker + kayma.
         (L) limit, sinyal mumunun kapanisinda, yalnizca sonraki mum icin gecerli; dolum fiyat limitin otesine gecerse (AL: low < limit), maker.
  Stop: girişten k * sigma15 uzakta (sigma15 = sqrt(30 mumluk EWMA r^2 * 15), sinyal mumunda). Hedef: R * stop mesafesi.
  Cikis: stop (taker + kayma; mum stopun otesinde acilirsa acilis fiyati), hedef (limit, maker; fiyat hedefin otesine gecmeli),
         ya da H mum sonra kapanis (taker + kayma). Ayni mumda ikisi de degerse once stop sayilir (ihtiyatli).
  Izgara: k in {1,0; 1,5; 2,0}, R in {1,0; 1,5; 2,0}, H in {5; 15; 30}, giris P ve L (54 ayar).
  Maliyet: VIP 0 (maker %0,02, taker %0,05, kayma %0,01) ana senaryo; dusuk ucret (maker %0, taker %0,02, kayma %0,01) ek.
  1R = stopta kaybedilen tutar (stop mesafesi + giris ve stop cikisi maliyeti); pozisyon buyuklugu gostergede buna gore hesaplanir.
  Secim: 2025'te VIP 0 ile ortalama net R'si en yuksek ayar. Dogrulama: ayni ayarin 2026 sonucu.
  Basari kurali: secilen ayarda iki yilda da ortalama net R > 0 ve gun kumelenmis t >= 2 -> "kenar var".
                 Aksi hâlde "kenar yok": sinyal kullanicinin istegiyle gosterilir, kartlarda beklenen net sonuc yazilir.

Kullanim: VSP_VERI=<klasor> python3 arastirma/sinyal_v6.py   (veri: izleme.py guncelle ile npz_izleme/)
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme

KS = [1.0, 1.5, 2.0]
RS = [1.0, 1.5, 2.0]
HS = [5, 15, 30]
HMAX = max(HS)
SEN = {"VIP0": (0.0002, 0.0005, 0.0001), "Dusuk": (0.0, 0.0002, 0.0001)}  # maker, taker, kayma (kesir)
W = 15  # ufuk (dk), VSP varsayilani


def olay_engeli(ts):
    """VSP.pine: evInH (08:30, 09:30, Pazar 18:00, FOMC 14:00 ufukta ya da NY acilisinin ilk 14 dk) veya evNow."""
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    em = (et.hour * 60 + et.minute).to_numpy()
    dow = et.dayofweek.to_numpy()  # 0 = Pazartesi, 6 = Pazar
    gun = np.asarray(et.strftime("%Y-%m-%d"))
    ymd = (et.year * 10000 + et.month * 100 + et.day).to_numpy()
    fom = np.isin(gun, list(izleme.FOMC))
    hol = np.isin(ymd, list(izleme.NYHOL))
    dhol = np.isin(ymd, list(izleme.DATAHOL))
    wk = dow < 5
    dataDay = ~dhol & (dow >= 1) & (dow <= 4)
    big = np.isin(gun, izleme.ADAYS)
    evData = dataDay & ((em == 510) | (big & (em >= 510) & (em <= 518)))
    evOpen = ~hol & wk & (em >= 570) & (em <= 583)
    evTen = ~dhol & wk & (em >= 600) & (em <= 608)
    evSun = (dow == 6) & (em >= 1080) & (em <= 1087)
    evFomc = fom & (em >= 839) & (em <= 884)
    inD = dataDay & (em >= 510 - W) & (em < 510)
    inO = ~hol & wk & (em >= 570 - W) & (em < 570)
    inS = (dow == 6) & (em >= 1080 - W) & (em < 1080)
    inF = fom & (em >= 840 - W) & (em < 840)
    return evData | evOpen | evTen | evSun | evFomc | inD | inO | inS | inF


def olaylar(s):
    z = np.load(os.path.join(izleme.NPZ, f"{s}.npz"))
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sig = np.sqrt(ew * W)
    rs = pd.Series(r)
    sd1 = rs.rolling(1440).std(ddof=0).to_numpy()
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
    dnAgo = (t - 1) - izleme.son_ind(fDn)
    upAgo = (t - 1) - izleme.son_ind(fUp)
    newDn = fDn & (dnAgo >= 15)
    newUp = fUp & (upAgo >= 15)
    engel = olay_engeli(ts)
    gecerli = (t >= 3000) & (t < n - HMAX - 2) & np.isfinite(sig) & (sig > 0) & ~engel
    ix = np.flatnonzero((newDn | newUp) & gecerli)
    yon = np.where(newDn[ix], 1, -1)  # +1 AL (sert satistan sonra), -1 SAT
    j = ix[:, None] + 1 + np.arange(HMAX)[None, :]  # giris mumu ve sonrasi
    return {"sym": s, "ts": ts[ix], "yon": yon, "sig": sig[ix], "c0": c[ix], "o": o[j], "h": h[j], "l": l[j], "c": c[j]}


def islem(E, k, R, H, giris, sen):
    """Her olay icin net getiri (kesir) ve R. Acik islem varken yeni sinyal alinmaz (parite bazinda, ardisik)."""
    mk, tk, sl = SEN[sen]
    y = E["yon"].astype(float)
    if giris == "P":
        ent = E["o"][:, 0]
        dolu = np.ones(len(y), bool)
        fin = tk + sl
    else:
        ent = E["c0"].copy()
        dolu = np.where(y > 0, E["l"][:, 0] < ent, E["h"][:, 0] > ent)
        fin = mk
    d = k * E["sig"]  # stop mesafesi (log ~ kesir)
    stop = ent * np.exp(-y * d)
    hedef = ent * np.exp(y * R * d)
    hh, ll, oo, cc = E["h"][:, :H], E["l"][:, :H], E["o"][:, :H], E["c"][:, :H]
    sv = np.where(y[:, None] > 0, ll <= stop[:, None], hh >= stop[:, None])
    tv = np.where(y[:, None] > 0, hh > hedef[:, None], ll < hedef[:, None])
    if giris == "L":  # limit dolum mumunda hedef sayilmaz (hedef dolumdan once gelmis olabilir); stop sayilir (ihtiyatli)
        tv[:, 0] = False
    big = H + 5
    i_s = np.where(sv.any(1), sv.argmax(1), big)
    i_t = np.where(tv.any(1), tv.argmax(1), big)
    stop_ilk = (i_s <= i_t) & (i_s < big)
    hedef_ilk = (i_t < i_s)
    # stop fiyati: mum stopun otesinde acildiysa acilis (giris mumunun acilisi P'de giris fiyati oldugu icin dogal)
    ii = np.clip(i_s, 0, H - 1)
    o_s = oo[np.arange(len(y)), ii]
    if giris == "L":
        o_s = np.where(ii == 0, ent, o_s)
    stop_px = np.where(y > 0, np.minimum(stop, o_s), np.maximum(stop, o_s))
    son = cc[:, H - 1]
    cik = np.where(stop_ilk, stop_px, np.where(hedef_ilk, hedef, son))
    fout = np.where(hedef_ilk, mk, tk + sl)
    brut = y * (np.log(cik) - np.log(ent))
    net = brut - fin - fout
    risk = d + fin + tk + sl  # 1R: stopta kayip (mesafe + giris + stop cikisi maliyeti)
    sure = np.where(stop_ilk, i_s + 1, np.where(hedef_ilk, i_t + 1, H))
    # ardisik islem: acik islem bitmeden yeni sinyal alinmaz
    al = np.zeros(len(y), bool)
    serbest = -1
    tsi = E["ts"]
    for q in range(len(y)):
        if not dolu[q]:
            continue
        if tsi[q] >= serbest:
            al[q] = True
            serbest = tsi[q] + 60 * (1 + sure[q])
    return pd.DataFrame({"sym": E["sym"], "ts": tsi[al], "yon": y[al].astype(int), "brut": brut[al], "net": net[al], "R": net[al] / risk[al],
                         "sonuc": np.where(stop_ilk[al], "stop", np.where(hedef_ilk[al], "hedef", "sure"))})


def ozet(df):
    if len(df) == 0:
        return dict(n=0, netR=np.nan, t=np.nan, net_bp=np.nan, brut_bp=np.nan, parite_pozitif=np.nan)
    g = df.assign(gun=df["ts"] // 86400).groupby("gun")["R"].agg(["sum", "count"])
    m = g["sum"].sum() / g["count"].sum()
    # gun kumelenmis standart hata
    e = g["sum"] - m * g["count"]
    se = np.sqrt((e ** 2).sum()) / g["count"].sum()
    pp = (df.groupby("sym")["R"].mean() > 0).mean()
    return dict(n=len(df), netR=m, t=m / se if se > 0 else np.nan, net_bp=df["net"].mean() * 1e4, brut_bp=df["brut"].mean() * 1e4, parite_pozitif=pp)


def main():
    EV = [olaylar(s) for s in izleme.SYMS]
    print("olay:", sum(len(e["yon"]) for e in EV))
    rows = []
    sonuc = {}
    for giris in ("P", "L"):
        for k in KS:
            for R in RS:
                for H in HS:
                    for sen in SEN:
                        df = pd.concat([islem(E, k, R, H, giris, sen) for E in EV], ignore_index=True)
                        df["yil"] = pd.to_datetime(df["ts"], unit="s", utc=True).year
                        sonuc[(giris, k, R, H, sen)] = df
                        for yil in (2025, 2026):
                            o = ozet(df[df["yil"] == yil])
                            rows.append(dict(giris=giris, k=k, R=R, H=H, sen=sen, yil=yil, **o))
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 500)
    v = T[T["sen"] == "VIP0"].pivot_table(index=["giris", "k", "R", "H"], columns="yil", values=["netR", "t", "net_bp", "brut_bp", "n"])
    print(v.round(3).to_string())
    a25 = T[(T["sen"] == "VIP0") & (T["yil"] == 2025)].sort_values("netR", ascending=False).iloc[0]
    sec = (a25["giris"], a25["k"], a25["R"], int(a25["H"]))
    print("\nSECILEN (2025 VIP0 en yuksek net R):", sec)
    for sen in SEN:
        df = sonuc[sec + (sen,)]
        for yil in (2025, 2026):
            d = df[df["yil"] == yil]
            print(sen, yil, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in ozet(d).items()})
            for yn, ad in ((1, "AL"), (-1, "SAT")):
                print("   ", ad, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in ozet(d[d["yon"] == yn]).items()}, d[d["yon"] == yn]["sonuc"].value_counts(normalize=True).round(2).to_dict())
    o25 = ozet(sonuc[sec + ("VIP0",)].query("yil == 2025"))
    o26 = ozet(sonuc[sec + ("VIP0",)].query("yil == 2026"))
    kenar = o25["netR"] > 0 and o26["netR"] > 0 and o25["t"] >= 2 and o26["t"] >= 2
    print("\nKARAR:", "kenar var" if kenar else "kenar yok")
    # 2026 en iyi ayar (yalnizca bilgi; secimde kullanilmaz)
    b26 = T[(T["sen"] == "VIP0") & (T["yil"] == 2026)].sort_values("netR", ascending=False).head(5)
    print("\n2026'nin en iyi 5 ayari (yalnizca bilgi):\n", b26.round(3).to_string())
    T.to_csv(os.path.join(izleme.VERI, "sinyal_v6.csv"), index=False)


if __name__ == "__main__":
    main()
