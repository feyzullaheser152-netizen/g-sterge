"""K3 / G4: ortalama şeritleri ve hacim akışı (1 dk; 22 Binance USDT-M paritesi). Topluluk göstergelerinin sinyal ve durum dizileri.

Kaynak göstergeler (varsayılan girdilerle):
  EMA   EMA 20/50/100/200 (Pine v2/v3 study); kaynak dosyada yazar ve lisans başlığı yok (TradingView açık kaynak kuralları gereği
        yazar/kaynak anılarak yeniden kullanılır). Betiğin sinyali yok; şerit dizilimi ve fiyatın EMA200'e göre konumu bilgidir.
  MAD   Madrid Moving Average Ribbon, Madrid, Mozilla Public License 2.0. i_exp = true (üstel), ma05..ma90 (5 adım) ve ma100, kaynak kapanış.
  VFI   Volume Flow Indicator [LazyBear] (lisans başlığı yok; TradingView kuralları gereği yazar anılarak yeniden kullanılır).
        Uzunluk 130, coef 0,2, vcoef 2,5, sinyal 5, smoothVFI = false.
Mantık uyarlaması; kod kopyalanmadı, yalnızca araştırma içindir.

Çıktılar:
  S  EMAX : EMA20 EMA50'yi yukarı keser (AL) / aşağı keser (SAT).
     E200X: kapanış EMA200'ü yukarı keser / aşağı keser.
     MADT : ma05 rengi başka bir renkten LIME'a döner (AL) / başka bir renkten RUBI'ye döner (SAT).
     MADR : ma05 rengi başka bir renkten GREEN'e döner (AL; "dipten alım" yeniden giriş) / MAROON'a döner (SAT; "tepeden satış").
     VFI0 : vfi 0'ı yukarı keser / aşağı keser.   VFIX: vfi vfima'yı yukarı keser / aşağı keser.
  D  "EMA dizilimi (20>50>100>200)": +1 ema20>ema50>ema100>ema200, -1 kesin ters dizilim, aksi 0.
     "Fiyat EMA200 üstü": +1 close > ema200, aksi -1.
     "Madrid şerit çoğunluğu": sign(LIME renkli MA sayısı - RUBI renkli MA sayısı), 18 MA (ma05..ma90).
     "Madrid ma05 trendi": +1 LIME, -1 RUBI, aksi 0.
     "VFI > 0": sign(vfi) (na ise 0).   "VFI > sinyal": sign(vfi - vfima) (na ise 0).
  U  "Madrid ma05 geri dönüş rengi (GREEN/MAROON)": ma05 rengi GREEN ya da MAROON.

Pine anlamına uyum notları:
  - ema = topluluk_sinyal.ema (alfa 2/(n+1); Pine'daki ilk n-1 mumun na olması ve SMA tohumu yerine ilk değerden başlar: tohum farkı
    yalnızca ısınma mumlarında; testte t >= 5000 kullanılır). Akışkan nokta farkı en son basamak düzeyindedir (change(ma) = 0 sınırında
    renk ayrımı bu düzeyde gürültüdür).
  - maColor(_ma, _maRef): diffMA = change(_ma) (ilk mumda na -> tüm karşılaştırmalar yanlış -> GRAY). Üçlü sıra korunur:
    diffMA >= 0 ve ma > ref LIME; diffMA < 0 ve ma > ref MAROON; diffMA <= 0 ve ma < ref RUBI; diffMA >= 0 ve ma < ref GREEN; aksi GRAY.
    (diffMA = 0 ve ma < ref -> RUBI; ma = ref -> GRAY.) Her MA kendi change() geçmişini kullanır; referans ma100.
  - "Renge döner": renk[t] hedef renk ve renk[t-1] farklı; ilk mumda yanlış.
  - VFI: typical = hlc3; inter = log(typical) - log(typical[1]); vinter = stdev(inter, 30) (nüfus sapması, ddof = 0);
    cutoff = coef * vinter * close; vave = sma(volume, 130)[1]; vmax = vave * vcoef; vc = volume < vmax ? volume : vmax
    (vmax na iken karşılaştırma yanlış -> vc = vmax = na); mf = typical - typical[1]; vcp = mf > cutoff ? vc : mf < -cutoff ? -vc : 0
    (cutoff na iken 0); vfi = sum(vcp, 130) / vave (pencerede na varsa na; ma() özdeşlik); vfima = ema(vfi, 5) (vfi na iken na).
    Verideki en uzun sıfır hacim dizisi 19 mum (< 130) olduğundan ısınmadan sonra vave > 0 ve vfi hep tanımlı.
  - Her değer yalnızca t ve önceki mumların verisiyle hesaplanır (repaint yok); sinyaller mum kapanışında.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topluluk_sinyal import rma, ema, sma, stdev, highest, lowest, cross_up, cross_dn, true_range, pivot

GRAY, LIME, RUBI, GREEN, MAROON = 0, 1, -1, 2, -2
MAD_N = list(range(5, 95, 5))  # ma05..ma90 (18 çizgi)


def sh(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


def isaret(x):
    return np.where(np.isnan(x), 0, np.sign(x)).astype(np.int64)


def ma_renk(ma, ref):
    """Madrid maColor: kodlar LIME 1, RUBI -1, GREEN 2, MAROON -2, GRAY 0."""
    d = ma - sh(ma, 1)
    ust, alt = ma > ref, ma < ref
    with np.errstate(invalid="ignore"):
        kos = [(d >= 0) & ust, (d < 0) & ust, (d <= 0) & alt, (d >= 0) & alt]
    return np.select(kos, [LIME, MAROON, RUBI, GREEN], GRAY).astype(np.int8)


def renge_doner(col, hedef):
    onceki = np.r_[col[:1], col[:-1]]
    out = (col == hedef) & (onceki != hedef)
    out[0] = False
    return out


def vfi_hesap(h, l, c, v, length=130, coef=0.2, vcoef=2.5, siglen=5):
    typ = (h + l + c) / 3.0
    lt = np.log(typ)
    inter = lt - sh(lt, 1)
    vinter = stdev(inter, 30)
    cutoff = coef * vinter * c
    vave = sh(sma(v, length), 1)
    vmax = vave * vcoef
    with np.errstate(invalid="ignore"):
        vc = np.where(v < vmax, v, vmax)
        mf = typ - sh(typ, 1)
        vcp = np.where(mf > cutoff, vc, np.where(mf < -cutoff, -vc, 0.0))
    top = pd.Series(vcp).rolling(length).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vfi = top / vave
    vfi = np.where(np.isfinite(vfi), vfi, np.nan)
    vfima = np.where(np.isnan(vfi), np.nan, ema(vfi, siglen))
    return vfi, vfima


def hesapla(z):
    h, l, c, v = (np.asarray(z[k], dtype=np.float64) for k in ("h", "l", "c", "v"))
    n = len(c)
    # G4-A: EMA 20/50/100/200
    e20, e50, e100, e200 = ema(c, 20), ema(c, 50), ema(c, 100), ema(c, 200)
    diz = np.where((e20 > e50) & (e50 > e100) & (e100 > e200), 1, np.where((e20 < e50) & (e50 < e100) & (e100 < e200), -1, 0)).astype(np.int64)
    ust200 = np.where(c > e200, 1, -1).astype(np.int64)
    # G4-B: Madrid şeridi (üstel)
    ref = e100  # ma100 = ema(close, 100)
    say = np.zeros(n, np.int64)
    col05 = None
    for N in MAD_N:
        col = ma_renk(ema(c, N), ref)
        say += (col == LIME).astype(np.int64) - (col == RUBI).astype(np.int64)
        if N == 5:
            col05 = col
    cogun = np.sign(say).astype(np.int64)
    tr05 = np.where(col05 == LIME, 1, np.where(col05 == RUBI, -1, 0)).astype(np.int64)
    gd05 = (col05 == GREEN) | (col05 == MAROON)
    # G4-C: VFI
    vfi, vfima = vfi_hesap(h, l, c, v)
    sifir = np.zeros(n)
    return {
        "S": {
            "EMAX": (cross_up(e20, e50), cross_dn(e20, e50)),
            "E200X": (cross_up(c, e200), cross_dn(c, e200)),
            "MADT": (renge_doner(col05, LIME), renge_doner(col05, RUBI)),
            "MADR": (renge_doner(col05, GREEN), renge_doner(col05, MAROON)),
            "VFI0": (cross_up(vfi, sifir), cross_dn(vfi, sifir)),
            "VFIX": (cross_up(vfi, vfima), cross_dn(vfi, vfima)),
        },
        "D": {
            "EMA dizilimi (20>50>100>200)": diz,
            "Fiyat EMA200 üstü": ust200,
            "Madrid şerit çoğunluğu": cogun,
            "Madrid ma05 trendi": tr05,
            "VFI > 0": isaret(vfi),
            "VFI > sinyal": isaret(vfi - vfima),
        },
        "U": {"Madrid ma05 geri dönüş rengi (GREEN/MAROON)": gd05},
        "X": {},
        "STOPS": {},
    }
