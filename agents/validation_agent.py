from dataclasses import dataclass, field
from typing import List
from datetime import datetime
import re

from agents.extraction_agent import ExtractedFields


@dataclass
class ValidationReport:
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0

    @property
    def pass_rate(self) -> float:
        return self.checks_passed / self.checks_run if self.checks_run else 0.0


class ValidationAgent:
    def run(self, fields: ExtractedFields) -> ValidationReport:
        issues = []
        checks = 0
        passed = 0

        # Check 1: total present and positive
        checks += 1
        if fields.total is not None and fields.total > 0:
            passed += 1
        else:
            issues.append("Missing or non-positive total.")

        # Check 2: date is parseable and not in the future
        checks += 1
        parsed_date = self._try_parse_date(fields.date)
        if parsed_date and parsed_date <= datetime.now():
            passed += 1
        else:
            issues.append(f"Date missing, unparseable, or in the future: {fields.date!r}")

        # Check 3: vendor name present and plausible (not just digits/symbols)
        checks += 1
        if fields.vendor_name and re.search(r"[A-Za-z]{2,}", fields.vendor_name):
            passed += 1
        else:
            issues.append("Vendor name missing or implausible.")

        # Check 4: if line items exist, they should sum close to total
        checks += 1
        if fields.line_items:
            line_sum = sum(item.get("price", 0) for item in fields.line_items)
            if fields.total and abs(line_sum - fields.total) < max(0.05 * fields.total, 0.5):
                passed += 1
            else:
                issues.append(f"Line items sum ({line_sum:.2f}) doesn't match total "
                              f"({fields.total}).")
        else:
            issues.append("No line items extracted (informational, not a hard failure).")
            passed += 1  # informational only, doesn't fail the doc

        return ValidationReport(
            is_valid=(len(issues) == 0 or all("informational" in i for i in issues)),
            issues=issues,
            checks_run=checks,
            checks_passed=passed,
        )

    @staticmethod
    def _try_parse_date(date_str):
        if not date_str:
            return None
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None