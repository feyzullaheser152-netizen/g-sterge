import glob, os, zipfile, io, numpy as np, pandas as pd
SRC = "../data_bn"
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
rows = []
for npz in sorted(glob.glob(f"{SRC}/npz/*.npz")):
    s = os.path.basename(npz)[:-4]
    z = np.load(npz); ts, c = z["ts"], z["c"]
    fr = []
    for f in sorted(glob.glob(f"{SRC}/fund/{s}-fundingRate-*.zip")):
        with zipfile.ZipFile(f) as zz:
            fr.append(pd.read_csv(io.BytesIO(zz.read(zz.namelist()[0]))))
    fr = pd.concat(fr)
    ft = (fr["calc_time"].to_numpy() // 60000) * 60  # dakikaya yuvarla
    rate = fr["last_funding_rate"].to_numpy(float) * 1e4  # bp
    idx = np.searchsorted(ts, ft)
    ok = (idx >= 60) & (idx + 60 < len(ts))
    for i, r, t in zip(idx[ok], rate[ok], ft[ok]):
        if ts[i] != t: continue
        lc = np.log(c)
        rows.append(dict(sym=s, part="2025" if t < CUT else "2026", rate=r,
                         pre30=(lc[i - 1] - lc[i - 31]) * 1e4, pre5=(lc[i - 1] - lc[i - 6]) * 1e4,
                         post15=(lc[i + 15] - lc[i]) * 1e4, post60=(lc[i + 60] - lc[i]) * 1e4))
df = pd.DataFrame(rows)
df["grp"] = pd.cut(df.rate, [-1e9, -1, -0.2, 0.2, 1, 1e9], labels=["<-1bp", "-1..-0.2", "~0", "0.2..1", ">1bp"])
print("Fonlama anı çevresinde getiri (bp). pre30: son 30 dk, pre5: son 5 dk, post15/60: sonrası")
print(df.groupby(["part", "grp"], observed=True)[["pre30", "pre5", "post15", "post60"]].agg(["mean", "count"]).round(1).to_string())
