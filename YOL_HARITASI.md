# Bir yıllık proje yol haritası

## Projenin ilk kapsamı

İlk teslim edilebilir ürün: Kullanıcı kütle, hız ve kanat geometrisini girer;
sistem bu koşullara uygun verisi olan airfoilleri mevcut profille kıyaslar ve
gerekçeleriyle üç aday gösterir. Veri koşulları kapsamıyorsa eksikliği bildirir.

Başlangıçta klasik kuyruklu, sabit kanatlı, düşük hızlı bir örnek kullanın. İHA
tipini henüz seçmediğiniz için bu bir çalışma varsayımıdır. Uçan kanada geçilirse
moment ve trim gereksinimleri değişir. Çok rotorlu araçlarda ise rotor, pervane
ve tahrik modeli gerekir; aynı sabit kanat yaklaşımı doğrudan kullanılamaz.

İlk araştırma sorusu: **Belirlenen uçuş zarfı ve tasarım kısıtları altında hangi
aday profiller mevcut profile göre daha uygun performans sunuyor ve neden?**

İlk sürüm 80 aday arasından seçim yapar. Yeni profil geometrisi üreten sürekli
optimizasyon daha sonraki bir araştırma konusudur. Motor, pervane, yapı, kontrol
ve enerji sistemini aynı anda optimize etmeyi ilk teslimin kapsamına almayın.

## 1. “Daha iyi uçmak” ne demek?

Bu ifadeyi hocanızla ölçülebilir bir hedefe çevirin:

| Öncelik | Örnek değerlendirme | Gerekli ek model |
| --- | --- | --- |
| Seyir verimi | Aynı uçuş noktasında daha düşük toplam sürükleme | 3B kanat, gövde ve trim |
| Havada kalış | Görev boyunca daha düşük enerji tüketimi | Tahrik verimi, batarya, görev profili |
| Düşük hız | Uygun stall marjı ve kalkış davranışı | 3B CLmax, deneysel doğrulama |
| Üretim kolaylığı | Kiriş yerleşimine ve üretim yöntemine uygun kalınlık | Geometri ve yapı kısıtları |

İlk hedef olarak **belirlenmiş bir seyir noktasında profil taraması** seçin.
Maksimum cl/cd oranını farklı kaldırma noktalarında bulup hepsini tek puana
indirgemeyin. Aynı hedef kaldırmada cd, moment ve kısıtları birlikte inceleyin.
İlk uygulama üç adayı avantajları ve bedelleriyle gösterirse daha açıklanabilir
olur. Tek puan gerekiyorsa ağırlıkların seçimini ve duyarlılığını raporlayın.

## 2. Kullanıcıdan hangi bilgiler alınmalı?

| Alan | Birim / açıklama | Neden gerekli? |
| --- | --- | --- |
| İHA düzeni | Klasik kuyruk / uçan kanat vb. | Modelin uygulanabilirliği |
| Toplam uçuş kütlesi | kg, faydalı yük ve batarya dahil | Gerekli kaldırma |
| Kanat alanı | m² | Kanat yüklemesi ve CL |
| Açıklık | m | Açıklık oranı |
| Kanat planformu ve kordlar | m; ilk örnek dikdörtgen | Yerel Reynolds ve yük dağılımı |
| Seyir hızı ve hız aralığı | m/s, hava hızı | Dinamik basınç ve uçuş zarfı |
| Atmosfer | İlk araçta yoğunluk, viskozite ve ses hızı | Reynolds ve Mach |
| Mevcut profil | Profil kimliği veya DAT | Kıyaslama tabanı |
| Hedef ve kısıtlar | Verim, minimum kalınlık, moment vb. | Adayların elenmesi |

Ürün arayüzünde ileride irtifa ve sıcaklıktan atmosfer özellikleri hesaplanabilir.
Mevcut örnekte hava özellikleri açıkça girilir. İrtifa tek başına her atmosferi
belirlemez. Birim dönüşümlerini girişte yapıp içeride SI birimleri kullanın.

