import glob, os, zipfile, io, numpy as np, pandas as pd
SRC = "../data_bn"; CUT = pd.Timestamp("2026-01-01")
rows = []
for s in sorted({os.path.basename(f).split("-metrics-")[0] for f in glob.glob(f"{SRC}/metrics/*.zip")}):
    parts = []
    for f in sorted(glob.glob(f"{SRC}/metrics/{s}-metrics-*.zip")):
        with zipfile.ZipFile(f) as z: parts.append(pd.read_csv(io.BytesIO(z.read(z.namelist()[0]))))
    m = pd.concat(parts); m["t"] = pd.to_datetime(m["create_time"]); m = m.drop_duplicates("t").set_index("t").sort_index().asfreq("5min")
    k = np.load(f"{SRC}/npz/{s}.npz")
    px = pd.Series(k["c"], index=pd.to_datetime(k["ts"], unit="s")).resample("5min").last()
    df = pd.DataFrame({"ls": m["count_long_short_ratio"], "p": px}).dropna()
    df = df[df.ls > 0]
    lp = np.log(df.p.to_numpy())
    lspct = pd.Series(df.ls.to_numpy()).rolling(288 * 7, min_periods=288).rank(pct=True).to_numpy()
    for h in (6, 12, 48):
        f = np.r_[(lp[h:] - lp[:-h]) * 1e4, np.full(h, np.nan)]
        part = np.where(df.index < CUT, "2025", "2026")
        for p in ("2025", "2026"):
            sel = part == p
            base = np.nanmean(f[sel][::12])
            lo = np.nanmean(f[sel & (lspct <= 0.05)][::12]); hi = np.nanmean(f[sel & (lspct >= 0.95)][::12])
            rows.append(dict(sym=s, part=p, h=h * 5, base=base, crowd_short_long=lo - base, crowd_long_short=-(hi - base)))
R = pd.DataFrame(rows)
print("Piyasa yönünden arındırılmış fazla getiri (bp) = koşullu getiri - aynı parite/yıl ortalaması")
print(R.groupby(["part", "h"])[["base", "crowd_short_long", "crowd_long_short"]].mean().round(1).to_string())
print("\nFazla getirisi pozitif parite oranı (%):")
print((R.assign(a=R.crowd_short_long > 0, b=R.crowd_long_short > 0).groupby(["part", "h"])[["a", "b"]].mean() * 100).round(0).to_string())
