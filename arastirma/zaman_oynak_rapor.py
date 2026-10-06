"""Test 2 asama 3: aday dakikalar icin ayrintili rapor (profil + gun bazinda dagilim)."""
import pickle
import numpy as np, pandas as pd
from zaman_oynak_an import P, SYMS, Y, WK, WE, pairavg, mult, arr, hm

G = pickle.load(open("/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/zaman_oynak_gun.pkl", "rb"))
CUTD = int(pd.Timestamp("2026-01-01").timestamp()) // 86400
FOMC = ["2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
        "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"]
FOMCD = set(int(pd.Timestamp(d).timestamp()) // 86400 for d in FOMC)
GUN = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"]


def tomin(s):
    a, b = s.split(":")
    return int(a) * 60 + int(b)


def prof_cache():
    C = {}
    for sysn in ("utc", "et"):
        for y in (0, 1):
            for nm, dows in (("wk", WK), ("we", WE)):
                for f in ("sxc", "sx", "sr"):
                    C[(sysn, y, nm, f)] = pairavg(sysn, f, y, dows)
                for d in (0, 1):
                    C[(sysn, y, nm, "dst", d)] = pairavg(sysn, "sxc", y, dows, dsts=(d,))
            for dw in range(7):
                C[(sysn, y, "dow", dw)] = pairavg(sysn, "sxc", y, (dw,))
    return C


C = prof_cache()


def medratio(sysn, y, wk, m):
    vals = []
    for s in SYMS:
        md = P[s][sysn]["medx"].reshape(2, 2, 1440)[y, wk]
        if np.isfinite(md[m]):
            vals.append(md[m] / np.nanmean(md))
    return np.mean(vals)


def hit(sysn, y, dows, m):
    vals = []
    for s in SYMS:
        a = arr(s, sysn, "hx")[y][:, list(dows)].sum(axis=(0, 1)); n = arr(s, sysn, "cnt")[y][:, list(dows)].sum(axis=(0, 1))
        if n[m] > 0:
            vals.append(a[m] / n[m])
    return np.mean(vals)


def ndays(sysn, y, dows, m):
    return int(arr("BTCUSDT", sysn, "cnt")[y][:, list(dows)].sum(axis=(0, 1))[m])


def daydist(sysn, m, y, dowsel=WK, extra=None):
    """Gun bazinda capraz-parite carpani: ort(x_dakika) / ort(gunun x ortalamasi)."""
    num = []; den = []
    for s in SYMS:
        g = G[s][sysn]
        if m not in g["px"].columns:
            return None
        num.append(g["px"][m].rename(s)); den.append(g["dm"]["x"].rename(s))
    N = pd.concat(num, axis=1); D = pd.concat(den, axis=1).reindex(N.index)
    dm = N.mean(axis=1) / D.mean(axis=1)
    idx = dm.index.to_numpy()
    dow = (idx + 3) % 7
    yy = (idx >= CUTD).astype(int)
    sel = (yy == y) & np.isin(dow, list(dowsel))
    if extra is not None:
        sel &= extra(idx)
    v = dm[sel].dropna().to_numpy()
    if len(v) == 0:
        return None
    ex = np.clip(v - 1, 0, None); srt = np.sort(ex)[::-1]
    top10 = srt[: max(1, len(v) // 10)].sum() / max(srt.sum(), 1e-12)
    return dict(n=len(v), mean=v.mean(), med=np.median(v), p15=(v > 1.5).mean(), p2=(v > 2).mean(), p3=(v > 3).mean(), top10=top10)


def fmtd(d):
    if d is None:
        return "-"
    return f"n={d['n']} ort={d['mean']:.2f} medyan={d['med']:.2f} >1.5:%{100*d['p15']:.0f} >2:%{100*d['p2']:.0f} >3:%{100*d['p3']:.0f} ilk%10 gun fazlaligin %{100*d['top10']:.0f}"


def report(name, sysn, hhmm):
    m = tomin(hhmm)
    print(f"\n######## {name}  [{sysn.upper()} {hhmm}]")
    for y in (0, 1):
        A = C[(sysn, y, "wk", "sxc")][0]; Mp = C[(sysn, y, "wk", "sxc")][1]
        raw = C[(sysn, y, "wk", "sx")][0][m]; rng = C[(sysn, y, "wk", "sr")][0][m]
        we = C[(sysn, y, "we", "sxc")][0][m]
        d1 = C[(sysn, y, "wk", "dst", 1)][0][m]; d0 = C[(sysn, y, "wk", "dst", 0)][0][m]
        np15 = int((Mp[:, m] >= 1.5).sum()); np12 = int((Mp[:, m] >= 1.2).sum())
        win = " ".join(f"{k:+d}:{A[(m + k) % 1440]:.2f}" for k in range(-3, 8))
        pre = A[[(m - 10 + k) % 1440 for k in range(8)]].mean()
        print(f" {Y[y]} hafta ici carpan={A[m]:.2f} (ham {raw:.2f}, aralik {rng:.2f}, medyan {medratio(sysn, y, 0, m):.2f}) | q90 isabet %{100*hit(sysn, y, WK, m):.0f} (taban %10) | gun={ndays(sysn, y, WK, m)} | parite>=1.5: {np15}/22, >=1.2: {np12}/22")
        print(f"      yerel sicrama (m / m-10..m-3 ort)={A[m]/pre:.2f} | yaz saati(EDT)={d1:.2f} kis(EST)={d0:.2f} | hafta sonu={we:.2f}")
        print(f"      pencere {win}")
        print("      gunler " + " ".join(f"{GUN[dw]}:{C[(sysn, y, 'dow', dw)][0][m]:.2f}" for dw in range(7)))
        print(f"      gun bazinda (hafta ici): {fmtd(daydist(sysn, m, y))}")


def other(sysn, hhmm, shifts):
    m = tomin(hhmm)
    o = "utc" if sysn == "et" else "et"
    out = []
    for sh in shifts:
        mm = (m + sh * 60) % 1440
        for y in (0, 1):
            A = C[(o, y, "wk", "sxc")][0]
            d1 = C[(o, y, "wk", "dst", 1)][0][mm]; d0 = C[(o, y, "wk", "dst", 0)][0][mm]
            out.append(f"{o.upper()} {hm(mm)} {Y[y]}: tum={A[mm]:.2f} EDT={d1:.2f} EST={d0:.2f}")
    print("   diger sistem: " + " | ".join(out))


if __name__ == "__main__":
    ET = [("ABD veri 08:30", "08:30"), ("ABD veri 08:30 +1", "08:31"), ("NY acilis", "09:30"), ("NY acilis +1", "09:31"), ("09:45 PMI/ceyrek", "09:45"),
          ("ABD veri 10:00", "10:00"), ("10:30 EIA", "10:30"), ("FOMC 14:00", "14:00"), ("14:30", "14:30"), ("NY kapanis 16:00", "16:00"), ("CME yeniden acilis 18:00", "18:00")]
    for nm, t in ET:
        report(nm, "et", t)
        other("et", t, (4, 5))
    UT = [("Gun acilisi/fonlama 00:00", "00:00"), ("Fonlama 08:00", "08:00"), ("Fonlama 16:00", "16:00"), ("22:00 UTC", "22:00"), ("20:00 UTC", "20:00")]
    for nm, t in UT:
        report(nm, "utc", t)
        other("utc", t, (-4, -5))
    # Pazar 18:00 ET (CME haftalik acilis)
    print("\n######## Pazar 18:00 ET (CME haftalik acilis)")
    m = tomin("18:00")
    for y in (0, 1):
        A = C[("et", y, "dow", 6)][0]
        pre = A[[(m - 10 + k) % 1440 for k in range(8)]].mean()
        print(f" {Y[y]} Pazar carpan={A[m]:.2f} yerel={A[m]/pre:.2f} pencere " + " ".join(f"{k:+d}:{A[(m + k) % 1440]:.2f}" for k in range(-3, 8)))
        print(f"      gun bazinda: {fmtd(daydist('et', m, y, dowsel=(6,)))}")
    # FOMC gunleri
    print("\n######## FOMC gunleri (14:00 ve 14:30 ET)")
    for t in ("13:59", "14:00", "14:01", "14:02", "14:30", "14:31"):
        mm = tomin(t)
        for y in (0, 1):
            f1 = daydist("et", mm, y, extra=lambda idx: np.isin(idx, list(FOMCD)))
            f0 = daydist("et", mm, y, extra=lambda idx: ~np.isin(idx, list(FOMCD)))
            print(f" {t} {Y[y]} FOMC: {fmtd(f1)}\n            diger: {fmtd(f0)}")