## 3. 70–80 airfoil için veri toplama

`data/airfoil_candidates.csv` dosyasında 80 aday ve resmi koordinat bağlantıları
hazır. Liste 20 Drela AG, 20 Eppler, 20 Selig, 12 NACA, 6 Selig/Donovan, Clark Y
ve MH32 içerir. Aileleri göstermek için hazırlanmıştır; nihai görev seçimi değildir.

Üç veri katmanını ayrı tutun:

1. **Kimlik:** ad, aile, kaynak, seçim gerekçesi ve kullanım koşulları.
2. **Geometri:** x/c–y/c noktaları, kaynak dosya, sürüm ve geometri denetimleri.
3. **Aerodinamik polar:** belirli koşullarda α, cl, cd, cm ve yakınsama bilgisi.

Polar, bu katsayıların hücum açısı boyunca nasıl değiştiğini gösteren veri
serisidir. Aynı airfoil farklı Reynolds ve yüzey koşullarında farklı polarlar
üretir. Bu nedenle internetten tek bir “maksimum L/D” sayısı alıp kıyaslamayın.

Önce 5 profilin veri hattını baştan sona kurun; sonra 80'e genişletin. İlk beş:
NACA 2412, E387, SD7037, S1223 ve Clark Y. Bu seçim bir yöntem denemesidir,
uçuş performansı önerisi değildir.

Geometri kalite kontrolünde başlık/yorum satırlarını, Selig–Lednicer farkını,
nokta sırasını, birim kordu, yinelenen noktaları ve yüzey sürekliliğini inceleyin.
Tüm profilleri aynı panelleme yaklaşımıyla analiz edin; ham geometriyi koruyun.

Kaynak başlangıçları:

