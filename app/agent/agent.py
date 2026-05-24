"""
CodeReviewAgent — main orchestration class.
"""

from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .diff_parser import FileDiff, parse_diff
from .llm_client import LLMClient
from .prompts import build_user_prompt, load_system_prompt


SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}

log = logging.getLogger(__name__)


@dataclass
class ReviewIssue:
    file: str
    line: int
    severity: str
    category: str
    message: str


@dataclass
class ReviewResult:
    issues: List[ReviewIssue] = field(default_factory=list)
    files_reviewed: int = 0
    files_skipped: int = 0
    skip_reasons: List[str] = field(default_factory=list)

    def filter_severity(self, min_severity: str) -> List[ReviewIssue]:
        threshold = SEVERITY_ORDER.get(min_severity, 0)
        return [
            i for i in self.issues
            if SEVERITY_ORDER.get(i.severity, 0) >= threshold
        ]

    def summary(self) -> str:
        if not self.issues:
            return f"No issues found across {self.files_reviewed} file(s)."

        counts = {"high": 0, "medium": 0, "low": 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1

        parts = [f"{n} {s}" for s, n in counts.items() if n > 0]
        return f"{len(self.issues)} issue(s) found ({', '.join(parts)}) across {self.files_reviewed} file(s)."


class CodeReviewAgent:
    def __init__(
        self,
        llm: LLMClient,
        standards_path: Optional[Path] = None,
        max_files_per_run: int = 20,
    ):
        self.llm = llm
        self.system_prompt = load_system_prompt(standards_path)
        self.max_files_per_run = max_files_per_run

    def review(self, diff_text: str) -> ReviewResult:
        file_diffs = parse_diff(diff_text)
        result = ReviewResult()

        if not file_diffs:
            return result

        for file_diff in file_diffs[: self.max_files_per_run]:
            try:
                issues = self._review_file(file_diff)
                result.issues.extend(issues)
                result.files_reviewed += 1
            except Exception as exc:
                log.error("Failed to review %s: %s", file_diff.path, exc, exc_info=True)
                result.files_skipped += 1
                result.skip_reasons.append(f"{file_diff.path}: {exc}")

        result.issues.sort(
            key=lambda i: (i.file, i.line, -SEVERITY_ORDER.get(i.severity, 0))
        )
        return result

    def _review_file(self, file_diff: FileDiff) -> List[ReviewIssue]:
        user_prompt = build_user_prompt(file_diff)
        response = self.llm.complete(self.system_prompt, user_prompt, max_tokens=8192)
        log.debug("LLM raw response for %s:\n%s", file_diff.path, response.text)
        issues = self._parse_response(response.text, file_diff.path)
        log.info("Reviewed %s — %d issue(s) found", file_diff.path, len(issues))
        return issues

    @staticmethod
    def _parse_response(response_text: str, file_path: str) -> List[ReviewIssue]:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.MULTILINE)

        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not json_match:
            return []

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return []

        issues = []
        for item in data.get("issues", []):
            try:
                issues.append(
                    ReviewIssue(
                        file=file_path,
                        line=int(item["line"]),
                        severity=str(item.get("severity", "low")).lower(),
                        category=str(item.get("category", "general")),
                        message=str(item["message"]),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue

        return issues
