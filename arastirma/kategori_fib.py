"""Fibonacci geri cekilme seviyeleri, yakin-placebo yontemiyle (levels2.py ile ayni olcum; kod yeniden yazildi).
22 Binance USDT-M paritesi, 1 dk; 2025 kesif, 2026 dogrulama. Her paritenin ilk 3000 mumu atlanir.

Seviyeler: onceki UTC gununun (ve onceki haftanin; hafta Pazartesi 00:00 UTC) yuksek H / dusuk L degerinden
  0,236 / 0,382 / 0,5 / 0,618 / 0,786 geri cekilmeleri; donem boyunca sabit.
  Geri cekilme yonu, cizimdeki standart kullanim gibi onceki donemin salinim yonune gore:
    dusuk yuksekten ONCE olustuysa (yukari salinim): seviye = H - f x (H-L)
    yuksek dusukten once olustuysa (asagi salinim): seviye = L + f x (H-L)
    (ayni mumdaysa donemin kapanis > acilis ise yukari sayilir)
  Onceki donem eksikse (veri basindaki yarim gun/hafta) seviye yok.
  Referans (yontem kontrolu, BULGULAR 9a ile karsilastirma): onceki donem yuksek ve dusuk.
Olay: donem icinde seviyeye ilk temas; yukaridan (l[1] > seviye, l <= seviye) = destek (isaret +1),
  asagidan (h[1] < seviye, h >= seviye) = direnc (isaret -1); her yon icin donem basina ilk temas.
Olcum: tepki = isaret x ln(c[i+15]/seviye) x 1e4 (bp, + = seviyeden geri itildi);
  tutma = sonraki 15 mumda hicbir kapanis seviyenin 0,5 x sqrt(15 x ewVar) otesine gecmedi;
  oynaklik = ileri 15 dk RV / sqrt(15 x ewVar) (medyan).
Kontrol: her gercek seviye ve donem icin seviye x (1 +- U(0,003, 0,015)) (rastgele yon) 4 sahte seviye; donem boyunca sabit.
  Ana sonuc tohum 0; saglamlik icin 5 tohum (her biri 4 placebo).
t: olay haftasina (Pazartesi baslangicli) gore kumelenmis SE (fark icin etki fonksiyonu).
ON KAYITLI KURAL: seviye ancak 2025 VE 2026'da tepki farki >= +3 bp, t >= 2 ve tutma farki > 0 ise sansdan iyi."""
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
NPL = 4
NSEED = 5
FIBS = [0.236, 0.382, 0.5, 0.618, 0.786]
PERS = [("Gün", 1440), ("Hafta", 10080)]
LNAMES = []
for p, _ in PERS:
    for f in FIBS:
        LNAMES.append(f"{p} Fib {f:.3f}".replace(".", ","))
    LNAMES.append(f"{p} ref: önceki yüksek")
    LNAMES.append(f"{p} ref: önceki düşük")
LCODE = {nm: i for i, nm in enumerate(LNAMES)}


