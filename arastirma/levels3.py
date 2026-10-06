"""Grafikteki gunluk cizgilerin ayni yakin-placebo yontemiyle testi: onceki gun yuksek/dusuk (UTC gunu) ve Asya seansi (00-08 UTC)
yuksek/dusuk (08:00-24:00 UTC arasinda gecerli). Placebo: seviye * (1 +- U(%0,3, %1,5)), 4 adet. Olcumler levels2.py ile ayni."""
import os, sys, glob
sys.argv = ["x"]
exec(open("levels2.py").read().split("def main")[0])
rng_ = np.random.default_rng(9)
out = []
for f in sorted(glob.glob(f"{SRC}/*.npz")):
    s = os.path.basename(f)[:-4]
    z = np.load(f)
    h, l, c, ts = z["h"], z["l"], z["c"], z["ts"]
    t = pd.to_datetime(ts, unit="s", utc=True)
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    rvf = np.sqrt(pd.Series(r * r)[::-1].rolling(H).sum()[::-1].to_numpy()); rvf = np.r_[rvf[1:], np.nan]
    day = np.asarray(t.floor("D").astype(str))
    hr = t.hour.to_numpy()
    order = pd.Series(np.arange(len(c))).groupby(day).first().sort_values().index
    dH = pd.Series(h).groupby(day).max().reindex(order); dL = pd.Series(l).groupby(day).min().reindex(order)
    asia = hr < 8
    aH = pd.Series(np.where(asia, h, np.nan)).groupby(day).max().reindex(order); aL = pd.Series(np.where(asia, l, np.nan)).groupby(day).min().reindex(order)
    lv = {"Önceki gün yüksek": dH.shift(1).reindex(day).to_numpy(), "Önceki gün düşük": dL.shift(1).reindex(day).to_numpy(), "Asya yüksek": np.where(asia, np.nan, aH.reindex(day).to_numpy()), "Asya düşük": np.where(asia, np.nan, aL.reindex(day).to_numpy())}
    for nm, LL in lv.items():
        level_events(nm, "seviye", LL, day, c, h, l, ew, rvf, ts, s, out)
        for j in range(NPL):
            mag = rng_.uniform(0.003, 0.015, len(order)) * rng_.choice([-1, 1], len(order))
            level_events(nm, "placebo", LL * (1 + pd.Series(mag, index=order).reindex(day).to_numpy()), day, c, h, l, ew, rvf, ts, s, out)
    print("tamam", s, file=sys.stderr, flush=True)
D = pd.concat([d for d in out if d is not None])
D.to_pickle("levels3.pkl")
rows = []
for (name, part), g in D.groupby(["lvl", "part"]):
    a, b = g[g.kind == "seviye"], g[g.kind == "placebo"]
    dr, ser = cl_diff(a.react.to_numpy(), b.react.to_numpy(), a.wk.to_numpy(), b.wk.to_numpy())
    dh, seh = cl_diff(a.hold.to_numpy(), b.hold.to_numpy(), a.wk.to_numpy(), b.wk.to_numpy())
    rows.append({"seviye": name, "yıl": part, "n_sev": len(a), "n_plc": len(b), "tepki_sev": a.react.mean(), "tepki_plc": b.react.mean(), "fark_bp": dr, "t": dr / ser, "tutma_fark": dh * 100, "t_tutma": dh / seh, "oyn_sev": a.vol.median(), "oyn_plc": b.vol.median()})
print(pd.DataFrame(rows).round(2).to_string(index=False))
pr = D.groupby(["lvl", "part", "sym", "kind"]).react.mean().unstack("kind")
print((pr["seviye"] - pr["placebo"]).gt(0).groupby(level=[0, 1]).mean().unstack("part").mul(100).round(0).to_string())
