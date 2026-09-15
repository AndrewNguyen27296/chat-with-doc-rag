"""Portfolio invariant: this repository stays inside its safe verticals.

Run with pytest, or standalone with no test dependencies at all:

    pytest -q tests/test_domain_scope.py
    python tests/test_domain_scope.py

Every text file that would be tracked is scanned for the out-of-scope
vocabulary. A sentence that names the domain in order to EXCLUDE it (a
non-compete note, a "never use" rule) is the invariant being honoured, not
broken, so prohibitions are allowed and everything else is flagged. Prose
wraps, and the word that makes a sentence a prohibition often sits a line or
two above the term it prohibits, so the sentence is judged, not the line.

This file is the only place the vocabulary may appear bare, and it skips
itself.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve()

SCANNED_SUFFIXES = {".py", ".md", ".toml", ".txt", ".json", ".yaml", ".yml", ".example"}
SKIPPED_DIRS = {".git", ".venv", "venv", ".chroma", "__pycache__", ".pytest_cache", "node_modules"}

BANNED = re.compile(
    r"\b(kwh|mwh|smart meters?|electricity|utility bill(?:ing|s)?|district heating|"
    r"carbon footprint|scope [123]|energy|metering|sustainability|consumption data)\b",
    re.IGNORECASE,
)
EXEMPT = re.compile(
    r"non-compete|domain restriction|stays? (?:entirely )?out of|out of scope|"
    r"outside the scope|excluded|exclusively|\bno energy\b|zero energy|stay inside|"
    r"guardrail|must not|never use|\bnever\b|\bban(?:ned|s)?\b|prohibit",
    re.IGNORECASE,
)


def _tracked_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        if any(part in SKIPPED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.resolve() == HERE:
            continue
        files.append(path)
    return sorted(files)


def test_the_scan_covers_the_files_that_matter() -> None:
    names = {p.relative_to(ROOT).as_posix() for p in _tracked_text_files()}
    for required in ("README.md", "CLAUDE.md", "app.py", "requirements.txt",
                     "rag/config.py", "scripts/make_sample_docs.py"):
        assert required in names, f"scan skipped {required}"
    assert not any(n.startswith(".venv/") for n in names), "scan wandered into .venv"


def test_no_out_of_scope_domain_content_anywhere() -> None:
    offenders: list[str] = []
    for path in _tracked_text_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines):
            if not BANNED.search(line):
                continue
            window = " ".join(lines[max(0, index - 2): index + 2])
            if EXEMPT.search(window):
                continue
            rel = path.relative_to(ROOT).as_posix()
            offenders.append(f"{rel}:{index + 1}: {line.strip()[:100]}")
    assert not offenders, "out-of-scope domain content:\n  " + "\n  ".join(offenders)


# --- standalone runner ----------------------------------------------------


def _main() -> int:
    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, test in tests:
        try:
            test()
        except AssertionError as error:
            failed += 1
            print(f"FAIL  {name}\n      {error}")
        except Exception as error:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}\n      {type(error).__name__}: {error}")
        else:
            print(f"pass  {name}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
