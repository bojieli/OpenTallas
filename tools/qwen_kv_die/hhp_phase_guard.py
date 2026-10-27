#!/usr/bin/env python3
"""Typed phase-issue guard for the KV per-PC es merge ownership phase (qkd_static_kv_pc_es_merge_b), incl. the opt-in
HHP c708 central OWN phase (physical/die_plan/qwen_kvsys/cores/harden/kvspc_phase_delivery.py, PHASE_DELAY = 1).

Edges are core edges.  BOOT_END = first edge that samples emb_boot_ready = 1; REOPEN = first edge that samples 0.
PHASE_DELAY d: 0 = main (own <= !emb_boot_ready), 1 = c708 (own_pin <= !ebr; own <= own_pin).

Constraints a static schedule must satisfy (COORD ruling TOK-ALL-14 on HHP c708; d = 1 gives the three shifted ones):
  W  writer word (wes[0])           BOOT_END + 1 + d <= e <= REOPEN                (c708: first writer word >= BOOT_END+2)
  S  slice word (hes[0])            REOPEN + d <= e <= BOOT_END - 1                (c708: first slice write >= REOPEN+1)
  E  embedding return (er/cv)       issue >= BOOT_END, return - issue >= 1 + d,   (c708: emb issue->return >= 2 edges)
                                    BOOT_END + 1 + d <= return <= REOPEN + d
  B  slice return (er/cv, boot)     return <= BOOT_END - 1 (retired before emb_ready rises), return >= REOPEN + 1 + d
The writer upper bound REOPEN and slice upper bound BOOT_END-1 are the main (d = 0) contract, kept strict under c708.
`hw_predict` is the exact edge model of the RTL face used by the directed boundary bench.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["writer", "slice", "emb_return", "slice_return"]


@dataclass(frozen=True)
class Event:
    kind: Kind
    edge: int
    issue: int | None = None          # emb_return only: the embedding issue edge


@dataclass(frozen=True)
class PhaseWindow:
    """One run window of a PC: [boot_end, reopen] (reopen None = open-ended)."""
    boot_end: int
    reopen: int | None = None


@dataclass(frozen=True)
class PhaseSchedule:
    windows: tuple[PhaseWindow, ...]
    events: tuple[Event, ...]
    phase_delay: int = 1                  # 1 = c708 candidate, 0 = main
    weaken: tuple[str, ...] = field(default=())   # bench mutants only: 'W', 'S', 'E'


def check(s: PhaseSchedule) -> list[str]:
    """Violations (empty = schedule admitted)."""
    d = s.phase_delay
    if d not in (0, 1):
        return [f"phase_delay {d} unsupported"]
    ws = sorted(s.windows, key=lambda w: w.boot_end)
    for a, b in zip(ws, ws[1:]):
        if a.reopen is None or a.reopen >= b.boot_end:
            return ["windows overlap or unclosed"]
    wmin = 1 + d - (1 if "W" in s.weaken else 0)
    smin = d - (1 if "S" in s.weaken else 0)
    emin = 1 + d - (1 if "E" in s.weaken else 0)

    def run_window(e, lo_off, hi_off):
        return any(w.boot_end + lo_off <= e and (w.reopen is None or e <= w.reopen + hi_off) for w in ws)

    def boot_ok(e, lo_off, hi_off):
        # boot windows: (-inf, first boot_end), and (reopen_k, boot_end_{k+1})
        prev = None
        for w in ws:
            lo = -10**9 if prev is None else prev + lo_off
            if lo <= e <= w.boot_end + hi_off:
                return True
            prev = w.reopen
            if prev is None:
                return False
        return e >= prev + lo_off
    v = []
    for ev in s.events:
        if ev.kind == "writer" and not run_window(ev.edge, wmin, 0):
            v.append(f"W writer word at {ev.edge}: needs BOOT_END+{wmin} <= e <= REOPEN")
        elif ev.kind == "slice" and not boot_ok(ev.edge, smin, -1):
            v.append(f"S slice word at {ev.edge}: needs REOPEN+{smin} <= e <= BOOT_END-1")
        elif ev.kind == "emb_return":
            if ev.issue is None:
                v.append(f"E embedding return at {ev.edge} without its issue edge"); continue
            if not run_window(ev.issue, 0, 0):
                v.append(f"E embedding issue at {ev.issue} outside the run window")
            if ev.edge - ev.issue < emin:
                v.append(f"E embedding return {ev.edge} only {ev.edge - ev.issue} edges after issue {ev.issue}: needs >= {emin}")
            if not run_window(ev.edge, emin, d):
                v.append(f"E embedding return at {ev.edge}: needs BOOT_END+{emin} <= e <= REOPEN+{d}")
        elif ev.kind == "slice_return" and not boot_ok(ev.edge, 1 + d, -1):
            v.append(f"B slice return at {ev.edge}: needs REOPEN+{1 + d} <= e <= BOOT_END-1")
    return v


def hw_predict(direction: str, cls: str, off: int, d: int, nface_ff: bool = False) -> dict:
    """Exact edge model of the RTL face for one event at T+off around one transition T (RISE = BOOT_END, FALL = REOPEN).
    own_seen(e) = own value the edge-e logic reads = !ebr(e-1-d); own_pin_seen(e) = !ebr(e-1)."""
    new_own = 0 if direction == "RISE" else 1

    def own_seen(e):
        return new_own if e >= 1 + d else 1 - new_own

    def pin_seen(e):
        return new_own if e >= 1 else 1 - new_own
    e = off
    if cls == "writer":
        return dict(fault=int(own_seen(e) == 1 or (nface_ff and pin_seen(e) == 1)))
    if cls == "slice":
        return dict(fault=int(own_seen(e + 1) == 0))
    if cls == "er":
        sl = own_seen(e)
        return dict(ep=1 - sl, slice=sl)
    if cls == "cv":
        return dict(slice=own_seen(e))
    raise ValueError(cls)


if __name__ == "__main__":
    """CLI: python3 hhp_phase_guard.py SCHEDULE.json -> exit 1 on any violation."""
    j = json.loads(open(sys.argv[1]).read())
    s = PhaseSchedule(windows=tuple(PhaseWindow(**w) for w in j["windows"]),
                      events=tuple(Event(**e) for e in j["events"]), phase_delay=j.get("phase_delay", 1))
    vv = check(s)
    print(json.dumps(dict(admitted=not vv, violations=vv), indent=1))
    sys.exit(1 if vv else 0)
