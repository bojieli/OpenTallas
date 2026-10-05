#!/usr/bin/env python3
"""Generate the core lockstep bench sources into OUT: two emitted Qwen cores (the original ot_hdc_core_vector_weight.sv
and the successor rtl/hbm_accel/qwen/fmax/ot_hdc_core_vector_weight_f12.sv), each in a copy of the physical context
wrapper (stream gating + registered-boundary unit stubs), renamed _ref / _f12; the bench
tb_qwen_core_f12_lockstep.sv drives both with the same program, starts and stream arrivals."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_rt_core_emit_w12 as E  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
isa = (ROOT / "rtl/hdc/ot_hdc_isa.svh").read_text()
wrap = (ROOT / "rtl/hbm_accel/qwen/fmax/ot_qwen_hbmacc_core_ctx.sv").read_text()
stubs = (ROOT / "rtl/hbm_accel/qwen/fmax/ot_qwen_core_ctx_stubs.sv").read_text()
for tag, src in (("ref", ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv"),
                 ("f12", ROOT / "rtl/hbm_accel/qwen/fmax/ot_hdc_core_vector_weight_f12.sv")):
    t = src.read_text().replace("module ot_hdc_core_vector_weight_f12 #(", "module ot_hdc_core_vector_weight #(")
    t = E.emit(t).replace('`include "ot_hdc_isa.svh"', isa)
    t = t.replace("module ot_qwen_rom_core #(", f"module ot_qwen_rom_core_{tag} #(")
    t = t.replace("ot_qwen_me_spine_w12 #(", f"ot_qwen_me_spine_w12_{tag} #(").replace("ot_hdc_vstream_rt #(", f"ot_hdc_vstream_rt_{tag} #(")
    (out / f"core_{tag}.sv").write_text(t)
    w = wrap.replace("module ot_qwen_hbmacc_core_ctx #(", f"module ot_qwen_hbmacc_core_ctx_{tag} #(")
    w = w.replace("    ot_qwen_rom_core #(", f"    ot_qwen_rom_core_{tag} #(")
    if tag == "ref":
        w = w.replace(",.ME_ISSUE_RE(ME_ISSUE_RE),.DEC_FAST(DEC_FAST)) core (", ") core (")
    (out / f"ctx_{tag}.sv").write_text(w)
    s = stubs.replace("module ot_qwen_me_spine_w12 #(", f"module ot_qwen_me_spine_w12_{tag} #(")
    s = s.replace("module ot_hdc_vstream_rt #(", f"module ot_hdc_vstream_rt_{tag} #(")
    (out / f"stubs_{tag}.sv").write_text(s)
print(out)
