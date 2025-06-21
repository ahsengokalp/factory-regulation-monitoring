# factory-regulation-monitoring

Resmi Gazete icerigini gunluk cekip departman policy kurallari ile (ilk adimda ISG) filtreleyen Python projesi.

## Kurulum

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
```

## Ayarlar

```bash
copy .env.example .env
```

Ornek:
- `RG_BASE_URL`: Resmi Gazete ana URL
- `RG_DAILY_PATH`: Gunluk sayfa yolu (`eskiler/YYYY/MM/YYYYMMDD.htm`)
- `ISG_MIN_SCORE`: ISG policy esik skoru

## Calistirma

```bash
factory-monitor --dry-run
```

veya

```bash
python -m app.main --dry-run
```
