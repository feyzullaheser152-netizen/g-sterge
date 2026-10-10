"""Katki testi, dorduncu grup (1 dk; 22 Binance USDT-M paritesi; 2025 kesif / 2026 dogrulama; komisyon sifir, BULGULAR 14b).

Gostergeler (kullanici Ekim 2026'da gonderdi; daha once sinanmadilar):
  k5_wyckoff  : Wyckoff [theUltimator5] (lisans belirtilmemis; TradingView acik kaynak varsayilani MPL 2.0). Kampanya motoru (SC/BC, AR, ST, Spring/UTAD,
                Test, SOS/SOW, LPS/LPSY, Faz E) ve kendi LONG/SHORT ENTRY isaretleri (Entry Strictness = Standard, Auto). Ust zaman dilimleri 3, 5, 15 dk.
  k5_zprofil  : Buyers & Sellers Profile + Dynamic S/R [Zeiierman] (CC BY-NC-SA 4.0). Hacim profiliyle yer degistirilmis pivot destek/direncler.
  k5_bosribbon: Trend Target Ribbon [BOSWaves] (MPL 2.0). ALMA + sapma + egim trendi; donus isaretleri, yapisal stop ve 1R-4R hedefler.
  k5_shaakuni : Shaakuni - Liquidity Levels & Order Blocks v1.4.0 (MPL 2.0). Yalnizca Order Block kismi (yapi kirilimi + ATR itki + tazelik kurali).
                Onceki gun/hafta uclari ve %50 (EQ) seviyeleri daha once sinandi (BULGULAR 7, 9, 10e; rastgele seviyelerden iyi degil), onceki gun
                supurmesi de (isaret yillar arasinda degisiyor); tekrarlanmaz.
  k5_vdelta   : Volume Delta Pivot Matrix [BigBeluga] (CC BY-NC-SA 4.0). Pivot (5,5) seviyeleri, pivot cevresindeki 11 mumun kapanis konumuyla
                agirliklandirilmis hacim deltasi; kapanis seviyeyi gecince seviye silinir.
Mantik uyarlamasi; kod kopyalanmadi, yalnizca arastirma icindir. Her modul bagimsiz bir ajanla Pine koduna karsi dogrulanir (scratchpad/k5_kaynak).

ON KAYIT (sonuclardan once yazildi; esikler katki_testi3 ile ayni).
Modul sozlesmesi: hesapla(z) -> {"S": {kod: (al, sat)}, "D": {ad: int -1/0/1}, "U": {ad: bool}, "X": {ad: float +-1/nan}, "STOPS": {ad: (uzun, kisa)},
  "NATIVE": {kod: stop fiyati (yalnizca sinyal mumunda, digerleri nan)}}. Butun ciktilar mum kapanisinda bilinir (repaint yok).
Sinyaller (1. katman):
  WENT  : Wyckoff grafik zaman dilimi LONG/SHORT ENTRY (Auto, Standard): entryTime bu mum oldugunda; yon = outcome.
  WENTM : Gostergenin cizdigi butun ENTRY isaretleri: WENT + ust zaman dilimi (3/5/15 dk) yapisi secildiginde (mtfActive) saklanan girisler.
          Ust zaman dilimi girisi, 1 dk grafikte ILK saklandigi mumda tarihlenir (bilindigi an), etiketin cizildigi e.t aninda degil.
  WSPR  : Spring (AL) / UTAD (SAT) onayi.        WSOS: SOS (AL) / SOW (SAT).        WLPS: LPS (AL) / LPSY (SAT).
  WE    : Faz E (markup AL / markdown SAT).      WCT : Faz C testi (Test ya da terminal test; yon = outcome).
  WCLX  : Klimaks onayi (SC AL / BC SAT).
  ZNEW  : yeni profil onayli destek (AL) / direnc (SAT).
  ZBRK  : destek kirildi (SAT) / direnc kirildi (AL); ayni mumda ikisi birden ise yok.
  ZTCH  : dokunus (gostergede tanimli degil, on kayitla): onceki mumdan kalan aktif destek p icin low <= p ve close > p -> AL;
          direnc icin high >= p ve close < p -> SAT; ikisi birden ise yok.
  BFLIP : BOSWaves trend donusu (bullFlip AL / bearFlip SAT).
  SOBY  : Shaakuni yeni OB (boga OB olusunca AL / ayi OB olusunca SAT; olusum mumu = yapi kirilimi mumu).
  SOBM  : Shaakuni OB'nin ilk dokunusu (taze boga OB'ye ilk temas AL / taze ayi OB'ye ilk temas SAT; ikisi birden ise yok).
  VDPB  : delta pivot seviyesi kirildi (gostergenin silme kosulu: destek icin close <= seviye -> SAT; direnc icin close >= seviye -> AL).
  VDPT  : dokunus (on kayitla): onceki mumdan kalan aktif destek icin low <= seviye ve close > seviye -> AL; direnc icin high >= seviye ve close < seviye -> SAT.
  VDPTD : VDPT, yalnizca o anda cizilecek seviyelerle: aktif seviyelerin |delta|'si en buyuk |delta|'nin en az %20'si olanlar, en yeniden
          eskiye en fazla 10 tane (gostergenin son mumda uyguladigi filtre her mumda o anki aktif seviyelerle).
  Hepsi 54 ayarlik izgarada (TS.sim_izgara). Kural: 2025 R > 0, t >= 2; 2026 R > 0, t >= 3.
  Ek (yerel cikis, ayni kural): BFLIP gostergenin kendi pozisyonuyla: sonraki mumun acilisinda giris, NATIVE stop (gostergenin yapisal stopu),
  cikis stop ya da ters donus (donus mumundan sonraki acilis), en fazla 240 mum. R = brut / (stop mesafesi / giris).
2) Filtre (VSP islemleri; v6.1 sinyali, piyasa girisi, stop 2 sigma15, hedef 2R, 5 dk): D ve U durumlari ve uyum (W:) durumlari:
  "W:Wyckoff SC/Spring/C testi son 15 mumda (islem yonunde)", "W:Profil seviyesine dokunus son 5 mumda (islem yonunde)".
  Kural (katki_testi2 ile ayni): iki yilda ayni isaret, |fark| >= 1 bp, |t| >= 2 (2025) ve >= 3 (2026), kapsam %20-80.
3) Oynaklik bilgisi: R2 artisi iki yilda >= 0,005.
4) Yon bilgisi: sonraki 15 dk farki iki yilda ayni isaret, >= 1 bp, t 2/3.
6) Cikis: X donusleri (K2.exits ile ayni; kabul: iki yilda >= +0,5 bp, 2026 t >= 3).
7) Stop yerlesimi: STOPS (VSP olaylarinda; hedef 2R, 5 dk; olcu R; kabul: R farki iki yilda >= +0,01 ve 2026 t >= 3).
Giris zamanlamasi, coin secimi, saat/gun ve BTC baglami katmanlari bu gostergelerle ilgili yeni bilgi icermedigi icin tekrarlanmaz (BULGULAR 17).
Kullanim: VSP_VERI=<klasor> python3 arastirma/katki_testi5.py   (K5_IZGARA=0: 1. katman izgarasi onceki katki5_A.csv'den okunur)
"""
import math, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
import katki_testi as K1
import katki_testi2 as K2
import katki_testi3 as K3
import k5_wyckoff, k5_zprofil, k5_bosribbon, k5_shaakuni, k5_vdelta

