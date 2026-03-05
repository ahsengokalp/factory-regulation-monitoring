# factory-regulation-monitoring

Bu proje, Resmi Gazete fihristini gunluk olarak tarar, kayitlari fabrika departmanlarina gore siniflandirir ve ilgili birimlere e-posta gonderir.

Departmanlar:
- `isg`
- `ik`
- `muhasebe`
- `lojistik`

## Ne Yapar

1. Secilen gunun Resmi Gazete fihristini ceker.
2. Maddeleri parse eder (`title`, `url`, `section`, `subsection`).
3. LLM oncesi filtreleme uygular.
4. Aday kayitlarin detay metnini ceker (HTML/PDF/OCR fallback).
5. LLM ile coklu departman siniflandirmasi yapar.
6. Guven esigi (`confidence >= 40`) altini eler.
7. Departman bazli hit listesi olusturur.
8. Hit olan departmanlara e-posta yollar.
9. Tum mail sonucunu JSONL + bagimsiz HTML log ekranina yazar.

## LLM Akisi (Ozet)

- LLM'e her kayit gitmez.
- Once aday kapisi calisir (`SKIP_ILAN`, `SKIP_NEG_HARD`, `CANDIDATE_LLM`).
- Sadece `CANDIDATE_LLM` olan kayitlarin metni modele verilir.
- Modele giden metin: `text[:2500]` (ilk 2500 karakter).
- Model donusu: `isg/ik/muhasebe/lojistik + confidence + evidence`.
- `confidence < 40` ise kayit departmanlara dusmez.

## Proje Yapisi

```text
src/
  app/
    main.py                # CLI giris noktasi
    config.py              # .env ayarlari
    streamlit_debug.py     # Streamlit debug ekrani
    mail_log_dashboard.py  # log HTML'i manuel yeniden uretme komutu
  pipeline/
    run_daily.py           # ana orkestrasyon
  gazette/
    client.py              # gunluk URL ve HTML cekme
    parser.py              # fihrist parse
    detail_text.py         # detay metin cekme (html/pdf/ocr)
  llm/
    ollama_client.py       # Ollama siniflandirma istemcisi
  notify/
    emailer.py             # SMTP gonderimi + log event yazimi
    mail_log.py            # logs/mail_events.jsonl + logs/mail_log_dashboard.html
    templates.py           # e-posta HTML/subject
  policies/
    *.py                   # departman kurallari
```

## Kurulum

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```

## .env Ayarlari

`.env.example` dosyasini kopyalayin:

```bash
copy .env.example .env
```

Temel alanlar:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx@gmail.com
SMTP_PASSWORD=xxxx
SMTP_SECURE=true
SMTP_AUTH=true
SMTP_TLS_REJECT_UNAUTHORIZED=true
SMTP_ENABLED=true

MAIL_FROM=Toolbox <docker@dikkan.com>
ADMIN_MAIL_ENABLED=true
ADMIN_RECIPIENTS=admin1@company.com,admin2@company.com

ISG_RECIPIENTS=isg1@company.com,isg2@company.com
IK_RECIPIENTS=ik1@company.com,ik2@company.com
MUHASEBE_RECIPIENTS=muh1@company.com,muh2@company.com
LOJISTIK_RECIPIENTS=loj1@company.com,loj2@company.com

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
```

## Terminalden Calistirma

Belirli bir gun:

```bash
python -m src.app.main --date 2026-03-05
```

Bugun icin (PowerShell):

```powershell
python -m src.app.main --date (Get-Date -Format 'yyyy-MM-dd')
```

Calisinca:
- terminale item/hit/mail bilgileri basilir,
- SMTP aciksa mail gonderilir,
- mail sonucu log dosyalarina yazilir,
- admin alicilarina "calisti/calismadi" durum ozeti maili gonderilir.

## Admin Durum Maili

Her calistirmada admin tarafina durum maili gider:
- Basarili calismada: hangi departmanlara mail gittigi, kime gittigi, konu ve ornek basliklar.
- Hatali calismada: "calismadi" durumu + hata ozeti + traceback.

