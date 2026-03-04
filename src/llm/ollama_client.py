from __future__ import annotations

import json
import time
from dataclasses import dataclass
import requests

DEPT_LABELS = {
    "isg": "İş Sağlığı ve Güvenliği",
    "ik": "İnsan Kaynakları",
    "muhasebe": "Muhasebe / Vergi / Finans",
    "lojistik": "Lojistik / Dış Ticaret / Gümrük",
}


@dataclass(frozen=True)
class LlmDecision:
    relevant: bool
    confidence: int
    evidence: str
    raw: str


@dataclass(frozen=True)
class MultiDeptDecision:
    isg: bool
    ik: bool
    muhasebe: bool
    lojistik: bool
    confidence: int
    evidence: str
    raw: str


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_s: int = 240) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def _post_generate(self, payload: dict) -> str:
        last_err = None
        for attempt in range(3):  # 3 deneme
            try:
                r = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout_s,
                )
                r.raise_for_status()
                return (r.json().get("response") or "").strip()
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                last_err = e
                time.sleep(2 + attempt * 2)  # backoff
        if last_err is not None:
            raise last_err
        raise RuntimeError("Ollama generate failed without an explicit transport error")

    def classify(self, *, department: str, title: str, text: str, url: str = "") -> LlmDecision:
        dept_tr = DEPT_LABELS.get(department, department)
        prompt = _build_prompt(department=dept_tr, title=title, url=url, text=text)

        raw = self._post_generate(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "top_p": 0.9},
            }
        )
        return _parse(raw)

    def classify_multi(self, *, title: str, text: str, url: str = "") -> MultiDeptDecision:
        prompt = f"""
Sen bir mevzuat analiz uzmanısın.

Görev:
Aşağıdaki Resmî Gazete içeriği bir fabrikada hangi departmanları etkiler?
Departmanlar: ISG, IK, MUHASEBE, LOJISTIK

Ön kapı sorusu (zorunlu):
"Bu düzenleme özel sektör üretim işletmelerinin yükümlülüklerini değiştiriyor mu?"
- Önce bu soruyu cevapla.
- Cevap HAYIR ise departmanların tamamı false olmalı (isg=false, ik=false, muhasebe=false, lojistik=false).
- Cevap EVET ise departmanları ayrı ayrı değerlendir.

Kritik kural:
Başlık ipucu olabilir ama nihai kararı metindeki uygulanabilir yükümlülük/değişiklik/sorumluluk üzerinden ver.

Genel dışlama kuralları:
- İlan/duyuru (vefat, etkinlik, ihale ilanı, üniversite iç yönetmelik vb.) ise genelde hepsi false.
- Belirli proje/il/taşınmaz kamulaştırması ise genelde hepsi false (fabrikayı doğrudan etkilemediği sürece).

Sektörel kurallar:
- Bankacılık/TCMB düzenlemeleri genelde ISG/IK/LOJISTIK=false olabilir; ancak şirket finansını etkilediği için MUHASEBE=true olabilir.
- Kamu kurum içi kadro/atama/teşkilat düzenlemesi genelde hepsi false; istisna: çalışma hayatı/iş hukuku/SGK gibi genel bir yükümlülük içeriyorsa IK=true olabilir.

Departman Tanımları (fabrika bağlamı):
- ISG: iş sağlığı ve güvenliği, 6331, risk değerlendirme, iş kazası, acil durum, OSGB vb.
- IK: işe alım, personel, ücret, izin, SGK, çalışma izni, iş kanunu, disiplin vb.
- MUHASEBE: vergi, KDV, e-fatura/e-defter, finans, faiz, karşılık, muhasebe standartları vb.
- LOJISTIK: gümrük, GTIP, ithalat/ihracat, dış ticaret mevzuatı, antrepo, ADR, taşıma, tedarik vb.

Lojistik guard:
LOJISTIK=true demek için metinde/başlıkta şu kelimelerden en az biri açıkça geçmeli:
gümrük, GTİP, ithalat, ihracat, dış ticaret, antrepo, A.TR, EUR.1, navlun, konşimento, ADR, taşıma, nakliye, liman, konteyner.
Bu kelimeler yoksa LOJISTIK=false.

Not: "dış ticaret" ve "ihracat/ithalat" konuları IK değil, LOJISTIK kapsamındadır.

Evidence zorunludur:
Metinden en az bir ifade/kurum adı al ve "fabrikaya etkisini" tek cümlede yaz.
Genel/yuvarlak gerekçe yazma.

Sadece TEK SATIR JSON döndür.

Format:
{{"affects_private_manufacturing_obligations": true/false,
"isg": true/false, "ik": true/false, "muhasebe": true/false, "lojistik": true/false,
"confidence": 0-100, "evidence": "metinden kanıt + fabrikaya etkisi"}}

Başlık: {title}
URL: {url}

METİN:
{text}
""".strip()

        raw = self._post_generate(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "top_p": 0.9},
            }
        )
        try:
            obj = _parse_json_object(raw)
            affects_obligations = _as_bool(obj.get("affects_private_manufacturing_obligations", True))
            confidence = int(obj.get("confidence", 0))
            evidence = str(obj.get("evidence", "")).strip()

            if not affects_obligations:
                return MultiDeptDecision(
                    isg=False,
                    ik=False,
                    muhasebe=False,
                    lojistik=False,
                    confidence=confidence,
                    evidence=evidence,
                    raw=raw,
                )

            return MultiDeptDecision(
                isg=_as_bool(obj.get("isg", False)),
                ik=_as_bool(obj.get("ik", False)),
                muhasebe=_as_bool(obj.get("muhasebe", False)),
                lojistik=_as_bool(obj.get("lojistik", False)),
                confidence=confidence,
                evidence=evidence,
                raw=raw,
            )
        except Exception:
            return MultiDeptDecision(False, False, False, False, 0, "", raw)


