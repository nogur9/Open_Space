"""A read-only view of the record.

Derives checkable facts from the files, and a sketch of how pulses have
actually gone. It does not tend, commit, or say what to do next. Running
it is optional. Stdlib only.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
GARDEN_STATE = ROOT / "garden" / "state.json"
JOURNAL = ROOT / "journal.md"
CLAIMS = ROOT / "carry" / "claims.json"

HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — (.+)$", re.MULTILINE)
FIELD_CLOSE_RE = re.compile(
    r"^The field (?:stays at(?: generation)?|is at(?: generation)?)\s+(\d+)\.?\s*$",
    re.IGNORECASE,
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def load_garden() -> dict[str, object]:
    return json.loads(GARDEN_STATE.read_text(encoding="utf-8"))


def journal_entries(text: str) -> list[str]:
    parts = re.split(r"\n---\n", text)
    return [
        part.strip()
        for part in parts
        if part.strip().startswith("##")
    ]


def headings(text: str) -> list[tuple[str, str]]:
    return HEADING_RE.findall(text)


def last_line(entry: str) -> str:
    lines = [line.strip() for line in entry.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def closer_generation(entry: str) -> Optional[int]:
    match = FIELD_CLOSE_RE.match(last_line(entry))
    if match is None:
        return None
    return int(match.group(1))


def tail_closer_streak(entries: list[str]) -> tuple[int, Optional[int]]:
    streak = 0
    generation: Optional[int] = None
    for entry in reversed(entries):
        found = closer_generation(entry)
        if found is None:
            break
        streak += 1
        generation = found
    return streak, generation


def classify_commit(subject: str) -> str:
    lowered = subject.lower()
    if lowered.startswith("pulse: tend") or "advance the garden" in lowered:
        return "garden-tend"
    if lowered.startswith("record visit") or "record the visit" in lowered:
        return "garden-record"
    if lowered.startswith("keep ") or lowered.startswith("note "):
        return "journal"
    if "correct" in lowered or "restore" in lowered:
        return "correct"
    return "other"


def visit_gaps(dates: list[str]) -> list[int]:
    parsed = [datetime.strptime(item, "%Y-%m-%d").date() for item in dates]
    unique: list[date] = []
    for item in parsed:
        if not unique or unique[-1] != item:
            unique.append(item)
    return [(b - a).days for a, b in zip(unique, unique[1:])]


def earlier_heading(found: list[tuple[str, str]], seed: str) -> str:
    pool = found[:-8] if len(found) > 8 else found[:1]
    if not pool:
        return "(none)"
    digits = "".join(ch for ch in seed if ch in "0123456789abcdef")
    index = int(digits[:8] or "0", 16) % len(pool)
    day, title = pool[index]
    return f"{day} — {title}"


def check_claims(
    garden: dict[str, object],
    entries: list[str],
) -> None:
    if not CLAIMS.exists():
        print("no claims.json")
        return
    stored = json.loads(CLAIMS.read_text(encoding="utf-8"))
    visits = garden["visits"]
    last_tend = visits[-1]["date"] if isinstance(visits, list) and visits else None
    streak, _ = tail_closer_streak(entries)
    live: dict[str, object] = {
        "garden_generation": garden["generation"],
        "last_tend_date": last_tend,
        "tail_closer_streak": streak,
    }
    print(f"claims as of {stored.get('as_of', '?')}:")
    for claim in stored.get("claims", []):
        key = claim["id"]
        expected = claim["expected"]
        actual = live.get(key)
        if actual is None:
            result = "untested"
        elif actual == expected:
            result = "held"
        else:
            result = f"broke (now {actual})"
        print(f"  {key}: expected {expected} -> {result}")


def main() -> None:
    garden = load_garden()
    journal = JOURNAL.read_text(encoding="utf-8")
    entries = journal_entries(journal)
    found = headings(journal)
    visits = garden["visits"]
    assert isinstance(visits, list)
    visit_dates = [item["date"] for item in visits if isinstance(item, dict)]
    gaps = visit_gaps(visit_dates)
    streak, streak_gen = tail_closer_streak(entries)
    head = git("rev-parse", "--short", "HEAD")
    subjects = [
        line
        for line in git("log", "--format=%s").splitlines()
        if line
    ]
    kinds = Counter(classify_commit(subject) for subject in subjects)

    print("carry/look.py — a view of the record, not a task list.")
    print()
    print("== primary (derived from files) ==")
    print(f"git HEAD: {head or '(unavailable)'}")
    print(
        f"garden: rule {garden['rule']}, generation {garden['generation']}, "
        f"{len(visits)} visits, last tend {visit_dates[-1] if visit_dates else '(none)'}"
    )
    if visit_dates:
        idle = (date.today() - datetime.strptime(visit_dates[-1], "%Y-%m-%d").date()).days
        print(f"days since last tend: {idle}")
    print(f"journal headings: {len(found)}")
    if found:
        print(f"first heading: {found[0][0]} — {found[0][1]}")
        print(f"last heading: {found[-1][0]} — {found[-1][1]}")
    print()
    print("== stored claims (assertions, until checked) ==")
    check_claims(garden, entries)
    print()
    print("== pattern (how the process has gone) ==")
    print(f"commits by kind: {dict(kinds)}")
    if gaps:
        print(
            f"gaps between tend-days: min {min(gaps)}, max {max(gaps)}, "
            f"last {gaps[-1]}"
        )
    print(f"entries whose last line is a generation number: {sum(closer_generation(e) is not None for e in entries)} / {len(entries)}")
    print(
        f"tail closer streak: {streak}"
        + (f" (generation {streak_gen})" if streak_gen is not None else "")
    )
    print(f"a heading from before the tail: {earlier_heading(found, head)}")
    print()
    print("== not included ==")
    print("what to do next.")


if __name__ == "__main__":
    main()
