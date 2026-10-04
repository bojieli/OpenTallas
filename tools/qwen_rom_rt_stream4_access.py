#!/usr/bin/env python3
"""Generate rm_access.hpp for the 4-stack STREAM4 die (rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv).

Runs tools/qwen_rom_rt_rm_access.py (unchanged) with the die's array names taken from the HBM_STREAM
top (ot_qwen_rom_rt_die_w12_stream4) instead of the REAL_MEM top; arguments are that tool's.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qwen_rom_rt_rm_access as A  # noqa: E402

_find = A.find


def find(names, pattern, what):
    return _find(names, pattern.replace("ot_qwen_rom_rt_die_w12_rm__DOT__", "ot_qwen_rom_rt_die_w12_stream4__DOT__"), what)


A.find = find

if __name__ == "__main__":
    A.main()
