"""
Prompt construction for the agent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .diff_parser import FileDiff, format_diff_for_prompt

# Resolve prompts directory relative to project root
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def load_system_prompt(standards_path: Optional[Path] = None) -> str:
    """Build the system prompt: agent persona + coding standards."""
    persona = (PROMPTS_DIR / "system_prompt.md").read_text()

    if standards_path is None:
        standards_path = PROMPTS_DIR / "qe_standards.md"
    standards = standards_path.read_text()

    return f"{persona}\n\n---\n\n# Team Coding Standards\n\n{standards}"


def build_user_prompt(file_diff: FileDiff) -> str:
    """Build the user-message prompt for a single file's diff."""
    diff_text = format_diff_for_prompt(file_diff)

    return f"""Review the following code changes against the team coding standards.

{diff_text}

Return a JSON object with this exact structure:
{{
  "issues": [
    {{
      "line": <integer, line number in the new file>,
      "severity": "high" | "medium" | "low",
      "category": "<short tag, e.g. 'naming', 'error-handling', 'security', 'magic-number'>",
      "message": "<one-sentence description of the issue and how to fix it>"
    }}
  ]
}}

Rules:
- Flag every clear violation of the documented standards. Do not skip obvious issues.
- If after careful review no standards are violated, return {{"issues": []}}.
- Be specific about line numbers — use the line number from the diff annotation.
- Do not add commentary outside the JSON.
- Keep messages concise and actionable.
- Severity guide: "high" = security/correctness/strong convention; "medium" = maintainability/readability; "low" = style nitpick.
"""
