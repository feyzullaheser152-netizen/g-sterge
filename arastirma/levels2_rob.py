"""Madde 3 saglamlik: haftalik P, onceki hafta yuksek/dusuk; farkli placebo mesafe bantlari ve eski kontrol (hafta acilisi +-%1)."""
import os, sys
sys.argv = ["x"]
exec(open("levels2.py").read().split("def main")[0])
import glob
rng_ = np.random.default_rng(5)
BANDS = {"yakın %0,3-0,75": (0.003, 0.0075), "orta %0,75-1,5": (0.0075, 0.015), "uzak %1,5-3": (0.015, 0.03)}
out = []
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]
    z = np.load(f)
    h, l, c, ts = z["h"], z["l"], z["c"], z["ts"]
    t = pd.to_datetime(ts, unit="s", utc=True)
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    rvf = np.sqrt(pd.Series(r * r)[::-1].rolling(H).sum()[::-1].to_numpy()); rvf = np.r_[rvf[1:], np.nan]
    key = np.asarray(t.tz_localize(None).to_period("W-SUN").astype(str))
    gH = pd.Series(h).groupby(key).max(); gL = pd.Series(l).groupby(key).min(); gC = pd.Series(c).groupby(key).last()
    order = pd.Series(np.arange(len(c))).groupby(key).first().sort_values().index
    pH, pL, pC = (x.reindex(order).shift(1) for x in (gH, gL, gC))
    P = (pH + pL + pC) / 3
    ref = pd.Series(c).groupby(key).first().reindex(key).to_numpy()
    for nm, ser in {"P": P, "önceki yüksek": pH, "önceki düşük": pL}.items():
        LL = ser.reindex(key).to_numpy()
        level_events(nm, "seviye", LL, key, c, h, l, ew, rvf, ts, s, out)
        for bn, (a, b) in BANDS.items():
            for j in range(NPL):
                mag = rng_.uniform(a, b, len(order)) * rng_.choice([-1, 1], len(order))
                level_events(nm, bn, LL * (1 + pd.Series(mag, index=order).reindex(key).to_numpy()), key, c, h, l, ew, rvf, ts, s, out)
        if nm == "P":
            for j in range(NPL):
                off = pd.Series(rng_.uniform(-0.01, 0.01, len(order)), index=order).reindex(key).to_numpy()
                level_events(nm, "eski: açılış ±%1", ref * (1 + off), key, c, h, l, ew, rvf, ts, s, out)
    print("tamam", s, file=sys.stderr, flush=True)
D = pd.concat([d for d in out if d is not None])
D.to_pickle("levels2_rob.pkl")
rows = []
for sub, DD in (("tüm temaslar", D),):
    for (name, part), g in DD.groupby(["lvl", "part"]):
        a = g[g.kind == "seviye"]
        for kind in [k for k in g.kind.unique() if k != "seviye"]:
            b = g[g.kind == kind]
            dr, ser = cl_diff(a.react.to_numpy(), b.react.to_numpy(), a.wk.to_numpy(), b.wk.to_numpy())
            dh, seh = cl_diff(a.hold.to_numpy(), b.hold.to_numpy(), a.wk.to_numpy(), b.wk.to_numpy())
            rows.append({"seviye": name, "yıl": part, "kontrol": kind, "n_sev": len(a), "n_kont": len(b), "tepki_sev": a.react.mean(), "tepki_kont": b.react.mean(), "fark_bp": dr, "t": dr / ser, "tutma_fark": dh * 100, "t_tutma": dh / seh})
print(pd.DataFrame(rows).round(2).to_string(index=False))
