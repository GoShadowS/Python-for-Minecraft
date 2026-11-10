#!/usr/bin/env python3
"""Emits the contents of a file as GitHub Actions annotations.

The CI job logs themselves are served from a storage host
(``*.blob.core.windows.net`` / ``results-receiver.actions.githubusercontent.com``) that is
not reachable from the sandbox this repository is developed in, while the annotations of a
check run *are* readable through ``api.github.com``::

    gh api repos/<owner>/<repo>/check-runs/<job-id>/annotations

So build failures and version probes are routed through annotations instead. The message is
chunked, because a single annotation is truncated past a few tens of kilobytes.

Usage::

    tools/ci_annotate.py <level> <title> <file> [chunk-bytes]
"""

from __future__ import annotations

import sys

DEFAULT_CHUNK = 8000


def escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    level, title, path = sys.argv[1], sys.argv[2], sys.argv[3]
    chunk = int(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_CHUNK
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    if not text.strip():
        print("::%s title=%s::(empty)" % (level, escape(title)))
        return 0
    total = (len(text) + chunk - 1) // chunk
    for index in range(total):
        part = text[index * chunk:(index + 1) * chunk]
        label = title if total == 1 else "%s [%d/%d]" % (title, index + 1, total)
        print("::%s title=%s::%s" % (level, escape(label), escape(part)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
