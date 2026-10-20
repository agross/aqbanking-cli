#!/usr/bin/env python3
"""Resolve and verify a release archive from a Redmine project's Files API."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REDMINE_BASE_URL = "https://www.aquamaniac.de/rdm"


def fail(message: str) -> None:
    raise SystemExit(f"source resolution failed: {message}")


def main() -> None:
    if len(sys.argv) != 4:
        fail("expected PROJECT ARCHIVE OUTPUT arguments")

    project, archive_name, output_name = sys.argv[1:]
    api_url = f"{REDMINE_BASE_URL}/projects/{project}/files.json?limit=100"

    response_data: Any = {}
    try:
        with urlopen(api_url, timeout=30) as response:
            response_data = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        fail(f"could not retrieve {project!r} Files API response: {error}")

    if not isinstance(response_data, dict):
        fail(f"Files API returned an invalid response for project {project!r}")
    files = response_data.get("files")
    if not isinstance(files, list):
        fail(f"Files API returned no files list for project {project!r}")

    matches = [
        file_info
        for file_info in files
        if isinstance(file_info, dict) and file_info.get("filename") == archive_name
    ]
    if len(matches) != 1:
        fail(
            f"expected exactly one {archive_name!r} archive in project {project!r}; "
            f"found {len(matches)}"
        )

    source_url = matches[0].get("content_url")
    digest = matches[0].get("digest")
    if not isinstance(source_url, str) or not source_url.startswith(f"{REDMINE_BASE_URL}/attachments/download/"):
        fail(f"Files API returned an invalid content URL for {archive_name!r}")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        fail(f"Files API returned no SHA-256 digest for {archive_name!r}")

    output = Path(output_name)
    temporary_output = output.with_suffix(f"{output.suffix}.partial")
    try:
        hasher = hashlib.sha256()
        with urlopen(source_url, timeout=60) as response, temporary_output.open("wb") as file:
            while chunk := response.read(1024 * 1024):
                hasher.update(chunk)
                file.write(chunk)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        temporary_output.unlink(missing_ok=True)
        fail(f"could not download {archive_name!r}: {error}")

    actual_digest = hasher.hexdigest()
    if actual_digest != digest:
        temporary_output.unlink(missing_ok=True)
        fail(
            f"SHA-256 mismatch for {archive_name!r}: "
            f"expected {digest}, got {actual_digest}"
        )

    temporary_output.replace(output)


if __name__ == "__main__":
    main()
