"""Klasik mum formasyonlari, 1 dakikalik mumlar (22 Binance USDT-M paritesi; 2025 kesif, 2026 dogrulama).

Tanimlar (i = formasyonun son mumu; bilgi i mumunun KAPANISINDA bilinir, repaint yok):
  govde = |c-o|, aralik = h-l, ust fitil = h-max(o,c), alt fitil = min(o,c)-l, ATR = RMA(TR,14), ATR[1] = bir onceki mumun ATR'si.
  Yutan boga : c>o, c[1]<o[1], o<=c[1], c>=o[1], govde > govde[1]                       yon +1
  Yutan ayi  : c<o, c[1]>o[1], o>=c[1], c<=o[1], govde > govde[1]                       yon -1
  Cekic      : govde>0, alt fitil >= 2 x govde, ust fitil <= 0,3 x govde                 yon +1
  Cekic + z  : ayrica z15[1] <= -2 (formasyondan ONCEKI 15 dk hareket asagi)            yon +1
  Kayan yildiz: govde>0, ust fitil >= 2 x govde, alt fitil <= 0,3 x govde               yon -1
  Kayan yildiz + z: ayrica z15[1] >= 2                                                   yon -1
  Doji       : govde <= 0,1 x aralik, aralik >= 1 x ATR[1]; yon = onceki 15 dk hareketin tersi (-isaret z15[1])
  Ic mum     : h<h[1], l>l[1]; yon = ana mumun yonu (isaret(c[1]-o[1]), devam)
  Dis mum    : h>h[1], l<l[1]; yon = mumun kendi yonu (isaret(c-o), devam)
  Uc beyaz asker: son 3 mumun her biri c>o, govde >= 0,5 x ATR(formasyon oncesi), ust fitil <= 0,3 x govde,
               kapanislar art arda yukselir, her acilis onceki govdenin icinde (o[k-1] <= o[k] <= c[k-1])   yon +1
  Uc kara karga: ayna tanim                                                              yon -1
  Marubozu   : govde >= 0,9 x aralik, aralik >= 1,5 x ATR[1]; yon = isaret(c-o) (devam)
  z15 = ln(c/c[15]) / (sd1 x sqrt 15), sd1 = ta.stdev(r1,1440) (populasyon) -- VSP ile ayni.
Olcum: ileri getiri ln(c[i+k]/c[i]) x 1e4 (k = 5, 15), formasyon yonunde, parite-yil kosulsuz ortalamasindan arindirilmis:
  etki = yon x (ileri getiri - mu[parite, yil]).  t: UTC takvim gunune gore kumelenmis SE.
  % parite: parite ortalama etkisi > 0 olan parite orani.
  Oynaklik: ileri 15 dk gerceklesen oynaklik RV = sqrt(sum r1[i+1..i+15]^2);
    RV/EWMA = RV / sqrt(ewVar x 15) ortalamasi, kosulsuz ortalamaya bolunmus (1,00 = VSP beklenen hareket kutusu
    formasyondan sonra da ayni olcude dogru); x normal = RV / (sigma_base x sqrt 15), kosulsuza bolunmus;
    x15 ham = sonraki 15 mumda ortalama |r1| / sigma_base (DURUM renk kuralinin olcusu: SARI >= 1,5, KIRMIZI >= 3,0).
ON KAYITLI KURAL: formasyon ancak 15 dk etkisi iki yilda da |etki| >= 3 bp, ayni isaret ve |t| >= 2 ise "bilgi verici"
  (yine de maliyetin altinda; ancak bilgi olarak gosterilebilir, sinyal olarak degil).
Her paritenin ilk 3000 mumu atlanir."""
import os
import sys

import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
Y = {0: "2025", 1: "2026"}

