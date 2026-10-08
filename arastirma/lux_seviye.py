"""lux_seviye.py - LuxAlgo "Smart Money Concepts" seviyelerinin testi (22 Binance USDT-M paritesi, 2025 / 2026).

Algilama: arastirma/smc_port.py (LuxAlgo mantiginin bagimsiz Python uygulamasi; varsayilan girdiler). Kod kopyalanmadi.

Seviyeler (hepsi olustugu mumun KAPANISINDA bilinir; temas en erken bir sonraki mumda):
  1. Ic Order Block: olusum = ic BOS/CHoCH mumu; gecerlilik = High/Low ile gecersizlesene kadar
     (boga: low < alt kenar; ayi: high > ust kenar) ya da 100'luk liste sinirindan dusene kadar.
  2. FVG (grafik zaman dilimi, otomatik esik): gecerlilik = LuxAlgo silme kuralina kadar
     (boga: low < alt kenar; ayi: high > "top" alani; orijinalde ayi FVG'nin "top" alani bosluğun ALT kenaridir).
  3. EQH / EQL: seviye = iki esit tepenin yuksegi (EQH) / iki esit dibin dusugu (EQL); tespit anindan ilk temasa kadar.
     EQH direnc (asagidan temas), EQL destek (yukaridan temas). Insanlarin bekledigi: likidite supurmesi (fiyat gecip gider).
  4. Trailing tepe / dip (LuxAlgo "Strong/Weak High/Low"): degeri her degistiginde yeni seviye; degisene kadar gecerli.
     Tepe direnc, dip destek. Strong/Weak etiketi temastan onceki mumun swing egilimine gore (tepe: egilim ayi ise Strong).

Olay = olusumdan sonra, seviye gecerliyken ILK temas; fiyat bolgeye disaridan girer:
  boga bolgesi / destek: fiyat once ustte olmali (olusum mumunda low >= ust kenar; sonradan: low > ust kenar),
  temas = low <= ust kenar; ayi bolgesi / direnc: aynalanmis hali. Tek seviyelerde (EQH/EQL, trailing) olusum mumunda
  kesin disarida olma sarti var (seviyeye degen mum = temas etmis). EQH/EQL olusumda disarida degilse olay yok.
  Referans = ilk ulasilan kenar.
Olcum: tepki = isaret * ln(c[i+15] / ref) * 1e4 bp (+ = tuttu).
  Tutma: c[i+1..i+15] icinde bolgenin uzak kenarinin otesinde kapanis yok (tek seviyede: seviyenin 0,5*sqrt(15*ew) otesi;
  ew = 1 dk log getiri karesinin EWMA'si, span 30, adjust=False).
  Asim: i..i+15 icinde fiyatin yakin kenarin otesine gittigi en buyuk mesafe (bp; likidite supurmesi icin).
  Oynaklik: sonraki 15 dk gerceklesen / EWMA tahmini.
Kontrol: her seviye/bolge icin 4 yakin placebo kopyasi: fiyatin s*U(0,003; 0,015)'i kadar kaydirilmis (rastgele yon,
  ayni genislik), ayni mumda olusur, ayni ilk temas ve gecerlilik mantigi (bolgelerde kendi gecersizlesme kurali;
  OB'de gercek bolgenin listeden dusme bari; trailing'de gercek seviyenin degistigi bar).
Istatistik: fark = gercek - placebo; olay haftasina gore kumelenmis standart hata. Ilk 3000 mum atlanir.
ON KAYITLI KURAL: Seviye ancak 2025 VE 2026'da tepki farki >= +3 bp, t >= 2 ve tutma farki > 0 ise sanstan iyidir.
  Ayrica: iki yilda fark <= -3 bp ve t <= -2 ise "placebodan anlamli olarak daha sik kiriliyor" (yine maliyetle tartilir).

Calistirma: python3 arastirma/lux_seviye.py   (VERI ortam degiskeni = npz klasoru, varsayilan ../data_bn/npz;
            TOHUM = placebo tohumu, varsayilan 29; NSYM = parite sayisi siniri)
            python3 arastirma/lux_seviye.py analiz lux_seviye_29.pkl   (kayitli olay tablosundan yalnizca rapor)
Cikti: tablolar stdout'a; olay tablosu lux_seviye_<TOHUM>.pkl (calisma klasorune).
Saglamlik (on kayitli test degil): placebo olaylari gercek olaylarin bekleme ya da olusumdaki uzaklik dagilimina gore
  yeniden agirliklandirilir (placebolar cogunlukla fiyattan daha uzakta kalir, daha gec ve daha hizli bir hareketle temas eder).
"""
import glob
import os
import sys
import time
from collections import OrderedDict