- Koordinatlar: [UIUC airfoil dizini](https://m-selig.ae.illinois.edu/ads/coord_database.html).
- Deneysel karşılaştırma: [UIUC düşük hızlı testleri](https://m-selig.ae.illinois.edu/uiuc_lsat.html).
- 2B analiz: [MIT XFOIL ve belgesi](https://web.mit.edu/drela/Public/web/xfoil/).

## 4. Karşılaştırma motoru nasıl çalışacak?

```text
İHA ve görev girdileri
        ↓
Birim, tutarlılık ve kapsam denetimi
        ↓
Gerekli kanat CL ve referans Reynolds hesabı
        ↓
Koşulları kapsayan polarların seçimi
        ↓
Kalınlık, moment ve veri kalitesi kısıtları
        ↓
Ortak hedef cl noktasında 2B ön karşılaştırma
        ↓
Seçilen adaylar için 3B kanat ve trim analizi
        ↓
Mevcut profille kıyas ve gerekçeli aday listesi
```

İlk fizik hesabı:

```text
W = m × g
q = 0.5 × ρ × V²
CL_gerekli = W / (q × S)
Re_referans = ρ × V × c_referans / μ
AR = b² / S
Mach = V / a
```

Burada düz, yatay ve ivmesiz uçuş varsayılır. İlk hesap kaldırmayı bütünüyle
kanada atar; kuyruk kuvveti/trim etkisi henüz dahil değildir. Kodda bu ilk adım
hazırdır.

**Kanadın CL değeri, 2B profilin cl değeri değildir.** İlk 2B taramada eşit kabul
edilecekse bunu açık bir yaklaşım olarak yazın; nihai öneriyi buna dayandırmayın.
Kanat açıklığı boyunca kord, Reynolds ve yük farklılaşır. Sonraki aşamada
kaldırma çizgisi/VLM gibi bir 3B kanat modeliyle dağılımı çözün ve yerel profil
polarlarıyla ilişkilendirin. VLM tek başına stall ve viskoz sürüklemeyi çözmez.

Polar üretiminde tüm adaylar için Reynolds, Mach, Ncrit, geçiş konumları,
panelleme, çözücü sürümü ve yakınsama ölçütlerini kaydedin. Ncrit sınır tabaka
geçiş modelinin parametresidir; bilinmiyorsa tek kesin değer varsaymak yerine
senaryolarla duyarlılığını inceleyin.

Örnek deney matrisi: görev belirlendikten sonra Re = 100k, 200k, 400k, 600k, 1M;
α = −4°…12° ve 0.5° adım. Bunlar yalnızca başlangıç değerleridir; her profil için
geçerli aralık veya stall kapsaması garantisi vermez. 80 × 5 × 33 = **13,200
denenen analiz noktası / tek Mach ve geçiş senaryosu** eder. Yakınsamayan
noktalar bunun içinde başarısız denemelerdir.

Koşullar arasındaki interpolasyonu doğrulayın. Kapsam dışına taşan isteklerde
sessiz ekstrapolasyon yapmayın. Aynı Reynolds sayısı bile farklı yüzey veya geçiş
koşullarıyla üretilmiş polarları doğrudan karşılaştırılabilir yapmaz.

Sonuç ekranı öneriyi şu çerçevede açıklamalı:

> Belirlenen seyir koşulları ve kalınlık kısıtı altında bu üç aday değerlendirildi.
> Adayın tahmini sürüklemesi mevcut profilden daha düşük; moment gereksinimi ise
> daha yüksek. Sonuç şu veri aralığına ve şu model varsayımlarına dayanıyor.

Gerçek hesap yapılmadan iyileşme yüzdesi, uçuş süresi veya stall hızı üretmeyin.
Profil sürüklemesindeki azalmayı doğrudan toplam İHA sürüklemesi veya uçuş süresi
kazancı olarak sunmayın.

## 5. Bir yıllık takvim

Takvim yaklaşık bir yıl içindir. Gerçek ilk teslim tarihi belli olduğunda ara
teslimleri ona göre öne alın. Ekip kapasitesi bilinmediği için bunlar efor
garantisi değil, aşama ve çıktı önerileridir.

| Dönem | Çalışma | İncelenebilir çıktı / tamamlanma koşulu |
| --- | --- | --- |
| Ay 1 | Görev, İHA tipi, literatür ve veri şeması | Onaylanmış kapsam; 80 aday kaydı; 5 geometri çizimi |
| Ay 2 | İlk 5 profilin 2B polarları | Tekrarlanabilir koşullar, grafikler ve hata kayıtları |
| Ay 3 | Veri hattını 70–80 profile genişletme | Kaynak ve koşul bazında kapsama raporu; eksik listesi |
| Ay 4 | 2B model doğrulama | Deneysel polarlarla kıyas; ölçütler ve geçerli bölge |
| Ay 5 | Kısıtlı aday seçimi | Aynı uçuş noktasında gerekçeli ilk 3 aday; mevcut profil tabanı |
| Ay 6 | İlk kullanıcı arayüzü | Girdi → hesap → grafik → açıklama akışı |
| Ay 7–8 | 3B kanat, yerel polar ve trim etkileri | İki örnek kanat için karşılaştırmalı analiz |
| Ay 9 | Birden fazla uçuş noktası | Hız/kütle/yüzey belirsizliğine karşı aday sıralaması |
| Ay 10 | Laboratuvar veya uygun referans doğrulaması | Simülasyon–referans farkları ve hata nedenleri |
| Ay 11 | Kullanılabilirlik ve performans | Senaryo testleri, kullanıcı geri bildirimi, rapor dışa aktarımı |
| Ay 12 | Son rapor ve demonstrasyon | Tekrarlanabilir kurulum, sonuçlar ve sınırlılıklar |

Makine öğrenmesi ilk teslim için zorunlu değil. Sonradan yeterli veri ve ihtiyaç
oluşursa analiz hızlandırma modeli eklenebilir. Aynı profilin komşu açılarının
eğitim ve test setlerine rastgele dağılması yanıltıcı başarı verir; değerlendirmeyi
profil/geometri ve koşul grupları üzerinden ayırın. Tahmin edilen veri ile çözücü
ve deneysel veriyi ayrı etiketleyin.

## 6. İlk iki haftada tam olarak ne yapılmalı?

| Zaman | İş | Gün sonunda görülecek çıktı |
| --- | --- | --- |
| Gün 1–2 | Hocayla hedef, İHA tipi ve başarı ölçütlerini netleştirin | Bir sayfalık kapsam belgesi |
| Gün 3–4 | Bu depoyu çalıştırın; 80 aday kaydını inceleyin | SQLite veri tabanı ve kaynaklı CSV |
| Gün 5–7 | İlk 5 koordinatı toplayın ve çizin | 5 profil grafiği, geometri hata notları |
| Gün 8–10 | XFOIL'i kurup aynı koşullarda ilk polarları üretin | Ham çıktılar, ayar dosyaları, yakınsama günlüğü |
| Gün 11–14 | cl–α, cd–cl, cm–α grafiklerini inceleyin | İlk karşılaştırma ve doğrulama planı |

İlk haftanın başarı tanımı: “80 airfoilin hepsini optimize ettik” değil;
**verinin kaynağı belli, örnek uçuş koşulu hesaplanıyor ve beş profilin analiz
girdileri hazırlanabiliyor.**

## 7. Doğrulamayı baştan tasarlayın

- Hesapları birim ve elle kontrol edilen örneklerle doğrulayın.
- En az üç farklı profilde deneysel verinin Reynolds ve yüzey koşullarını
  eşleştirin; eşleşmeyen noktaları açıkça ayırın.
- Ortak aralıkta cl ve cd farklarını, sıfır kaldırma açısını ve veri kapsamını
  raporlayın. Stall yakınındaki uyuşmazlıkları ayrı değerlendirin.
- Yakınsamayan noktayı “sıfır sürükleme” veya “kesin stall” olarak yorumlamayın.
- Kabul edilebilir hatayı hocanızla, referans ölçüm belirsizliği ve kullanım
  amacı üzerinden belirleyin. Evrensel bir yüzde sınırı yoktur.
- Önerinin hız, kütle, geçiş ve yüzey koşullarına duyarlılığını gösterin.

## 8. Teknoloji ve iş paylaşımı

Şimdiki araç: Python standart kütüphanesi + SQLite. Böylece işe başlamak için
sunucu kurulumu veya ücretli servis gerekmez. Sonraki aşamada hesap ve grafik
için NumPy/SciPy/Pandas/Matplotlib; öğrenci demosu için Streamlit düşünülebilir.
Çok kullanıcılı ürüne ihtiyaç oluşursa FastAPI + PostgreSQL ve ayrı bir arayüze
geçin. Fizik/karşılaştırma kodunu arayüzden bağımsız tutun.

Ekip büyüklüğüne göre şu sorumlulukları paylaşın: aerodinamik ve doğrulama;
veri toplama ve analiz otomasyonu; yazılım ve kullanıcı deneyimi. Her hafta bir
kişi diğerinin çıktısını aynı girdilerle yeniden üretsin.

## Hocaya ilk görüşmede götürülecekler

1. İlk ürünün bir cümlelik tanımı ve kapsam sınırı.
2. 80 aday kaynak listesi ve listeyi daraltma ölçütleri.
3. Koordinat ile polar verisi ayrımını gösteren şema.
4. Örnek İHA hesabı ve ilk beş profilin analiz planı.
5. Doğrulama kaynakları, ölçütleri ve bir yıllık ara teslim takvimi.

Karara bağlanacak konular: İlk hedef İHA/görev; hocanın 70–80 profil için yalnız
koordinat mı yoksa aerodinamik polar da mı beklediği; kullanılabilecek deneysel
imkânlar ve ilk ara teslim tarihi.