def per_symbol(si, sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, o, h, l, c = z["ts"], z["o"].astype(float), z["h"].astype(float), z["l"].astype(float), z["c"].astype(float)
    n = len(ts)
    lc = np.log(c)
    r1z = np.r_[0.0, np.diff(lc)]
    ew = pd.Series(r1z * r1z).ewm(span=30, adjust=False).mean().to_numpy()
    cs = np.concatenate([[0.0], np.cumsum(r1z * r1z)])
    rvf = np.full(n, np.nan); rvf[:n - H] = np.sqrt(cs[1 + H:n + 1] - cs[1:n + 1 - H])
    wkall = (ts - 345600) // 604800
    out = []

    def measure(ix, lvl, sgn):
        ok = (ix >= WARM) & (ix < n - H - 1) & np.isfinite(lvl)
        ix, lvl, sgn = ix[ok], lvl[ok], sgn[ok]
        if len(ix) == 0:
            return None
        react = sgn * np.log(c[ix + H] / lvl) * 1e4
        sig = np.sqrt(ew[ix] * H)
        path = c[ix[:, None] + np.arange(1, H + 1)[None, :]]
        beyond = np.any(sgn[:, None] * np.log(path / lvl[:, None]) < -0.5 * sig[:, None], axis=1)
        return dict(ix=ix, react=react, hold=(~beyond).astype(np.float32), vol=rvf[ix] / sig, side=sgn)

    def level_events(code, kind, seed, LL, key):
        same = np.r_[False, key[1:] == key[:-1]]
        Lp = np.r_[np.nan, LL[:-1]]
        lp = np.r_[np.nan, l[:-1]]; hp = np.r_[np.nan, h[:-1]]
        with np.errstate(invalid="ignore"):
            sup = (lp > Lp) & (l <= LL) & same
            res = (hp < Lp) & (h >= LL) & same
        for cond, sg in ((sup, 1.0), (res, -1.0)):
            ii = np.where(cond)[0]
            if len(ii) == 0:
                continue
            _, fi = np.unique(key[ii], return_index=True)
            ix = ii[fi]
            m = measure(ix, LL[ix], np.full(len(ix), sg))
            if m is None:
                continue
            k = len(m["ix"])
            out.append(pd.DataFrame({"sym": np.int16(si), "lvl": np.int16(code), "kind": np.int8(kind), "seed": np.int8(seed),
                                     "yr": (ts[m["ix"]] >= CUT).astype(np.int8), "wk": wkall[m["ix"]].astype(np.int32),
                                     "side": m["side"].astype(np.int8), "react": m["react"].astype(np.float32),
                                     "hold": m["hold"], "vol": m["vol"].astype(np.float32)}, index=np.arange(k)))

    for pi, (pname, plen) in enumerate(PERS):
        key = ts // 86400 if pname == "Gün" else (ts - 345600) // 604800
        uk, st = np.unique(key, return_index=True)
        en = np.r_[st[1:], n]
        ln = en - st
        PH = np.maximum.reduceat(h, st); PL = np.minimum.reduceat(l, st)
        iH = np.array([np.argmax(h[a:b]) for a, b in zip(st, en)])
        iL = np.array([np.argmin(l[a:b]) for a, b in zip(st, en)])
        upsw = (iL < iH) | ((iL == iH) & (c[en - 1] > o[st]))
        full = ln == plen
        # onceki donem degerleri
        prevok = np.r_[False, (uk[1:] - uk[:-1] == 1) & full[:-1]]
        pH = np.r_[np.nan, PH[:-1]]; pL = np.r_[np.nan, PL[:-1]]; pup = np.r_[False, upsw[:-1]]
        pH = np.where(prevok, pH, np.nan); pL = np.where(prevok, pL, np.nan)
        R = pH - pL
        lv = {}
        for f in FIBS:
            lv[f"{pname} Fib {f:.3f}".replace(".", ",")] = np.where(pup, pH - f * R, pL + f * R)
        lv[f"{pname} ref: önceki yüksek"] = pH
        lv[f"{pname} ref: önceki düşük"] = pL
        for nm, per in lv.items():
            code = LCODE[nm]
            LL = np.repeat(per, ln)
            level_events(code, 0, 0, LL, key)
            for sd in range(NSEED):
                rg = np.random.default_rng([56, si, code, sd])
                for j in range(NPL):
                    mag = rg.uniform(0.003, 0.015, len(st)) * rg.choice([-1.0, 1.0], len(st))
                    level_events(code, 1, sd, LL * (1 + np.repeat(mag, ln)), key)
        # salinim yonu istatistigi
        print(f"# {sym} {pname}: dönem={len(st)} yukarı salınım oranı={np.mean(upsw[full]):.2f} ort aralık={np.nanmean(R / pL) * 100:.2f}%",
              file=sys.stderr, flush=True)
    return pd.concat(out, ignore_index=True)


def cl_diff(va, ca, vb, cb):
    va = np.asarray(va, float); vb = np.asarray(vb, float)
    ma, mb = va.mean(), vb.mean()
    ea = pd.Series((va - ma) / len(va)).groupby(np.asarray(ca)).sum()
    eb = pd.Series((vb - mb) / len(vb)).groupby(np.asarray(cb)).sum()
    inf = ea.sub(eb, fill_value=0.0).to_numpy()
    G = len(inf)
    se = np.sqrt(G / (G - 1) * np.sum(inf ** 2))
    return ma - mb, se


def summarize(a, b):
    dr, ser = cl_diff(a.react, a.wk, b.react, b.wk)
    dh, seh = cl_diff(a.hold, a.wk, b.hold, b.wk)
    pa = a.groupby("sym").react.mean(); pb = b.groupby("sym").react.mean()
    pp = (pa - pb.reindex(pa.index)).dropna()
    return dict(n_s=len(a), n_p=len(b), r_s=a.react.mean(), r_p=b.react.mean(), d=dr, t=dr / ser, dh=dh * 100, th=dh / seh,
                v_s=float(np.median(a.vol)), v_p=float(np.median(b.vol)), ppos=float(np.mean(pp > 0) * 100), npar=len(pp))


def passes(r0, r1):
    return r0["d"] >= 3 and r0["t"] >= 2 and r0["dh"] > 0 and r1["d"] >= 3 and r1["t"] >= 2 and r1["dh"] > 0


def main():
    os.makedirs(OUT, exist_ok=True)
    D = []
    for si, s in enumerate(SYMS):
        D.append(per_symbol(si, s))
        print(f"# {s} tamam", file=sys.stderr, flush=True)
    D = pd.concat(D, ignore_index=True)
    D.to_pickle(os.path.join(OUT, "kategori_fib.pkl"))
    Y = {0: "2025", 1: "2026"}
    print("Fibonacci geri çekilmeleri: ilk temas sonrası 15 dk; fark = seviye - yakın placebo (tohum 0, 4 placebo); t hafta kümelenmiş.")
    print("tepki bp (+ = seviyeden geri itildi); tutma farkı puan; oyn = ileri 15 dk RV / EWMA tahmini (medyan); %par = fark > 0 olan parite oranı.\n")
    real = D[D.kind == 0]; plc = D[D.kind == 1]
    groups = [(nm, [LCODE[nm]]) for nm in LNAMES]
    for p, _ in PERS:
        groups.append((f"{p} Fib (5 oran birlikte)", [LCODE[f"{p} Fib {f:.3f}".replace(".", ",")] for f in FIBS]))
    hdr = f"{'seviye':30s} {'yıl':4s} {'n_sev':>6s} {'n_plc':>7s} {'tepki_s':>7s} {'tepki_p':>7s} {'fark':>6s} {'t':>5s} {'tutma_f':>7s} {'t_tut':>5s} {'oyn_s':>5s} {'oyn_p':>5s} {'%par':>4s}"
    print(hdr)
    RES = {}
    for nm, codes in groups:
        for y in (0, 1):
            a = real[real.lvl.isin(codes) & (real.yr == y)]
            b = plc[plc.lvl.isin(codes) & (plc.yr == y) & (plc.seed == 0)]
            r = summarize(a, b)
            RES[(nm, y)] = r
            print(f"{nm:30s} {Y[y]:4s} {r['n_s']:6d} {r['n_p']:7d} {r['r_s']:+7.2f} {r['r_p']:+7.2f} {r['d']:+6.2f} {r['t']:+5.1f} {r['dh']:+7.2f} {r['th']:+5.1f} {r['v_s']:5.2f} {r['v_p']:5.2f} {r['ppos']:4.0f}")

    print("\nDestek / direnç ayrımı (5 oran birlikte, tohum 0):")
    for p, _ in PERS:
        codes = [LCODE[f"{p} Fib {f:.3f}".replace(".", ",")] for f in FIBS]
        for sd_, sdn in ((1, "destek (yukarıdan temas)"), (-1, "direnç (aşağıdan temas)")):
            line = [f"  {p} {sdn:26s}"]
            for y in (0, 1):
                a = real[real.lvl.isin(codes) & (real.yr == y) & (real.side == sd_)]
                b = plc[plc.lvl.isin(codes) & (plc.yr == y) & (plc.seed == 0) & (plc.side == sd_)]
                r = summarize(a, b)
                line.append(f"{Y[y]}: n {r['n_s']}  fark {r['d']:+.2f} (t {r['t']:+.1f})  tutma {r['dh']:+.2f} (t {r['th']:+.1f})")
            print("  ".join(line))

    print("\nTohum sağlamlığı (5 tohum x 4 placebo): fark aralığı ve kuralı geçen tohum sayısı")
    for nm, codes in groups:
        ds = {0: [], 1: []}; npass = 0
        for sd in range(NSEED):
            rr = {}
            for y in (0, 1):
                a = real[real.lvl.isin(codes) & (real.yr == y)]
                b = plc[plc.lvl.isin(codes) & (plc.yr == y) & (plc.seed == sd)]
                rr[y] = summarize(a, b)
                ds[y].append((rr[y]["d"], rr[y]["t"]))
            npass += passes(rr[0], rr[1])
        print(f"  {nm:30s} 2025 fark {min(d for d, _ in ds[0]):+.2f}..{max(d for d, _ in ds[0]):+.2f} (t {min(t for _, t in ds[0]):+.1f}..{max(t for _, t in ds[0]):+.1f})"
              f"  2026 fark {min(d for d, _ in ds[1]):+.2f}..{max(d for d, _ in ds[1]):+.2f} (t {min(t for _, t in ds[1]):+.1f}..{max(t for _, t in ds[1]):+.1f})  geçen tohum {npass}/{NSEED}")

    print("\nÖN KAYITLI KURAL (iki yılda fark >= +3 bp, t >= 2, tutma farkı > 0; tohum 0):")
    for nm, _ in groups:
        r0, r1 = RES[(nm, 0)], RES[(nm, 1)]
        print(f"  {nm:30s} -> {'ŞANSTAN İYİ' if passes(r0, r1) else 'geçmedi'}")


if __name__ == "__main__":
    main()
