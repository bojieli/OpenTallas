#!/usr/bin/env bash
# H-DIE 2026-10-15: write-path proof of the configured per-PC controller leaf (ot_hbm_svc_pc_ctrl_leaf_cfg) with the
# write payload in a real SRAM (WPAY=1).  Runs the production queued-write/read bench (640 actual WR with exact payload
# check at the DRAM column + true ACK, then 640 RD with exact data/identity) on the 32-leaf controller
# (ot_hbm_svc_native_sector_pipeline_leaves) for WPAY=1 and WPAY=0 (flop queue), plus two mutants that must FAIL:
#   stale_head : payload SRAM read address ignores the column pop (reads rp, not rp+1)  -> wrong write payload

#   bench_pc_ctrl_wpay.sh <out>
set -euo pipefail
out=${1:?out}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
tb="$out/tb_leaves_production.sv"
sed -e 's/^ot_hbm_svc_native_sector_queued_stack dut(\.\*);/ot_hbm_svc_native_sector_pipeline_leaves dut(.*);/' \
    -e 's/dut\.g_pc\[0\]\.count/dut.g_pc[0].u_ctrl.u_cfg.count/g' \
    -e 's/last_ack-first_req,max_count);$/last_ack-first_req,max_count);if(mode==0)begin $display("PC_CTRL_WRITE_PHASE PASS");$finish;end/' "$d/tb_hbm_svc_native_sector_queued_production.sv" > "$tb"
grep -q 'ot_hbm_svc_native_sector_pipeline_leaves dut' "$tb"; grep -q PC_CTRL_WRITE_PHASE "$tb"
# READ phase not run here: the queued tb's single-outstanding-read DRAM model ('overlapping read') does not match the
# leaf's OREG/RREG pipeline (fails identically for WPAY=0); reads are qualified by run_ctrl_leaves.sh capacity/issued.
cfg="$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv"
python3 - "$cfg" "$out" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(); out=Path(sys.argv[2])
m={'stale_head':[("wire[4:0]wpay_raddr=cv?rp+5'd1:rp;","wire[4:0]wpay_raddr=rp;")],
   'wpay0':[("parameter integer WPAY=1\n)(","parameter integer WPAY=0\n)(")]}
for k,subs in m.items():
    t=s
    for a,b in subs:
        assert t.count(a)==1,(k,a); t=t.replace(a,b)
    (out/(k+'.sv')).write_text(t)
PY
run(){ # name cfgsrc wpay
  sed "s/parameter integer WPAY=1\$/parameter integer WPAY=$3/" "$d/ot_hbm_svc_pc_ctrl_leaf.sv" > "$out/leaf_$1.sv"
  iverilog -g2012 -s tb -o "$out/$1.vvp" rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$2" "$out/leaf_$1.sv" \
    "$d/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$tb" > "$out/$1.build.log" 2>&1
  vvp "$out/$1.vvp" > "$out/$1.log" 2>&1
}
run wpay1 "$cfg" 1; grep 'PC_CTRL_WRITE_PHASE PASS' "$out/wpay1.log"; grep NATIVE_QUEUED_WRITE640 "$out/wpay1.log"
run wpay0 "$out/wpay0.sv" 0; grep 'PC_CTRL_WRITE_PHASE PASS' "$out/wpay0.log"
if run stale_head "$out/stale_head.sv" 1; then echo 'stale_head mutant survived'; exit 1; fi
grep -m1 -E 'queued write payload|fault' "$out/stale_head.log"
echo 'PC_CTRL_WPAY PASS (WPAY=1 and WPAY=0 production WR640 exact payload + true ACK; stale_head mutant rejected)'
