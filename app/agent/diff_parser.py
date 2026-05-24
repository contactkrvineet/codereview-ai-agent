"""
Git diff parser.

Parses unified diff format (output of `git diff`) into structured objects
the agent can reason about. Uses the `unidiff` library for robust parsing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from unidiff import PatchSet


# File extensions the agent will analyze.
# Covers source code, config, templates, infra, and data files.
DEFAULT_REVIEWABLE_EXTENSIONS = {
    # Application code
    ".py", ".java", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rb", ".rs", ".kt", ".scala", ".cs", ".cpp", ".c", ".h",
    ".swift", ".php", ".dart",
    # Config / infra
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".env",
    ".json", ".xml",
    # Web / templates
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".jinja", ".jinja2",
    # Shell / scripts
    ".sh", ".bash", ".zsh", ".ps1", ".bat",
    # Data / DB
    ".sql", ".graphql", ".gql",
    # Docs (only when they contain code-like content)
    ".md", ".rst",
    # Test-specific
    ".feature",
}

log = logging.getLogger(__name__)


@dataclass
class DiffHunk:
    """A single contiguous change block within a file."""

    start_line: int           # First line number in the new file
    end_line: int             # Last line number in the new file
    content: str              # The actual diff text (with +/- prefixes)
    is_addition_only: bool    # True if only adds lines (no removals)


@dataclass
class FileDiff:
    """All changes for a single file."""

    path: str
    hunks: List[DiffHunk] = field(default_factory=list)
    is_new_file: bool = False
    is_deleted: bool = False

    @property
    def extension(self) -> str:
        return Path(self.path).suffix.lower()

    @property
    def line_count(self) -> int:
        return sum(h.end_line - h.start_line + 1 for h in self.hunks)


def parse_diff(diff_text: str, reviewable_extensions: Optional[set] = None) -> List[FileDiff]:
    """
    Parse a unified diff into structured FileDiff objects.

    Filters out files with extensions not in `reviewable_extensions`.
    Filters out deleted files (no point reviewing what's gone).
    """
    if reviewable_extensions is None:
        reviewable_extensions = DEFAULT_REVIEWABLE_EXTENSIONS

    patch_set = PatchSet(diff_text)
    results = []

    for patched_file in patch_set:
        # Skip deleted files
        if patched_file.is_removed_file:
            log.debug("Skipping deleted file: %s", patched_file.path)
            continue

        ext = Path(patched_file.path).suffix.lower()
        # Skip files with unreviewable extensions
        if ext not in reviewable_extensions:
            log.warning("Skipping unrecognised extension '%s': %s", ext, patched_file.path)
            continue

        file_diff = FileDiff(
            path=patched_file.path,
            is_new_file=patched_file.is_added_file,
            is_deleted=False,
        )

        for hunk in patched_file:
            content_lines = []
            has_removal = False
            for line in hunk:
                content_lines.append(str(line).rstrip("\n"))
                if line.is_removed:
                    has_removal = True

            file_diff.hunks.append(
                DiffHunk(
                    start_line=hunk.target_start,
                    end_line=hunk.target_start + hunk.target_length - 1,
                    content="\n".join(content_lines),
                    is_addition_only=not has_removal,
                )
            )

        if file_diff.hunks:
            results.append(file_diff)

    return results


def format_diff_for_prompt(file_diff: FileDiff, max_hunks: int = 10) -> str:
    """
    Format a FileDiff into a compact text representation for LLM input.

    Truncates after `max_hunks` to avoid blowing context windows on huge changes.
    """
    lines = [f"File: {file_diff.path}"]
    if file_diff.is_new_file:
        lines.append("(new file)")

    for i, hunk in enumerate(file_diff.hunks[:max_hunks]):
        lines.append(f"\nHunk {i+1} (lines {hunk.start_line}-{hunk.end_line}):")
        lines.append(hunk.content)

    if len(file_diff.hunks) > max_hunks:
        remaining = len(file_diff.hunks) - max_hunks
        lines.append(f"\n... ({remaining} more hunks truncated)")

    return "\n".join(lines)