# (ad, tur) tur: "F" = formasyon (kurala tabi), "R" = referans/saglamlik
PATS = [
    ("Yutan boğa", "F"), ("Yutan ayı", "F"),
    ("Çekiç", "F"), ("Çekiç + z15[1]<=-2", "F"),
    ("Kayan yıldız", "F"), ("Kayan yıldız + z15[1]>=2", "F"),
    ("Doji", "F"), ("İç mum", "F"), ("Dış mum", "F"),
    ("Üç beyaz asker", "F"), ("Üç kara karga", "F"), ("Marubozu", "F"),
    ("Sağlamlık: Çekiç + z15[0]<=-2", "R"), ("Sağlamlık: Kayan yıldız + z15[0]>=2", "R"),
    ("Referans: her mum (yön = mum yönü)", "R"),
    ("Referans: z15[1]<=-2 (yön +1)", "R"), ("Referans: z15[1]>=2 (yön -1)", "R"),
    ("Referans: her mum, yön = -işaret z15[1]", "R"),
]
# formasyon -> dogal referans (sekil, salt hareketten fazla bir sey katiyor mu?)
REFS = {
    "Çekiç + z15[1]<=-2": "Referans: z15[1]<=-2 (yön +1)",
    "Kayan yıldız + z15[1]>=2": "Referans: z15[1]>=2 (yön -1)",
    "Doji": "Referans: her mum, yön = -işaret z15[1]",
    "Marubozu": "Referans: her mum (yön = mum yönü)",
    "Dış mum": "Referans: her mum (yön = mum yönü)",
    "Yutan boğa": "Referans: her mum (yön = mum yönü)",
    "Yutan ayı": "Referans: her mum (yön = mum yönü)",
}


def sh(x, k=1, fill=np.nan):
    o = np.full(len(x), fill, dtype=float); o[k:] = x[:-k]; return o


