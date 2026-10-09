#!/usr/bin/env python3
"""safe-qwen A6 adoption gate (REVIEW_20261008 addendum ~21:20): a Qwen ROM layer run with the emitted core at FQ_HEAD = 1.

The token drivers emit ot_qwen_rom_core with tools/qwen_rom_rt_core_emit_w12.emit.  This wrapper applies
tools/qwen_missing/emit_partition.fq_head to that emitted core (module ot_qwen_rom_core, parameter FQ_HEAD defaulting
to 1: the instruction FIFO's registered head word, the same transform as the qfd_sp_constants_sequencer master), then
runs the named driver unchanged with the remaining arguments.  The layer's exit x is checked bit-exactly against the
ISA oracle by the driver, so every matvec / SU / collective op the layer issues runs through the FQ_HEAD decode.

    fqh_token.py <driver.py> [driver args...]      e.g.  fqh_token.py tools/qwen_rom_rt_token_stream4_w12.py --stream4 ...
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/qwen_missing"))
import qwen_rom_rt_core_emit_w12 as E  # noqa: E402
import emit_partition as P  # noqa: E402

_emit = E.emit


def emit_fqh(text: str) -> str:
    out = P.fq_head(_emit(text), module="ot_qwen_rom_core", default=1)
    assert "parameter integer FQ_HEAD = 1" in out
    return out


E.emit = emit_fqh
drv = sys.argv[1]
sys.argv = [drv] + sys.argv[2:]
print("FQH_TOKEN: ot_qwen_rom_core emitted with FQ_HEAD = 1 (safe-qwen A6)", flush=True)
runpy.run_path(drv, run_name="__main__")
