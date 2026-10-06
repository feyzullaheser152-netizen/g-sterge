import glob, os, zipfile, io, numpy as np, pandas as pd
SRC = "../data_bn"
CUT = pd.Timestamp("2026-01-01")
def thin(ix, gap):
    keep, last = [], -10**9
    for i in ix:
        if i - last >= gap: keep.append(i); last = i
    return np.array(keep, int)
out = []
for s in sorted({os.path.basename(f).split("-metrics-")[0] for f in glob.glob(f"{SRC}/metrics/*.zip")}):
    parts = []
    for f in sorted(glob.glob(f"{SRC}/metrics/{s}-metrics-*.zip")):
        with zipfile.ZipFile(f) as z:
            parts.append(pd.read_csv(io.BytesIO(z.read(z.namelist()[0]))))
    m = pd.concat(parts)
    m["t"] = pd.to_datetime(m["create_time"])
    m = m.drop_duplicates("t").set_index("t").sort_index().asfreq("5min")
    k = np.load(f"{SRC}/npz/{s}.npz")
    px = pd.Series(k["c"], index=pd.to_datetime(k["ts"], unit="s")).resample("5min").last()
    df = pd.DataFrame({"oi": m["sum_open_interest"], "ls": m["count_long_short_ratio"], "p": px}).dropna()
    lp = np.log(df.p.to_numpy()); loi = np.log(df.oi.to_numpy()); ls = df.ls.to_numpy()
    n = len(df)
    doi = np.r_[np.nan, np.diff(loi)]; dp = np.r_[np.nan, np.diff(lp)]
    sdoi = pd.Series(doi).rolling(288 * 3, min_periods=288).std().to_numpy()
    sdp = pd.Series(dp).rolling(288 * 3, min_periods=288).std().to_numpy()
    zoi, zp = doi / sdoi, dp / sdp
    lspct = pd.Series(ls).rolling(288 * 7, min_periods=288).rank(pct=True).to_numpy()
    fwd = {h: np.r_[(lp[h:] - lp[:-h]) * 1e4, np.full(h, np.nan)] for h in (6, 12, 48)}  # 30dk,60dk,4s
    part = np.where(df.index < CUT, "2025", "2026")
    H = {
        "H7 OI ani artış + fiyat yukarı -> DEVAM (long)": ((zoi >= 3) & (zp >= 2), 1),
        "H7 OI ani artış + fiyat aşağı -> DEVAM (short)": ((zoi >= 3) & (zp <= -2), -1),
        "H8 OI ani düşüş + fiyat sert düştü -> DÖNÜŞ (long)": ((zoi <= -3) & (zp <= -2), 1),
        "H8 OI ani düşüş + fiyat sert çıktı -> DÖNÜŞ (short)": ((zoi <= -3) & (zp >= 2), -1),
        "H9 Kalabalık long (L/S oranı %95 dilim) -> SHORT": (lspct >= 0.95, -1),
        "H9 Kalabalık short (L/S oranı %5 dilim) -> LONG": (lspct <= 0.05, 1),
    }
    for name, (mask, sg) in H.items():
        for i in thin(np.flatnonzero(np.nan_to_num(mask).astype(bool)), 12):
            out.append(dict(sym=s, hyp=name, part=part[i], f30=fwd[6][i] * sg, f60=fwd[12][i] * sg, f240=fwd[48][i] * sg))
R = pd.DataFrame(out)
print("İleri getiri işlem yönünde (bp); % = ortalaması pozitif parite oranı\n")
for hyp, g in R.groupby("hyp", sort=False):
    line = []
    for part, gp in g.groupby("part"):
        cells = []
        for col in ("f30", "f60", "f240"):
            x = gp[col].dropna(); t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else 0
            pos = (gp.groupby("sym")[col].mean() > 0).mean() * 100
            cells.append(f"{col[1:]}dk {x.mean():+6.1f}(t{t:+.1f},%{pos:.0f})")
        line.append(f"{part} n={len(gp):5d} " + " ".join(cells))
    print(hyp); [print("   " + l) for l in line]