import numpy as np
import pandas as pd

from smc_port import olaylar

SRC = os.environ.get("VERI", "../data_bn/npz")
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
NPL = 4
ATLA = 3000
TOHUM = int(os.environ.get("TOHUM", "29"))
OB_SINIR = 100

TURLER = ["İç OB", "FVG", "EQH", "EQL", "Trailing tepe", "Trailing dip"]
ALTLAR = ["boğa", "ayı", "Strong", "Weak", "-"]


# ------------------------------------------------------------------------------------------------
# aralik sorgulari: seyrek tablo + ikili atlama (bas'tan itibaren kosulu saglayan ilk indeks)
# ------------------------------------------------------------------------------------------------
def tablo(x, f):
    t = [x]
    k = 1
    while (1 << k) <= len(x):
        p = t[-1]
        s = 1 << (k - 1)
        t.append(f(p[:-s], p[s:]))
        k += 1
    return t


def ilk(tab, bas, v, mod):
    """mod: 'le' x <= v, 'lt' x < v (min tablosu); 'ge' x >= v, 'gt' x > v (maks tablosu). Yoksa n."""
    n = len(tab[0])
    pos = np.minimum(np.asarray(bas, np.int64), n)
    for k in range(len(tab) - 1, -1, -1):
        L = 1 << k
        ok = pos + L <= n
        if not ok.any():
            continue
        b = tab[k][np.where(ok, pos, 0)]
        if mod == "le":
            atla = b > v
        elif mod == "lt":
            atla = b >= v
        elif mod == "ge":
            atla = b < v
        else:
            atla = b <= v
        pos = np.where(ok & atla, pos + L, pos)
    return pos


def temas(S, x, tmin, tmax, yon):
    """S: seviye sozlugu (ayni yon). yon=+1 destek (x = low), -1 direnc (x = high).
    tmin/tmax: x'in min / maks tablolari. Doner: (ilk temas bari, yoksa -1; silahlanma bari)."""
    n = len(x)
    t, E, M, m0, son = S["t"], S["E"], S["M"], S["m0"], S["son"]
    kati0, gec = S["kati0"], S["gec"]
    xt = x[t]
    if yon == 1:
        sil0 = np.where(kati0, xt > E, xt >= E)
    else:
        sil0 = np.where(kati0, xt < E, xt <= E)
    j = np.where(sil0, t, n).astype(np.int64)
    g = ~sil0 & gec
    if g.any():
        j[g] = ilk(tmax if yon == 1 else tmin, t[g] + 1, E[g], "gt" if yon == 1 else "lt")
    olu = np.zeros(len(t), bool)
    gm = g & np.isfinite(M)
    if gm.any():
        mi = ilk(tmin if yon == 1 else tmax, m0[gm], M[gm], "lt" if yon == 1 else "gt")
        olu[gm] = mi < j[gm]
    i = np.full(len(t), n, np.int64)
    a = j < n
    i[a] = ilk(tmin if yon == 1 else tmax, j[a] + 1, E[a], "le" if yon == 1 else "ge")
    gecerli = (j <= son) & (i <= son) & ~olu & (i < n - H - 1)
    return np.where(gecerli, i, -1), j


# ------------------------------------------------------------------------------------------------
# seviye kumeleri
# ------------------------------------------------------------------------------------------------
def ob_son_bar(ev, n):
    """Ic OB'nin 100'luk listeden dustugu bar (dahil gecerli); dusmeyenler n-1. Liste smc_port ile ayni sirada yurutulur."""
    yeni = ev[ev.kind == "OB_int_new"]
    sil = ev[ev.kind == "OB_int_mitigated"]
    kimlik = {(int(a), int(b)): k for k, (a, b) in enumerate(zip(yeni.created_ts, yeni.bias))}
    sil_bar = {}
    for b, ct, bi in zip(sil.bar, sil.created_ts, sil.bias):
        sil_bar.setdefault(int(b), []).append(kimlik[(int(ct), int(bi))])
    yb = yeni.bar.to_numpy()
    son = np.full(len(yeni), n - 1, np.int64)
    canli = OrderedDict()
    j = 0
    dusen = 0
    for b in sorted(set(yb.tolist()) | set(sil_bar)):
        while j < len(yb) and yb[j] == b:
            if len(canli) >= OB_SINIR:
                k, _ = canli.popitem(last=False)
                son[k] = b
                dusen += 1
            canli[j] = None
            j += 1
        for k in sil_bar.get(b, []):
            del canli[k]
    return son, dusen


