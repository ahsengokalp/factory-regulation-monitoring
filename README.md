# factory-regulation-monitoring

Resmî Gazete günlük içeriklerini çekip departman bazlı policy kurallarıyla filtreleyen, sonuçları e-posta olarak gönderen bir Python projesi.

Departmanlar:
- `isg`
- `ik`
- `muhasebe`
- `lojistik`

## Nasıl Çalışır

Sistem her çalışmada bu adımları izler:

1. Verilen tarihe göre Resmî Gazete URL’i üretilir.
2. Günlük sayfanın HTML’i çekilir.
3. HTML içinden fihrist maddeleri parse edilir (`title`, `url`, `section`, `subsection`).
4. Her madde, her departman policy’sine göre puanlanır.
5. Policy sonucu `is_relevant=True` olan maddeler `hit` sayılır.
6. Her departman için hit varsa ilgili alıcılara HTML e-posta gönderilir.

## Proje Yapısı

```text
src/
  app/
    main.py              # CLI giriş noktası
    config.py            # .env ayarları (SMTP + alıcılar)
    streamlit_debug.py   # görsel debug ekranı
  core/
    models.py            # GazetteItem veri modeli
    http.py              # requests session + retry
  gazette/
    client.py            # günlük URL ve HTML çekme
    parser.py            # HTML -> GazetteItem listesi
  policies/
    base.py              # DepartmentPolicy ve PolicyDecision
    isg.py
    ik.py
    muhasebe.py
    lojistik.py
  notify/
    emailer.py           # SMTP mail gönderimi
    templates.py         # generic HTML mail şablonları
  pipeline/
    run_daily.py         # orchestrator (fetch/parse/evaluate/send)
```

## Kurulum

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```

## .env Ayarları

`.env.example` dosyasını kopyalayın:

```bash
copy .env.example .env
```

Minimum gerekli değişkenler:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx@gmail.com
SMTP_PASSWORD=xxxx
MAIL_FROM=xxx@gmail.com

ISG_RECIPIENTS=isg1@company.com,isg2@company.com
IK_RECIPIENTS=ik1@company.com,ik2@company.com
MUHASEBE_RECIPIENTS=muh1@company.com,muh2@company.com
LOJISTIK_RECIPIENTS=loj1@company.com,loj2@company.com
```

Notlar:
- Gmail kullanıyorsanız App Password gerekir (2FA açık olmalı).
- Kurumsalda genelde Exchange / Office365 SMTP kullanılır.
- `.env` dosyası BOM içeriyorsa config tarafı `utf-8-sig` ile okuyacak şekilde ayarlıdır.

## CLI ile Çalıştırma

Belirli bir tarih için:

```bash
python -m src.app.main --date 2026-02-27
```

Bu komut:
- veriyi çeker,
- policy’leri çalıştırır,
- hit’leri konsola yazar,
- hit olan departmanlara e-posta gönderir.

## Streamlit Debug Ekranı

Debug UI tüm akışı görsel olarak incelemek için vardır.

Çalıştırma:

```bash
streamlit run src/app/streamlit_debug.py
```

Tarayıcıda genelde: `http://localhost:8501`

Import yolu sorunu yaşarsanız:

```powershell
$env:PYTHONPATH = (Get-Location).Path
streamlit run src/app/streamlit_debug.py
```

### Sol Panel Seçenekleri

- `Date`: Hangi günün verisi işlenecek.
- `Table row limit`: Tablolarda gösterilecek maksimum satır.
- `Only show relevant policy rows`: Sadece `is_relevant=True` satırlarını göster.
- `Enable real email sending`: Açıkken panel içinden gerçek e-posta gönderimine izin ver.
- `Run debug`: Akışı çalıştır.

### Debug Sekmeleri

- `Overview`
  - Çekilen URL, HTML boyutu, env ayar özeti (şifre maskeli)
  - section/subsection dağılımı
  - cross-policy matrix (bir kaydı hangi policy’ler tuttu)
- `Items`
  - Parse edilen tüm maddeler
- `Policies`
  - Policy bazında skor, reason, hit oranı
- `Email Preview`
  - Departman bazında alıcı listesi, subject ve HTML önizleme
  - İstenirse seçili departmanlar için gerçek gönderim
- `HTML`
  - Çekilen ham HTML’den kesit

## Policy Skorlama Mantığı

Tüm policy dosyaları aynı prensiple çalışır:

- `HIGH_SIGNAL` regex eşleşmesi: `+10`
- `MID_SIGNAL` regex eşleşmesi: `+3`
- Toplam skor `>= 10` ise kayıt ilgili kabul edilir.
- `section` içinde `İLAN` geçerse doğrudan dışlanır (`score=0`).

## E-posta Routing

`pipeline/run_daily.py` içinde departman -> alıcı eşlemesi:

- `isg -> ISG_RECIPIENTS`
- `ik -> IK_RECIPIENTS`
- `muhasebe -> MUHASEBE_RECIPIENTS`
- `lojistik -> LOJISTIK_RECIPIENTS`

Her departman için `hits` varsa:
- subject `build_generic_email_subject(...)`
- body `build_generic_email_html(...)`
- SMTP gönderim `send_html_email(...)`

## Hızlı Sorun Giderme

- `ModuleNotFoundError: No module named 'src'`
  - `streamlit run src/app/streamlit_debug.py` komutunu proje kökünden çalıştırın.
  - Gerekirse `PYTHONPATH` komutunu kullanın (üstte var).

- `SMTP_HOST Field required`
  - `.env` dosyasını kontrol edin.
  - İlk satırda BOM kaynaklı bozulma varsa dosyayı UTF-8 (veya UTF-8 BOM) formatında kaydedin; config `utf-8-sig` ile okumaya ayarlı.

- Mail gitmiyor
  - SMTP host/port/user/pass doğruluğunu test edin.
  - Gmail’de App Password kullandığınızdan emin olun.
  - Ağ/Firewall/SMTP erişim kısıtlarını kontrol edin.
