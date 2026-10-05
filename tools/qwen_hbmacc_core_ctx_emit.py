#!/usr/bin/env python3
"""Write the generated Qwen core ot_qwen_rom_core (tools/qwen_rom_rt_core_emit_w12.py, unchanged text) with the ISA
header inlined, for the physical context route rtl/hbm_accel/qwen/fmax/ot_qwen_hbmacc_core_ctx.sv (the physical flow
takes no include path).  --core SRC selects another core source (a successor) emitted the same way."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_rt_core_emit_w12 as E  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--core", type=Path, default=E.CORE)
a = ap.parse_args()
text = E.emit(a.core.read_text().replace("module ot_hdc_core_vector_weight_f12 #(", "module ot_hdc_core_vector_weight #("))
inc = '`include "ot_hdc_isa.svh"'
if text.count(inc) != 1:
    raise SystemExit("isa include anchor")
text = text.replace(inc, (ROOT / "rtl/hdc/ot_hdc_isa.svh").read_text())
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(text)
print(a.out)
