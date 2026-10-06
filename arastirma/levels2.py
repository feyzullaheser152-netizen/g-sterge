"""Madde 3: Haftalik ve aylik seviyelerin testi (22 Binance paritesi, 2025 / 2026).
Seviyeler: haftalik P, R1, S1, R2, S2, onceki hafta yuksek/dusuk; aylik P, R1, S1, onceki ay yuksek/dusuk.
Haftalar Pazartesi 00:00 UTC'de, aylar ayin 1'i 00:00 UTC'de baslar (TradingView kripto haftalik/aylik mumlari).
Kontrol (placebo): her gercek seviye icin ayni donemde, seviyenin %0,3-%1,5 yakinina (rastgele yon) kaydirilmis 4 sahte seviye.
Olay: donem icinde seviyeye ilk temas (yukaridan inerek = destek, asagidan cikarak = direnc).
Olcum (ilk temastan itibaren): 15 dk sonra seviyeden geri itilme (bp, + = tuttu); tutma: 15 dk icinde kapanisin
seviyenin 0,5 sigma otesine gecmemesi; oynaklik: sonraki 15 dk gerceklesen / EWMA tahmini.
Istatistik: fark (seviye - placebo), olay haftasina gore kumelenmis standart hata, t.
On kayitli kural: bir seviye ancak 2025 VE 2026'da tepki farki >= +3 bp, t >= 2 ve tutma farki > 0 ise eklenir."""
import glob, os, sys
import numpy as np, pandas as pd

SRC = "../data_bn/npz"
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
NPL = 4
rng_ = np.random.default_rng(23)


def lag(x, k=1):
    o = np.full(len(x), np.nan); o[k:] = x[:-k]; return o


def measure(name, kind, ix, lvl, sgn, c, ew, rvf, ts, sym):
    ok = (ix > 3000) & (ix < len(c) - H - 1) & np.isfinite(lvl)
    ix, lvl, sgn = ix[ok], lvl[ok], sgn[ok]
    if len(ix) == 0:
        return None
    react = np.log(c[ix + H] / lvl) * 1e4 * sgn
    sig = np.sqrt(ew[ix] * H)
    path = np.stack([c[ix + k] for k in range(1, H + 1)], 1)
    beyond = np.any(sgn[:, None] * np.log(path / lvl[:, None]) < -0.5 * sig[:, None], 1)
    vol = rvf[ix] / sig
    wk = (ts[ix] - 345600) // 604800  # Pazartesi baslangicli hafta numarasi (kumeleme icin)
    return pd.DataFrame({"sym": sym, "lvl": name, "kind": kind, "part": np.where(ts[ix] < CUT, "2025", "2026"), "react": react, "hold": (~beyond).astype(float), "vol": vol, "wk": wk})


def first_touch(key, cond):
    dfh = pd.DataFrame({"d": key, "c": cond, "i": np.arange(len(cond))})
    return dfh[dfh.c].groupby("d").i.first().to_numpy()


def level_events(name, kind, LL, key, c, h, l, ew, rvf, ts, sym, out):
    same = key == np.r_[key[:1], key[:-1]]
    sup = np.nan_to_num((lag(l) > lag(LL)) & (l <= LL)).astype(bool) & same
    res = np.nan_to_num((lag(h) < lag(LL)) & (h >= LL)).astype(bool) & same
    for cond, sg in ((sup, 1), (res, -1)):
        ix = first_touch(key, cond)
        if len(ix):
            m = measure(name, kind, ix, LL[ix], np.full(len(ix), sg), c, ew, rvf, ts, sym)
            if m is not None:
                out.append(m)


def cl_diff(a, b, ga, gb):
    """Ortalama farki ve kume-saglam standart hata (etki fonksiyonu ile)."""
    ma, mb = a.mean(), b.mean()
    psi = np.r_[(a - ma) / len(a), -(b - mb) / len(b)]
    g = np.r_[ga, gb]
    s = pd.Series(psi).groupby(g).sum().to_numpy()
    se = np.sqrt((s ** 2).sum())
    return ma - mb, se


