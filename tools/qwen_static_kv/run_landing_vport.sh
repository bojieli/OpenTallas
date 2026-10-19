#!/bin/bash
# run_landing_vport.sh OUT (KVJ-F 2026-10-17, stub audit K-1): the landing V response joined to its real consumer, the 16
# PV16 V ports, exactly as the static-join template (kv_static.template) and kv_die.py _pv144_buses wire them
# (rtl/test/qwen_static_kv/tb_static_landing_vport.sv: 32 x qkd_static_kv_landing_seg_h + 16 x qkd_pv16_vport r6).
#   positive: CTX 8192 and 2048, hierarchical segment (closed row_h3 / lane_h4 / relay_h2 children) -> PASS, and the flat
#             segment at CTX 8192 (same cycles) -> PASS; DQ 0 / RT 9 (direct join, no die relays: vq register -> landing pin 1 + seg LAT 8)
#   mutants (each must FAIL): JOIN_MUT 1 (port sides swapped), JOIN_MUT 2 (V gets on the wrong group), VP_MUT 3 (K/V flag
#             ignored: K words on the shared rsp bus taken as V), VP_MUT 1 (sel inverted), RT_ADJ -1 and +1 (slot off the rsp)
# Prints 'PASS landing_vport join' and exits 0 only if every positive passes and every mutant fails.
set -u
O=$1; mkdir -p "$O"
V5=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; VL=${VERILATOR:-$( [ -x $V5 ] && echo $V5 || command -v verilator)}
S=rtl/qwen_sys/static_kv_20261014
J=${JOBS:-8}
build(){ # tag params...
  local tag=$1; shift
  $VL --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN --build-jobs $J \
    --top-module tb_static_landing_vport "$@" --Mdir "$O/obj_$tag" \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
    $S/qkd_static_kv_landing.sv $S/qkd_static_kv_hop.sv $S/qkd_static_kv_landing_seg.sv $S/qkd_static_kv_landing_seg_h.sv \
    $S/qkd_pv16_vport.sv rtl/test/qwen_static_kv/tb_static_landing_vport.sv \
    > "$O/build_$tag.log" 2>&1 || { echo "BUILD FAIL $tag"; tail -5 "$O/build_$tag.log"; return 3; }
  "$O/obj_$tag/Vtb_static_landing_vport" > "$O/run_$tag.log" 2>&1
  grep -E "^(PASS|FAIL) landing_vport" "$O/run_$tag.log" | tail -1
}
rc=0
pos(){ l=$(build "$@"); echo "$1 (must PASS): ${l:-no result line}"; case "$l" in PASS*) ;; *) rc=1;; esac; }
neg(){ l=$(build "$@"); echo "$1 (must FAIL): ${l:-no result line}"; case "$l" in FAIL*) ;; *) rc=1;; esac; }
pos h_ctx8192 -GCTX=8192 -GSEGH=1
pos h_ctx2048 -GCTX=2048 -GSEGH=1
pos f_ctx8192 -GCTX=8192 -GSEGH=0
neg mut_join_sides -GCTX=2048 -GJOIN_MUT=1
neg mut_join_vq -GCTX=2048 -GJOIN_MUT=2
neg mut_vp_kvflag -GCTX=2048 -GVP_MUT=3
neg mut_vp_sel -GCTX=2048 -GVP_MUT=1
neg mut_rt_m1 -GCTX=2048 -GRT_ADJ=-1
neg mut_rt_p1 -GCTX=2048 -GRT_ADJ=1
[ $rc = 0 ] && echo "PASS landing_vport join: 32 landing segments (seg_h + flat) -> 16 V ports, K at LAT 8 + 8192 V rows exact, 6 mutants caught" \
            || echo "FAIL landing_vport join"
exit $rc