Kontrol ayarlari:
- `ADMIN_MAIL_ENABLED=true/false`
- `ADMIN_RECIPIENTS=...`

## Cron ile Gunluk Calistirma (Linux Sunucu)

Bu repo icine cron icin hazir script eklendi:
- `scripts/run_daily.sh`

Kurulum adimlari:

1. Script'i calistirilabilir yap:
```bash
chmod +x scripts/run_daily.sh
```

2. Elle test et:
```bash
./scripts/run_daily.sh
```

3. `crontab` girisi ekle (her gun saat 10:00, Istanbul):
```cron
CRON_TZ=Europe/Istanbul
0 10 * * * /opt/factory-regulation-monitoring/scripts/run_daily.sh
```

Not:
- Path'i kendi sunucu dizinine gore guncelleyin.
- Script varsayilan olarak bugun tarihini kullanir.
- Isterseniz tarih parametresi de verebilirsiniz: `./scripts/run_daily.sh 2026-03-05`

## Log Ekrani (Streamlit'ten Bagimsiz)

Bu ekran Streamlit degil, dogrudan HTML dosyasidir.

Uretilen dosyalar:
- `logs/mail_events.jsonl` (ham event kaydi)
- `logs/mail_log_dashboard.html` (gorsel log ekrani)

Mail gonderim adiminda event geldiginde dashboard otomatik guncellenir.

Manuel yeniden uretmek icin:

```bash
python -m src.app.mail_log_dashboard
```

Acma yollari:

```powershell
start .\logs\mail_log_dashboard.html
```

veya dosyaya cift tik:
- `logs/mail_log_dashboard.html`

Ekranda gorulen alanlar:
- time
- status (`sent`, `failed`, `skipped_disabled`, `failed_no_recipients`)
- from
- recipients
- subject
- content preview
- message

Logo kullanimi:
- `assets/dikkan_logo.png` (veya `.jpg`, `.jpeg`, `.svg`) dosyasi varsa dashboard tepesinde otomatik gosterilir.

## Debug Ekrani (Ayri)

Bu ekran Streamlit tabanli inceleme ekranidir ve log HTML'den bagimsizdir.

Calistirma:

```bash
streamlit run src/app/streamlit_debug.py
```

Tarayici:
- `http://localhost:8501`

Import sorunu olursa:

```powershell
$env:PYTHONPATH = (Get-Location).Path
streamlit run src/app/streamlit_debug.py
```

Debug tablari:
- `Overview`: URL, HTML boyutu, settings ozeti, section dagilimi
- `Items`: parse edilen tum kayitlar + candidate status
- `Policies`: policy/score/reason gorunumu
- `LLM`: LLM raw cevaplari ve confidence
- `Email Preview`: gonderim onizleme, istenirse manuel gonderim
- `HTML`: cekilen ham HTML kesiti

## Calisma Akisi (Uctan Uca)

1. `src.app.main` -> `run_daily.run` cagirilir.
2. Gunluk index cekilir, maddeler parse edilir.
3. Aday kapisiyla LLM oncesi filtreleme yapilir.
4. Adaylarin detay metni cekilir.
5. LLM siniflandirir (`text[:2500]`).
6. Confidence gate uygulanir.
7. Departman hit listeleri olusur.
8. Hit varsa departman bazli subject/body hazirlanir.
9. SMTP ile gonderim denenir.
10. Sonuc `mail_log.append_mail_event` ile kaydedilir.
11. `logs/mail_log_dashboard.html` guncellenir.

## Kisa Sorun Giderme

- Mail gitmiyorsa:
  - `SMTP_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` alanlarini kontrol edin.
  - Alici listeleri bos olmamali.
  - Kurumsal firewall/SMTP erisimini kontrol edin.

- Log ekrani bossa:
  - henuz hic mail olayi olusmamis olabilir.
  - bir kez pipeline calistirip tekrar acin.
  - gerekirse `python -m src.app.mail_log_dashboard` ile yeniden uretin.

- Debug ekrani acilmiyorsa:
  - komutu proje kokunden calistirin.
  - gerekirse `PYTHONPATH` ayarlayin.