def main():
    out = []
    for f in sorted(glob.glob(f"{SRC}/*.npz"))[:int(os.environ.get("NSYM", "99"))]:
        s = os.path.basename(f)[:-4]
        z = np.load(f)
        h, l, c, ts = z["h"], z["l"], z["c"], z["ts"]
        t = pd.to_datetime(ts, unit="s", utc=True)
        lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
        ew = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
        rvf = np.sqrt(pd.Series(r * r)[::-1].rolling(H).sum()[::-1].to_numpy()); rvf = np.r_[rvf[1:], np.nan]
        tn = t.tz_localize(None)
        for per, rule in (("Haftalık", "W-SUN"), ("Aylık", "M")):
            key = np.asarray(tn.to_period(rule).astype(str))
            gH = pd.Series(h).groupby(key).max(); gL = pd.Series(l).groupby(key).min(); gC = pd.Series(c).groupby(key).last()
            order = pd.Series(np.arange(len(c))).groupby(key).first().sort_values().index
            pH, pL, pC = (x.reindex(order).shift(1) for x in (gH, gL, gC))
            P = (pH + pL + pC) / 3
            lv = {"P": P, "R1": 2 * P - pL, "S1": 2 * P - pH, "R2": P + (pH - pL), "S2": P - (pH - pL), "önceki yüksek": pH, "önceki düşük": pL}
            if per == "Aylık":
                lv = {k: lv[k] for k in ("P", "R1", "S1", "önceki yüksek", "önceki düşük")}
            for nm, ser in lv.items():
                name = f"{per} {nm}"
                LL = ser.reindex(key).to_numpy()
                level_events(name, "seviye", LL, key, c, h, l, ew, rvf, ts, s, out)
                for j in range(NPL):
                    mag = rng_.uniform(0.003, 0.015, len(order)) * rng_.choice([-1, 1], len(order))
                    off = pd.Series(mag, index=order).reindex(key).to_numpy()
                    level_events(name, "placebo", LL * (1 + off), key, c, h, l, ew, rvf, ts, s, out)
        print("tamam", s, file=sys.stderr, flush=True)
    D = pd.concat([d for d in out if d is not None])
    D.to_pickle("levels2.pkl")
    rows = []
    for (name, part), g in D.groupby(["lvl", "part"]):
        a, b = g[g.kind == "seviye"], g[g.kind == "placebo"]
        if len(a) < 30 or len(b) < 30:
            continue
        dr, ser = cl_diff(a.react.to_numpy(), b.react.to_numpy(), a.wk.to_numpy(), b.wk.to_numpy())
        dh, seh = cl_diff(a.hold.to_numpy(), b.hold.to_numpy(), a.wk.to_numpy(), b.wk.to_numpy())
        rows.append({"seviye": name, "yıl": part, "n_sev": len(a), "n_plc": len(b), "tepki_sev": a.react.mean(), "tepki_plc": b.react.mean(), "fark_bp": dr, "t": dr / ser, "tutma_fark_puan": dh * 100, "t_tutma": dh / seh, "oyn_sev": a.vol.median(), "oyn_plc": b.vol.median()})
    R = pd.DataFrame(rows)
    print("İlk temas sonrası 15 dk; fark = seviye - placebo (hafta kümelenmiş t)")
    print(R.round(2).to_string(index=False))
    # parite bazinda tutarlilik: farkin pozitif oldugu parite orani
    print("\nParite bazında tepki farkı > 0 oranı (%)")
    pr = D.groupby(["lvl", "part", "sym", "kind"]).react.mean().unstack("kind")
    pr = (pr["seviye"] - pr["placebo"]).gt(0).groupby(level=[0, 1]).mean().unstack("part") * 100
    print(pr.round(0).to_string())


main()
