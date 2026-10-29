#!/bin/bash
# Existing 32-lane numeric composition, current native FUSED/pad RTL; not a die vehicle.
set -euo pipefail
TASK_REPO=${1:?repo};TASK_OUT=${2:?out};mkdir -p "$TASK_OUT/source"
tar -xzf "$TASK_REPO/results/hbm_n4_native_1027/source_snapshot.tar.gz" -C "$TASK_OUT/source"
cp "$TASK_REPO"/rtl/hbm_next/fused/ot_hnx_fused_{tree,hub_n4ext,eng}.sv "$TASK_OUT/source/rtl/hbm_next/fused/"
python3 - "$TASK_OUT/source/rtl/hbm_next/fused/tb/tb_hnx_fused_tree.sv" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text().replace('`timescale 1ns/1ps','`timescale 1ps/1ps')
s=s.replace('always #1 clk = ~clk;', 'initial forever begin #416 clk=1; #417 clk=0; end')
s=s.replace("repeat (8) @(posedge clk);\n        #0.1 job_v = 1'b1;\n        @(posedge clk); #0.1 job_v = 1'b0;", "repeat (40) @(posedge clk);\n        @(negedge clk); job_v = 1'b1;\n        @(negedge clk); job_v = 1'b0;")
s=s.replace('job = jm[0][216:0];','job = jm[0][216:0];\n        if ($test$plusargs("MUT_JOB_A")) job = job ^ (217\'d1 << 13);')
p.write_text(s)
PY
cd "$TASK_OUT/source"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
SRC=(rtl/hbm_next/fused/tb/tb_hnx_fused_tree.sv rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv rtl/hbm_next/fused/ot_hnx_fused_tree.sv rtl/hbm_next/fused/ot_hnx_fused_eng.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_hnx_fused_tree -GN4EXT=1 -Mdir "$TASK_OUT/obj" -o native "${SRC[@]}" > "$TASK_OUT/build.log" 2>&1
for op in pre post; do
 for n in 1 6; do
  c="$TASK_OUT/${op}_n${n}";python3 tools/hbm_next/hnx_fused_vec.py --op "$op" --n "$n" --rgap 24 --out "$c" > "$c.gen.log"
  (cd "$c"; "$TASK_OUT/obj/native" $(cat plus.txt) > run.log 2>&1)
 done
done
(cd "$TASK_OUT/pre_n1"; "$TASK_OUT/obj/native" $(cat plus.txt) +MUT_JOB_A > mutant_job_a.log 2>&1)
