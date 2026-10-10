#!/bin/bash
# sys-takeover 2026-10-09: committed TU PHY/core retry composition bench (tb_hbm_tu_retry_phy_port: 256-deep landing
# debt, 1300 full-545 records with phase-shifted pops, FEC-UE go-back-N replay delivering once, link-down) on the stripped
# NOEPOCH=1 port.  The stale-24-bit-session step is removed (no session in the stripped design).
#   tu_retry_strip_bench.sh pos|neg|negdup OUT    (neg: wrong landing slot; negdup: receiver accepts duplicates)
set -uo pipefail
mode=$1; W=$2; mkdir -p "$W"; L=rtl/hbm_accel/tu/link_retry_sram_20261008
python3 - "$W" <<'PY'
import sys,pathlib
t=pathlib.Path('rtl/hbm_accel/tu/link_retry_sram_20261008/tb_hbm_tu_retry_phy_port.sv').read_text()
R=[("ot_hbm_tu_retry_phy_port #(.ENABLE(1)) dut(","ot_hbm_tu_retry_phy_port #(.ENABLE(1),.NOEPOCH(1)) dut("),
   (' epoch=3;reset_link;run=0;fv=1;fe=2;fs=1300;fp=1300;fn=1;repeat(8)tick;\n if(fault||retained||ingress||debt)$fatal(1,"old session controls crossed reset");\n $display("PASS coordinated reset/linkdown and stale24bit session; defaultoff has no storage/outputs");',
    ' reset_link;run=0;fv=0;repeat(8)tick;\n if(fault||retained||ingress||debt)$fatal(1,"reset did not clear retry state");\n $display("PASS coordinated reset/linkdown (NOEPOCH: no session identity); defaultoff has no storage/outputs");')]
for a,b in R:
    assert t.count(a)==1,a; t=t.replace(a,b)
(pathlib.Path(sys.argv[1])/'tb.sv').write_text(t)
m=pathlib.Path(L:='rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_retry_phy_ingress.sv').read_text()
a="assign out_data=head[hp];"; assert m.count(a)==1
(pathlib.Path(sys.argv[1])/'ingress_mut.sv').write_text(m.replace(a,"assign out_data=head[hp+1'b1];"))
PY
ING=$L/ot_hbm_retry_phy_ingress.sv; D=()
[[ $mode == neg ]] && ING=$W/ingress_mut.sv
[[ $mode == negdup ]] && D=(-DOT_HBM_RETRY_MUT_DUPLICATE)
iverilog -g2012 -I rtl/common "${D[@]}" -s tb_hbm_tu_retry_phy_port -o "$W/s.vvp" rtl/common/ot_secded.sv $L/ot_hbm_replay_sram.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $L/ot_hbm_link_retry_sram.sv \
  $L/ot_hbm_retry_pop_cdc.sv $ING $L/ot_hbm_tu_retry_port.sv $L/ot_hbm_tu_retry_phy_port.sv "$W/tb.sv" >"$W/build.log" 2>&1 || { cat "$W/build.log" | head; echo TURS_BENCH_ERROR; exit 2; }
vvp -n "$W/s.vvp" >"$W/run.log" 2>&1; grep -E "^PASS|FATAL" "$W/run.log" | head -8
if [[ $mode == pos ]]; then grep -q '^PASS_ALL' "$W/run.log" && ! grep -qi fatal "$W/run.log" && { echo TU_RETRY_STRIP_PASS; exit 0; }; echo TU_RETRY_STRIP_FAIL; exit 1; fi
grep -qi fatal "$W/run.log" && { echo TU_RETRY_STRIP_NEG_DETECTED; exit 1; }; echo TU_RETRY_STRIP_NEG_MISSED; exit 0
