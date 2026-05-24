"""
Parses GitHub and GitLab URLs into structured references.

Supported URL patterns:

    GitHub:
        https://github.com/{owner}/{repo}/pull/{number}
        https://github.com/{owner}/{repo}/commit/{sha}
        https://github.com/{owner}/{repo}/compare/{base}...{head}

    GitLab:
        https://gitlab.com/{owner}/{repo}/-/merge_requests/{iid}
        https://gitlab.com/{owner}/{repo}/-/commit/{sha}
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional


Platform = Literal["github", "gitlab"]
RefType = Literal["pr", "commit", "compare"]


@dataclass
class ParsedRef:
    """Structured representation of a parsed VCS URL."""

    platform: Platform
    owner: str
    repo: str
    ref_type: RefType
    identifier: str                # PR/MR number, commit SHA, or "base...head"
    base: Optional[str] = None     # For compare URLs
    head: Optional[str] = None     # For compare URLs


# ─── GitHub patterns ────────────────────────────────────────────────────
_GH_PR = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<num>\d+)"
)
_GH_COMMIT = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/commit/(?P<sha>[a-f0-9]{7,40})"
)
_GH_COMPARE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/compare/"
    r"(?P<base>[^.]+)\.\.\.(?P<head>[^/?]+)"
)

# ─── GitLab patterns ────────────────────────────────────────────────────
_GL_MR = re.compile(
    r"^https?://gitlab\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/-/merge_requests/(?P<iid>\d+)"
)
_GL_COMMIT = re.compile(
    r"^https?://gitlab\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/-/commit/(?P<sha>[a-f0-9]{7,40})"
)


class InvalidURLError(ValueError):
    """Raised when a URL doesn't match any supported pattern."""


def parse_url(url: str) -> ParsedRef:
    """
    Parse a GitHub or GitLab URL into a structured reference.

    Raises InvalidURLError if the URL isn't recognized.
    """
    url = url.strip()
    if not url:
        raise InvalidURLError("URL is empty.")

    # Try GitHub patterns
    if m := _GH_PR.match(url):
        return ParsedRef(
            platform="github",
            owner=m.group("owner"),
            repo=m.group("repo"),
            ref_type="pr",
            identifier=m.group("num"),
        )
    if m := _GH_COMMIT.match(url):
        return ParsedRef(
            platform="github",
            owner=m.group("owner"),
            repo=m.group("repo"),
            ref_type="commit",
            identifier=m.group("sha"),
        )
    if m := _GH_COMPARE.match(url):
        return ParsedRef(
            platform="github",
            owner=m.group("owner"),
            repo=m.group("repo"),
            ref_type="compare",
            identifier=f"{m.group('base')}...{m.group('head')}",
            base=m.group("base"),
            head=m.group("head"),
        )

    # Try GitLab patterns
    if m := _GL_MR.match(url):
        return ParsedRef(
            platform="gitlab",
            owner=m.group("owner"),
            repo=m.group("repo"),
            ref_type="pr",
            identifier=m.group("iid"),
        )
    if m := _GL_COMMIT.match(url):
        return ParsedRef(
            platform="gitlab",
            owner=m.group("owner"),
            repo=m.group("repo"),
            ref_type="commit",
            identifier=m.group("sha"),
        )

    raise InvalidURLError(
        "URL not recognized. Supported formats:\n"
        "  GitHub:  https://github.com/<owner>/<repo>/pull/<number>\n"
        "           https://github.com/<owner>/<repo>/commit/<sha>\n"
        "           https://github.com/<owner>/<repo>/compare/<base>...<head>\n"
        "  GitLab:  https://gitlab.com/<owner>/<repo>/-/merge_requests/<iid>\n"
        "           https://gitlab.com/<owner>/<repo>/-/commit/<sha>"
    )
