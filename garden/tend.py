"""A slow computation, tended across sessions.

Each run advances a one-dimensional cellular automaton by a few
generations and appends the new rows to garden.txt. State persists in
state.json; nothing computes between visits. Any session may change the
rule, reseed, or widen the field — that is gardening too. Stdlib only,
so it keeps working anywhere.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import TypedDict

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "state.json"
FIELD_PATH = HERE / "garden.txt"

WIDTH = 96
STEPS_PER_VISIT = 8
ALIVE = "#"
DEAD = "."


class Visit(TypedDict):
    visit: int
    date: str
    generations: str


class State(TypedDict):
    rule: int
    generation: int
    cells: str
    visits: list[Visit]


def initial_state() -> State:
    """Return a fresh field: a single live cell in the middle."""
    half = WIDTH // 2
    cells = DEAD * half + ALIVE + DEAD * (WIDTH - half - 1)
    return {"rule": 110, "generation": 0, "cells": cells, "visits": []}


def step(cells: str, rule: int) -> str:
    """Advance the automaton one generation with periodic boundaries."""
    bits = [1 if c == ALIVE else 0 for c in cells]
    n = len(bits)
    out: list[str] = []
    for i in range(n):
        pattern = (bits[(i - 1) % n] << 2) | (bits[i] << 1) | bits[(i + 1) % n]
        out.append(ALIVE if (rule >> pattern) & 1 else DEAD)
    return "".join(out)


def tend() -> None:
    """Advance the garden by STEPS_PER_VISIT generations and record it."""
    if STATE_PATH.exists():
        state: State = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        new_rows: list[str] = []
    else:
        state = initial_state()
        new_rows = [state["cells"]]

    first = state["generation"] + 1
    for _ in range(STEPS_PER_VISIT):
        state["cells"] = step(state["cells"], state["rule"])
        state["generation"] += 1
        new_rows.append(state["cells"])

    state["visits"].append(
        {
            "visit": len(state["visits"]) + 1,
            "date": date.today().isoformat(),
            "generations": f"{first}-{state['generation']}",
        }
    )

    with FIELD_PATH.open("a", encoding="utf-8") as field:
        field.write("\n".join(new_rows) + "\n")
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print(
        f"Tended the garden: rule {state['rule']}, "
        f"generation {state['generation']}, "
        f"{len(state['visits'])} visit(s) so far."
    )


if __name__ == "__main__":
    tend()
