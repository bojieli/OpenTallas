#!/usr/bin/env python3
"""Zero-latency issue-loop fallbacks over the final DEC_LA core (results/rtl/qwen_core_decode_closure_20261004/
CODEX_HANDOFF.md), behind parameter DEC_LA_ISSUE_FB (default 0 = the DEC_LA core unchanged).

FB >= 1: per-consumer kept copies of `issue` (fallback 1).
FB >= 2: the chase source is selected by registered one-hot flags written with NEXT at LOAD (fallback 2).
Every level is cycle-identical to the DEC_LA core: no edge is added and the issue loop stays one cycle."""


def apply(text: str, level: int) -> str:
    old = "    parameter integer DEC_LA = 0\n) ("
    assert text.count(old) == 1
    text = text.replace(old, "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_ISSUE_FB = 0\n) (")
    if level == 0:
        return text
    raise NotImplementedError(level)
