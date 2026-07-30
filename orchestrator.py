import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

from agents.ocr_agent import OCRAgent
from agents.extraction_agent import ExtractionAgent
from agents.validation_agent import ValidationAgent

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT,
    ocr_avg_confidence REAL,
    ocr_time_sec REAL,
    extraction_method TEXT,
    vendor_name TEXT,
    date TEXT,
    total REAL,
    line_items_json TEXT,
    is_valid INTEGER,
    validation_issues TEXT,
    validation_pass_rate REAL,
    processed_at TEXT
);
"""


class DocumentPipeline:
    def __init__(self, db_path: str = "pipeline_results.db", use_llm: bool = None):
        self.ocr_agent = OCRAgent()
        self.extraction_agent = ExtractionAgent(use_llm=use_llm)
        self.validation_agent = ValidationAgent()
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(SCHEMA)
        conn.commit()
        conn.close()

    def process_document(self, image_path: str) -> dict:
        ocr_result = self.ocr_agent.run(image_path)
        fields = self.extraction_agent.run(ocr_result.full_text)
        report = self.validation_agent.run(fields)

        record = {
            "image_path": image_path,
            "ocr_avg_confidence": ocr_result.avg_confidence,
            "ocr_time_sec": ocr_result.processing_time_sec,
            "extraction_method": fields.extraction_method,
            "vendor_name": fields.vendor_name,
            "date": fields.date,
            "total": fields.total,
            "line_items_json": json.dumps(fields.line_items or []),
            "is_valid": int(report.is_valid),
            "validation_issues": json.dumps(report.issues),
            "validation_pass_rate": report.pass_rate,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save(record)
        return record

    def _save(self, record: dict):
        conn = sqlite3.connect(self.db_path)
        cols = ", ".join(record.keys())
        placeholders = ", ".join("?" for _ in record)
        conn.execute(f"INSERT INTO documents ({cols}) VALUES ({placeholders})",
                     list(record.values()))
        conn.commit()
        conn.close()

    def process_folder(self, images_dir: str):
        image_paths = sorted(
            p for p in Path(images_dir).glob("*")
            if p.suffix.lower() in {".png", ".jpg", ".jpeg"}
        )
        print(f"Found {len(image_paths)} images in {images_dir}")
        for i, path in enumerate(image_paths, 1):
            print(f"[{i}/{len(image_paths)}] Processing {path.name} ...")
            try:
                record = self.process_document(str(path))
                status = "VALID" if record["is_valid"] else "FLAGGED"
                print(f"    -> {status}  total={record['total']}  "
                      f"method={record['extraction_method']}")
            except Exception as e:
                print(f"    -> ERROR: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images_dir", required=True)
    parser.add_argument("--db", default="pipeline_results.db")
    parser.add_argument("--use_llm", action="store_true",
                         help="Force LLM extraction (requires ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()

    pipeline = DocumentPipeline(db_path=args.db, use_llm=args.use_llm or None)
    pipeline.process_folder(args.images_dir)
    print(f"\nDone. Results saved to {args.db}")


if __name__ == "__main__":
    main()