"""Aday 3 analizi (makas.py tarafindan cagrilir: python3 -I arastirma/makas.py analiz).

On dogrulama kapisi (Mart 2024), K1 (EDGE), K2 (olay ani makasi), K3 (tick tabani) ve tanimlayici tablolar.
Kurallar makas.py basindaki ON KAYIT bolumundedir; bu dosya kurallari degistirmez, yalnizca uygular.
Karar disi saglamlik olculeri ayrica isaretlenir ("ek").
"""
import os, sys, glob, json, math
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import makas as M  # noqa: E402
from makas_edge import edge  # noqa: E402

NYTZ = "America/New_York"
EVK = ["08:30", "09:30–09:43", "10:00–10:08", "Pazar 18:00–18:07", "FOMC 13:59–14:44"]
EVX = "FOMC 14:00–14:05"
FOMC_VAL = {"2024-03-20"}


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    k = np.isfinite(a) & np.isfinite(b)
    if k.sum() < 5:
        return np.nan
    ra = pd.Series(a[k]).rank().to_numpy(); rb = pd.Series(b[k]).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def ny_fields(ts, fomc):
    t = pd.to_datetime(ts, unit="s", utc=True).tz_convert(NYTZ)
    em = (t.hour * 60 + t.minute).to_numpy()
    dow = t.dayofweek.to_numpy()
    d = np.asarray(t.strftime("%Y-%m-%d"))
    fom = np.isin(d, list(fomc)); hol = np.isin(d, list(M.NYHOL)); dhol = np.isin(d, list(M.DATAHOL))
    wk = dow < 5
    ev = {"08:30": (em == 510) & (dow >= 1) & (dow <= 4) & ~dhol, "09:30–09:43": wk & ~hol & (em >= 570) & (em <= 583), "10:00–10:08": wk & ~dhol & (em >= 600) & (em <= 608), "Pazar 18:00–18:07": (dow == 6) & (em >= 1080) & (em <= 1087), "FOMC 13:59–14:44": fom & (em >= 839) & (em <= 884), EVX: fom & (em >= 840) & (em <= 845)}
    anyev = np.zeros(len(ts), bool)
    for k in EVK:
        anyev |= ev[k]
    return t.hour.to_numpy(), dow, d, ev, anyev


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:.{nd}f}".replace(".", ",")


def olay_oranlari(D, val, base_mask_fn=None):
    """D: dakika tablosu (sym, yil, nyh, dow, ev_*, anyev, val sutunu). Oran = medyan_olay(val / B(nyh)); B = olaysiz medyan."""
    out = {}
    ok = np.isfinite(D[val].to_numpy())
    base = D[ok & ~D["anyev"].to_numpy()].groupby(["sym", "yil", "nyh"])[val].median()
    base2 = D[ok & ~D["anyev"].to_numpy()].assign(gt=lambda x: np.where(x["dow"] == 6, "paz", np.where(x["dow"] < 5, "hi", "cmt"))).groupby(["sym", "yil", "nyh", "gt"])[val].median()
    for k in EVK + [EVX]:
        E = D[ok & D["ev_" + k].to_numpy()]
        if len(E) == 0:
            continue
        b = base.reindex(pd.MultiIndex.from_arrays([E["sym"], E["yil"], E["nyh"]])).to_numpy()
        gt = "paz" if k.startswith("Pazar") else "hi"
        b2 = base2.reindex(pd.MultiIndex.from_arrays([E["sym"], E["yil"], E["nyh"], np.full(len(E), gt)])).to_numpy()
        E = E.assign(r=E[val].to_numpy() / b, r2=E[val].to_numpy() / b2)
        out[k] = E
    return out


