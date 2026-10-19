#!/bin/bash
# q3h central-SU latency reference (tb_q3h_su_lat): x / t images + golden r from tools/hdc_golden, Verilator 5.050.
# Usage (repository root): rtl/test/qwen_dv/run_q3h_lat.sh <out_dir>
out=$1; mkdir -p $out
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
R=$(python3 - "$out" <<'PY'
import sys; sys.path.insert(0, "tools"); import numpy as np, hdc_golden as G
F = np.float32; rng = np.random.default_rng(11)
x = (rng.standard_normal(4096) * 0.7).astype(F); t = (rng.standard_normal(4096) * 0.3).astype(F)
xn = G.add(x, t)
r = G.rsqrt(G.add(G.mul(G.reduce_chunked(G.mul(xn, xn)), F(1.0 / 4096)), F(1e-6)))
with open(sys.argv[1] + "/q3h_x.hex", "w") as f:
    for v in np.concatenate([x, t]): f.write("%08x\n" % int(np.asarray(v, F).view(np.uint32)))
print("%08x" % int(np.asarray(r, F).view(np.uint32)))
PY
)
F="rtl/qwen_sys/static_schedule_20261014/ot_hdc_vstream_static_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv
   rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_vstream_sfu_t.sv rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv
   rtl/hdc/ot_hdc_vreduce.sv rtl/physical/ot_hdc_vreduce_entries64.sv rtl/physical/ot_hdc_vred_pending_guard.sv
   rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv
   rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/lib/ot_rst_pipe.sv
   rtl/test/full_sm_service/sram_models.sv rtl/test/qwen_dv/tb_q3h_su_lat.sv"
$V --binary --timing -j ${JOBS:-16} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 \
   --x-initial 0 --top-module tb_q3h_su_lat --prefix Vtb --Mdir $out/obj $F -o tb > $out/build.log 2>&1 \
   || { echo BUILD_FAIL; grep -m20 -i "%Error" $out/build.log; exit 2; }
(cd $out && ./obj/tb +R=$R) | grep -E "^(Q3H|PASS|FAIL)"
