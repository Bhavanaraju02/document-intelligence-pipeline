import os
import re
import json
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


EXTRACTION_SCHEMA_PROMPT = """You are a document field extraction agent. \
You will be given noisy OCR text from a scanned receipt. Extract the \
following fields as JSON, using null when a field cannot be determined. \
Do not invent values that are not supported by the text.

Return ONLY valid JSON, no preamble, no markdown fences, matching this schema:
{
  "vendor_name": string or null,
  "date": string or null,
  "total": number or null,
  "line_items": [{"name": string, "price": number}],
  "confidence_notes": string  // brief note on anything ambiguous
}

OCR TEXT:
---
{ocr_text}
---
JSON:"""


@dataclass
class ExtractedFields:
    vendor_name: Optional[str] = None
    date: Optional[str] = None
    total: Optional[float] = None
    line_items: list = None
    confidence_notes: str = ""
    extraction_method: str = "rule_based"

    def to_dict(self):
        return asdict(self)


class ExtractionAgent:
    def __init__(self, use_llm: Optional[bool] = None, model: str = "claude-sonnet-4-6"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.use_llm = (use_llm if use_llm is not None else bool(api_key)) and _ANTHROPIC_AVAILABLE
        self.model = model
        if self.use_llm:
            self.client = anthropic.Anthropic(api_key=api_key)

    def run(self, ocr_text: str) -> ExtractedFields:
        if self.use_llm:
            try:
                return self._extract_with_llm(ocr_text)
            except Exception as e:
                # Fall back gracefully rather than crashing the pipeline
                fields = self._extract_with_rules(ocr_text)
                fields.confidence_notes = f"LLM call failed ({e}); used rule-based fallback."
                return fields
        return self._extract_with_rules(ocr_text)

    def _extract_with_llm(self, ocr_text: str) -> ExtractedFields:
        prompt = EXTRACTION_SCHEMA_PROMPT.format(ocr_text=ocr_text)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return ExtractedFields(
            vendor_name=data.get("vendor_name"),
            date=data.get("date"),
            total=data.get("total"),
            line_items=data.get("line_items", []),
            confidence_notes=data.get("confidence_notes", ""),
            extraction_method="llm",
        )

    def _extract_with_rules(self, ocr_text: str) -> ExtractedFields:
        total_match = re.search(r"(?:total|amount due)[:\s]*\$?(\d+\.\d{2})", ocr_text, re.I)
        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", ocr_text)
        lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]
        vendor_guess = lines[0] if lines else None

        return ExtractedFields(
            vendor_name=vendor_guess,
            date=date_match.group(1) if date_match else None,
            total=float(total_match.group(1)) if total_match else None,
            line_items=[],
            confidence_notes="Rule-based extraction: vendor is a guess (first line), "
                              "line items not parsed.",
            extraction_method="rule_based",
        )


if __name__ == "__main__":
    import sys
    sample_text = sys.stdin.read() if not sys.stdin.isatty() else sys.argv[1]
    agent = ExtractionAgent()
    fields = agent.run(sample_text)
    print(json.dumps(fields.to_dict(), indent=2))