# ------------------------------------------------------------------ 1) on dogrulama
def dogrula_analiz():
    files = sorted(glob.glob(f"{M.DG}/*.npz"))
    H, MN = [], []
    meta = {}
    for f in files:
        sym, day = os.path.basename(f)[:-4].rsplit("_", 1)
        z = np.load(f)
        tick = float(z["tick"]); o = z["ohlc"]; n = z["n"]; ss = z["ssum"]; q = z["q_tw"]
        meta[(sym, day)] = [int(x) for x in z["meta"]] + [float(z["age_med"])]
        for h in range(24):
            sl = slice(60 * h, 60 * h + 60)
            nh = n[sl].sum()
            en = z["eff_n"][sl].sum()
            sm = z["smed"][sl]
            H.append(dict(sym=sym, day=day, h=h, n=nh, s=ss[sl].sum() / nh if nh >= 20 else np.nan, s_med=np.nanmedian(sm) if nh >= 20 and np.isfinite(sm).any() else np.nan, q=np.nanmean(q[sl]) if np.isfinite(q[sl]).any() else np.nan, qt=z["qt_sum"][sl].sum() / en if en > 0 else np.nan, e=edge(o[0, sl], o[1, sl], o[2, sl], o[3, sl]) * 1e4, eff=z["eff_sum"][sl].sum() / en if en > 0 else np.nan))
        c = pd.Series(o[3]).ffill().bfill().to_numpy()
        MN.append(pd.DataFrame(dict(sym=sym, day=day, m=np.arange(1440), n=n, ssum=ss, q=q, q1=z["q1_frac"], effs=z["eff_sum"], effn=z["eff_n"], effvw=z["eff_vw"], notl=z["notional"], c=c, tick=tick, ts=int(z["d0"]) // 1000 + 60 * np.arange(1440))))
    H = pd.DataFrame(H); D = pd.concat(MN, ignore_index=True)
    rows = []
    for sym, g in H.groupby("sym"):
        v = g[np.isfinite(g.s) & np.isfinite(g.q) & (g.q > 0)]
        rho = spearman(v.s, v.q); L = float(np.median(v.s / v.q)) if len(v) else np.nan
        ve = g[np.isfinite(g.e) & np.isfinite(g.q) & (g.q > 0)]
        d = D[D.sym == sym]
        qv = d.q.to_numpy()
        vm = g[np.isfinite(g.s_med) & np.isfinite(g.q) & (g.q > 0)]
        vt = g[np.isfinite(g.s) & np.isfinite(g.qt) & (g.qt > 0)]
        ek = dict(ek_rho_medyan=spearman(vm.s_med, vm.q), ek_L_medyan=float(np.median(vm.s_med / vm.q)) if len(vm) else np.nan, ek_rho_islem_q=spearman(vt.s, vt.qt), ek_L_islem_q=float(np.median(vt.s / vt.qt)) if len(vt) else np.nan)
        rows.append(dict(sym=sym, saat=len(v), rho=rho, L=L, gecti=bool(rho >= 0.7 and 0.8 <= L <= 1.25), **ek, rho_edge_q=spearman(ve.e, ve.q), L_edge_q=float(np.median(ve.e / ve.q)) if len(ve) else np.nan, q_yari_med=float(np.nanmedian(qv)) / 2, q_yari_ort=float(np.nanmean(qv)) / 2, s_yari_ort=float(d.ssum.sum() / d.n.sum()) / 2, s_yari_med_dk=float(np.nanmedian(np.where(d.n > 0, d.ssum / d.n.clip(lower=1), np.nan))) / 2, eff_islem=float(d.effs.sum() / d.effn.sum()), eff_hacim=float(d.effvw.sum() / d.notl.sum()), q_1tick=float(np.nanmean(d.q1)), tick_bp=float(np.nanmedian(d.tick / d.c)) * 1e4))
    R = pd.DataFrame(rows).set_index("sym")
    need = math.ceil(0.8 * len(R))
    gate = int(R.gecti.sum()) >= need
    # Olay dakikalari: gercek kotasyonla (q) ve olcutle (s) ayni oran
    hh, dow, dd, ev, anyev = ny_fields(D.ts.to_numpy(), FOMC_VAL)
    D = D.assign(yil="2024", nyh=hh, dow=dow, anyev=anyev, s_m=np.where(D.n > 0, D.ssum / D.n.clip(lower=1), np.nan), **{"ev_" + k: v for k, v in ev.items()})
    oq = olay_oranlari(D, "q"); os_ = olay_oranlari(D, "s_m")
    ev_rows = []
    for k in EVK + [EVX]:
        if k not in oq:
            continue
        a = oq[k].groupby("sym")["r"].median(); b = os_[k].groupby("sym")["r"].median()
        ev_rows.append(dict(olay=k, gun=oq[k].day.nunique(), q_oran_med=float(a.median()), s_oran_med=float(b.median()), q_oran_min=float(a.min()), q_oran_max=float(a.max())))
    EV = pd.DataFrame(ev_rows)
    R.to_csv(f"{M.OUT}/makas_dogrula.csv"); EV.to_csv(f"{M.OUT}/makas_dogrula_olay.csv", index=False)
    return R, gate, need, EV, meta


# ------------------------------------------------------------------ 2) ana orneklem
def ilk_pazar(y, m):
    import datetime as dt
    d = dt.date(y, m, 1)
    while d.weekday() != 6:
        d += dt.timedelta(1)
    return d.isoformat()


def yukle():
    MN = []
    for f in sorted(glob.glob(f"{M.DK}/*.npz")):
        sym, day = os.path.basename(f)[:-4].rsplit("_", 1)
        z = np.load(f)
        c = pd.Series(z["ohlc"][3]).ffill().bfill().to_numpy()
        MN.append(pd.DataFrame(dict(sym=sym, day=day, m=np.arange(1440, dtype=np.int16), n=z["n"].astype(np.int32), ssum=z["ssum"], smed=z["smed"], n1=z["n1"], nle0=z["nle0"], c=c, tick=float(z["tick"]), ts=int(z["d0"]) // 1000 + 60 * np.arange(1440, dtype=np.int64))))
    D = pd.concat(MN, ignore_index=True)
    hh, dow, dd, ev, anyev = ny_fields(D.ts.to_numpy(), set(M.FOMC))
    tu = pd.to_datetime(D.ts.to_numpy(), unit="s", utc=True)
    D["yil"] = D.day.str[:4]
    D["nyh"] = hh; D["dow"] = dow; D["anyev"] = anyev
    for k, v in ev.items():
        D["ev_" + k] = v
    D["uh"] = tu.hour.to_numpy(); D["udow"] = tu.dayofweek.to_numpy()
    D["s_m"] = np.where(D.n > 0, D.ssum / D.n.clip(lower=1), np.nan)
    D["inA"] = D.day.str[8:] == "15"
    ev_days = set(M.FOMC + M.CPI + M.NFP)
    fs = {ilk_pazar(y, m) for y, m in M.months()}
    D["inB"] = D.sym.isin(M.SYM8) & D.day.isin(ev_days)
    D["inE"] = D.sym.isin(M.SYM8) & D.day.isin(fs)
    g = np.full(len(D), "", dtype=object)
    wk = D.udow.to_numpy() < 5
    g[wk & (D.uh.to_numpy() >= 13) & (D.uh.to_numpy() <= 20)] = "ABD"
    g[wk & (D.uh.to_numpy() <= 7)] = "Asya"
    g[~wk] = "HS"
    D["grp"] = g
    return D


def edge_saatlik(D):
    rows = []
    for sym, gs in D.groupby("sym"):
        z = np.load(f"{M.NPZ}/{sym}.npz")
        ts = z["ts"]; o, h, l, c = z["o"], z["h"], z["l"], z["c"]
        for day in gs.day.unique():
            d0 = int(pd.Timestamp(day, tz="UTC").value // 10**9)
            want = d0 + 60 * np.arange(1440)
            ix = np.searchsorted(ts, want)
            ix = np.clip(ix, 0, len(ts) - 1)
            okk = ts[ix] == want
            O = np.where(okk, o[ix], np.nan); Hh = np.where(okk, h[ix], np.nan); Ll = np.where(okk, l[ix], np.nan); C = np.where(okk, c[ix], np.nan)
            for hr in range(24):
                sl = slice(60 * hr, 60 * hr + 60)
                e = edge(O[sl], Hh[sl], Ll[sl], C[sl]) if np.isfinite(C[sl]).sum() >= 30 else np.nan
                rows.append((sym, day, hr, e * 1e4 if np.isfinite(e) else np.nan, int(okk[sl].sum())))
    return pd.DataFrame(rows, columns=["sym", "day", "uh", "edge", "nbar"])


def analiz_ana(gate):
    D = yukle()
    print("dakika satiri:", len(D), "parite-gun:", D.groupby(["sym", "day"]).ngroups, flush=True)
    # saatlik s
    Hs = D.groupby(["sym", "day", "uh"]).agg(n=("n", "sum"), ssum=("ssum", "sum"), yil=("yil", "first"), grp=("grp", "first"), inA=("inA", "first")).reset_index()
    Hs["s"] = np.where(Hs.n >= 20, Hs.ssum / Hs.n.clip(lower=1), np.nan)
    E = edge_saatlik(D)
    Hs = Hs.merge(E, on=["sym", "day", "uh"], how="left")
    Hs.to_csv(f"{M.OUT}/makas_saatlik.csv", index=False)
    res = {}
    # ---------------- K1
    k1 = []
    for (sym, yil), g in Hs.groupby(["sym", "yil"]):
        v = g[np.isfinite(g.s) & np.isfinite(g.edge)]
        rho = spearman(v.edge, v.s)
        L = float(np.median(v.edge / v.s)) if len(v) else np.nan
        k1.append(dict(sym=sym, yil=yil, saat=len(v), rho=rho, L=L, gecti=bool(np.isfinite(rho) and rho >= 0.5 and np.isfinite(L) and 0.67 <= L <= 1.5)))
    K1 = pd.DataFrame(k1)
    K1.to_csv(f"{M.OUT}/makas_k1.csv", index=False)
    k1y = {y: float(g.gecti.mean()) for y, g in K1.groupby("yil")}
    res["K1"] = dict(yil_oran=k1y, tutar=bool(all(v >= 0.8 for v in k1y.values())), rho_med={y: float(g.rho.median()) for y, g in K1.groupby("yil")}, L_med={y: float(g.L.median()) for y, g in K1.groupby("yil")})
    # ---------------- K2
    O = olay_oranlari(D, "s_m")
    k2 = []
    k2s = []
    for k, Ek in O.items():
        for yil, Ey in Ek.groupby("yil"):
            ps = Ey.groupby("sym")["r"].median(); ps2 = Ey.groupby("sym")["r2"].median()
            ndays = Ey.day.nunique()
            # ek: cift agirlikli havuz oran (olay dakikalarinin toplam ortalamasi / ayni saat olaysiz toplam ortalama)
            pool = []
            for sym, Es in Ey.groupby("sym"):
                base = D[(D.sym == sym) & (D.yil == yil) & (~D.anyev) & D.nyh.isin(Es.nyh.unique())]
                bb = base.groupby("nyh").agg(ss=("ssum", "sum"), nn=("n", "sum"))
                bm = (bb.ss / bb.nn).reindex(Es.nyh).to_numpy()
                # olay dakikalarini saat agirligiyla: her olay dakikasi icin s_pool / B_pool(saat)
                pool.append(dict(sym=sym, pool=float(Es.ssum.sum() / Es.n.sum()) / float(np.average(bm, weights=Es.n)) if Es.n.sum() > 0 else np.nan, smed_r=float(np.nanmedian(Es.smed)) / float(np.nanmedian(base.smed)) if np.isfinite(base.smed).any() else np.nan))
            pool = pd.DataFrame(pool).set_index("sym")
            # gun kumelenmis: her olay gununun parite-dakika medyan oraninin log'u
            dm = Ey.groupby("day")["r"].median()
            dm = dm[dm > 0]
            lt = np.log(dm.to_numpy())
            tval = float(lt.mean() / (lt.std(ddof=1) / np.sqrt(len(lt)))) if len(lt) >= 3 and lt.std(ddof=1) > 0 else np.nan
            k2.append(dict(olay=k, yil=yil, gun=ndays, parite=len(ps), oran_med=float(ps.median()), oran_q25=float(ps.quantile(0.25)), oran_q75=float(ps.quantile(0.75)), oran2_med=float(ps2.median()), pool_med=float(pool["pool"].median()), smed_med=float(pool["smed_r"].median()), gun_oran_med=float(dm.median()) if len(dm) else np.nan, gun_ge2=float((dm >= 2).mean()) if len(dm) else np.nan, t_log=tval))
            for sym in ps.index:
                k2s.append(dict(olay=k, yil=yil, sym=sym, oran=float(ps[sym]), oran2=float(ps2[sym]), pool=float(pool.loc[sym, "pool"]), n_dk=int((Ey.sym == sym).sum())))
    K2 = pd.DataFrame(k2); K2s = pd.DataFrame(k2s)
    K2.to_csv(f"{M.OUT}/makas_k2.csv", index=False); K2s.to_csv(f"{M.OUT}/makas_k2_parite.csv", index=False)
    karar = {}
    for k in EVK:
        g = K2[K2.olay == k].set_index("yil")
        if not {"2025", "2026"} <= set(g.index):
            karar[k] = "karar yok (yil eksik)"; continue
        if (g.gun < 3).any():
            karar[k] = "karar yok (<3 gun)"; continue
        karar[k] = "TUTAR" if (g.oran_med >= 2).all() else "tutmaz"
    tutan = [k for k, v in karar.items() if v == "TUTAR"]
    kk = None
    if tutan:
        mn = min(float(K2[(K2.olay == k)].oran_med.min()) for k in tutan)
        kk = math.floor(mn * 2) / 2
    res["K2"] = dict(karar=karar, tutan=tutan, carpan=kk, kapi_gecti=gate)
    # uygulama bicimi secimi (yalnizca bir tip tutarsa anlamli)
    if tutan and kk:
        mask = np.zeros(len(D), bool)
        for k in tutan:
            mask |= D["ev_" + k].to_numpy()
        Ev = D[mask].groupby("sym").agg(ss=("ssum", "sum"), nn=("n", "sum"), tick=("tick", "median"), c=("c", "median"))
        meas = Ev.ss / Ev.nn / 2
        p1 = 1.0 * kk
        p2 = np.maximum(1.0, kk * 0.5 * Ev.tick / Ev.c * 1e4)
        e1 = float(np.median(np.abs(np.log(p1 / meas.clip(lower=1e-6)))))
        e2 = float(np.median(np.abs(np.log(p2 / meas.clip(lower=1e-6)))))
        res["K2"]["bicim_hata"] = dict(i=e1, ii=e2, secim="i" if e1 <= e2 else "ii")
    # ---------------- K3 ve parite tablolari
    rows = []
    for (sym, yil), g in D.groupby(["sym", "yil"]):
        A = g[g.inA]
        okm = g.n > 0
        tick_bp = float(np.median(g.tick / g.c)) * 1e4
        smed_t = np.rint(g.smed[okm] * g.c[okm] / 1e4 / g.tick[okm])
        r = dict(sym=sym, yil=yil, gun_A=A.day.nunique(), tick_bp=tick_bp, yari_tick_bp=tick_bp / 2, cift_1tick=float(g.n1.sum() / g.n.sum()), cift_le0=float(g.nle0.sum() / g.n.sum()), dk_med_1tick=float((smed_t == 1).mean()))
        sa = A.s_m.to_numpy()
        r["yari_med"] = float(np.nanmedian(sa)) / 2
        r["yari_ort"] = float(A.ssum.sum() / A.n.sum()) / 2
        r["pay_yari_gt1bp"] = float(np.mean(sa[np.isfinite(sa)] / 2 > 1.0))
        for gg in ("ABD", "Asya", "HS"):
            r["yari_med_" + gg] = float(np.nanmedian(A.s_m[A.grp == gg])) / 2 if (A.grp == gg).any() else np.nan
        Ha = Hs[(Hs.sym == sym) & (Hs.yil == yil) & Hs.inA]
        r["edge_yari_med"] = float(np.nanmedian(Ha.edge)) / 2 if np.isfinite(Ha.edge).any() else np.nan
        for gg in ("ABD", "Asya", "HS"):
            x = Ha.edge[Ha.grp == gg]
            r["edge_yari_med_" + gg] = float(np.nanmedian(x)) / 2 if np.isfinite(x).any() else np.nan
        # olay dakikalari ve ayni NY saatindeki olaysiz dakikalar (tum orneklem gunleri)
        evm = g.anyev & np.isfinite(g.s_m)
        hrs = g.nyh[evm].unique()
        non = (~g.anyev) & g.nyh.isin(hrs) & np.isfinite(g.s_m)
        r["olay_yari_med"] = float(np.median(g.s_m[evm])) / 2 if evm.any() else np.nan
        r["olaysiz_ayni_saat_yari_med"] = float(np.median(g.s_m[non])) / 2 if non.any() else np.nan
        r["olay_yari_ort"] = float(g.ssum[evm].sum() / g.n[evm].sum()) / 2 if evm.any() else np.nan
        r["olaysiz_ayni_saat_yari_ort"] = float(g.ssum[non].sum() / g.n[non].sum()) / 2 if non.any() else np.nan
        r["olay_pay_yari_gt1bp"] = float(np.mean(g.s_m[evm] / 2 > 1.0)) if evm.any() else np.nan
        rows.append(r)
    P = pd.DataFrame(rows)
    P.to_csv(f"{M.OUT}/makas_parite.csv", index=False)
    res["K3"] = {y: dict(cift_1tick_med=float(g.cift_1tick.median()), dk_med_1tick_med=float(g.dk_med_1tick.median())) for y, g in P.groupby("yil")}
    return res, K1, K2, K2s, P, Hs


def main():
    out = {}
    if glob.glob(f"{M.DG}/*.npz"):
        R, gate, need, EV, meta = dogrula_analiz()
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
        print("=== On dogrulama (Mart 2024) ===")
        print(R.round(3).to_string())
        print(f"kapi: {int(R.gecti.sum())}/{len(R)} parite gecti, gereken {need} -> {'GECTI' if gate else 'GECMEDI'}")
        print(EV.round(2).to_string())
        out["dogrulama"] = dict(gecen=int(R.gecti.sum()), n=len(R), gereken=need, kapi=gate, tablo=R.reset_index().to_dict("records"), olay=EV.to_dict("records"))
    else:
        gate = False
    if glob.glob(f"{M.DK}/*.npz"):
        res, K1, K2, K2s, P, Hs = analiz_ana(gate)
        print("=== K1 ===")
        print(K1.round(3).to_string())
        print(res["K1"])
        print("=== K2 ===")
        print(K2.round(2).to_string())
        print(res["K2"])
        print("=== Parite tablosu ===")
        print(P.round(3).to_string())
        print(res["K3"])
        out.update(res)
    with open(f"{M.OUT}/makas_sonuc.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
