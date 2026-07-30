from dataclasses import dataclass, field
from typing import List
import time

import easyocr


@dataclass
class TextRegion:
    text: str
    bbox: list          # 4 corner points from EasyOCR
    confidence: float


@dataclass
class OCRResult:
    image_path: str
    regions: List[TextRegion] = field(default_factory=list)
    processing_time_sec: float = 0.0

    @property
    def full_text(self) -> str:
        """Concatenate all detected text, roughly top-to-bottom."""
        sorted_regions = sorted(self.regions, key=lambda r: r.bbox[0][1])
        return "\n".join(r.text for r in sorted_regions)

    @property
    def avg_confidence(self) -> float:
        if not self.regions:
            return 0.0
        return sum(r.confidence for r in self.regions) / len(self.regions)


class OCRAgent:
    def __init__(self, languages=None, gpu=False):
        self.languages = languages or ["en"]
        self.reader = easyocr.Reader(self.languages, gpu=gpu)

    def run(self, image_path: str) -> OCRResult:
        start = time.time()
        raw_results = self.reader.readtext(image_path)  # [(bbox, text, conf), ...]
        elapsed = time.time() - start

        regions = [
            TextRegion(text=text, bbox=bbox, confidence=conf)
            for bbox, text, conf in raw_results
        ]
        return OCRResult(image_path=image_path, regions=regions, processing_time_sec=elapsed)


if __name__ == "__main__":
    import sys
    agent = OCRAgent()
    result = agent.run(sys.argv[1])
    print(f"Detected {len(result.regions)} text regions in {result.processing_time_sec:.2f}s")
    print(f"Average confidence: {result.avg_confidence:.2f}")
    print("---")
    print(result.full_text)