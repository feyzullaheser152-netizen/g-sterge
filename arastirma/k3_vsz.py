"""Volume-based Support & Resistance Zones V2 (synapticex, Lij_MC ve sonraki duzenlemeler) mantik uyarlamasi.

Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir.

Gosterge: her zaman diliminde (grafik, 4 saat, gun, hafta) 5 mumluk fraktal (H[3] > H[4] > H[5], H[2] < H[3], H[1] < H[2]) ve fraktal mumun hacmi
6 mumluk hacim ortalamasinin ustunde ise direnc (FractalUp = H[3]; bolge = govdenin ustu). Destek simetrik (FractalDown = L[3]; bolge = govdenin alti).
Ust zaman dilimi: degerler yalnizca tamamlanmis UZD mumlarindan (t-1 ... t-5) hesaplanir; 1 dk grafikte UZD mumunun ilk dakikasindan itibaren kullanilir
(gercek zamanda gostergenin verdigi deger; gelecege sizinti yok). Haftalik seviye 21 ayda cok az olay urettigi icin sinanmadi.
Sinyaller (alarm tanimlari): kirilim = close FractalUp'i yukari keser (AL) / FractalDown'u asagi keser (SAT);
bolge tepkisi = close destek bolgesini asagi keser (AL, destekten donus beklentisi) / direnc bolgesini yukari keser (SAT).
"""
import numpy as np, pandas as pd
from topluluk_sinyal import cross_up, cross_dn


def _fraktal(H, L, O, C, V):
    """UZD dizileri uzerinde: her UZD mumu t icin t-1..t-5'e dayanan FractalUp/Down ve bolgeler (t mumunun basinda bilinir)."""
    n = len(H)
    sh = lambda x, k: np.r_[np.full(k, np.nan), x[:-k]]
    vma = pd.Series(V).rolling(6).mean().to_numpy()
    up = (sh(H, 3) > sh(H, 4)) & (sh(H, 4) > sh(H, 5)) & (sh(H, 2) < sh(H, 3)) & (sh(H, 1) < sh(H, 2)) & (sh(V, 3) > sh(vma, 3))
    dn = (sh(L, 3) < sh(L, 4)) & (sh(L, 4) < sh(L, 5)) & (sh(L, 2) > sh(L, 3)) & (sh(L, 1) > sh(L, 2)) & (sh(V, 3) > sh(vma, 3))
    up = np.nan_to_num(up).astype(bool)
    dn = np.nan_to_num(dn).astype(bool)
    H3, L3, O3, C3 = sh(H, 3), sh(L, 3), sh(O, 3), sh(C, 3)
    fu = pd.Series(np.where(up, H3, np.nan)).ffill().to_numpy()
    fd = pd.Series(np.where(dn, L3, np.nan)).ffill().to_numpy()
    rz = pd.Series(np.where(up, np.where(C3 >= O3, C3, O3), np.nan)).ffill().to_numpy()
    sz = pd.Series(np.where(dn, np.where(C3 >= O3, O3, C3), np.nan)).ffill().to_numpy()
    return fu, fd, rz, sz


def _uzd(ts, o, h, l, c, v, saniye):
    """1 dk -> UZD (UTC sinirlari). Cikti: 1 dk mum basina, ait oldugu UZD mumunun basinda bilinen degerler."""
    g = ts // saniye
    df = pd.DataFrame({"g": g, "o": o, "h": h, "l": l, "c": c, "v": v})
    a = df.groupby("g").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    fu, fd, rz, sz = _fraktal(a["h"].to_numpy(), a["l"].to_numpy(), a["o"].to_numpy(), a["c"].to_numpy(), a["v"].to_numpy())
    idx = np.searchsorted(a.index.to_numpy(), g)
    return fu[idx], fd[idx], rz[idx], sz[idx]


def hesapla(z):
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    S, D, U = {}, {}, {}
    seviyeler = {"1dk": _fraktal(h, l, o, c, v), "4s": _uzd(ts, o, h, l, c, v, 4 * 3600), "G": _uzd(ts, o, h, l, c, v, 86400)}
    for ad, (fu, fd, rz, sz) in seviyeler.items():
        bal, bsat = cross_up(c, fu), cross_dn(c, fd)
        S["VSZB_" + ad] = (bal & ~bsat, bsat & ~bal)
        ral, rsat = cross_dn(c, sz), cross_up(c, rz)
        S["VSZR_" + ad] = (ral & ~rsat, rsat & ~ral)
        D[f"Hacim S/R {ad}: fiyat dirençle destek arasında konum (desteğe yakın +)"] = np.where(np.isfinite(fu) & np.isfinite(fd) & (fu > fd), np.where(c - fd < fu - c, 1, -1), 0)
    return {"S": S, "D": D, "U": U, "X": {}, "STOPS": {}}