def seviyeler(ev, br, n):
    """Gercek seviyeler: sutunlar tur, alt, yon, t, E, F, M, m0, son, kati0, gec, tek, gen (kaydirma tabani)."""
    parca = []
    # 1. ic OB
    ob = ev[ev.kind == "OB_int_new"]
    son, dusen = ob_son_bar(ev, n)
    top, bot, bias = ob.top.to_numpy(), ob.bottom.to_numpy(), ob.bias.to_numpy(int)
    U, D = np.maximum(top, bot), np.minimum(top, bot)
    boga = bias == 1
    t = ob.bar.to_numpy(np.int64)
    parca.append(pd.DataFrame({"tur": "İç OB", "alt": np.where(boga, "boğa", "ayı"), "yon": bias, "t": t,
                               "E": np.where(boga, U, D), "F": np.where(boga, D, U), "M": np.where(boga, bot, top),
                               "m0": t, "son": son, "kati0": False, "gec": True, "tek": False, "gen": (U + D) / 2}))
    # 2. FVG
    fv = ev[ev.kind == "FVG_new"]
    top, bot, bias = fv.top.to_numpy(), fv.bottom.to_numpy(), fv.bias.to_numpy(int)
    U, D = np.maximum(top, bot), np.minimum(top, bot)
    boga = bias == 1
    t = fv.bar.to_numpy(np.int64)
    parca.append(pd.DataFrame({"tur": "FVG", "alt": np.where(boga, "boğa", "ayı"), "yon": bias, "t": t,
                               "E": np.where(boga, U, D), "F": np.where(boga, D, U), "M": np.where(boga, bot, top),
                               "m0": t + 1, "son": n - 1, "kati0": False, "gec": True, "tek": False, "gen": (U + D) / 2}))
    # 3. EQH / EQL
    for ad, yon, f in (("EQH", -1, np.maximum), ("EQL", 1, np.minimum)):
        e = ev[ev.kind == ad]
        L = f(e.level.to_numpy(), e.prev_level.to_numpy())
        t = e.bar.to_numpy(np.int64)
        parca.append(pd.DataFrame({"tur": ad, "alt": "-", "yon": yon, "t": t, "E": L, "F": np.nan, "M": np.nan,
                                   "m0": t, "son": n - 1, "kati0": True, "gec": False, "tek": True, "gen": L}))
    # 4. trailing tepe / dip
    for ad, sutun, yon in (("Trailing tepe", "trailing_top", -1), ("Trailing dip", "trailing_bottom", 1)):
        v = br[sutun].to_numpy()
        onceki = np.r_[np.nan, v[:-1]]
        t = np.flatnonzero(np.isfinite(v) & (v != onceki))
        son = np.r_[t[1:], n - 1].astype(np.int64)
        L = v[t]
        parca.append(pd.DataFrame({"tur": ad, "alt": "-", "yon": yon, "t": t, "E": L, "F": np.nan, "M": np.nan,
                                   "m0": t, "son": son, "kati0": True, "gec": True, "tek": True, "gen": L}))
    S = pd.concat(parca, ignore_index=True)
    S = S[(S.t >= ATLA) & np.isfinite(S.E)].reset_index(drop=True)
    return S, dusen


def placebolar(S, rng):
    """Her seviye icin NPL kopya: E, F, M ayni mutlak miktarda (s * U(0,003; 0,015) * gen) kaydirilir."""
    out = [S.assign(tip=0, d=0.0)]
    m = len(S)
    for j in range(1, NPL + 1):
        d = rng.uniform(0.003, 0.015, m) * rng.choice([-1.0, 1.0], m) * S.gen.to_numpy()
        out.append(S.assign(tip=j, E=S.E + d, F=S.F + d, M=S.M + d, d=d))
    return pd.concat(out, ignore_index=True)


