#!/bin/bash
# run_qtkm_bench.sh: tb_hgi_coll_qtkm (SW quadrant body TOPK_MERGE + credit-flow line writes across RLY relays).
#   run_qtkm_bench.sh <outdir> <vecdir (tools/hgi_coll_tkm_vectors.py)>
# every case PASS at RLY 8 / TCRD 8; syn_sel / syn_cand with +WSTALL=30 and at RLY 20 / TCRD 4; CRL_MUT 1 and MUT_TKM 1 on
# syn_sel must FAIL.  SUMMARY lines "OK|WRONG name expect got ...", then QTKM PASS / QTKM FAIL.
set -uo pipefail
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "$1"); VEC=$(realpath -m "$2"); mkdir -p "$O/logs"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
[ -d "$VEC" ] || { echo "QTKM FAIL: missing vectors $VEC" >&2; exit 2; }
mapfile -t cases < <(find "$VEC" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
[ "${#cases[@]}" -gt 0 ] || { echo "QTKM FAIL: no vector cases" >&2; exit 2; }
for c in syn_sel syn_cand; do
  [ -d "$VEC/$c" ] || { echo "QTKM FAIL: missing required case $c" >&2; exit 2; }
done
C=rtl/hbm_accel/generic/collective
build() { local ob=$O/$1; shift
  ( cd "$R" && $V --binary --timing -j ${JOBS:-8} -O2 ${VFLAGS:-} --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
    -Wno-MULTIDRIVEN -Wno-WIDTHCONCAT --top-module tb_hgi_coll_qtkm -Mdir "$ob" -Irtl/hbm_accel/generic "$@" \
    --hierarchical $C/p2p/qtkm_hier.vlt $C/p2p/tb_hgi_coll_qtkm.sv $C/p2p/ot_hgi_coll_qep.sv $C/p2p/ot_hbm_accel_tu_endpoint_qpsg.sv $C/p2p/ot_hgi_coll_qrec.sv $C/p2p/ot_hgi_coll_crl.sv $C/p2p/ot_hgi_coll_rgx_wtx.sv \
    $C/tkm/ot_hgi_coll_tkm.sv $C/p2p/ot_hgi_coll_tkm_native.sv $C/tkm/ot_hgi_coll_tkm_seq_split.sv $C/tkm/ot_hgi_coll_tkm_seq_lane_core.sv $C/tkm/ot_hgi_coll_tkm_lane.sv $C/tkm/ot_hgi_coll_tkm_buffer.sv $C/tkm/ot_hgi_coll_tkm_packer.sv rtl/lib/ot_rst_relay.sv $C/rgx/ot_hgi_coll_rgx_src.sv $C/rgx/ot_hgi_coll_rgx_sink.sv $C/rgx/ot_hgi_coll_rgx_snk.sv \
    rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv \
    rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
    rtl/hdc/ot_hdc_fastfp.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
    rtl/hbm_accel/generic/ot_hgi_cfg.sv $C/ot_hgi_coll_decode.sv $C/ot_hgi_coll_amerge.sv > "$ob.build.log" 2>&1 ) || echo "BUILD FAIL $ob" >> "$O/SUMMARY"
}
run() { local n=$1 e=$2 o=$3 c=$4; shift 4
  "$O/$o/Vtb_hgi_coll_qtkm" +DIR="$VEC/$c" "$@" > "$O/logs/$n.log" 2>&1
  if grep -q "^PASS tb_hgi_coll_tkm" "$O/logs/$n.log"; then r=PASS; else r=FAIL; fi
  local cy; cy=$(grep -o "CYCLES=[0-9]*" "$O/logs/$n.log" | head -1); local why; why=$(grep -m1 -o "FAIL.*" "$O/logs/$n.log" | cut -c1-120)
  [ "$r" = "$e" ] && v=OK || v=WRONG; echo "$v $n expect=$e got=$r $cy $why | $c $*" >> "$O/SUMMARY"
}
: > "$O/SUMMARY"
# The production parent is large even with tile hierarchy. Allow concurrency only against a measured job envelope.
# Each variant is independent; the fleet can still run other streams while these elaborations serialize.
if [ "${BUILD_JOBS:-1}" -gt 1 ]; then
  build obj_base & build obj_r20 -GRLY=20 -GTCRD=4 & build obj_crl -GCRL_MUT=1 & build obj_mt1 -GMUT_TKM=1 & wait
else
  build obj_base; build obj_r20 -GRLY=20 -GTCRD=4; build obj_crl -GCRL_MUT=1; build obj_mt1 -GMUT_TKM=1
fi
if grep -q "BUILD FAIL" "$O/SUMMARY"; then cat "$O/SUMMARY"; echo "QTKM FAIL"; exit 2; fi
for c in "${cases[@]}"; do run $c PASS obj_base $c & done; wait
for c in syn_sel syn_cand; do run ${c}_wstall30 PASS obj_base $c +WSTALL=30 +SEED=3 & run ${c}_r20 PASS obj_r20 $c +WSTALL=20 +SEED=4 & done
run mut_crl_syn_sel FAIL obj_crl syn_sel & run mut_tkm1_syn_sel FAIL obj_mt1 syn_sel & wait
sort -o "$O/SUMMARY" "$O/SUMMARY"
if grep -q "^WRONG\|BUILD FAIL" "$O/SUMMARY"; then echo "QTKM FAIL"; exit 1; else echo "QTKM PASS $(grep -c ^OK "$O/SUMMARY") cases"; fi
