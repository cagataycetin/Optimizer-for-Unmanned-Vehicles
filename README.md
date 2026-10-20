# İHA Optimizasyon — Masaüstü Uygulaması

Amaç: Kullanıcının uçuş koşullarına ve tasarım kısıtlarına göre mevcut profilini
aday airfoillerle karşılaştıran, önerisinin gerekçesini gösteren bir karar destek
uygulaması geliştirmek.

Bu depo, projenin çalışan masaüstü taslağıdır. Henüz airfoil önerisi üretmez.
İHA tipi kesinleşmediği için örnek hesap klasik sabit kanatlı, düz ve yatay uçuşa
aittir. Bir yıllık çalışma planı: [YOL_HARITASI.md](YOL_HARITASI.md).

## Şu anda neler var?

- Genel bakış, İHA tasarımı, airfoil kütüphanesi, karşılaştırma ve yol haritası ekranları.
- Butonlarla uçuş koşulu hesabı, JSON tasarım kaydetme/açma ve CSV raporu.
- Profil arama, aile filtresi, DAT içe aktarma ve ortak ölçekte geometri çizimleri.
- UIUC kataloğundan seçilmiş **80 adayın** adı, ailesi ve koordinat kaynak bağlantısı.
- **2 profilin** gerçek koordinatları: NACA 2412 (35 nokta), S1223 (81 nokta).
- SQLite veri tabanı oluşturma ve Selig/Lednicer DAT dosyalarını içeri alma aracı.
- Ağırlık, kanat yüklemesi, gerekli kanat CL, referans Reynolds ve Mach hesabı.
- Sonraki aşamada simülasyon ve deneysel polarları ayrı saklayacak veri şeması.

**80 aday kaydı, 80 analiz edilmiş profil anlamına gelmez.** Diğer 78 profilin
koordinatları indirilmemiştir. Hiçbir profil için polar analizi çalıştırılmamıştır.
`status` komutundaki öneri durumu, bu başlangıç sürümünde daima `false` döner;
henüz bir öneri hazırlığı denetleyicisi yazılmamıştır.

## İlk çalıştırma

PyCharm kullanıyorsanız [PyCharm kurulum rehberini](PYCHARM_KURULUM.md) izleyin.
`main.py` dosyasına sağ tıklayıp **Run 'main'** seçerek parametresiz başlangıç
arayüzünü açabilirsiniz. Veri tabanı otomatik hazırlanır; işlemleri açılan
pencereden yapabilirsiniz. Windows'ta **BASLAT.bat** dosyasına çift tıklamak da
uygulamayı başlatır. Bu dosya önce proje `.venv` ortamını, ardından kurulu
Python'u dener. Bilgisayarda Python 3.10+ ve Tkinter bulunmalıdır; bu paket
Python'dan bağımsız bir `.exe` değildir.

```bash
python3 main.py
```

Uygulamada ilk deneme:

1. **İHA Tasarımı** ekranında örnek değerleri inceleyin veya değiştirin.
2. **Uçuş Koşullarını Hesapla** ile sonuçları görün. Değerleri değiştirince eski
   sonuçlar temizlenir; tekrar hesaplamak gerekir.
3. **Tasarımı Kaydet** ile JSON dosyası oluşturun; **Tasarım Aç** ile yeniden yükleyin.
4. **Airfoil Kütüphanesi** içinde profil arayın, aile seçin ve geometriyi inceleyin.
5. **Karşılaştırma** ekranında NACA 2412 ve S1223 çizimlerini üst üste görün.

**Sonuçları CSV Olarak Al**, Excel ile açılabilen UTF-8 ve noktalı virgülle ayrılmış
bir rapor üretir. Girdilerin sayısal değeri için ondalık virgül veya nokta kullanılabilir.
Kayıtlı projeler JSON'dur; başka projeye taşınabilir. DAT içe aktarma işlemi
seçili profilin yeni geometri sürümünü yerel veri tabanına ekler.

Masaüstü arayüzü için harici Python paketi gerekmiyor. Bazı Linux Python
kurulumlarında Tkinter ayrıca sistem paketinden kurulmalıdır; resmi Windows
Python kurulumunda Tcl/Tk bileşenini etkin tutun.

Komut satırı araçları da kullanılabilir:

Python 3.10+ yeterlidir; harici paket veya veri tabanı sunucusu gerekmez.
Terminali bu proje klasöründe açın:

```bash
python3 uav.py init
python3 uav.py status
python3 uav.py flight examples/aircraft.json
python3 -m unittest discover -s tests -v
```

Windows'ta gerekirse `python3` yerine `python` kullanın. Veri tabanı
`data/airfoils.sqlite3` içinde oluşur. `init` tekrar çalıştırıldığında aynı aday ve
aynı içerikli geometri çoğaltılmaz. Geometri içeriği değişirse yeni sürüm saklanır.

Öğretici örnek girdi: 5 kg kütle, 0.8 m² alan, 2.5 m açıklık, 0.32 m referans
kord, 18 m/s hız ve deniz seviyesine yakın standart hava özellikleri. Bu değerler
gerçek bir İHA'dan alınmamıştır. Sonuçlar yaklaşık:

