"""Aday 2 (v5.7): ABD veri gunu (CPI / NFP) ayrimi. Tarihler takvim.py'de olcumden once donduruldu.

Olcu (bolum 10, olay_pencere.py ile ayni): x = |r1| / sigma_taban; sigma_taban = onceki 1440 mumun r1 std'si (ddof=0),
bir mum gecikmeli. "x normal" = ortalama x / yilin kosulsuz ortalamasi (2025: 0,725; 2026: 0,701). Ilk 3000 mum atlanir.
Pencere: 08:25-09:29 ET (mum acilis zamani), dakika dakika. Ornek: 2025-01 .. 2026-09 tam aylar.
Gruplar (FOMC gunleri ve veri tatilleri haric):
  A = CPI ya da NFP gunu (Sali-Cuma), B = diger Sali-Cuma, M = Pazartesi (referans).
Birincil istatistik: parite medyani (her paritenin ortalamasi / taban, 22 paritenin medyani).
Ikincil: birlesik ortalama (olay_pencere.py gibi), gun kumelenmis ortalama ve t, gunlere gore bootstrap.
On kayitli kural takvim.py docstring'inde.
Kullanim: python3 arastirma/veri_gunu.py  (cikti: scratchpad/bt/v57/)
"""
import glob, os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import takvim as T

SRC = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/data_bn/npz"
OUT = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/v57"
BASE = {2025: 0.725, 2026: 0.701}
M0, M1 = 505, 569  # 08:25 .. 09:29
YILLAR = (2025, 2026)
RNG = np.random.default_rng(20261009)

K = T.tarih_kumeleri()
A, CPI, NFP, PPI, TATIL, FOMC = K["A"], K["CPI"], K["NFP"], K["PPI"], K["TATIL"], K["FOMC"]
KAP = set()
for a, b in T.KAPANMA:
    KAP |= {d.strftime("%Y-%m-%d") for d in pd.date_range(a, b)}


def gun_tipi(d, dow):
    if d in TATIL or d in FOMC:
        return None
    if dow == 0:
        return "M"
    if 1 <= dow <= 4:
        return "A" if d in A else "B"
    return None


rows = []
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    sym = os.path.basename(f)[:-4]
    z = np.load(f)
    ts, c = z["ts"], z["c"].astype(float)
    r = np.r_[np.nan, np.diff(np.log(c))]
    sb = pd.Series(r).rolling(1440).std(ddof=0).shift(1).to_numpy()
    x = np.abs(r) / sb
    x[:3000] = np.nan
    t = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    mins = (t.hour * 60 + t.minute).to_numpy()
    m = (mins >= M0) & (mins <= M1) & np.isfinite(x) & (ts < 1790812800)
    tt = t[m]
    df = pd.DataFrame({"sym": sym, "d": np.asarray(tt.strftime("%Y-%m-%d")), "dow": tt.dayofweek.to_numpy(), "yil": tt.year.to_numpy(), "dk": mins[m], "x": x[m]})
    df["g"] = [gun_tipi(d, w) for d, w in zip(df["d"], df["dow"])]
    df = df[df["g"].notna()]
    df["xn"] = df["x"] / df["yil"].map(BASE)
    rows.append(df[["sym", "d", "dow", "yil", "dk", "g", "xn"]])
    del z, ts, c, r, sb, x, t
D = pd.concat(rows, ignore_index=True)
D.to_pickle(f"{OUT}/veri_gunu_x.pkl")


def hhmm(dk):
    return f"{dk // 60:02d}:{dk % 60:02d}"


def profil(sub):
    """parite medyani ve birlesik ortalama, (yil, dk) bazinda"""
    ps = sub.groupby(["yil", "dk", "sym"])["xn"].mean()
    med = ps.groupby(["yil", "dk"]).median().unstack(0)
    pool = sub.groupby(["yil", "dk"])["xn"].mean().unstack(0)
    ng = sub.groupby("yil")["d"].nunique()
    return med, pool, ng


def gruplar(D):
    return {
        "A": D[D.g == "A"], "B": D[D.g == "B"], "M": D[D.g == "M"],
        "A_CPI": D[(D.g == "A") & D.d.isin(CPI)], "A_NFP": D[(D.g == "A") & D.d.isin(NFP)],
        "B_kapanmasiz": D[(D.g == "B") & ~D.d.isin(KAP)], "B_PPIsiz": D[(D.g == "B") & ~D.d.isin(PPI)],
        "PPI": D[(D.g == "B") & D.d.isin(PPI)], "B_Persembe": D[(D.g == "B") & (D.dow == 3)], "B_SaCaCu": D[(D.g == "B") & (D.dow != 3)],
    }


