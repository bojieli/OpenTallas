#!/usr/bin/env python3
"""HA8 Qwen3-8B HBM-accelerator token vehicle with the 1.2 GHz successors (HBM-accel fmax closure, 2026-10-04).

Runs tools/qwen_hbmacc_rt_token_w12.py unchanged (same arguments, host, plan, oracle checks) with these substitutions,
each selectable, so one layer can be re-measured with the closed RTL:
  --core-f12   the generated core from rtl/hbm_accel/qwen/fmax/ot_hdc_core_vector_weight_f12.sv, ME_ISSUE_RE = DEC_FAST = 1
  --gate-opt N die stream gating ot_qwen_hbmacc_gate_f12 OPT N (die top rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12_f12.sv)
  --tpseq-f12  TP sequencer ot_qwen_tp_seq_w12_f12 REG_OUT = REG_CDATA = 1
  --coll-f12   collective package ot_rom_oneshot_allreduce_f12 (--coll-fifo 1 flop registered head / 2 SRAM, ADD_IMPL = 1 LAT7 adds)
  --wst-f12    stream ot_hbmacc_qwen_wstream_f12
  --vs-f12     stream unit successor (tools/qwen_hbmacc_vstream_f12_emit.py), --vs-la / --vs-lm
The successor die top is always compiled (with ME_ISSUE_RE / GATE_OPT / TPSEQ_F12 = 0 it is the original die).
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_hbmacc_rt_token_w12 as T  # noqa: E402
import qwen_rom_rt_core_emit_w12 as E  # noqa: E402

FMAX = ROOT / "rtl/hbm_accel/qwen/fmax"
argv = sys.argv[1:]


def flag(name, default=None, val=False):
    if name not in argv:
        return default
    i = argv.index(name)
    argv.pop(i)
    return argv.pop(i) if val else True


core_f12 = flag("--core-f12", False)
gate_opt = int(flag("--gate-opt", "0", True))
tpseq_f12 = flag("--tpseq-f12", False)
coll_f12 = flag("--coll-f12", False)
coll_fifo = int(flag("--coll-fifo", "1", True))   # FIFO_IMPL: 1 flop registered head (TP2 DEPTH 16), 2 SRAM (TP4 DEPTH 1024)
wst_f12 = flag("--wst-f12", False)
vs_f12 = flag("--vs-f12", False)
vs_la = int(flag("--vs-la", "5", True))
vs_lm = int(flag("--vs-lm", "6", True))

KEEP = [ROOT / "rtl/hdc/ot_hdc_fastfp.sv", ROOT / "rtl/hdc/ot_hdc_fastfp_lat.sv", ROOT / "rtl/hdc/ot_hdc_prefix.sv", ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv",
        ROOT / "rtl/hdc/ot_hdc_fp32_mul_lat.sv"]
DIE_F12 = T.RR / "ot_qwen_hbmacc_rt_die_w12_f12.sv"
T.DIE_SV = DIE_F12
T.DIE_RTL = [p for p in T.DIE_RTL if p.name != "ot_qwen_hbmacc_rt_die_w12.sv"] + [
    DIE_F12, FMAX / "ot_qwen_hbmacc_gate_f12.sv", FMAX / "ot_qwen_tp_seq_w12_f12.sv",
    *[k for k in KEEP if k not in T.DIE_RTL]]
die_params = [f"-GME_ISSUE_RE={int(bool(core_f12))}", f"-GDEC_FAST={int(bool(core_f12))}", f"-GGATE_OPT={gate_opt}", f"-GTPSEQ_F12={int(bool(tpseq_f12))}"]
if core_f12:
    class _Core:
        def read_text(self):
            return (FMAX / "ot_hdc_core_vector_weight_f12.sv").read_text().replace(
                "module ot_hdc_core_vector_weight_f12 #(", "module ot_hdc_core_vector_weight #(")

        def read_bytes(self):
            return (FMAX / "ot_hdc_core_vector_weight_f12.sv").read_bytes()
    E.CORE = _Core()
src = inspect.getsource(T.build)
rep = [('"-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1",', '"-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1", *DIE_F12_PARAMS,')]
if coll_f12:
    rep += [('("coll", "ot_rom_oneshot_allreduce", [*map(str, BASE.COLL_RTL),',
             '("coll", "ot_rom_oneshot_allreduce_f12", [*map(str, BASE.COLL_RTL), *map(str, COLL_F12),'),
            ('"-GBPC_NUM=3600"]', f'"-GBPC_NUM=3600", "-GFIFO_IMPL={coll_fifo}", "-GADD_IMPL=1"]')]
if wst_f12:
    rep += [('("wst", "ot_hbmacc_qwen_wstream", [*map(str, WST_RTL)],',
             '("wst", "ot_hbmacc_qwen_wstream_f12", [*map(str, WST_RTL), str(WST_F12)],')]
if vs_f12:
    import qwen_hbmacc_vstream_f12_emit as VS  # noqa: E402
    rep += [("vs_sv.write_text(qwen_rom_rt_core_emit_w12.emit_vstream(qwen_rom_rt_core_emit_w12.VSTREAM.read_text()))",
             "vs_sv.write_text(VS_RT_TEXT)"),
            ('[str(core_sv), str(vs_sv), *map(str, DIE_RTL)]', '[str(core_sv), str(vs_sv), *map(str, DIE_RTL), *map(str, VS_UNITS)]'),
            ('("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")', 'VS_HIER')]
for a, b in rep:
    if src.count(a) != 1:
        raise SystemExit(f"build anchor: {a}")
    src = src.replace(a, b)
ns = T.__dict__
ns["DIE_F12_PARAMS"] = die_params
ns["COLL_F12"] = [FMAX / "ot_rom_oneshot_die_f12.sv", *KEEP,
                  ROOT / "physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v"]
ns["WST_F12"] = FMAX / "ot_hbmacc_qwen_wstream_f12.sv"
if vs_f12:
    ns["VS_RT_TEXT"], ns["VS_UNITS"], ns["VS_HIER"] = VS.vehicle(vs_la, vs_lm)
exec(compile(src, T.__file__, "exec"), ns)
T.SOURCES = sorted(set([*T.SOURCES, *T.DIE_RTL, Path(__file__), *(ns["COLL_F12"] if coll_f12 else []),
                        *([ns["WST_F12"]] if wst_f12 else []), *(ns["VS_UNITS"] if vs_f12 else []),
                        FMAX / "ot_hdc_core_vector_weight_f12.sv"]))
sys.argv = [sys.argv[0], *argv]
T.main()