| Büyüklük | Sonuç |
| --- | ---: |
| Gerekli kanat CL | 0.309 |
| Referans Reynolds | 394,410 |
| Mach | 0.053 |
| Açıklık oranı | 7.81 |

Referans kord, örnekte dikdörtgen kanadın kordudur. Genel kanatta uygun bir
referans/ortalama aerodinamik kord belirlenmelidir. Yerel kord ve yük dağılımı,
kanat boyunca farklı Reynolds ve profil cl değerleri doğurur. Bu araç bunları
henüz çözmez. `current_airfoil` sonraki karşılaştırma için örnekte tutulur;
mevcut hesap airfoil aerodinamiğini kullanmaz.

## Diğer koordinatları toplama

İnternet erişimi olan bilgisayarda önce 5 adayla başlayın:

```bash
python3 uav.py fetch --limit 5
python3 uav.py status
```

Tüm adayların koordinatları için:

```bash
python3 uav.py fetch
```

Araç önce `data/raw/` içindeki dosyayı kullanır; yoksa CSV'deki resmi UIUC
bağlantısını dener. Başarısız indirmeleri bildirir ve hata koduyla çıkar; eksik
veriyi uydurmaz. `--limit 5`, kataloğun ilk beş kaydını ifade eder. Önbellekteki
dosyalar ayrıca indirilmez.

Bu çalışma ortamının izin verilen ağ adresleri UIUC'yi içermediği için toplu
indirme burada denenmedi. İki örnek, resmi kaynakların web üzerinden okunan
sayısal koordinatlarından, boşlukları düzenlenerek dosyalara aktarıldı.

Alternatif olarak UIUC'den dosyayı kendiniz alıp şu şekilde içeri aktarabilirsiniz:

```bash
python3 uav.py import-dat e387 /tam/yol/e387.dat
```

İçe aktarma temel sayısal/format denetimleri yapar. Tam bir geometri kalite
kontrolü değildir; kendini kesen yüzey, eğrilik süreksizliği ve panelleme kalitesi
ayrıca incelenmelidir. Dosyalar otomatik yumuşatılmaz veya yeniden ölçeklenmez.
Özgün ve işlenmiş koordinatları ileride ayrı sürümlerde tutun.

## Veri tabanı mantığı

```text
airfoils → geometries → polar_runs → polar_points
profil     şekil        analiz      açıya bağlı katsayılar
```

Bir profilin birçok geometri sürümü; bir geometrinin farklı Reynolds, Mach,
geçiş ve yüzey koşullarında birçok analizi olabilir. Bu nedenle `CL_max` veya
`L/D_max` profil tablosunda tek, değişmez sayı olarak tutulmaz.

Kaynak, içerik özeti ve içe alma zamanı geometriyle saklanır. `polar_runs`, analiz
ayarlarını ve veri türünü; `polar_points`, hücum açısı, cl, cd, cm ve yakınsama
durumunu tutmak için hazırdır. Polar içe aktarıcısı ve çözücü entegrasyonu sonraki
iştir. Ham çözücü çıktıları da saklanmalıdır.

## Sıradaki somut geliştirme

NACA 2412, E387, SD7037, S1223 ve Clark Y için tek bir ortak Reynolds/Mach/geçiş
ayarında XFOIL polarları üretin. Aynı hedef profil cl değerindeki cd ve cm
değerlerini karşılaştırın; açıları eşitlemek aynı kaldırma ihtiyacını sağlamaz.
Bu yalnızca 2B taramadır. Kanat seviyesindeki sonuç için 3B analiz gereklidir.
Stall yakınında yakınsamayan noktalar ve deneysel veriyle uyuşmazlıklar özellikle
kaydedilmelidir.

## Kaynaklar

- [UIUC koordinat veri tabanı](https://m-selig.ae.illinois.edu/ads/coord_database.html)
- [NACA 2412 koordinatları](https://m-selig.ae.illinois.edu/ads/coord/naca2412.dat)
- [S1223 koordinatları](https://m-selig.ae.illinois.edu/ads/coord/s1223.dat)
- [UIUC düşük hızlı airfoil deneyleri](https://m-selig.ae.illinois.edu/uiuc_lsat.html)
- [MIT XFOIL](https://web.mit.edu/drela/Public/web/xfoil/)
- [XFOIL kullanım belgesi](https://web.mit.edu/drela/Public/web/xfoil/xfoil_doc.txt)

Katalog listesi 18 Ekim 2026 tarihinde resmi dizinden kontrol edilerek hazırlandı.
Seçim, farklı aileleri kapsayan bir **ön liste**dir; bütün adayların görevinize
uygun olduğunu veya deneysel verilerinin bulunduğunu ifade etmez. Son listeyi
hedef Reynolds aralığı, üretilebilirlik ve veri bulunabilirliğiyle daraltın.
Verileri yayınlama aşamasında kaynakların kullanım koşullarını ayrıca kaydedin.
