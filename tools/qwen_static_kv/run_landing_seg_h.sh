#!/bin/bash
# run_landing_seg_h.sh pos|neg OUT (KVCTRL 1815, 2026-10-16): run_landing_seg.sh with the HIERARCHICAL segment
# qkd_static_kv_landing_seg_h (4 lanes + row + 2 relays; every clock entry fed by the TB clock) as the DUT; the TB is the
# unchanged tb_static_landing, copied and re-pointed at the _h module (only the instance line changes).
# Original header: the hardened static landing segment qkd_static_kv_landing_seg
# in tb_static_landing at production shape (32 groups = 32 segment instances on their cfg straps, 128 PCs with the real
# 128x256 SRAM model, VMAP 1 = PV16 V layout, VREQ 1 = V gets on the vport face), latency 8 edges.
#   pos: K contexts CTX 1000 / 2048 / 4096 / 8192 must PASS (every K and V row word, t, kind on its edge); at 8192 the
#        fault modes 1-5 must FAIL; the old K ordinal (DUT_MUT 3, aliasing rows) must FAIL at CTX 2048
#   neg: the segment with HOP_MUT 1 (branch-0 response hop flips a data bit) must FAIL -> prints
#        'FAIL landing_seg mutant detected' and exits 1
set -u
M=$1; O=$2; mkdir -p "$O"
V5=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; VL=${VERILATOR:-$( [ -x $V5 ] && echo $V5 || command -v verilator)}
S=rtl/qwen_sys/static_kv_20261014
TB=$O/tb_static_landing_h.sv
sed -e 's/qkd_static_kv_landing_seg #(/qkd_static_kv_landing_seg_h #(/' -e 's/\.ck(ck),\.rst_n(rst),\.cfg_stack/.ck(ck),.ck_p0(ck),.ck_p1(ck),.ck_p2(ck),.ck_p3(ck),.ck_r0(ck),.ck_r3(ck),.rst_n(rst),.cfg_stack/' \
  rtl/test/qwen_static_kv/tb_static_landing.sv > $TB
[ $(grep -c 'qkd_static_kv_landing_seg_h #(' $TB) = 1 ] && [ $(grep -c 'ck_r3(ck)' $TB) = 1 ] || { echo "TB re-point FAILED"; exit 4; }
build(){ # ctx dut_mut hop_mut
  $VL --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN --build-jobs 8 \
    --top-module tb_static_landing -GVMAP=1 -GDUT_VMAP=1 -GVREQ=1 -GPHYS=1 -GCTX=$1 -GDUT_MUT=$2 -GSEG_HOP_MUT=$3 --Mdir "$O/obj_$1_$2_$3" \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
    $S/qkd_static_kv_landing.sv $S/qkd_static_kv_hop.sv $S/qkd_static_kv_landing_seg_h.sv $TB \
    > "$O/build_$1_$2_$3.log" 2>&1 || { echo "BUILD FAIL $1 $2 $3"; tail -5 "$O/build_$1_$2_$3.log"; exit 3; }; }
res(){ "$O/obj_$1_$2_$3/Vtb_static_landing" +faultmode=$4 2>&1 | tee "$O/run_$1_$2_$3_$4.log" | grep -E "^(PASS|FAIL) staticlanding" | tail -1; }
if [ "$M" = neg ]; then
  build 8192 0 1; l=$(res 8192 0 1 0); echo "mutant run: ${l:-no result line}"
  case "$l" in FAIL*) echo "FAIL landing_seg mutant detected (response hop data bit)"; exit 1;; esac
  echo "mutant NOT detected"; exit 0
fi
rc=0
chk(){ case "$2" in $1*) ;; *) rc=1;; esac; }
for c in 1000 2048 4096 8192; do build $c 0 0; l=$(res $c 0 0 0); echo "CTX $c: ${l:-no result line}"; chk PASS "$l"; done
for f in 1 2 3 4 5; do l=$(res 8192 0 0 $f); echo "CTX 8192 faultmode $f (must FAIL): ${l:-no result line}"; chk FAIL "$l"; done
build 2048 3 0; l=$(res 2048 3 0 0); echo "CTX 2048 old K ordinal DUT_MUT 3 (must FAIL): ${l:-no result line}"; chk FAIL "$l"
[ $rc = 0 ] && echo "PASS landing_seg exact (hier seg_h): 32 segments x 4 PCs, K at CTX 1000/2048/4096/8192 + V (PV16, vport face) every word, fault modes 1-5 and the aliasing ordinal caught" || echo "FAIL landing_seg"
exit $rc