def per_symbol(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, o, h, l, c = z["ts"], z["o"].astype(float), z["h"].astype(float), z["l"].astype(float), z["c"].astype(float)
    n = len(ts)
    idx = np.arange(n)
    lc = np.log(c)
    r1 = np.empty(n); r1[0] = np.nan; r1[1:] = np.diff(lc)
    r1z = np.nan_to_num(r1)
    sd1 = pd.Series(r1).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    sb = sh(sd1)
    ewv = pd.Series(r1z * r1z).ewm(span=30, adjust=False).mean().to_numpy()
    sigH = np.sqrt(ewv * H)
    pc = sh(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))); tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    atr1 = sh(atr)
    with np.errstate(invalid="ignore", divide="ignore"):
        lc15 = np.full(n, np.nan); lc15[15:] = lc[15:] - lc[:-15]
        z15 = np.where(sd1 > 0, lc15 / (sd1 * np.sqrt(15)), np.nan)
    z15p = sh(z15)
    f5 = np.full(n, np.nan); f5[:n - 5] = (lc[5:] - lc[:n - 5]) * 1e4
    f15 = np.full(n, np.nan); f15[:n - H] = (lc[H:] - lc[:n - H]) * 1e4
    cs = np.concatenate([[0.0], np.cumsum(r1z * r1z)])
    rvf = np.full(n, np.nan); rvf[:n - H] = np.sqrt(cs[1 + H:n + 1] - cs[1:n + 1 - H])
    with np.errstate(invalid="ignore", divide="ignore"):
        rvr = rvf / sigH
        rvb = rvf / (sb * np.sqrt(H))
        xb = np.abs(r1) / sb
    xz = np.where(np.isfinite(xb), xb, 0.0); xn = np.isfinite(xb).astype(float)
    cx = np.concatenate([[0.0], np.cumsum(xz)]); cn = np.concatenate([[0.0], np.cumsum(xn)])
    x15 = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        x15[:n - H] = (cx[1 + H:n + 1] - cx[1:n + 1 - H]) / (cn[1 + H:n + 1] - cn[1:n + 1 - H])
    valid = (idx >= WARM) & (idx < n - H) & np.isfinite(sb) & (sb > 0) & (sigH > 0) & np.isfinite(f15) & np.isfinite(x15)
    yr = (ts >= CUT).astype(np.int8)
    day = (ts // 86400).astype(np.int64)

    # kosulsuz
    unc = {}
    mu5 = np.zeros(2); mu15 = np.zeros(2)
    for y in (0, 1):
        m = valid & (yr == y)
        mu5[y] = f5[m].mean(); mu15[y] = f15[m].mean()
        unc[y] = dict(n=int(m.sum()), s5=float(f5[m].sum()), s15=float(f15[m].sum()), srv=float(rvr[m].sum()), srvb=float(rvb[m].sum()),
                      sx15=float(x15[m].sum()), ndays=int(len(np.unique(day[m]))))

    body = np.abs(c - o); rng = h - l
    upw = h - np.maximum(o, c); low = np.minimum(o, c) - l
    bull = c > o; bear = c < o
    o1, c1, h1, l1 = sh(o), sh(c), sh(h), sh(l)
    o2, c2 = sh(o, 2), sh(c, 2)
    b1 = np.abs(c1 - o1)
    one = np.ones(n)
    with np.errstate(invalid="ignore"):
        pats = {}
        pats["Yutan boğa"] = (bull & (c1 < o1) & (o <= c1) & (c >= o1) & (body > b1), one)
        pats["Yutan ayı"] = (bear & (c1 > o1) & (o >= c1) & (c <= o1) & (body > b1), -one)
        ham = (body > 0) & (low >= 2 * body) & (upw <= 0.3 * body)
        star = (body > 0) & (upw >= 2 * body) & (low <= 0.3 * body)
        pats["Çekiç"] = (ham, one)
        pats["Çekiç + z15[1]<=-2"] = (ham & (z15p <= -2), one)
        pats["Kayan yıldız"] = (star, -one)
        pats["Kayan yıldız + z15[1]>=2"] = (star & (z15p >= 2), -one)
        pats["Doji"] = ((body <= 0.1 * rng) & (rng >= atr1) & (rng > 0), -np.sign(np.nan_to_num(z15p)))
        pats["İç mum"] = ((h < h1) & (l > l1), np.sign(np.nan_to_num(c1 - o1)))
        pats["Dış mum"] = ((h > h1) & (l < l1), np.sign(c - o))
        # uc asker / karga: barlar i-2, i-1, i; buyukluk esigi ATR[i-3]
        atr3 = sh(atr, 3)
        upw1, upw2 = sh(upw), sh(upw, 2)
        low1, low2 = sh(low), sh(low, 2)
        bd1, bd2 = b1, np.abs(c2 - o2)
        ws = (bull & (c1 > o1) & (c2 > o2) & (body >= 0.5 * atr3) & (bd1 >= 0.5 * atr3) & (bd2 >= 0.5 * atr3)
              & (upw <= 0.3 * body) & (upw1 <= 0.3 * bd1) & (upw2 <= 0.3 * bd2) & (c > c1) & (c1 > c2)
              & (o1 >= o2) & (o1 <= c2) & (o >= o1) & (o <= c1))
        bc = (bear & (c1 < o1) & (c2 < o2) & (body >= 0.5 * atr3) & (bd1 >= 0.5 * atr3) & (bd2 >= 0.5 * atr3)
              & (low <= 0.3 * body) & (low1 <= 0.3 * bd1) & (low2 <= 0.3 * bd2) & (c < c1) & (c1 < c2)
              & (o1 <= o2) & (o1 >= c2) & (o <= o1) & (o >= c1))
        pats["Üç beyaz asker"] = (ws, one)
        pats["Üç kara karga"] = (bc, -one)
        pats["Marubozu"] = ((body >= 0.9 * rng) & (rng >= 1.5 * atr1) & (rng > 0), np.sign(c - o))
        pats["Sağlamlık: Çekiç + z15[0]<=-2"] = (ham & (z15 <= -2), one)
        pats["Sağlamlık: Kayan yıldız + z15[0]>=2"] = (star & (z15 >= 2), -one)
        pats["Referans: her mum (yön = mum yönü)"] = (body > 0, np.sign(c - o))
        pats["Referans: z15[1]<=-2 (yön +1)"] = (z15p <= -2, one)
        pats["Referans: z15[1]>=2 (yön -1)"] = (z15p >= 2, -one)
        pats["Referans: her mum, yön = -işaret z15[1]"] = (np.isfinite(z15p), -np.sign(np.nan_to_num(z15p)))

    rows = []
    for name, _ in PATS:
        m, d = pats[name]
        sel = m & valid & (d != 0)
        ii = np.where(sel)[0]
        if len(ii) == 0:
            continue
        y_ = yr[ii]; dd = d[ii]
        e5 = dd * (f5[ii] - mu5[y_]); e15 = dd * (f15[ii] - mu15[y_])
        raw15 = dd * f15[ii]
        df = pd.DataFrame({"yr": y_, "day": day[ii], "n": 1, "s5": e5, "s15": e15, "r15": raw15, "srv": rvr[ii], "srvb": rvb[ii], "sx15": x15[ii]})
        g = df.groupby(["yr", "day"], sort=False).sum().reset_index()
        g["pat"] = name; g["sym"] = sym
        rows.append(g)
    return pd.concat(rows, ignore_index=True), unc


def cl_stats(g, col):
    """g: gun bazinda toplamlar (n, col). Ortalama ve gune gore kumelenmis SE."""
    gg = g.groupby("day")[["n", col]].sum()
    N = gg["n"].sum()
    if N < 2:
        return np.nan, np.nan, int(N)
    m = gg[col].sum() / N
    e = gg[col].to_numpy() - m * gg["n"].to_numpy()
    G = len(e)
    se = np.sqrt(G / (G - 1) * np.sum(e ** 2)) / N
    return m, se, int(N)


def cl_diff(ga, gb, col):
    a = ga.groupby("day")[["n", col]].sum(); b = gb.groupby("day")[["n", col]].sum()
    Na, Nb = a["n"].sum(), b["n"].sum()
    ma, mb = a[col].sum() / Na, b[col].sum() / Nb
    ea = (a[col] - ma * a["n"]) / Na; eb = (b[col] - mb * b["n"]) / Nb
    inf = ea.sub(eb, fill_value=0.0).to_numpy()
    G = len(inf)
    se = np.sqrt(G / (G - 1) * np.sum(inf ** 2))
    return ma - mb, se


def main():
    os.makedirs(OUT, exist_ok=True)
    A = []; U = {}
    for s in SYMS:
        g, unc = per_symbol(s)
        A.append(g); U[s] = unc
        print(f"# {s} tamam", file=sys.stderr, flush=True)
    A = pd.concat(A, ignore_index=True)
    A.to_pickle(os.path.join(OUT, "kategori_mum.pkl"))

    nb = {y: sum(U[s][y]["n"] for s in SYMS) for y in (0, 1)}
    symdays = {y: sum(U[s][y]["ndays"] for s in SYMS) for y in (0, 1)}
    urv = {y: sum(U[s][y]["srv"] for s in SYMS) / nb[y] for y in (0, 1)}
    urvb = {y: sum(U[s][y]["srvb"] for s in SYMS) / nb[y] for y in (0, 1)}
    ux15 = {y: sum(U[s][y]["sx15"] for s in SYMS) / nb[y] for y in (0, 1)}
    print("Klasik mum formasyonları, 1 dk, 22 parite. Etki = yön x (ileri getiri - parite-yıl koşulsuz ortalaması), bp.")
    print("t: UTC gününe göre kümelenmiş. %par: parite ortalama 15 dk etkisi > 0 olan parite oranı (en az 20 olaylı pariteler).")
    print("RV/EWMA: ileri 15 dk gerçekleşen oynaklık / sqrt(ewVar x 15), koşulsuza bölünmüş (1,00 = kutu formasyonsuz mumlardaki kadar doğru).")
    print("x norm: ileri 15 dk RV / (sigma_base x sqrt15), koşulsuza bölünmüş.")
    print("x15 ham: sonraki 15 mumda ortalama |r1|/sigma_base (DURUM renk kuralının ölçüsü; SARI >= 1,5, KIRMIZI >= 3,0 iki yılda).")
    for y in (0, 1):
        mu15 = sum(U[s][y]["s15"] for s in SYMS) / nb[y]
        print(f"Koşulsuz {Y[y]}: mum={nb[y]}  ort 15 dk getiri={mu15:+.3f} bp  RV/EWMA ort={urv[y]:.3f}  RV/(sb*sqrt15) ort={urvb[y]:.3f}  x15 ham ort={ux15[y]:.3f}")
    print()

    res = {}
    hdr = f"{'formasyon':42s} {'yıl':4s} {'n':>9s} {'/gün/par':>8s} {'etki5':>6s} {'t5':>5s} {'etki15':>6s} {'t15':>5s} {'ham15':>6s} {'%par':>4s} {'RV/EWMA':>7s} {'x norm':>6s} {'x15ham':>6s}"
    print(hdr)
    for name, kind in PATS:
        P = A[A.pat == name]
        for y in (0, 1):
            g = P[P.yr == y]
            if g["n"].sum() < 2:
                continue
            m5, se5, N = cl_stats(g, "s5")
            m15, se15, _ = cl_stats(g, "s15")
            raw = g["r15"].sum() / N
            ps = g.groupby("sym")[["n", "s15"]].sum()
            ps = ps[ps["n"] >= 20]
            ppos = float(np.mean(ps["s15"] / ps["n"] > 0) * 100) if len(ps) else np.nan
            rv = g["srv"].sum() / N / urv[y]
            rvb = g["srvb"].sum() / N / urvb[y]
            x15m = g["sx15"].sum() / N
            res[(name, y)] = dict(n=N, e5=m5, t5=m5 / se5, e15=m15, t15=m15 / se15, raw=raw, ppos=ppos, npar=len(ps), rv=rv, rvb=rvb, freq=N / symdays[y], x15=x15m)
            r = res[(name, y)]
            print(f"{name:42s} {Y[y]:4s} {N:9d} {r['freq']:8.2f} {m5:+6.2f} {r['t5']:+5.1f} {m15:+6.2f} {r['t15']:+5.1f} {raw:+6.2f} {ppos:4.0f} {rv:7.2f} {rvb:6.2f} {x15m:6.2f}")

    print("\nŞekil, salt hareketten / salt mum yönünden fazlasını katıyor mu? (formasyon - doğal referans, 15 dk etki, gün kümelenmiş t)")
    for name, ref in REFS.items():
        out = [f"{name:28s} vs {ref:40s}"]
        for y in (0, 1):
            a = A[(A.pat == name) & (A.yr == y)]; b = A[(A.pat == ref) & (A.yr == y)]
            d, se = cl_diff(a, b, "s15")
            out.append(f"{Y[y]}: {d:+.2f} bp (t {d / se:+.1f})")
        print("  ".join(out))

    print("\nÖN KAYITLI KURAL (15 dk: iki yılda |etki| >= 3 bp, aynı işaret, |t| >= 2):")
    for name, kind in PATS:
        if kind != "F":
            continue
        a, b = res.get((name, 0)), res.get((name, 1))
        if a is None or b is None:
            print(f"  {name}: veri yok"); continue
        ok = (abs(a["e15"]) >= 3 and abs(b["e15"]) >= 3 and np.sign(a["e15"]) == np.sign(b["e15"])
              and abs(a["t15"]) >= 2 and abs(b["t15"]) >= 2 and np.sign(a["t15"]) == np.sign(a["e15"]) and np.sign(b["t15"]) == np.sign(b["e15"]))
        print(f"  {name:28s} 2025 {a['e15']:+.2f} (t {a['t15']:+.1f})  2026 {b['e15']:+.2f} (t {b['t15']:+.1f})  -> {'BİLGİ VERİCİ' if ok else 'geçmedi'}")


if __name__ == "__main__":
    main()
