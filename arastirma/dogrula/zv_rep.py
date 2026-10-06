"""Bagimsiz dogrulama, asama 3: onerilen dakikalar icin 2025 / 2026 carpanlari."""
import sys
import numpy as np, pandas as pd
from zv_an import D0, ND, CUTD, SYMS

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/dogrula/"
MEAS = sys.argv[1] if len(sys.argv) > 1 else "xa"
CAP = {"xa": 8.0, "xb": 8.0, "xc": 13.0}[MEAS]
E = np.load(BASE + f"E_{MEAS}.npy")
days = D0 + np.arange(ND)
dow = (days + 3) % 7  # 0=Pzt
yr = np.where(days < int(pd.Timestamp("2025-01-01").timestamp()) // 86400, -1, np.where(days < CUTD, 0, 1))
yr[days > int(pd.Timestamp("2026-09-30").timestamp()) // 86400] = -1
Y = {0: "2025", 1: "2026"}
dd = lambda s: int(pd.Timestamp(s).timestamp()) // 86400
FOMC = [dd(s) for s in ["2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"]]
HOL = [dd(s) for s in ["2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"]]
isF = np.isin(days, FOMC); isH = np.isin(days, HOL)
Ec = np.minimum(E, CAP)
WK = (0, 1, 2, 3, 4)
tm = lambda s: int(s[:2]) * 60 + int(s[3:])
hm = lambda i: f"{i // 60:02d}:{i % 60:02d}"


def mult(X, mask):
    P = np.nanmean(X[:, mask, :], axis=1)  # parite x dakika
    M = P / np.nanmean(P, axis=1, keepdims=True)
    return np.nanmean(M, axis=0), M


def medm(mask):
    P = np.nanmedian(E[:, mask, :], axis=1)
    return np.nanmean(P / np.nanmean(P, axis=1, keepdims=True), axis=0)


def dayratio(mask, m):
    num = np.nanmean(E[:, mask, m], axis=0)
    den = np.nanmean(np.nanmean(E[:, mask, :], axis=2), axis=0)
    v = num / den
    return v[np.isfinite(v)]


def dstat(v):
    ex = np.sort(np.clip(v - 1, 0, None))[::-1]
    top = ex[: max(1, len(v) // 10)].sum() / max(ex.sum(), 1e-12)
    return f"n={len(v)} ort={v.mean():.2f} medyan={np.median(v):.2f} >1.5:%{100*(v>1.5).mean():.0f} >2:%{100*(v>2).mean():.0f} ilk%10 pay %{100*top:.0f}"


def wkmask(y, dows=WK, extra=None):
    m = (yr == y) & np.isin(dow, dows)
    if extra is not None:
        m &= extra
    return m


print(f"=== Olcu {MEAS} (kesik {CAP}) ===")
cache = {}
for y in (0, 1):
    cache[y] = mult(Ec, wkmask(y)), mult(E, wkmask(y)), medm(wkmask(y))


def line(name, hh, y, dows=WK, extra=None):
    m = tm(hh)
    (A, M), (Ar, _), Md = cache[y] if (dows == WK and extra is None) else (mult(Ec, wkmask(y, dows, extra)), mult(E, wkmask(y, dows, extra)), medm(wkmask(y, dows, extra)))
    pre = A[[(m - 10 + k) % 1440 for k in range(8)]].mean()
    v = dayratio(wkmask(y, dows, extra), m)
    win = " ".join(f"{k:+d}:{A[(m + k) % 1440]:.2f}" for k in range(-2, 6))
    print(f" {name} {hh} {Y[y]}: kesik={A[m]:.2f} ham={Ar[m]:.2f} medyan={Md[m]:.2f} parite>=1.5 {int((M[:, m] >= 1.5).sum())}/{int(np.isfinite(M[:, m]).sum())} yerel={A[m]/pre:.2f} | {win}")
    print(f"      gun bazinda: {dstat(v)}")
    return A


for nm, hh in [("ABD veri", "08:30"), ("ABD veri", "08:31"), ("ABD veri", "08:32"), ("NY acilis", "09:30"), ("NY acilis", "09:31"), ("09:45", "09:45"), ("ABD veri", "10:00"), ("10:30", "10:30"), ("14:00 tum", "14:00"), ("NY kapanis", "16:00"), ("Globex", "18:00")]:
    for y in (0, 1):
        line(nm, hh, y)

print("\n--- Blok ortalamalari ve >=1.5 sureleri (hafta ici, kesik) ---")
for y in (0, 1):
    A = cache[y][0][0]
    def run15(start):
        k = 0
        while A[start + k] >= 1.5:
            k += 1
        return k
    print(f" {Y[y]}: 09:30-09:59 ort={A[570:600].mean():.2f} 10:00-10:30 ort={A[600:631].mean():.2f} 08:30'dan >=1.5 surekli={run15(510)} dk, 09:30'dan={run15(570)} dk; en sakin dk {hm(int(np.argmin(A)))}={A.min():.2f}")
    # carpan>=1.5 olan dakikalar (iki yil min) asagida

A0 = cache[0][0][0]; A1 = cache[1][0][0]
both = np.minimum(A0, A1)
sel = np.flatnonzero(both >= 1.5)
print(f" iki yilda >=1.5 ET dakika sayisi: {len(sel)}; ilk/son: {hm(sel.min())}..{hm(sel.max())}; 09:30-10:59 disinda kalan: {[hm(i) for i in sel if not (570 <= i < 660)]}")

print("\n--- Gun kirilimi (kesik profil) ---")
for hh in ("08:30", "09:30", "09:31", "10:00"):
    for y in (0, 1):
        r = []
        for d in range(5):
            A, _ = mult(Ec, wkmask(y, (d,)))
            r.append(f"{['Pzt','Sal','Car','Per','Cum'][d]}:{A[tm(hh)]:.2f}")
        print(f" {hh} {Y[y]}: " + " ".join(r))
for y in (0, 1):
    line("08:30 Sal-Cum", "08:30", y, dows=(1, 2, 3, 4))
    line("08:30 Pzt", "08:30", y, dows=(0,))

print("\n--- Resmi tatiller (NYSE kapali) haric ---")
for y in (0, 1):
    for hh in ("08:30", "09:31", "10:00"):
        line("tatilsiz", hh, y, extra=~isH)
        v = dayratio(wkmask(y, WK, isH), tm(hh))
        print(f"      yalniz tatil gunleri: {dstat(v) if len(v) else '-'}")

print("\n--- FOMC gunleri (gun bazinda oran) ---")
for hh in ("13:58", "13:59", "14:00", "14:01", "14:02", "14:03", "14:05", "14:10", "14:20", "14:29", "14:30", "14:31", "14:32", "14:35", "14:45"):
    for y in (0, 1):
        v1 = dayratio(wkmask(y, WK, isF), tm(hh)); v0 = dayratio(wkmask(y, WK, ~isF), tm(hh))
        print(f" {hh} {Y[y]} FOMC {dstat(v1)} | diger ort={v0.mean():.2f} medyan={np.median(v0):.2f}")
for y in (0, 1):
    msk = wkmask(y, WK, isF)
    num = np.nanmean(E[:, msk, :], axis=0); den = np.nanmean(np.nanmean(E[:, msk, :], axis=2), axis=0)
    R = num / den[:, None]
    mR = np.nanmean(R, axis=0); medR = np.nanmedian(R, axis=0)
    seg = " ".join(f"{hm(i)}:{mR[i]:.1f}/{medR[i]:.1f}" for i in range(838, 900, 2))
    print(f" FOMC {Y[y]} ort/medyan (2 dk adim): {seg}")
    print(f"   14:00-14:44 ort={mR[840:885].mean():.2f}  14:45-15:29 ort={mR[885:930].mean():.2f}  15:30-16:00 ort={mR[930:961].mean():.2f}")
    print("   gunluk 14:00: " + " ".join(f"{pd.Timestamp(d*86400, unit='s').date()}:{x:.1f}" for d, x in zip(days[msk], R[:, 840])))
    print("   gunluk 13:59: " + " ".join(f"{x:.1f}" for x in R[:, 839]))

print("\n--- Pazar 18:00 ET ---")
for y in (0, 1):
    for nm, ex in (("tum", None), ("29 Mayis 2026 oncesi", days < dd("2026-05-29")), ("29 Mayis 2026 sonrasi", days >= dd("2026-05-29"))):
        msk = wkmask(y, (6,), ex)
        if msk.sum() == 0:
            continue
        A, M = mult(Ec, msk)
        m = 1080
        v = dayratio(msk, m)
        print(f" {Y[y]} {nm}: Pazar-ici carpan={A[m]:.2f} parite>=1.5 {int((M[:, m] >= 1.5).sum())}/{int(np.isfinite(M[:, m]).sum())} | " + " ".join(f"{k:+d}:{A[m + k]:.2f}" for k in range(-2, 7)) + f" | gun: {dstat(v)}")
