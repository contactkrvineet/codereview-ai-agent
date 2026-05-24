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
      "category": "<short tag, e.g. 'naming', 'selector', 'assertion'>",
      "message": "<one-sentence description of the issue and how to fix it>"
    }}
  ]
}}

Rules:
- Only flag issues that violate the documented standards. Do not invent rules.
- If the change looks clean, return {{"issues": []}}.
- Be specific about line numbers — use the line number from the diff annotation.
- Keep messages concise and actionable. No fluff.
- Severity guide:
  * "high"   = correctness, security, or strong convention violations
  * "medium" = maintainability or readability issues
  * "low"    = nitpicks (style, formatting suggestions)
"""
