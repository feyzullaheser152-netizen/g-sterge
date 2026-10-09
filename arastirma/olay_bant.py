"""Aday 1: Olay ayarli beklenen hareket (VSP v5.7 arastirmasi).

Bu dosyanin ON KAYIT bolumu, olcum yapilmadan once (2026-10-09, ~07:20 UTC) yazildi. Genelleme listesi daha once
olay_bant_sec.py ile donduruldu (bt/v57/olay_bant_genel_liste.json, 2026-10-09T07:17:10Z, sha256 cbe82985...).

PINE ILE AYNI TANIMLAR
  r1 = ln(c/c[1]); ewVar = EMA(nz(r1^2), 30) (alfa 2/31, ilk deger = ilk girdi); em50 = 0,61*sigH, em80 = 1,23*sigH.
  Kapsama: |ln(c[t+H]/c[t])| <= bant. t = tahmin mumu (kapanisi), yil t'nin UTC yilina gore. Her paritenin ilk 3000 mumu atlanir.
  Mevcut model: sigH^2 = ewVar_t * H.
  Yeni model:   sig'^2 = EMA30((r1/f_t)^2) (olaydan arindirilmis EWMA); sigH^2 = sig'^2_t * sum_{j=1..H} f(t+j)^2.
  0,61 ve 1,23 yeniden uydurulmaz.

f TABLOSU (olay disi dakikalarda f = 1). New York saati, gun tipleri VSP.pine ile ayni:
  - Veri gunu = Sali-Cuma ve veri tatili degil (takvim.VERI_TATIL). A gunu = takvim.py'deki CPI ya da NFP gunu (aday 2'nin
    dondurulmus listesi); B = diger veri gunleri (FOMC gunleri dahil, Pine'daki gibi).
  - A gunleri 08:30-08:38 dakika dakika (9 deger)  <- ACIK SAPMA, asagiya bakin
  - B gunleri 08:30 (1)
  - NY acilisi 09:30-09:43 dakika dakika (14), Pzt-Cum, NYSE tatili haric
  - 09:44-10:29 tek blok (1), Pzt-Cum, NYSE tatili haric, 10:00-10:08 olay dakikalari haric
  - 10:00-10:08 dakika dakika (9), Pzt-Cum, veri tatili haric
  - Pazar 18:00-18:07 dakika dakika (8)
  - FOMC gunleri 4 blok: 13:59 / 14:00-14:05 / 14:06-14:29 / 14:30-14:44
  Toplam 46 deger ("ana" model).
  SAPMA (sonuc gorulmeden karar verildi): Tasarim 37 deger ve tek 08:30 degeri sayiyordu; aday 2 gecince "A ve B ayri"
  deniyordu. Aday 2, A gunlerinin mor penceresini 08:30-08:38 yapti. Tablonun geri kalani VSP'nin olay pencerelerini dakika
  dakika izledigi icin A gunleri de kendi penceresinde dakika dakika alinir. Duyarlilik olarak iki model daha raporlanir,
  karar "ana" modelle verilir:
    "lit" (38 deger): yalnizca A 08:30 ve B 08:30 ayri (tasarimin harfiyen okunusu);
    "tek" (37 deger): A/B ayrimi yok (tasarimin ozgun hali).
  Ornek donemi tatilleri: veri tatili = takvim.VERI_TATIL; NYSE tatilleri asagida NYHOL (2025-01-09 Carter yas gunu dahil).

f'NIN HESABI
  f_k = ortalama(|r_t| / sig'_{t-1}) [k dakikalarinda] / ayni ortalama [f = 1 olan dakikalarda]; sig' bir onceki mumdaki
  arindirilmis EWMA. f = 1'den baslanir, 2 yineleme yapilir. Her yinelemede tablo 22 paritenin medyanidir ve bir sonraki
  yinelemede butun paritelere ayni tablo uygulanir (Pine'da da tek tablo var). Sonuc 2 ondaliga yuvarlanir.
  3. yineleme yalnizca yakinsamayi gostermek icin raporlanir.
  Capraz uydurma: 2025'ten cikan f ile 2026, 2026'dan cikan f ile 2025 degerlendirilir (iki yil da orneklem disi).
  Pine'a onerilecek tablo: ayni yontemle iki yilin birlikte (2025-01..2026-09) uydurulmasi.

SINIFLAR (t tahmin ani)
  - "ufuk E": E olayinin baslangic mumu (t, t+H] icinde. Olaylar: 08:30 (A u B veri gunu), 09:30, 10:00, Pazar 18:00,
    FOMC 14:00. Ek (karar disi): 08:30 A, 08:30 B ayri.
  - "sonra E": E'nin baslangic mumu [t-14, t] icinde (H'den bagimsiz, olaydan sonraki 15 dk).
  - "olaysiz": [t-29, t+H] araligindaki her dakikada f = 1 ("ana" tablonun destegi; tum modeller ayni mum kumesinde).
  - "tumu".
  Kapsama: parite basina oran, sonra 22 paritenin medyani. Ek: havuzlanmis oran ve gune (UTC) gore kumelenmis standart hata.

ON KAYITLI KURAL (iki orneklem disi yilda da, parite medyani; H = 15)
  (a) Her "ufuk E" ve "sonra E" sinifinda (5 + 5 sinif) %80 bandi 76-84, %50 bandi 46-54. FOMC siniflarinda 70-90 ve 40-60.
  (b) "olaysiz" sinifta kapsama (parite medyani) mevcut modele gore en fazla 0,5 puan degisir (iki bant); "tumu" sinifinda
      yeni modelin kapsamasi 80 +- 3 ve 50 +- 3.
  (c) H = 5 ve H = 60'ta hicbir olayli sinifin ("ufuk E", 5 sinif; kural (a) "olayli" ile "olay sonrasi"ni ayirdigi icin)
      hedeften mutlak sapmasi, iki bantta da, mevcut modelinkinden buyuk olmamali. "sonra E" bilgi olarak raporlanir.
  Ucu de tutarsa ozellik eklenir.
GENELLEME (karar kapisi degil): dondurulmus 20 parite; f yalnizca 22 ana pariteden (capraz). Parite basina (a) ve (b)
  [ayni esikler, iki yil] tutuyorsa parite gecer. Paritelerin >= %80'i gecerse kartta "orta paritelerde de dogrulandi",
  aksi halde "yalnizca buyuk paritelerde dogrulandi". Parite medyanli sonuc da bilgi olarak raporlanir.

Komut: python3 -I olay_bant.py [hazirla|uydur|degerlendir|genel|rapor|hepsi]
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import takvim  # noqa: E402

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
SRC_G = os.path.join(BASE, "data_bn", "npz_genel")
OUT = os.path.join(BASE, "bt", "v57")
CACHE = os.path.join(OUT, "olay_bant_cache")
ANA = "BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT AVAXUSDT LINKUSDT LTCUSDT DOTUSDT NEARUSDT SUIUSDT AAVEUSDT UNIUSDT ENAUSDT 1000PEPEUSDT WIFUSDT ARBUSDT OPUSDT ZECUSDT HYPEUSDT".split()
WARM = 3000
HS = (5, 15, 60)
HMAX = max(HS)
K50, K80 = 0.61, 1.23
ALPHA = 2 / 31
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
END = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp())
YIL = {0: "2025", 1: "2026"}


def ymd_int(s):
    return int(s.replace("-", ""))


A_GUN = {ymd_int(d) for d in (set(takvim.CPI) | set(takvim.NFP))}
DHOL = {ymd_int(d) for d in takvim.VERI_TATIL}
FOMC = {ymd_int(d) for d in takvim.FOMC}
NYHOL = {20250101, 20250109, 20250120, 20250217, 20250418, 20250526, 20250619, 20250704, 20250901, 20251127, 20251225,
         20260101, 20260119, 20260216, 20260403, 20260525, 20260619, 20260703, 20260907}

# ana tablo anahtarlari (kod 1..46; 0 = olay disi)
KEYS = ([f"A 08:{30 + i}" for i in range(9)] + ["B 08:30"] + [f"Açılış 09:{30 + i}" for i in range(14)] + ["Blok 09:44–10:29"]
        + [f"10:{i:02d}" for i in range(9)] + [f"Pazar 18:{i:02d}" for i in range(8)] + ["FOMC 13:59", "FOMC 14:00–14:05", "FOMC 14:06–14:29", "FOMC 14:30–14:44"])
assert len(KEYS) == 46


def varyant(ad):
    """ana kod (0..46) -> varyant kodu; varyant anahtarlari."""
    vm = np.arange(47)
    if ad == "ana":
        return vm, list(KEYS)
    if ad == "lit":
        vm = np.zeros(47, dtype=int)
        vm[1] = 1
        vm[10] = 2
        vm[11:] = np.arange(3, 39)
        return vm, ["A 08:30", "B 08:30"] + KEYS[10:]
    if ad == "tek":
        vm = np.zeros(47, dtype=int)
        vm[1] = vm[10] = 1
        vm[11:] = np.arange(2, 38)
        return vm, ["08:30"] + KEYS[10:]
    raise ValueError(ad)


OLAYLAR = {"08:30": (0, 1), "09:30": (2,), "10:00": (3,), "Pazar 18:00": (4,), "FOMC": (5,), "08:30 A": (0,), "08:30 B": (1,)}
KAPI = ["08:30", "09:30", "10:00", "Pazar 18:00", "FOMC"]
SINIFLAR = [f"ufuk {e}" for e in OLAYLAR] + [f"sonra {e}" for e in OLAYLAR] + ["olaysız", "tümü"]


# ---------------------------------------------------------------- hazirla
def hazirla_sym(sym, src, tag):
    f = os.path.join(CACHE, f"{tag}_{sym}.npz")
    if os.path.exists(f):
        return
    z = np.load(os.path.join(src, f"{sym}.npz"))
    ts0, c0 = z["ts"], z["c"]
    m = ts0 < END
    ts0, c0 = ts0[m], c0[m]
    ts = np.arange(ts0[0], ts0[-1] + 60, 60, dtype=np.int64)
    c = np.full(len(ts), np.nan)
    c[((ts0 - ts0[0]) // 60).astype(np.int64)] = c0
    lc = np.log(c)
    r = np.empty(len(c))
    r[0] = np.nan
    r[1:] = np.diff(lc)
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    em = (et.hour * 60 + et.minute).to_numpy()
    dow = et.dayofweek.to_numpy()  # Pzt = 0 ... Paz = 6
    ymd = (et.year * 10000 + et.month * 100 + et.day).to_numpy()
    dhol = np.isin(ymd, list(DHOL))
    nyhol = np.isin(ymd, list(NYHOL))
    fom = np.isin(ymd, list(FOMC))
    isa = np.isin(ymd, list(A_GUN))
    wk = dow <= 4
    vg = ~dhol & (dow >= 1) & (dow <= 4)
    kod = np.zeros(len(ts), dtype=np.int16)
    mm = vg & isa & (em >= 510) & (em <= 518)
    kod[mm] = 1 + em[mm] - 510
    mm = vg & ~isa & (em == 510)
    kod[mm] = 10
    mm = wk & ~nyhol & (em >= 570) & (em <= 583)
    kod[mm] = 11 + em[mm] - 570
    ten = wk & ~dhol & (em >= 600) & (em <= 608)
    mm = wk & ~nyhol & (em >= 584) & (em <= 629) & ~ten
    kod[mm] = 25
    kod[ten] = 26 + em[ten] - 600
    mm = (dow == 6) & (em >= 1080) & (em <= 1087)
    kod[mm] = 35 + em[mm] - 1080
    kod[fom & (em == 839)] = 43
    kod[fom & (em >= 840) & (em <= 845)] = 44
    kod[fom & (em >= 846) & (em <= 869)] = 45
    kod[fom & (em >= 870) & (em <= 884)] = 46
    anc = np.zeros(len(ts), dtype=np.uint8)
    anc |= (vg & isa & (em == 510)).astype(np.uint8) << 0
    anc |= (vg & ~isa & (em == 510)).astype(np.uint8) << 1
    anc |= (wk & ~nyhol & (em == 570)).astype(np.uint8) << 2
    anc |= (wk & ~dhol & (em == 600)).astype(np.uint8) << 3
    anc |= ((dow == 6) & (em == 1080)).astype(np.uint8) << 4
    anc |= (fom & (em == 840)).astype(np.uint8) << 5
    np.savez(f, lc=lc, r2=np.nan_to_num(r) ** 2, ar=np.abs(r), kod=kod, anc=anc, yr=(ts >= CUT).astype(np.int8),
             day=(ts // 86400 - 20089).astype(np.int32), ts=ts)  # 20089 = 2025-01-01


def yukle(sym, tag):
    return dict(np.load(os.path.join(CACHE, f"{tag}_{sym}.npz")))


def ewm(x):
    return pd.Series(x).ewm(alpha=ALPHA, adjust=False).mean().to_numpy()


def hazirla():
    os.makedirs(CACHE, exist_ok=True)
    for s in ANA:
        hazirla_sym(s, SRC, "a")
        print("hazir", s, flush=True)


# ---------------------------------------------------------------- uydur
def uydur():
    """Her (varyant, uydurma yili) icin 3 yineleme; her yineleme butun pariteleri bir kez gezer."""
    combos = [(v, fy) for v in ("ana", "lit", "tek") for fy in ("2025", "2026", "havuz")]
    YS = {"2025": (0,), "2026": (1,), "havuz": (0, 1)}
    VM = {v: varyant(v) for v in ("ana", "lit", "tek")}
    F = {cb: np.ones(len(VM[cb[0]][1]) + 1) for cb in combos}
    hist = {cb: [] for cb in combos}
    for it in range(3):
        P = {cb: [] for cb in combos}
        for s in ANA:
            D = yukle(s, "a")
            n = len(D["r2"])
            okb = (np.arange(n) >= WARM) & np.isfinite(D["ar"])
            for cb in combos:
                vm, keys = VM[cb[0]]
                kv = vm[D["kod"]]
                fb = F[cb][kv]
                s2 = ewm(D["r2"] / fb ** 2)
                sp = np.empty(n)
                sp[0] = np.nan
                sp[1:] = np.sqrt(s2[:-1])
                with np.errstate(divide="ignore", invalid="ignore"):
                    u = D["ar"] / sp
                ok = okb & np.isfinite(u) & (sp > 0) & np.isin(D["yr"], YS[cb[1]])
                K = len(keys) + 1
                sm = np.bincount(kv[ok], weights=u[ok], minlength=K)
                cn = np.bincount(kv[ok], minlength=K)
                with np.errstate(divide="ignore", invalid="ignore"):
                    mu = sm / cn
                P[cb].append(mu / mu[0])
        for cb in combos:
            A = np.array(P[cb])
            Fn = np.nanmedian(A, axis=0)
            Fn[0] = 1.0
            F[cb] = Fn
            hist[cb].append({"F": Fn.tolist(), "q25": np.nanquantile(A, 0.25, axis=0).tolist(), "q75": np.nanquantile(A, 0.75, axis=0).tolist()})
        print("yineleme", it + 1, "bitti", flush=True)
    out = {}
    for cb in combos:
        keys = VM[cb[0]][1]
        out[f"{cb[0]}|{cb[1]}"] = {"keys": keys, "it1": hist[cb][0]["F"][1:], "it2": hist[cb][1]["F"][1:], "it3": hist[cb][2]["F"][1:],
                                   "q25_it2": hist[cb][1]["q25"][1:], "q75_it2": hist[cb][1]["q75"][1:],
                                   "f": [round(x, 2) for x in hist[cb][1]["F"][1:]]}
    with open(os.path.join(OUT, "olay_bant_f.json"), "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    rows = []
    for k, v in out.items():
        for i, key in enumerate(v["keys"]):
            rows.append({"model": k, "dakika": key, "f": v["f"][i], "it1": v["it1"][i], "it3": v["it3"][i], "q25": v["q25_it2"][i], "q75": v["q75_it2"][i]})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "olay_bant_f.csv"), index=False)
    print("f tablolari yazildi")


def tablo(var, fy):
    T = json.load(open(os.path.join(OUT, "olay_bant_f.json")))[f"{var}|{fy}"]
    return np.r_[1.0, np.array(T["f"])]


# ---------------------------------------------------------------- degerlendir
def modeller(genel=False):
    """model adi -> (varyant, {degerlendirme yili: uydurma tablosu})"""
    M = {"yeni": ("ana", {0: tablo("ana", "2026"), 1: tablo("ana", "2025")}),
         "havuz": ("ana", {0: tablo("ana", "havuz"), 1: tablo("ana", "havuz")})}
    if not genel:
        M["lit"] = ("lit", {0: tablo("lit", "2026"), 1: tablo("lit", "2025")})
        M["tek"] = ("tek", {0: tablo("tek", "2026"), 1: tablo("tek", "2025")})
        M["ic"] = ("ana", {0: tablo("ana", "2025"), 1: tablo("ana", "2026")})
    return M


def degerlendir_sym(D, M, gunluk=None):
    n = len(D["lc"])
    lc, kod, anc, yr, day = D["lc"], D["kod"], D["anc"], D["yr"], D["day"]
    ew0 = ewm(D["r2"])
    ce = [np.r_[0, np.cumsum((anc >> b) & 1)] for b in range(6)]
    ck = np.r_[0, np.cumsum(kod != 0)]
    VM = {v: varyant(v)[0] for v in ("ana", "lit", "tek")}
    sig = {}
    for m, (v, Fy) in M.items():
        for y in (0, 1):
            fb = Fy[y][VM[v][kod]]
            sig[(m, y)] = (ewm(D["r2"] / fb ** 2), np.r_[0, np.cumsum(fb ** 2)])
    tum = np.arange(WARM, n - HMAX - 1)
    rows = []
    for y in (0, 1):
        idx = tum[(yr[tum] == y) & (ew0[tum] > 0) & np.isfinite(lc[tum])]
        if len(idx) == 0:
            continue
        post = {e: sum(ce[b][idx + 1] - ce[b][idx - 14] for b in bits) > 0 for e, bits in OLAYLAR.items()}
        for H in HS:
            a = np.abs(lc[idx + H] - lc[idx])
            v_ok = np.isfinite(a)
            masks = {}
            for e, bits in OLAYLAR.items():
                masks[f"ufuk {e}"] = sum(ce[b][idx + H + 1] - ce[b][idx + 1] for b in bits) > 0
                masks[f"sonra {e}"] = post[e]
            masks["olaysız"] = (ck[idx + H + 1] - ck[idx - 29]) == 0
            masks["tümü"] = np.ones(len(idx), bool)
            sigs = {"mevcut": np.sqrt(ew0[idx] * H)}
            for m in M:
                s2, cs = sig[(m, y)]
                sigs[m] = np.sqrt(s2[idx] * (cs[idx + H + 1] - cs[idx + 1]))
            for m, sg in sigs.items():
                h50 = (a <= K50 * sg) & v_ok
                h80 = (a <= K80 * sg) & v_ok
                for k in SINIFLAR:
                    mk = masks[k] & v_ok
                    nn = int(mk.sum())
                    rows.append({"yil": YIL[y], "H": H, "sinif": k, "model": m, "n": nn, "h50": int(h50[mk].sum()), "h80": int(h80[mk].sum())})
                    if gunluk is not None and nn:
                        dd = day[idx[mk]]
                        key = (YIL[y], H, k, m)
                        g = gunluk.setdefault(key, np.zeros((3, 700)))
                        g[0] += np.bincount(dd, minlength=700)[:700]
                        g[1] += np.bincount(dd, weights=h50[mk], minlength=700)[:700]
                        g[2] += np.bincount(dd, weights=h80[mk], minlength=700)[:700]
    return rows


def degerlendir():
    M = modeller()
    rows, gunluk = [], {}
    for s in ANA:
        t0 = time.time()
        r = degerlendir_sym(yukle(s, "a"), M, gunluk)
        for x in r:
            x["sym"] = s
        rows += r
        print("degerlendirildi", s, f"{time.time() - t0:.0f} sn", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(OUT, "olay_bant_parite.csv"), index=False)
    hv = []
    for (y, H, k, m), g in gunluk.items():
        N = g[0].sum()
        for band, j, tgt in (("50", 1, 50), ("80", 2, 80)):
            p = g[j].sum() / N
            e = g[j] - p * g[0]
            G = int((g[0] > 0).sum())
            se = np.sqrt((e ** 2).sum() * G / max(G - 1, 1)) / N
            hv.append({"yil": y, "H": H, "sinif": k, "model": m, "bant": band, "havuz": 100 * p, "se": 100 * se, "t_hedef": (100 * p - tgt) / (100 * se) if se > 0 else np.nan, "n": int(N), "gun": G})
    pd.DataFrame(hv).to_csv(os.path.join(OUT, "olay_bant_havuz.csv"), index=False)


def genel():
    kayit = json.load(open(os.path.join(OUT, "olay_bant_genel_liste.json")))
    syms = [e["sym"] for e in kayit["secilen"]]
    M = modeller(genel=True)
    rows = []
    for s in syms:
        hazirla_sym(s, SRC_G, "g")
        r = degerlendir_sym(yukle(s, "g"), M)
        for x in r:
            x["sym"] = s
        rows += r
        print("genel", s, flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "olay_bant_genel_parite.csv"), index=False)


# ---------------------------------------------------------------- rapor
def kapsama(R):
    R = R[R["n"] > 0].copy()
    R["yil"] = R["yil"].astype(str)
    R["c50"] = 100 * R["h50"] / R["n"]
    R["c80"] = 100 * R["h80"] / R["n"]
    return R


def medyan(R):
    return R.groupby(["yil", "H", "sinif", "model"]).agg(c50=("c50", "median"), c80=("c80", "median"), n=("n", "sum"), parite=("sym", "nunique")).reset_index()


def kural(Mq, model, siniflar_a=None):
    """Mq: medyan tablosu (ya da tek parite tablosu). Dondurur: (a, b, c, ayrinti listesi)"""
    det = []
    idx = Mq.set_index(["yil", "H", "sinif", "model"])

    def g(y, H, k, m, b):
        try:
            return float(idx.loc[(y, H, k, m), f"c{b}"])
        except KeyError:
            return np.nan
    a_ok = b_ok = c_ok = True
    for y in ("2025", "2026"):
        for e in KAPI:
            for pre in ("ufuk", "sonra"):
                k = f"{pre} {e}"
                lo80, hi80, lo50, hi50 = (70, 90, 40, 60) if e == "FOMC" else (76, 84, 46, 54)
                c80, c50 = g(y, 15, k, model, 80), g(y, 15, k, model, 50)
                ok = (lo80 <= c80 <= hi80) and (lo50 <= c50 <= hi50)
                a_ok &= ok
                det.append(("a", y, k, f"{c50:.1f} / {c80:.1f}", ok))
        for b in (50, 80):
            d = g(y, 15, "olaysız", model, b) - g(y, 15, "olaysız", "mevcut", b)
            ok = abs(d) <= 0.5
            b_ok &= ok
            det.append(("b-olaysız", y, f"%{b}", f"{d:+.2f}", ok))
            t = g(y, 15, "tümü", model, b)
            ok = abs(t - b) <= 3
            b_ok &= ok
            det.append(("b-tümü", y, f"%{b}", f"{t:.1f}", ok))
        for H in (5, 60):
            for e in KAPI:
                k = f"ufuk {e}"
                for b in (50, 80):
                    dn, dc = abs(g(y, H, k, model, b) - b), abs(g(y, H, k, "mevcut", b) - b)
                    ok = dn <= dc
                    c_ok &= ok
                    det.append(("c", y, f"H{H} {k} %{b}", f"{dn:.1f} <= {dc:.1f}", ok))
    return a_ok, b_ok, c_ok, det


def rapor():
    R = kapsama(pd.read_csv(os.path.join(OUT, "olay_bant_parite.csv")))
    Mq = medyan(R)
    Mq.to_csv(os.path.join(OUT, "olay_bant_medyan.csv"), index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    lines = []
    for H in HS:
        P = Mq[Mq["H"] == H].pivot_table(index="sinif", columns=["yil", "model"], values=["c50", "c80"]).round(1)
        lines.append(f"\n=== H = {H}: parite medyani kapsama ===\n" + P.to_string())
    sonuc = {}
    for m in ("yeni", "lit", "tek", "ic", "havuz"):
        a, b, c, det = kural(Mq, m)
        sonuc[m] = {"a": a, "b": b, "c": c, "gecti": a and b and c, "basarisiz": [d for d in det if not d[4]]}
        lines.append(f"\n--- Kural, model {m}: (a) {a} (b) {b} (c) {c}")
        for d in det:
            if not d[4] or m == "yeni":
                lines.append("   " + " | ".join(str(x) for x in d))
    # genelleme
    gp = os.path.join(OUT, "olay_bant_genel_parite.csv")
    if os.path.exists(gp):
        G = kapsama(pd.read_csv(gp))
        per = []
        for s, Gs in G.groupby("sym"):
            Ms = Gs.groupby(["yil", "H", "sinif", "model"])[["c50", "c80"]].first().reset_index()
            a, b, c, det = kural(Ms, "yeni")
            per.append({"sym": s, "a": a, "b": b, "c": c, "gecti": a and b, "basarisiz_a": "; ".join(f"{d[1]} {d[2]} {d[3]}" for d in det if d[0] == "a" and not d[4])})
        Pg = pd.DataFrame(per)
        Pg.to_csv(os.path.join(OUT, "olay_bant_genel_kural.csv"), index=False)
        Mg = medyan(G)
        Mg.to_csv(os.path.join(OUT, "olay_bant_genel_medyan.csv"), index=False)
        a, b, c, det = kural(Mg, "yeni")
        sonuc["genel"] = {"parite_gecen": int(Pg["gecti"].sum()), "parite": len(Pg), "a_gecen": int(Pg["a"].sum()), "b_gecen": int(Pg["b"].sum()),
                          "medyan_a": a, "medyan_b": b, "medyan_c": c, "medyan_basarisiz": [d for d in det if not d[4]]}
        lines.append(f"\n=== GENELLEME: parite basina (a)&(b) gecen {Pg['gecti'].sum()}/{len(Pg)}; (a) {Pg['a'].sum()}, (b) {Pg['b'].sum()}; medyanla (a) {a} (b) {b} (c) {c}")
        lines.append(Pg.to_string())
        for H in HS:
            P = Mg[Mg["H"] == H].pivot_table(index="sinif", columns=["yil", "model"], values=["c50", "c80"]).round(1)
            lines.append(f"\n=== GENEL H = {H} ===\n" + P.to_string())
    txt = "\n".join(lines)
    with open(os.path.join(OUT, "olay_bant_out.txt"), "w") as fh:
        fh.write(txt)
    with open(os.path.join(OUT, "olay_bant_kural.json"), "w") as fh:
        json.dump(sonuc, fh, ensure_ascii=False, indent=1, default=str)
    print(txt)


if __name__ == "__main__":
    adim = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if adim in ("hazirla", "hepsi"):
        hazirla()
    if adim in ("uydur", "hepsi"):
        uydur()
    if adim in ("degerlendir", "hepsi"):
        degerlendir()
    if adim in ("genel", "hepsi"):
        genel()
    if adim in ("rapor", "hepsi"):
        rapor()
