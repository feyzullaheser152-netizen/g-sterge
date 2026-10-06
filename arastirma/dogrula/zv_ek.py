"""Ek kontroller: xb/xc ile ana carpanlar, haftalik tabana gore mutlak buyukluk, UTC dakikalari, DST ayrimi."""
import numpy as np, pandas as pd
from zv_an import D0, ND, CUTD, SYMS

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/dogrula/"
dd = lambda s: int(pd.Timestamp(s).timestamp()) // 86400
days = D0 + np.arange(ND); dow = (days + 3) % 7
yr = np.where(days < dd("2025-01-01"), -1, np.where(days < CUTD, 0, 1)); yr[days > dd("2026-09-30")] = -1
Y = {0: "2025", 1: "2026"}
tm = lambda s: int(s[:2]) * 60 + int(s[3:])
EV = [("08:30", (0, 1, 2, 3, 4)), ("08:30", (1, 2, 3, 4)), ("09:30", (0, 1, 2, 3, 4)), ("09:31", (0, 1, 2, 3, 4)), ("10:00", (0, 1, 2, 3, 4)), ("18:00", (6,))]


def mult(X, mask):
    P = np.nanmean(X[:, mask, :], axis=1)
    return P / np.nanmean(P, axis=1, keepdims=True)


# 1) xb (Pine sd1, bir mum gecikmeli) ile ayni carpanlar, kesik 8
E = np.minimum(np.load(BASE + "E_xb.npy"), 8.0)
print("== xb (1440 rolling std, Pine tanimi) hafta ici/pazar carpani, kesik 8 ==")
for hh, dw in EV:
    print(f" {hh} gunler={dw}: " + " | ".join(f"{Y[y]} {np.nanmean(mult(E, (yr == y) & np.isin(dow, dw))[:, tm(hh)]):.2f}" for y in (0, 1)))
for y in (0, 1):
    A = np.nanmean(mult(E, (yr == y) & np.isin(dow, (0, 1, 2, 3, 4))), axis=0)
    print(f"  {Y[y]} 09:30-09:59 ort={A[570:600].mean():.2f} 10:00-10:30 ort={A[600:631].mean():.2f}")
del E

# 2) xc: haftalik |r1| tabanina gore mutlak buyukluk (tum haftanin ortalama dakikasi = 1)
E = np.minimum(np.load(BASE + "E_xc.npy"), 13.0)
print("\n== xc: tum haftanin ortalama dakikasina gore (hafta=1) ve hafta ici ortalamaya gore ==")
for y in (0, 1):
    allm = (yr == y)
    wk = allm & np.isin(dow, (0, 1, 2, 3, 4))
    base_all = np.nanmean(E[:, allm, :], axis=(1, 2))
    base_wk = np.nanmean(E[:, wk, :], axis=(1, 2))
    sun = allm & (dow == 6)
    base_sun = np.nanmean(E[:, sun, :], axis=(1, 2))
    print(f" {Y[y]}: Pazar gunu ort / hafta ici ort = {np.nanmean(base_sun / base_wk):.2f};  Cmt = {np.nanmean(np.nanmean(E[:, allm & (dow == 5), :], axis=(1, 2)) / base_wk):.2f}")
    for hh, dw in EV:
        msk = allm & np.isin(dow, dw)
        v = np.nanmean(E[:, msk, tm(hh)], axis=1)
        print(f"   {hh} gunler={dw}: hafta={np.nanmean(v / base_all):.2f}  hafta-ici-ort={np.nanmean(v / base_wk):.2f}")
    msk = allm & (dow == 6)
    for nm, ex in (("29 May oncesi", days < dd("2026-05-29")), ("29 May sonrasi", days >= dd("2026-05-29"))):
        m2 = msk & ex
        if m2.sum():
            v = np.nanmean(E[:, m2, 1080], axis=1)
            print(f"   Pazar 18:00 {nm} (n={m2.sum()}): hafta-ici-ort={np.nanmean(v / base_wk):.2f}")
del E

# 3) UTC dakikalari (fonlama, ceyrek saat), xa kesik 8, hafta ici UTC gunleri
U = np.minimum(np.load(BASE + "U_xa.npy"), 8.0)
ud = dd("2025-01-01") + np.arange(U.shape[1]); udow = (ud + 3) % 7; uyr = (ud >= CUTD).astype(int)
z = np.load(BASE + "feat/BTCUSDT.npz")
# her UTC gunu icin ABD yaz saati mi (gun ortasi)
off = z["off"].reshape(-1, 1440)[:, 720]
dst = (off == -4 * 3600)
print("\n== UTC hafta ici (xa, kesik 8) ==")
for y in (0, 1):
    msk = (uyr == y) & (udow < 5)
    A = np.nanmean(mult(U, msk), axis=0)
    Ae = np.nanmean(mult(U, msk & dst), axis=0); As = np.nanmean(mult(U, msk & ~dst), axis=0)
    q = {k: A[[h * 60 + k for h in range(24)]].mean() for k in (0, 15, 30, 45)}
    qp = {k: A[[(h * 60 + k - 1) % 1440 for h in range(24)]].mean() for k in (0, 15, 30, 45)}
    hrs = A.reshape(24, 60).mean(axis=1)
    print(f" {Y[y]}: 00:00={A[0]:.2f} 08:00={A[480]:.2f} 16:00={A[960]:.2f} | 12:30 EDT={Ae[750]:.2f} EST={As[750]:.2f} | 13:30 EDT={Ae[810]:.2f} EST={As[810]:.2f} | 14:30 EDT={Ae[870]:.2f} EST={As[870]:.2f}")
    print(f"     ceyrek basi :00/:15/:30/:45 = {q[0]:.2f}/{q[15]:.2f}/{q[30]:.2f}/{q[45]:.2f}; bir onceki dk = {qp[0]:.2f}/{qp[15]:.2f}/{qp[30]:.2f}/{qp[45]:.2f}; en sakin saat {int(np.argmin(hrs))}:00 UTC = {hrs.min():.2f}")
    for d in range(5):
        Ad = np.nanmean(mult(U, (uyr == y) & (udow == d)), axis=0)
        print(f"     00:00 UTC {['Pzt','Sal','Car','Per','Cum'][d]}={Ad[0]:.2f}", end="")
    print()
    # Pazar UTC 22:00 / 23:00 yaz-kis
    ms = (uyr == y) & (udow == 6)
    Ae = np.nanmean(mult(U, ms & dst), axis=0); As = np.nanmean(mult(U, ms & ~dst), axis=0)
    print(f"     Pazar UTC 22:00 EDT={Ae[1320]:.2f} EST={As[1320]:.2f} | 23:00 EDT={Ae[1380]:.2f} EST={As[1380]:.2f}  (n EDT={int((ms & dst).sum())}, EST={int((ms & ~dst).sum())})")