KS, RS, HS = sinyal_v6.KS, sinyal_v6.RS, sinyal_v6.HS
MODS = [k5_wyckoff, k5_zprofil, k5_bosribbon, k5_shaakuni, k5_vdelta]
IZGARA = os.environ.get("K5_IZGARA", "1") != "0"


@njit(cache=True)
def sim_yerel_stop(o, h, l, c, ix, y, stopv, al, sat, maxh):
    """Gostergenin kendi pozisyonu: giris o[i+1]; cikis stop (mum acilisi stopun otesindeyse acilis) ya da ters donus (donus mumundan sonraki acilis)
    ya da maxh mum sonunda kapanis. Ardisik: acik pozisyon varken yeni giris yok (ters donus pozisyonu kapatip yenisini acar).
    Cikti: sinyal indeksi, yon, brut log getiri, R (stop mesafesine gore)."""
    n = len(c)
    m = len(ix)
    oi = np.empty(m, np.int64)
    oy = np.empty(m, np.int64)
    ob = np.empty(m)
    orr = np.empty(m)
    cnt = 0
    free = -1
    for q in range(m):
        i = ix[q]
        if i <= free or i + 2 >= n:
            continue
        yy = y[q]
        ent = o[i + 1]
        st = stopv[i]
        if not (st > 0):
            continue
        d = yy * (math.log(ent) - math.log(st))
        if not (d > 0):
            continue
        ex = np.nan
        j_end = min(i + maxh, n - 2)
        last = i + 1
        for j in range(i + 1, j_end + 1):
            last = j
            if (yy > 0 and l[j] <= st) or (yy < 0 and h[j] >= st):
                px = min(st, o[j]) if yy > 0 else max(st, o[j])
                ex = px
                break
            if j > i and ((yy > 0 and sat[j]) or (yy < 0 and al[j])):
                ex = o[j + 1]
                last = j
                break
        if np.isnan(ex):
            ex = c[j_end]
            last = j_end
        g = yy * (math.log(ex) - math.log(ent))
        oi[cnt] = i
        oy[cnt] = yy
        ob[cnt] = g
        orr[cnt] = g / d
        cnt += 1
        free = last - 1 if ((yy > 0 and sat[last]) or (yy < 0 and al[last])) else last
    return oi[:cnt], oy[:cnt], ob[:cnt], ob[:cnt].copy(), orr[:cnt]


