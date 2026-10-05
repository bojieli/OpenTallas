#!/usr/bin/env python3
"""Emit a default-off held-grant core; no pinned original source is changed."""
import argparse
from pathlib import Path
import qwen_rom_rt_core_emit_w12 as E
ROOT = Path(__file__).resolve().parents[1]

def emit():
    src = ROOT / "results/rtl/qwen_hbm_registered_admission_20261005/sources/ot_hdc_core_vector_weight_f12.sv"
    text = E.emit(src.read_text().replace("module ot_hdc_core_vector_weight_f12 #(",
                                           "module ot_hdc_core_vector_weight #("))
    replacements = [
        ("module ot_qwen_rom_core #(", "module ot_qwen_rom_core_admission #("),
        ("    parameter integer ME_ISSUE_RE = 0,", "    parameter integer ME_ADMISSION_PIPE = 0,\n    parameter integer ME_ISSUE_RE = 0,"),
        ("wire me_issue_ok = (ME_ISSUE_RE != 0) ? !me_rd_presented : me_en;",
         "wire me_issue_ok = (ME_ADMISSION_PIPE != 0) ? (me_en && !me_rd_presented) : ((ME_ISSUE_RE != 0) ? !me_rd_presented : me_en);"),
        ('`include "ot_hdc_isa.svh"', (ROOT / "rtl/hdc/ot_hdc_isa.svh").read_text()),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError("admission emitter source anchor: " + old)
        text = text.replace(old, new, 1)
    return text

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(emit())