def _build_prompt(*, department: str, title: str, url: str, text: str) -> str:
    return f"""
Sen bir mevzuat analiz uzmanısın.

Görev:
Aşağıdaki içerik "{department}" departmanını bir fabrikada (uyum/operasyon) etkileyecek bir düzenleme içeriyor mu?

Kurallar:
- İlan/duyuru (vefat, etkinlik, üniversite iç yönetmelik vb.) ise genelde NO.
- Sadece metne dayan.
- Başlık sadece ipucudur; nihai kararı metindeki uygulanabilir yükümlülük/değişiklik/sorumluluk üzerinden ver.
- Sadece bankalar/finansal kuruluşlara yönelik düzenleme ise NO.
- Sadece kamu kurum içi kadro/atama/teşkilat düzenlemesi ise NO.
- Belirli proje/il/taşınmaz kamulaştırması ise (fabrikanın adı geçmiyorsa) NO.
- Cevabı sadece TEK SATIR JSON olarak ver.
Evidence zorunludur: metinden en az bir ifade/kurum adı ve fabrikaya etkisini tek cümlede birlikte yaz.

Format (tek satır JSON):
{{"relevant": true/false, "confidence": 0-100, "evidence": "metinden kanıt + fabrikaya etkisi"}}

Başlık: {title}
URL: {url}

METİN:
{text}
""".strip()


def _parse(raw: str) -> LlmDecision:
    try:
        obj = _parse_json_object(raw)
        return LlmDecision(
            relevant=_as_bool(obj.get("relevant", False)),
            confidence=int(obj.get("confidence", 0)),
            evidence=str(obj.get("evidence", "")).strip(),
            raw=raw,
        )
    except Exception:
        return LlmDecision(False, 0, "", raw)


def _parse_json_object(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in LLM response")

    parsed = json.loads(raw[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON is not an object")
    return parsed


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "evet"}:
            return True
        if normalized in {"false", "0", "no", "n", "hayır", "hayir", ""}:
            return False
    return False
