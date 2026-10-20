# PyCharm ile açma ve çalıştırma

Bu sürüm ayrı bir masaüstü penceresinde çalışır. İlk deneme için internete veya
ek Python paketine ihtiyaç duymaz. Python 3.10+ ve Tkinter gerekir.

Windows'ta ZIP'i çıkardıktan sonra **BASLAT.bat** dosyasına çift tıklayarak
PyCharm açmadan da başlatabilirsiniz. Başlatıcı kurulu Python'u kullanır;
Python kurulu değilse bunu bildirir. Bu paket bağımsız bir `.exe` içermez.

## 1. Proje klasörünü açın

ZIP dosyasını bilgisayarınıza indirin ve tümünü çıkarın. Paket içindeki proje
klasörünün adı **İHA Optimizasyon Uygulaması Projesi** olarak ayarlanmıştır.
PyCharm'da **File > Open** ile bu klasörü seçin. ZIP dosyasının içinden tek bir
Python dosyası açmak yerine, `main.py` ve `schema.sql` dosyalarının beraber
bulunduğu klasörü açın.

Dosya yapısı şu şekilde görünmeli:

```text
İHA Optimizasyon Uygulaması Projesi/
    main.py
    desktop_app.py
    app_service.py
    BASLAT.bat
    uav.py
    schema.sql
    README.md
    PYCHARM_KURULUM.md
    YOL_HARITASI.md
    .run/
    data/
        airfoil_candidates.csv
        raw/
            naca2412.dat
            s1223.dat
    examples/
        aircraft.json
    tests/
```

Türkçe harfler ve boşluklar korunmuştur. Başlangıç kodu veri dosyalarını kendi
konumuna göre bulur; terminalin hangi klasörde olduğuna bağlı değildir.

## 2. Python yorumlayıcısını seçin

**“Python bulunamadı” hatası için:** `git init`, Git sürüm takibini başlatır;
Python kurulumu veya yorumlayıcı ayarı yapmaz. Önce aşağıdaki adımları uygulayın:

1. Python bilgisayarınızda kurulu değilse [resmi Python indirme sayfasından](https://www.python.org/downloads/)
   işletim sisteminize uygun Python 3.10+ kurulumunu tamamlayın. Kuruluysa bu
   adımı atlayın.
2. PyCharm ayarlarında **Python > Interpreter** bölümünü açın. Bazı sürümlerde
   bu bölüm **Project > Python Interpreter** altında bulunur.
3. **Add Interpreter > Add Local Interpreter** seçin.
4. Yeni bir **Virtualenv** oluşturun ve **Base interpreter** alanında kurulu
   Python'u seçin. Listede yoksa gözat düğmesiyle gerçek Python çalıştırılabilir
   dosyasını bulun. Windows'ta bu dosya `python.exe`, macOS/Linux'ta genellikle
   `python3` adını taşır.
5. Ortam konumu için projenin içindeki `.venv` klasörünü kullanın ve onaylayın.
   Ardından `main.py` dosyasına sağ tıklayıp Run seçin.

Resmi adımlar: [PyCharm Python interpreter ayarı](https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html).

Proje için **Python 3.10 veya üzeri** bir yorumlayıcı seçin. PyCharm yorumlayıcı
tanımlı olmadığını bildirirse proje ayarlarından Python Interpreter bölümünü
açın. Kurulu Python'u kullanabilir veya onunla bir `.venv` oluşturabilirsiniz.
Bilgisayarınızda Python kurulu değilse önce Python kurulmalıdır.

Paket herhangi bir bilgisayara ait sabit Python yolu içermez. Bu nedenle yerel
yorumlayıcıyı ilk açılışta sizin seçmeniz gerekir. PyCharm sürümüne ve işletim
sistemine göre ayarların menü konumu değişebilir.

## 3. Masaüstü uygulamasını çalıştırın

`main.py` dosyasına sağ tıklayıp **Run 'main'** seçin. Parametre girmeniz gerekmez.
Paket ayrıca proje yorumlayıcısını kullanan **IHA Masaustu Uygulamasi** çalıştırma ayarını
`.run/` klasöründe içerir. Bu ayar görünmezse doğrudan `main.py` üzerinden Run
kullanabilirsiniz.

Başarılı çalıştırmada **AERO DESIGN LAB** başlıklı çalışma alanı açılır. Solda
Genel Bakış, İHA Tasarımı, Airfoil Kütüphanesi, Karşılaştırma ve Yol Haritası
bölümleri bulunur.

**İHA Tasarımı** bölümünde örnek girdileri değiştirip **Uçuş Koşullarını Hesapla**
butonuna basın. Sonuç kartları aşağıda görünür. **Tasarımı Kaydet** ve **Tasarım Aç**
butonları JSON proje dosyalarıyla çalışır. CSV butonu hesaplama raporu verir.

**Airfoil Kütüphanesi** bölümünde arama yapın veya aile filtresini kullanın.
Listeden seçtiğiniz profilin geometrisi altta görünür. **DAT Dosyası Ekle** ile
seçili profile koordinat ekleyebilirsiniz. **Karşılaştırma** bölümünde NACA 2412
ve S1223'ü seçerek iki gerçek geometriyi ortak ölçekte görün.

Veri tabanı `data/airfoils.sqlite3` içinde otomatik oluşur. Tekrar çalıştırmak aynı
kayıtları çoğaltmaz. 80 aday kaydı, 2 hazır geometri vardır; henüz performans
önerisi üretilmez. Python komut satırı hesabı için `uav.py` kullanılabilir.

## Sorun giderme

| Belirti | Kontrol |
| --- | --- |
| Python interpreter tanımlı değil | Proje için kurulu Python 3.10+ seçin. |
| `the following arguments are required: command` | Parametresiz başlangıç için `main.py` çalıştırın. `uav.py` komut satırı aracıdır. |
| `No module named uav` | `main.py` ve `uav.py` aynı proje klasöründe olmalı; ZIP'in tümünü çıkarın. |
| `schema.sql` veya CSV bulunamadı | Yalnızca `.py` dosyalarını taşımayın; `data/` ve `examples/` dahil proje klasörünün tamamını çıkarın. |
| Yazma izni hatası | ZIP'i kullanıcı hesabınızın yazabildiği normal bir klasöre çıkarın. |
| Hazır çalıştırma ayarında modül bulunamadı | `main.py` dosyasına sağ tıklayıp Run seçerek yerel bir ayar oluşturun. |

Komut satırı seçenekleri ve testler için `README.md` dosyasına bakın.