G = gruplar(D)
P = {k: profil(v) for k, v in G.items()}

# --- Dakika tablosu (birincil: parite medyani) ---
tab = pd.DataFrame(index=[hhmm(k) for k in range(M0, M1 + 1)])
for g in ("A", "B", "M"):
    for y in YILLAR:
        tab[f"{g} {y}"] = P[g][0][y].reindex(range(M0, M1 + 1)).to_numpy()
tab.index.name = "ET"
tab.round(3).to_csv(f"{OUT}/veri_gunu_dakika_medyan.csv")
tabp = pd.DataFrame(index=tab.index)
for g in ("A", "B", "M"):
    for y in YILLAR:
        tabp[f"{g} {y}"] = P[g][1][y].reindex(range(M0, M1 + 1)).to_numpy()
tabp.round(3).to_csv(f"{OUT}/veri_gunu_dakika_birlesik.csv")

pd.set_option("display.width", 250)
print("Gun sayilari:", {g: P[g][2].to_dict() for g in P})
print("\nDakika basina x normal, PARITE MEDYANI (08:25-09:29 ET)")
print(tab.round(2).to_string())
print("\nDakika basina x normal, BIRLESIK ortalama")
print(tabp.round(2).to_string())

# --- On kayitli kural ---
mnA = P["A"][0][list(YILLAR)].min(axis=1)
mnB = P["B"][0][list(YILLAR)].min(axis=1)
kirmizi = [hhmm(k) for k in range(M0, M1 + 1) if mnA.loc[k] >= 3.0]
mor = []
for k in range(510, M1 + 1):
    if mnA.loc[k] >= 1.5:
        mor.append(hhmm(k))
    else:
        break
bmor = bool(mnB.loc[510] >= 1.5)
print("\n=== ON KAYITLI KURAL (parite medyani, iki yilin minimumu) ===")
print("A kirmizi dakikalar (>= x3):", kirmizi)
print("A mor ardisik dakikalar (08:30'dan, >= x1,5):", mor)
print(f"B 08:30: 2025 {P['B'][0].loc[510, 2025]:.2f} / 2026 {P['B'][0].loc[510, 2026]:.2f} -> mor {'KALIR' if bmor else 'KALDIRILIR'}")
print("A 08:25-08:29 (olay oncesi) min:", mnA.loc[505:509].round(2).to_dict())

# Ayni kural birlesik ortalamayla (duyarlilik)
mnAp = P["A"][1][list(YILLAR)].min(axis=1); mnBp = P["B"][1][list(YILLAR)].min(axis=1)
morp = []
for k in range(510, M1 + 1):
    if mnAp.loc[k] >= 1.5:
        morp.append(hhmm(k))
    else:
        break
print("Duyarlilik (birlesik): kirmizi", [hhmm(k) for k in range(M0, M1 + 1) if mnAp.loc[k] >= 3.0], "mor", morp, "B 08:30", P["B"][1].loc[510].round(2).to_dict())

# --- Alt gruplar 08:28-08:40 ---
print("\nAlt gruplar, parite medyani, 08:28-08:40")
alt = {}
for g in ("A", "A_CPI", "A_NFP", "B", "B_kapanmasiz", "B_PPIsiz", "B_Persembe", "B_SaCaCu", "PPI", "M"):
    for y in YILLAR:
        alt[f"{g} {y} (n={P[g][2].get(y, 0)})"] = P[g][0][y].reindex(range(508, 521)).to_numpy()
alt = pd.DataFrame(alt, index=[hhmm(k) for k in range(508, 521)]).T
alt.round(3).to_csv(f"{OUT}/veri_gunu_altgrup.csv")
print(alt.round(2).to_string())

# --- Gun kumelenmis istatistikler ve bootstrap (08:30, 08:31, 08:32) ---
print("\nGun kumelenmis (gun ici parite ortalamasi -> gunler arasi ortalama), t: esige gore; bootstrap: gunleri yeniden ornekleyip parite medyani")
ozet = []
for g in ("A", "B", "M", "A_CPI", "A_NFP"):
    sub = G[g]
    for y in YILLAR:
        sy = sub[sub.yil == y]
        for dk in (510, 511, 512):
            s = sy[sy.dk == dk]
            gun = s.groupby("d")["xn"].mean()
            n = len(gun); mu = gun.mean(); se = gun.std(ddof=1) / np.sqrt(n)
            th = 3.0 if (g.startswith("A") and dk == 510) else 1.5
            # bootstrap: gunleri yeniden ornekle, her ornekte parite medyani
            piv = s.pivot_table(index="d", columns="sym", values="xn", aggfunc="mean")
            arr = piv.to_numpy(); bs = []
            for _ in range(1000):
                idx = RNG.integers(0, len(arr), len(arr))
                bs.append(np.nanmedian(np.nanmean(arr[idx], axis=0)))
            bs = np.array(bs)
            ozet.append({"grup": g, "yil": y, "dk": hhmm(dk), "gun": n, "gun_ort": mu, "se": se, "esik": th, "t_esik": (mu - th) / se, "gun_medyan": gun.median(), "gun_pay>=1.5": (gun >= 1.5).mean(), "parite_med": P[g][0].loc[dk, y], "bs_p05": np.percentile(bs, 5), "bs_p95": np.percentile(bs, 95), "bs_pay>=esik": (bs >= th).mean(), "bs_pay>=1.5": (bs >= 1.5).mean()})
