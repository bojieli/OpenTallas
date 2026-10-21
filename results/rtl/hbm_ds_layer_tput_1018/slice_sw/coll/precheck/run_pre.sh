#!/usr/bin/env bash
# VEH-FMT-COLL pre-check: build tb_coll_replay once (Verilator 5.050), run every *.events.txt
set -u
H=$(cd "$(dirname "$0")" && pwd); B=/srv/opentallas-scratch/claude/layerbench-hbm/sw2
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
P=$B/rtl/hbm_accel/generic/collective/p2p
LIB=("$P/ot_hgi_coll_gq.sv" "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_ring_b_stop.sv"
     "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv"
     $B/rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv $B/rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
     $B/rtl/lib/ot_rst_relay.sv $B/physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv $B/physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
     $H/ot_hdc_actquant.sv $B/rtl/hdc/ot_hdc_fpu.sv $B/rtl/hdc/ot_hdc_fp32_mul_pipe.sv $B/rtl/hdc/ot_hdc_delay.sv
     $B/rtl/hdc/ot_hdc_fp32_add_lat.sv $B/rtl/hdc/ot_hdc_prefix.sv $B/rtl/hdc/ot_hdc_fastfp.sv)
sha256sum "${LIB[@]}" $H/tb_coll_replay.sv > $H/sources.sha256
if [ ! -x $H/obj/Vtb_coll_replay ]; then
  "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    --top-module tb_coll_replay --Mdir $H/obj $H/tb_coll_replay.sv "${LIB[@]}" > $H/build.log 2>&1 || { tail -30 $H/build.log; exit 2; }
fi
rc=0
for f in $H/*.events.txt; do
  n=$(basename $f .events.txt)
  $H/obj/Vtb_coll_replay +EV=$f > $H/$n.log 2>&1
  r=$(grep -m1 -E '^COLLRPL (PASS|FAIL)' $H/$n.log); echo "$n: $r"; grep -m4 MISMATCH $H/$n.log
  echo "$r" | grep -q PASS || rc=1
done
exit $rc
