"""
Fetches unified diff text from GitHub or GitLab.

Uses the public APIs / .diff endpoints (no auth required for public repos).
Optional GITHUB_TOKEN env var raises rate limit from 60/hr to 5000/hr.
"""

from __future__ import annotations

import httpx

from .config import GITHUB_TOKEN, MAX_DIFF_BYTES
from .url_parser import ParsedRef


class DiffFetchError(Exception):
    """Raised when diff fetching fails (404, 403, rate limit, oversized, etc.)."""


async def fetch_diff(ref: ParsedRef) -> str:
    """Fetch the unified diff for a parsed reference."""
    if ref.platform == "github":
        return await _fetch_github_diff(ref)
    if ref.platform == "gitlab":
        return await _fetch_gitlab_diff(ref)
    raise DiffFetchError(f"Unsupported platform: {ref.platform}")


async def _fetch_github_diff(ref: ParsedRef) -> str:
    """Fetch diff from GitHub via the REST API with diff Accept header."""
    if ref.ref_type == "pr":
        api_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/pulls/{ref.identifier}"
    elif ref.ref_type == "commit":
        api_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/commits/{ref.identifier}"
    elif ref.ref_type == "compare":
        api_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/compare/{ref.identifier}"
    else:
        raise DiffFetchError(f"Unsupported GitHub ref type: {ref.ref_type}")

    headers = {
        "Accept": "application/vnd.github.diff",
        "User-Agent": "CodeReview-Agent/0.1",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return await _http_get_diff(api_url, headers, source_name="GitHub")


async def _fetch_gitlab_diff(ref: ParsedRef) -> str:
    """
    Fetch diff from GitLab.

    GitLab needs us to look up the numeric project ID first (or use URL-encoded
    path), then hit the diff endpoint.
    """
    project_path = f"{ref.owner}%2F{ref.repo}"

    if ref.ref_type == "pr":
        # GitLab calls them "merge requests" with internal ID (iid)
        diff_url = (
            f"https://gitlab.com/api/v4/projects/{project_path}"
            f"/merge_requests/{ref.identifier}/raw_diffs"
        )
    elif ref.ref_type == "commit":
        diff_url = (
            f"https://gitlab.com/api/v4/projects/{project_path}"
            f"/repository/commits/{ref.identifier}/diff"
        )
    else:
        raise DiffFetchError(f"Unsupported GitLab ref type: {ref.ref_type}")

    headers = {"User-Agent": "CodeReview-Agent/0.1"}

    # GitLab commit endpoint returns JSON; MR endpoint returns raw diff text.
    if ref.ref_type == "commit":
        return await _http_get_gitlab_commit_diff(diff_url, headers)
    return await _http_get_diff(diff_url, headers, source_name="GitLab")


async def _http_get_diff(url: str, headers: dict, source_name: str) -> str:
    """Common HTTP fetcher for endpoints that return raw diff text."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise DiffFetchError(f"Network error fetching from {source_name}: {exc}") from exc

    _check_response(response, source_name)
    text = response.text
    _check_diff_size(text)
    return text


async def _http_get_gitlab_commit_diff(url: str, headers: dict) -> str:
    """
    GitLab commit diffs come as JSON arrays — reassemble into a unified diff.

    Each element looks like:
        {
            "diff": "@@ -1 +1 @@\n-old\n+new\n",
            "new_path": "file.py",
            "old_path": "file.py",
            "new_file": false,
            "renamed_file": false,
            "deleted_file": false,
        }
    """
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise DiffFetchError(f"Network error fetching from GitLab: {exc}") from exc

    _check_response(response, "GitLab")
    items = response.json()
    if not isinstance(items, list):
        raise DiffFetchError(f"Unexpected GitLab response shape: {type(items).__name__}")

    diff_blocks = []
    for item in items:
        # Build a unified-diff-style header so unidiff can parse it downstream
        header = (
            f"diff --git a/{item['old_path']} b/{item['new_path']}\n"
            f"--- a/{item['old_path']}\n"
            f"+++ b/{item['new_path']}\n"
        )
        diff_blocks.append(header + item["diff"])

    full_diff = "\n".join(diff_blocks)
    _check_diff_size(full_diff)
    return full_diff


def _check_response(response: httpx.Response, source_name: str) -> None:
    """Map HTTP errors to user-friendly messages."""
    if response.status_code == 200:
        return
    if response.status_code == 404:
        raise DiffFetchError(
            f"{source_name} returned 404. The repo may be private, the URL may be wrong, "
            "or the PR/commit may not exist."
        )
    if response.status_code in (401, 403):
        if "rate limit" in response.text.lower():
            raise DiffFetchError(
                f"{source_name} rate limit exceeded. "
                "Try again later, or the operator can set GITHUB_TOKEN for higher limits."
            )
        raise DiffFetchError(
            f"{source_name} access denied (status {response.status_code}). "
            "This usually means the repo is private. Private repo support requires authentication "
            "(Phase 2 of this project — not yet implemented)."
        )
    raise DiffFetchError(
        f"{source_name} returned unexpected status {response.status_code}: {response.text[:200]}"
    )


def _check_diff_size(text: str) -> None:
    """Reject diffs that are too large to send to the LLM."""
    size = len(text.encode("utf-8"))
    if size > MAX_DIFF_BYTES:
        raise DiffFetchError(
            f"Diff too large: {size:,} bytes (limit: {MAX_DIFF_BYTES:,}). "
            "Try a smaller PR or a single commit."
        )