oz = pd.DataFrame(ozet)
oz.round(3).to_csv(f"{OUT}/veri_gunu_kume.csv", index=False)
print(oz.round(2).to_string(index=False))

# --- A gunleri tek tek (08:30 ve 08:31, gun ici parite ortalamasi) ---
a = G["A"][G["A"].dk.isin([510, 511])].groupby(["d", "dk"])["xn"].mean().unstack()
a.columns = ["08:30", "08:31"]
a["tur"] = ["CPI+NFP" if (d in CPI and d in NFP) else ("CPI" if d in CPI else "NFP") for d in a.index]
a.round(2).to_csv(f"{OUT}/veri_gunu_A_gunleri.csv")
print("\nA gunleri tek tek (gun ici parite ortalamasi):")
print(a.round(2).to_string())
b = G["B"][G["B"].dk == 510].groupby("d")["xn"].mean()
print("\nB gunleri 08:30 dagilimi (gun ici parite ortalamasi):", {y: b[b.index.str[:4] == str(y)].describe(percentiles=[.5, .9]).round(2).to_dict() for y in YILLAR})
print("B 08:30 en buyuk 10 gun:", b.sort_values(ascending=False).head(10).round(2).to_dict())
# fazlalik payi: B ve A gunlerinin 08:30 toplam fazlaliginin (x-1) ne kadari A'da
for y in YILLAR:
    aa = a[a.index.str[:4] == str(y)]["08:30"]; bb = b[b.index.str[:4] == str(y)]
    exA = (aa - 1).clip(lower=0).sum(); exB = (bb - 1).clip(lower=0).sum()
    print(f"{y}: 08:30 fazlaliginin A payi = {exA / (exA + exB):.2f} (A gun {len(aa)}, B gun {len(bb)})")

# --- Saglamlik (on kayitli kuralin parcasi degil): A gunlerinde 08:29-08:40 bootstrap ve bir-gun-cikar pencere uzunlugu ---
print("\nA gunleri bootstrap (1000 tekrar, gunler yeniden orneklenir): parite medyani ve >= x1,5 olma payi")
GA = G["A"]; out = []
for y in YILLAR:
    for dk in range(509, 521):
        s = GA[(GA.yil == y) & (GA.dk == dk)]
        arr = s.pivot_table(index="d", columns="sym", values="xn", aggfunc="mean").to_numpy()
        bs = np.array([np.nanmedian(np.nanmean(arr[RNG.integers(0, len(arr), len(arr))], axis=0)) for _ in range(1000)])
        out.append({"yil": y, "dk": hhmm(dk), "parite_med": np.nanmedian(np.nanmean(arr, axis=0)), "bs_pay>=1.5": (bs >= 1.5).mean(), "bs_p05": np.percentile(bs, 5)})
ob = pd.DataFrame(out).pivot(index="dk", columns="yil")
ob.round(3).to_csv(f"{OUT}/veri_gunu_A_bootstrap.csv")
print(ob.round(2).to_string())


def mor_uzunluk(sub):
    med = sub.groupby(["yil", "dk", "sym"])["xn"].mean().groupby(["yil", "dk"]).median().unstack(0)
    mn = med[list(YILLAR)].min(axis=1); n = 0
    for k in range(510, M1 + 1):
        if mn.loc[k] >= 1.5:
            n += 1
        else:
            break
    return n, mn.loc[510]


lo = pd.DataFrame([(d,) + mor_uzunluk(GA[GA.d != d]) for d in sorted(GA.d.unique())], columns=["cikan_gun", "mor_dk", "min_0830"])
print("Bir A gunu cikarilinca mor pencere uzunlugu (dk):", lo.mor_dk.value_counts().sort_index().to_dict(), "| 08:30 iki yil minimumunun en dusugu:", round(lo.min_0830.min(), 2))
print("Pencereyi kisaltan gunler:", lo[lo.mor_dk < lo.mor_dk.max()][["cikan_gun", "mor_dk"]].to_dict("records"))
