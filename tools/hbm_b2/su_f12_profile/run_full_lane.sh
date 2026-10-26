#!/usr/bin/env bash
# Candidate common833 FULL lane component programme; execute via ot-run.
set -euo pipefail
repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
out=$(realpath -m "${1:?fresh output directory}")
test ! -e "$out"
mkdir -p "$out/source"
cd "$repo"
ops=${SU_FULL_OPS:-0}
if [ "$ops" = 1 ]; then
 python3 tools/hbm_b2/su_f12_profile/full_ops_compile.py "$out/vec" > "$out/vec.log"
 python3 tools/hbm_b2/su_f12_profile.py --full-qid 2 --out "$out/side_profile" > "$out/profile.log"
else
 python3 tools/hbm_static/su_arith_compile.py "$out/vec" > "$out/vec.log"
fi
python3 - "$repo" "$out/source" "$ops" <<'PY'
from pathlib import Path
import sys
root,out=map(Path,sys.argv[1:3])
p=root/'rtl/hbm_accel/generic/adapters/static_su/arithmetic'
s=(p/'ot_hbm_su_static_kind2_lat4_leaf1_physical.sv').read_text()
s=s.replace('ot_hbm_su_static_kind2_lat4_leaf1_physical','ot_hbm_su_static_full_f12_candidate').replace('.ALAT(3)', '.ALAT(4)')
(out/'full.sv').write_text(s)
s=(p/'tb_su_static_lane_leaf.sv').read_text().replace('always #5 clk=~clk;', 'always #0.4165 clk=~clk;')
# Same compiled 64 fixed issues in every baseline class. High QID is VM identity,
# while the physical source explicitly selects FULL arithmetic independently.
s=s.replace('`timescale 1ns/1ps','`timescale 1ns/1fs').replace('#1;', '#0.05;')
if sys.argv[3]=='1':
 s=s.replace('NOPS=31', 'NOPS=8').replace('176','384')
 s=s.replace('localparam integer FIRST_OUTPUT=8+LATENCY+4*PINREG;', 'integer FIRST_OUTPUT; reg[31:0] first[0:NOPS-1];')
 s=s.replace('op=j;count=0;', 'op=j;count=0;FIRST_OUTPUT=first[j];')
 s=s.replace('$readmemh({dir,"/seed.mem"},seed);', '$readmemh({dir,"/first.mem"},first);$readmemh({dir,"/seed.mem"},seed);')
 s=s.replace("wire [31:0] side_y=32'd0;", """wire [31:0] side_y;
 reg[2:0] fn_q,fn_out_q;
 always @(posedge clk)begin fn_q<=ci_sfu;fn_out_q<=cs_sfu;end
 wire side_fault;
 ot_hbm_su_static_side__b1f12 side_pipe(.clk({6{clk}}),.rst_n(rst_n),.v(side_v),.fn(fn_q),.x(side_x),.fn_out(fn_out_q),.y(side_y),.fault(side_fault));""")
 s=s.replace('if(fault||coll)', 'if(fault||coll||side_fault)')
(out/'tb.sv').write_text(s)
PY
S=rtl/hbm_accel/generic/adapters/static_su
src=("$out/source/tb.sv" "$out/source/full.sv" "$S/arithmetic/ot_hbm_su_static_lane_pinreg.sv" "$S/arithmetic/ot_hbm_su_static_lane.sv" "$S/arithmetic/ot_hbm_su_static_ins.sv"
 "$S/data_store/ot_hbm_su_static_pinned_bank.sv" "$S/data_store/ot_hbm_su_static_data_store.sv"
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
if [ "$ops" = 1 ]; then src+=("$out/side_profile/ot_hbm_su_static_side.sv"); fi
verilator --binary --timing -O1 -j "${CPUS:-4}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
 --top-module tb_su_static_lane_leaf +define+LEAF_TOP=ot_hbm_su_static_full_f12_candidate \
 -GMLAT=4 -GALAT=4 -GLEAF=1 -GLANE=256 -GPINREG=1 --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
bin="$out/obj/Vtb_su_static_lane_leaf"
"$bin" +DIR="$out/vec" > "$out/run.log" 2>&1
for mut in ADDR DATA PHASE; do
 set +e
 "$bin" +DIR="$out/vec" +MUT_"$mut" > "$out/mut_$mut.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
done
cat "$out/run.log"
echo FULL_F12_LANE_COMPONENT_PASS