# ------------------------------------------------------------------------------------------------
# bir parite
# ------------------------------------------------------------------------------------------------
def parite(yol, rng):
    z = np.load(yol)
    ts, h, l, c = z["ts"].astype(np.int64), z["h"].astype(float), z["l"].astype(float), z["c"].astype(float)
    n = len(c)
    ev, br = olaylar(yol)
    S, dusen = seviyeler(ev, br, n)
    P = placebolar(S, rng)
    P["i"] = -1
    P["j"] = -1
    for yon, x in ((1, l), (-1, h)):
        tmin = tablo(x, np.minimum)
        tmax = tablo(x, np.maximum)
        k = np.flatnonzero(P.yon.to_numpy() == yon)
        sec = {s: P[s].to_numpy()[k] for s in ("t", "E", "M", "m0", "son", "kati0", "gec")}
        ii, jj = temas(sec, x, tmin, tmax, yon)
        P.loc[P.index[k], "i"] = ii
        P.loc[P.index[k], "j"] = jj
        del tmin, tmax
    # olcumler
    lr = np.log(c)
    r = np.r_[np.nan, np.diff(lr)]
    ew = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    rvf = np.sqrt(pd.Series(r * r)[::-1].rolling(H).sum()[::-1].to_numpy())
    rvf = np.r_[rvf[1:], np.nan]                                     # i+1..i+15
    fmin_c = np.r_[pd.Series(c).rolling(H).min().to_numpy()[H:], np.full(H, np.nan)]   # min c[i+1..i+15]
    fmax_c = np.r_[pd.Series(c).rolling(H).max().to_numpy()[H:], np.full(H, np.nan)]
    fmin_l = np.r_[pd.Series(l).rolling(H + 1).min().to_numpy()[H:], np.full(H, np.nan)]  # min l[i..i+15]
    fmax_h = np.r_[pd.Series(h).rolling(H + 1).max().to_numpy()[H:], np.full(H, np.nan)]
    E = P[P.i >= 0].reset_index(drop=True)
    i = E.i.to_numpy(np.int64)
    t = E.t.to_numpy(np.int64)
    yon = E.yon.to_numpy().astype(float)
    ref = E.E.to_numpy()
    sig = np.sqrt(ew[i] * H)
    tepki = yon * np.log(c[i + H] / ref) * 1e4
    tek = E.tek.to_numpy(bool)
    sinir = np.where(tek, ref * np.exp(-yon * 0.5 * sig), E.F.to_numpy())
    kirik = np.where(yon > 0, fmin_c[i] < sinir, fmax_c[i] > sinir)
    asim = np.where(yon > 0, -np.log(fmin_l[i] / ref), np.log(fmax_h[i] / ref)) * 1e4
    alt = E.alt.to_numpy(object).copy()
    sb = br.swing_bias.to_numpy()
    for ad, guclu in (("Trailing tepe", -1), ("Trailing dip", 1)):
        m = E.tur.to_numpy() == ad
        alt[m] = np.where(sb[i[m] - 1] == guclu, "Strong", "Weak")
    D = pd.DataFrame({"sym": os.path.basename(yol)[:-4], "tur": E.tur.astype("category"), "alt": alt,
                      "tip": E.tip.to_numpy(np.int8), "yil": np.where(ts[i] < CUT, 2025, 2026).astype(np.int16),
                      "hafta": ((ts[i] - 345600) // 604800).astype(np.int32),
                      "tepki": tepki.astype(np.float32), "tutma": (~kirik).astype(np.int8), "asim": asim.astype(np.float32),
                      "oyn": (rvf[i] / sig).astype(np.float32), "bekleme": (i - t).astype(np.int32),
                      "mesafe": (yon * np.log(c[t] / ref) / np.sqrt(np.maximum(ew[t], 1e-14))).astype(np.float32),
                      "gec_sil": (E.j.to_numpy() > t).astype(np.int8),
                      "kayma": np.sign(E.d.to_numpy()).astype(np.int8)})   # placebo kayma yonu (+1 yukari; gercekte 0)
    bilgi = {"seviye": S.groupby("tur").size().to_dict(), "ob_dusen": dusen, "port_dusen": ev.attrs["istatistik"]["ob_sinir_dusen"]}
    # denetim: gercek OB'lerde kendi gecersizlesme kuralimizin bari ile smc_port'un silme bari (port, Pine'daki
    # "for [i, x] + remove" atlamasi yuzunden bazen bir ya da birkac bar gec siler; temas olcumunu yalnizca sonradan
    # silahlanan OB'lerde etkileyebilir)
    ob = ev[ev.kind == "OB_int_new"].reset_index(drop=True)
    mit = ev[ev.kind == "OB_int_mitigated"]
    port_m = pd.Series(mit.bar.to_numpy(), index=pd.MultiIndex.from_arrays([mit.created_ts.astype(int), mit.bias.astype(int)]))
    anahtar = pd.MultiIndex.from_arrays([ob.created_ts.astype(int), ob.bias.astype(int)])
    pm = port_m.reindex(anahtar).to_numpy()
    tmin = tablo(l, np.minimum)
    tmaxh = tablo(h, np.maximum)
    bo = ob.bias.to_numpy(int) == 1
    t0 = ob.bar.to_numpy(np.int64)
    kendi = np.where(bo, ilk(tmin, t0, ob.bottom.to_numpy(), "lt"), ilk(tmaxh, t0, ob.top.to_numpy(), "gt"))
    ok = np.isfinite(pm)
    bilgi["ob_silme_ayni"] = float(np.mean(kendi[ok] == pm[ok]))
    bilgi["ob_silme_gec"] = float(np.mean(kendi[ok] < pm[ok]))
    return D, bilgi


# ------------------------------------------------------------------------------------------------
# istatistik
# ------------------------------------------------------------------------------------------------
def kume_fark(a, b, ga, gb):
    """Ortalama farki ve hafta kumelenmis standart hata (etki fonksiyonu)."""
    ma, mb = a.mean(), b.mean()
    psi = np.r_[(a - ma) / len(a), -(b - mb) / len(b)]
    s = pd.Series(psi).groupby(np.r_[ga, gb]).sum().to_numpy()
    return ma - mb, np.sqrt((s ** 2).sum())


def ozet(D, anahtar):
    rows = []
    for (ad, yil), g in D.groupby([anahtar, "yil"], observed=True):
        a, b = g[g.tip == 0], g[g.tip > 0]
        if len(a) < 30 or len(b) < 30:
            continue
        fr, sr = kume_fark(a.tepki.to_numpy(float), b.tepki.to_numpy(float), a.hafta.to_numpy(), b.hafta.to_numpy())
        fh, sh = kume_fark(a.tutma.to_numpy(float), b.tutma.to_numpy(float), a.hafta.to_numpy(), b.hafta.to_numpy())
        fa, sa = kume_fark(a.asim.to_numpy(float), b.asim.to_numpy(float), a.hafta.to_numpy(), b.hafta.to_numpy())
        ps = g.groupby(["sym", g.tip > 0]).tepki.mean().unstack()
        rows.append({"seviye": ad, "yıl": yil, "n_ger": len(a), "n_plc": len(b), "tepki_ger": a.tepki.mean(),
                     "tepki_plc": b.tepki.mean(), "fark_bp": fr, "t": fr / sr, "tutma_ger_%": a.tutma.mean() * 100,
                     "tutma_fark_puan": fh * 100, "t_tutma": fh / sh, "aşım_fark_bp": fa, "t_aşım": fa / sa,
                     "oyn_ger": a.oyn.median(), "oyn_plc": b.oyn.median(), "bekleme_ger": a.bekleme.median(),
                     "bekleme_plc": b.bekleme.median(), "parite_+%": ((ps[False] - ps[True]) > 0).mean() * 100})
    return pd.DataFrame(rows)


def karar(R):
    out = []
    for ad, g in R.groupby("seviye", sort=False):
        g = g.set_index("yıl")
        if not {2025, 2026} <= set(g.index):
            out.append((ad, "yetersiz örnek"))
            continue
        iyi = all(g.loc[y, "fark_bp"] >= 3 and g.loc[y, "t"] >= 2 and g.loc[y, "tutma_fark_puan"] > 0 for y in (2025, 2026))
        kot = all(g.loc[y, "fark_bp"] <= -3 and g.loc[y, "t"] <= -2 for y in (2025, 2026))
        if iyi:
            out.append((ad, "GEÇTİ (şanstan iyi)"))
        elif kot:
            out.append((ad, "placebodan anlamlı olarak DAHA SIK KIRILIYOR"))
        else:
            out.append((ad, "geçmedi"))
    return pd.DataFrame(out, columns=["seviye", "karar"])


MESAFE_SINIR = [-np.inf, 0, 0.5, 1, 2, 3, 5, 8, 13, 20, 30, np.inf]


def eslesik_fark(g, deger, kutu, en_az=30):
    """Placebo, gercek olaylarin kutu dagilimina gore yeniden agirliklandirilir (kutu ici fark, gercek paylariyla).
    Hafta kumelenmis SE (agirliklar sabit sayilir). Doner: fark, se, kapsam (ortak kutulardaki gercek olay payi)."""
    a, b = g[g.tip == 0], g[g.tip > 0]
    na = a.groupby(kutu).size()
    nb = b.groupby(kutu).size()
    ortak = na.index[(na >= en_az) & (nb.reindex(na.index).fillna(0) >= en_az)]
    if len(ortak) == 0:
        return np.nan, np.nan, 0.0
    p = na[ortak] / na[ortak].sum()
    a = a[a[kutu].isin(ortak)]
    b = b[b[kutu].isin(ortak)]
    ma = a.groupby(kutu)[deger].mean()
    mb = b.groupby(kutu)[deger].mean()
    fark = float((p * (ma - mb)).sum())
    ka, kb = a[kutu].to_numpy(), b[kutu].to_numpy()
    psi_a = p.reindex(ka).to_numpy() * (a[deger].to_numpy(float) - ma.reindex(ka).to_numpy()) / na.reindex(ka).to_numpy()
    psi_b = -p.reindex(kb).to_numpy() * (b[deger].to_numpy(float) - mb.reindex(kb).to_numpy()) / nb.reindex(kb).to_numpy()
    s = pd.Series(np.r_[psi_a, psi_b]).groupby(np.r_[a.hafta.to_numpy(), b.hafta.to_numpy()]).sum().to_numpy()
    return fark, float(np.sqrt((s ** 2).sum())), float(na[ortak].sum() / na.sum())


def saglamlik(D, anahtar):
    """Baglam eslestirmesi: placebo olaylari (cogu daha uzakta, daha gec temas eder) gercek olaylarin
    bekleme (log2 dk) ya da olusumdaki uzaklik (sigma_1dk biriminde) dagilimina gore agirliklandirilir."""
    D = D.assign(k_bek=np.minimum(np.floor(np.log2(np.maximum(D.bekleme.to_numpy(), 1))), 12).astype(np.int8),
                 k_mes=np.digitize(D.mesafe.to_numpy(float), MESAFE_SINIR[1:-1]).astype(np.int8))
    rows = []
    for (ad, yil), g in D.groupby([anahtar, "yil"], observed=True):
        r = {"seviye": ad, "yıl": yil}
        for kutu, et in (("k_bek", "bek"), ("k_mes", "mes")):
            fr, sr, kap = eslesik_fark(g, "tepki", kutu)
            fh, sh, _ = eslesik_fark(g, "tutma", kutu)
            r.update({f"fark_{et}": fr, f"t_{et}": fr / sr, f"tutma_{et}": fh * 100, f"t_tutma_{et}": fh / sh, f"kapsam_{et}_%": kap * 100})
        rows.append(r)
    return pd.DataFrame(rows)


def rapor(D, tohum):
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(f"LuxAlgo SMC seviyeleri; ilk temas sonrasi {H} dk; fark = gercek - placebo (hafta kumelenmis t); tohum {tohum}")
    R = ozet(D, "tur")
    print(R.round(2).to_string(index=False))
    print()
    print(karar(R).to_string(index=False))
    D = D.assign(tur_alt=D.tur.astype(str) + " " + D.alt.astype(str))
    A = ozet(D[D.alt != "-"], "tur_alt")
    print("\nAlt kirilimlar (bilgi)")
    print(A.round(2).to_string(index=False))
    print()
    print(karar(A).to_string(index=False))
    print("\nPlacebo olaylari kayma yonune gore (sayi, ortalama tepki bp; kayma +1 = yukari)")
    pl = D[D.tip > 0]
    print(pl.groupby(["tur", "yil", "kayma"], observed=True).tepki.agg(["size", "mean"]).unstack("kayma").round(2).to_string())
    print("\nGercek olaylarda: olusumdaki uzaklik (sigma_1dk) ve bekleme (dk) medyani; sonradan silahlanan pay (%)")
    print(D[D.tip == 0].groupby(["tur", "yil"], observed=True).agg(mesafe=("mesafe", "median"), bekleme=("bekleme", "median"),
                                                                     gec_sil=("gec_sil", "mean")).round(3).to_string())
    print("\nSaglamlik (on kayitli test DEGIL): baglam eslestirmeli fark (bek = bekleme, mes = olusumdaki uzaklik)")
    print(saglamlik(D, "tur").round(2).to_string(index=False))
    print("\nUc deger duyarliligi (bilgi): 10 Ekim 2025 haftasi haric; tepki %1-%99 kirpilmis (tur-yil icinde)")
    hafta_10ekim = (int(pd.Timestamp("2025-10-10", tz="UTC").timestamp()) - 345600) // 604800
    R1 = ozet(D[D.hafta != hafta_10ekim], "tur")[["seviye", "yıl", "fark_bp", "t", "tutma_fark_puan", "t_tutma"]]
    W = D[["tur", "yil", "tip", "sym", "hafta", "tepki", "tutma", "asim", "oyn", "bekleme"]].copy()
    sinir = W[W.tip == 0].groupby(["tur", "yil"], observed=True).tepki.quantile([0.01, 0.99]).unstack()
    alt_s = sinir[0.01].reindex(pd.MultiIndex.from_arrays([W.tur, W.yil])).to_numpy()
    ust_s = sinir[0.99].reindex(pd.MultiIndex.from_arrays([W.tur, W.yil])).to_numpy()
    W["tepki"] = np.clip(W.tepki.to_numpy(float), alt_s, ust_s)
    R2 = ozet(W, "tur")[["seviye", "yıl", "fark_bp", "t"]].rename(columns={"fark_bp": "fark_kirpik", "t": "t_kirpik"})
    print(R1.merge(R2, on=["seviye", "yıl"]).round(2).to_string(index=False))
    print("\nStrong - Weak (yalnizca gercek olaylar; LuxAlgo iddiasi: Strong seviye daha iyi tutar)")
    rows = []
    for ad in ("Trailing tepe", "Trailing dip"):
        for yil in (2025, 2026):
            g = D[(D.tip == 0) & (D.tur == ad) & (D.yil == yil)]
            a, b = g[g.alt == "Strong"], g[g.alt == "Weak"]
            fr, sr = kume_fark(a.tepki.to_numpy(float), b.tepki.to_numpy(float), a.hafta.to_numpy(), b.hafta.to_numpy())
            fh, sh = kume_fark(a.tutma.to_numpy(float), b.tutma.to_numpy(float), a.hafta.to_numpy(), b.hafta.to_numpy())
            rows.append({"seviye": ad, "yıl": yil, "n_strong": len(a), "n_weak": len(b), "tepki_fark_bp": fr, "t": fr / sr,
                         "tutma_fark_puan": fh * 100, "t_tutma": fh / sh})
    print(pd.DataFrame(rows).round(2).to_string(index=False))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "analiz":
        D = pd.read_pickle(sys.argv[2])
        rapor(D, sys.argv[2])
        return
    rng = np.random.default_rng(TOHUM)
    parcalar = []
    for f in sorted(glob.glob(f"{SRC}/*.npz"))[:int(os.environ.get("NSYM", "99"))]:
        t0 = time.time()
        D, bilgi = parite(f, rng)
        parcalar.append(D)
        print("tamam", os.path.basename(f)[:-4], "%.0fs" % (time.time() - t0), bilgi, file=sys.stderr, flush=True)
    D = pd.concat(parcalar, ignore_index=True)
    D["tur"] = pd.Categorical(D.tur.astype(str), TURLER)
    D.to_pickle(f"lux_seviye_{TOHUM}.pkl")
    rapor(D, TOHUM)


if __name__ == "__main__":
    main()