def parite_isle(s):
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    o, h, l, c, v = (np.ascontiguousarray(x, dtype=np.float64) for x in (o, h, l, c, v))
    n = len(c)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(np.nan_to_num(r * r)).ewm(alpha=2 / 31, adjust=False).mean().to_numpy()
    sigall = np.sqrt(ew * 15)
    engel = sinyal_v6.olay_engeli(ts)
    t = np.arange(n)
    yilb = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    gunb = (ts // 86400 - TS.GUN0).astype(np.int64)
    S, D, U, X, STOPS, NATIVE = {}, {}, {}, {}, {}, {}
    for M in MODS:
        R_ = M.hesapla(z)
        S.update(R_.get("S", {}))
        D.update(R_.get("D", {}))
        U.update(R_.get("U", {}))
        X.update(R_.get("X", {}))
        STOPS.update(R_.get("STOPS", {}))
        NATIVE.update(R_.get("NATIVE", {}))
    gec = (t >= 5000) & (t < n - TS.NATIVE_MAX - 3) & np.isfinite(sigall) & (sigall > 0)
    out = {"A": {}}
    for ad, (al, sat) in S.items():
        al = np.asarray(al, bool)
        sat = np.asarray(sat, bool)
        ix = np.flatnonzero((al | sat) & gec & ~(al & sat))
        y = np.where(al[ix], 1, -1).astype(np.int64)
        if IZGARA:
            sg, blk = sigall[ix], engel[ix]
            for giris in ("P", "L"):
                for k in KS:
                    for R in RS:
                        for H in HS:
                            res = TS.sim_izgara(o, h, l, c, ix, y, sg, blk, k, R, H, giris == "L", 0.0, 0.0, 0.0, False)
                            out["A"][(ad, "izgara", giris, k, R, H)] = TS.toplam(yilb, gunb, *res)
        if ad in NATIVE:
            res = sim_yerel_stop(o, h, l, c, ix, y, np.asarray(NATIVE[ad], float), al, sat, TS.NATIVE_MAX)
            out["A"][(ad, "yerel", "P", 0, 0, 0)] = TS.toplam(yilb, gunb, *res)
    # VSP olaylari
    E = sinyal_v6.olaylar(s)
    ixv = np.searchsorted(ts, E["ts"])
    m = (ixv >= 5000) & (ixv < n - 40)
    ixv, yv, sgv = ixv[m], E["yon"][m].astype(np.int64), E["sig"][m]
    oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ixv, yv, sgv, np.zeros(len(ixv), bool), 2.0, 2.0, 5, False, 0.0, 0.0, 0.0, False)
    B = pd.DataFrame({"sym": s, "gun": ts[oi] // 86400, "yil": yilb[oi], "yon": oy, "brut": ob * 1e4})
    for ad, d in D.items():
        B["D:" + ad] = np.asarray(d)[oi] * oy > 0
    for ad, u in U.items():
        B["U:" + ad] = np.asarray(u, bool)[oi]
    w_al = np.asarray(S["WCLX"][0], bool) | np.asarray(S["WSPR"][0], bool) | np.asarray(S["WCT"][0], bool)
    w_sat = np.asarray(S["WCLX"][1], bool) | np.asarray(S["WSPR"][1], bool) | np.asarray(S["WCT"][1], bool)
    wa, ws_ = K3.son_k(w_al, 15), K3.son_k(w_sat, 15)
    za, zs = K3.son_k(np.asarray(S["ZTCH"][0], bool), 5), K3.son_k(np.asarray(S["ZTCH"][1], bool), 5)
    B["W:Wyckoff SC/Spring/C testi son 15 mumda (islem yonunde)"] = np.where(oy > 0, wa[oi], ws_[oi])
    B["W:Profil seviyesine dokunus son 5 mumda (islem yonunde)"] = np.where(oy > 0, za[oi], zs[oi])
    out["B"] = B
    # 3) ve 4)
    r2 = np.nan_to_num(r * r)
    cs = np.r_[0, np.cumsum(r2)]
    fut = np.sqrt(cs[np.minimum(t + 16, n)] - cs[np.minimum(t + 1, n)])
    idx = np.flatnonzero(gec & (t % 15 == 0) & (fut > 0))
    C = pd.DataFrame({"yil": yilb[idx], "gun": ts[idx] // 86400, "y": np.log(fut[idx]), "x0": np.log(sigall[idx]), "f15": (lc[np.minimum(idx + 15, n - 1)] - lc[idx]) * 1e4})
    for ad, u in U.items():
        C["U:" + ad] = np.asarray(u, bool)[idx].astype(float)
    for ad, d in D.items():
        C["D:" + ad] = np.asarray(d)[idx].astype(float)
    out["C"] = C
    # 6) cikis
    F = pd.DataFrame({"sym": s, "gun": ts[ixv] // 86400, "yil": yilb[ixv]})
    for ad, fl in X.items():
        base, alt = K2.exits(o, h, l, c, ixv, yv, sgv, np.asarray(fl, float), 30)
        F["base"] = base * 1e4
        F["X:" + ad] = alt * 1e4
    out["F"] = F
    # 7) stop yerlesimi
    G = pd.DataFrame({"sym": s, "gun": ts[ixv] // 86400, "yil": yilb[ixv]})
    ent = o[ixv + 1]
    var = {"2 sigma (temel)": 2.0 * sgv}
    for ad, (ls, ss) in STOPS.items():
        ls, ss = np.asarray(ls, float), np.asarray(ss, float)
        var[ad + " stopu"] = np.where(yv > 0, np.log(ent / ls[ixv]), np.log(ss[ixv] / ent))
    for ad, dd in var.items():
        dd = np.where(np.isfinite(dd), dd, np.nan)
        b_, r_ = K3.stop_varyant(o, h, l, c, ixv, yv, sgv, dd)
        G["R:" + ad] = r_
        G["bp:" + ad] = b_ * 1e4
    out["G"] = G
    print(s, "tamam", flush=True)
    return out


def main():
    A, B, C, F, G = {}, [], [], [], []
    with Pool(4) as p:
        for parca in p.imap_unordered(parite_isle, izleme.SYMS):
            A = TS.birlestir([A, parca["A"]]) if A else TS.birlestir([parca["A"]])
            B.append(parca["B"]); C.append(parca["C"]); F.append(parca["F"]); G.append(parca["G"])
    pd.to_pickle(dict(B=B, C=C, F=F, G=G), os.path.join(izleme.VERI, "katki5_parca.pkl"))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 40)
    rows = []
    for key, yl in A.items():
        for y in (2025, 2026):
            rows.append(dict(aday=key[0], tur=key[1], giris=key[2], k=key[3], R=key[4], H=key[5], yil=y, **TS.ozet(yl[y])))
    DA = pd.DataFrame(rows)
    if IZGARA:
        DA.to_csv(os.path.join(izleme.VERI, "katki5_A.csv"), index=False)
    else:
        eski = pd.read_csv(os.path.join(izleme.VERI, "katki5_A.csv"))
        DA = pd.concat([eski[eski["tur"] == "izgara"], DA[DA["tur"] == "yerel"]], ignore_index=True)
    kar = []
    for (ad, tur) in DA[["aday", "tur"]].drop_duplicates().itertuples(index=False):
        d = DA[(DA["aday"] == ad) & (DA["tur"] == tur)]
        a25 = d[d["yil"] == 2025].sort_values("netR", ascending=False).iloc[0]
        sel = d[(d["giris"] == a25["giris"]) & (d["k"] == a25["k"]) & (d["R"] == a25["R"]) & (d["H"] == a25["H"])]
        r25, r26 = sel[sel["yil"] == 2025].iloc[0], sel[sel["yil"] == 2026].iloc[0]
        gecti = r25["netR"] > 0 and r26["netR"] > 0 and r25["t"] >= 2 and r26["t"] >= 3
        kar.append(dict(aday=ad, tur=tur, ayar=f"{a25['giris']} k{a25['k']} R{a25['R']} H{a25['H']}" if tur == "izgara" else "yerel (stop + ters donus)", n25=r25["n"], n26=r26["n"],
                        R25=r25["netR"], t25=r25["t"], R26=r26["netR"], t26=r26["t"], bp25=r25["brut_bp"], bp26=r26["brut_bp"], AL26=r26["brutAL_bp"], SAT26=r26["brutSAT_bp"],
                        karar="GECTI" if gecti else "gecmedi"))
    print("=== 1) Sinyal ===")
    print(pd.DataFrame(kar).round(3).to_string())
    DB = pd.concat(B, ignore_index=True)
    print("\n=== 2) Filtre ve uyum (VSP islemleri) ===")
    fr = []
    for kol in [k for k in DB.columns if k[:2] in ("D:", "U:", "W:")]:
        res = {yl: K1.iki_grup(DB[DB["yil"] == yl], kol) for yl in (2025, 2026)}
        f25, t25, p25 = res[2025]
        f26, t26, p26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3 and min(p25, p26) >= 0.2 and max(p25, p26) <= 0.8
        fr.append(dict(durum=kol, pay25=p25, fark25=f25, t25=t25, pay26=p26, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(fr).round(3).to_string())
    DC = pd.concat(C, ignore_index=True)
    print("\n=== 3) Oynaklik bilgisi ===")
    cr = []
    for kol in [k for k in DC.columns if k.startswith("U:") or k.startswith("D:")]:
        tmp = DC
        if kol.startswith("D:"):
            tmp = DC.copy()
            tmp[kol] = (tmp[kol] != 0).astype(float)
        a = K1.r2_artis(tmp, kol)
        cr.append(dict(ozellik=kol, r2_25=a[2025], r2_26=a[2026], karar="KABUL" if min(a.values()) >= 0.005 else ""))
    print(pd.DataFrame(cr).round(4).to_string())
    print("\n=== 4) Yon bilgisi ===")
    yr = []
    for kol in [k for k in DC.columns if k.startswith("D:")]:
        res = {yl: K2.yon_farki(DC[DC["yil"] == yl], kol) for yl in (2025, 2026)}
        f25, t25 = res[2025]
        f26, t26 = res[2026]
        ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3
        yr.append(dict(durum=kol, fark25=f25, t25=t25, fark26=f26, t26=t26, karar="KABUL" if ok else ""))
    print(pd.DataFrame(yr).round(3).to_string())
    DF = pd.concat(F, ignore_index=True)
    print("\n=== 6) Cikis ===")
    xr = []
    for kol in [k for k in DF.columns if k.startswith("X:")]:
        rr = {yl: K3.esli_fark(DF[DF["yil"] == yl], kol, "base") for yl in (2025, 2026)}
        ok = rr[2025][0] >= 0.5 and rr[2026][0] >= 0.5 and rr[2026][1] >= 3
        xr.append(dict(cikis=kol, fark25=rr[2025][0], t25=rr[2025][1], fark26=rr[2026][0], t26=rr[2026][1], karar="KABUL" if ok else ""))
    print(pd.DataFrame(xr).round(3).to_string())
    DG = pd.concat(G, ignore_index=True)
    print("\n=== 7) Stop yerlesimi (R ve bp; fark = alternatif - 2 sigma) ===")
    gr = []
    for kol in [k for k in DG.columns if k.startswith("R:")]:
        ad = kol[2:]
        row = dict(stop=ad)
        for yl in (2025, 2026):
            d = DG[DG["yil"] == yl]
            row[f"R{yl % 100}"] = d[kol].mean()
            row[f"bp{yl % 100}"] = d["bp:" + ad].mean()
            f, tt, nn = K3.esli_fark(d, kol, "R:2 sigma (temel)")
            row[f"fark{yl % 100}"] = f
            row[f"t{yl % 100}"] = tt
            row[f"n{yl % 100}"] = nn
        row["karar"] = "KABUL" if (ad != "2 sigma (temel)" and row["fark25"] >= 0.01 and row["fark26"] >= 0.01 and row["t26"] >= 3) else ""
        gr.append(row)
    print(pd.DataFrame(gr).round(4).to_string())


if __name__ == "__main__":
    main()
