#!/usr/bin/env bash
# run_xdie_hbm_coll.sh <src root> <out dir> [ds|qw|all]   (TOKEN-XDIE-HBM2 2026-10-18; Verilator 5.050, run on the fleet via ot-run)
# Two-die HBM d4g GEN2 cross-die ALL_REDUCE co-sim with the REAL COLL parent (tb_xdie_hbm_coll.sv header): per die
# hb_coll_NE ot_hfd_coll_q2_hard_v8g (issuer_m / static_issuer_v6 programme store, F20-loaded) + hcollgi_NE gq_issue +
# cp_ep_NE / epcal_NE calendar + lane relays + ep_N2 hfd_ep_static + lk_N2 ot_pdie_serdes; programmes compiled at
# compiler cycles by tools/xdie_hbm_coll_compile.py.  One binary; per config (ds: SWD 333 = switch 250 + cable 27.6 ns,
# qw: SWD 4 = package trace 3.3 ns):
#   stage A  probe compile (assumed K1/K2/ready)                       -> measures K1, K2, gcL (launch constants)
#   stage B  measured K1/K2/gcL, release = assumed/measured ready + 80  -> measures READY (peer block ready edge)
#   stage C  release = READY + 8 (static bound)                         -> MUST PASS (bit-exact golden fold, 0 faults,
#                                                                          block_ready true at every static release)
#   mutants (ds, stage-C constants; each MUST FAIL):  order = die 1 folds ((x2+x3)+x0)+x1 (reduce-order swap),
#            flip = one programme word bit (die 1 second rx_expect reservation), early = die 1 release 40 cycles early
# + the old transport vehicle's TOPK_MERGE point (tb_xdie_hbm_link, DS, P = 1528 frames, committed constants).
set -u
SRC=$(realpath "$1"); OUT=$(realpath -m "$2"); WHICH=${3:-all}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
"$V" --version | tee "$OUT/verilator.version"
X=$SRC/rtl/hbm_accel/generic/collective/xdie; P=$SRC/rtl/hbm_accel/generic/collective/p2p; T=$SRC/rtl/hbm_accel/generic/collective/tkm
E=$SRC/rtl/hbm_accel/tu/ep_static_20261015; L=$SRC/rtl/dsrom_sys/s81_link; Q=$SRC/rtl/qwen_sys/split_20261014
VS=$SRC/rtl/hbm_accel/generic/vm/static; M=$SRC/physical/asap7_memory_macros; H=$SRC/rtl/hdc
C="python3 $SRC/tools/xdie_hbm_coll_compile.py"
# HBM-P6-CMP (10-23): LEAF_SPLIT=1 -> hb_coll = the over-cap split parent ot_hfd_coll_q2_hard_v8g_s (u_reduce =
# ot_hgi_coll_reduce_static_pr) and the compiler schedules it (--leaf-split 1: reduce publication +1).  CMP_LS overrides
# the compiler only (negative control: twin RTL + CMP_LS=0 must FAIL).  WHICH=dsqw = ds + qw + ds mutants, no topk.
LS=${LEAF_SPLIT:-0}; CLS=${CMP_LS:-$LS}; C="$C --leaf-split $CLS"
F="$X/tb_xdie_hbm_coll.sv
 $P/ot_hfd_coll_q_hard_v8g.sv $P/ot_hfd_coll_q_hard_v5.sv $P/ot_hgi_coll_ctl_v5.sv $P/ot_hfd_coll_q3_static_host_v4.sv
 $P/ot_hfd_coll_q2_static_host_v4.sv $P/ot_hgi_coll_static_program_target.sv $P/ot_hfd_coll_q_static_v4.sv
 $P/ot_hgi_coll_static_issuer.sv $P/ot_hgi_coll_static_issuer_v5.sv $P/ot_hgi_coll_static_issuer_v6.sv $P/ot_hgi_coll_qslots.sv
 $P/ot_hgi_coll_qslots_capture_pin_v2.sv $P/ot_hgi_coll_pring_static.sv $P/ot_hgi_coll_pring_captured_static.sv
 $P/ot_hgi_coll_pring_static_state_capture.sv $P/ot_hgi_coll_slice_v7.sv $P/ot_hgi_coll_reduce_static.sv
 $P/ot_hgi_coll_argmax_static.sv $SRC/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv $P/ot_hgi_coll_static_vmwrite.sv
 $P/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv $P/ot_hgi_coll_static_vmwrite_roots_v6.sv $P/ot_hgi_coll_static_link_capture.sv
 $P/ot_hgi_coll_static_capture_ctl.sv $P/ot_hgi_coll_static_pinreg_ctl.sv $P/ot_hgi_coll_static_pinreg_store.sv
 $P/ot_hgi_coll_static_seq_ctl.sv $T/ot_hgi_coll_tkm_static.sv $T/ot_hgi_coll_tkm.sv $T/ot_hgi_coll_tkm_buffer.sv
 $P/ot_hgi_coll_ring_ag.sv $P/ot_hgi_coll_ring_ag_lane.sv $P/ot_hgi_coll_gq.sv $P/ot_hgi_coll_ring_b_stop.sv
 $SRC/rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv
 $SRC/physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv $SRC/physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv
 $H/v41/ot_hdc_actquant.sv $H/ot_hdc_fpu.sv $H/ot_hdc_fp32_mul_pipe.sv $H/ot_hdc_delay.sv $H/ot_hdc_fp32_add_lat.sv
 $H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv $SRC/rtl/lib/ot_rst_relay.sv
 $VS/ot_static_program_target.sv $VS/hfd_hgi_vm_calendar.sv $VS/ot_vms_calendar_static_xcap.sv
 $Q/ot_qkvd_d2d_llr.sv $Q/ot_qwen_crc_parallel.sv
 $E/hfd_ep_static.sv $E/ot_hep_rx_store.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
 $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
if [ "$LS" = 1 ]; then
  sed 's/^\(\s*\)ot_hfd_coll_q2_hard_v8g #(/\1ot_hfd_coll_q2_hard_v8g_s #(/' $X/tb_xdie_hbm_coll.sv > "$OUT/tb_xdie_hbm_coll_s.sv"
  grep -q "ot_hfd_coll_q2_hard_v8g_s #(" "$OUT/tb_xdie_hbm_coll_s.sv" || { echo "XDIE2 LEAF_SPLIT tb rewrite FAIL"; exit 2; }
  F="${F/$X\/tb_xdie_hbm_coll.sv/$OUT/tb_xdie_hbm_coll_s.sv} $P/ot_hfd_coll_q2_hard_v8g_s.sv $P/ot_hgi_coll_reduce_static_pr.sv"
fi
echo "XDIE2_CFG LEAF_SPLIT=$LS CMP_LS=$CLS"
sha256sum $F $SRC/tools/xdie_hbm_coll_compile.py $SRC/tools/hbm_static/leaf_split_latency.py $P/static_uop_layout_v4.json > "$OUT/sources.sha256"
"$V" --binary --timing -O1 -j ${JOBS:-16} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT +incdir+$L --top-module tb_xdie_hbm_coll \
  --Mdir "$OUT/obj" -o tb $F > "$OUT/build.log" 2>&1 || { tail -60 "$OUT/build.log"; echo "XDIE2 build FAIL"; exit 2; }
echo "XDIE2 build ok"
sim() {  # tag dir swd
  local args; args=$(grep -o '^XDIE2_ARGS .*' "$2.compile.log" | cut -d' ' -f2-)
  timeout 7200 "$OUT/obj/tb" +verilator+seed+7 +DIR="$2" +SWD=$3 $args > "$OUT/$1.log" 2>&1
  grep -E '^XDIE2 |XDIE2_(AR|XLINK|FAULT|SCHED_FAIL|ERR)' "$OUT/$1.log" | head -12
}
stage() {  # tag swd compile-args...
  local tag=$1 swd=$2; shift 2
  $C "$OUT/$tag" "$@" > "$OUT/$tag.compile.log" 2>&1 || { cat "$OUT/$tag.compile.log"; echo "XDIE2 compile $tag FAIL"; exit 3; }
  cp "$OUT/$tag.compile.log" "$OUT/$tag/compile.log"
  sim "$tag" "$OUT/$tag" "$swd"
}
rc=0
for cfg in ds qw; do
  [ "$WHICH" = all ] || [ "$WHICH" = dsqw ] || [ "$WHICH" = $cfg ] || continue
  SWD=333; [ $cfg = qw ] && SWD=4
  stage ${cfg}_A $SWD --from -
  stage ${cfg}_B $SWD --from "$OUT/${cfg}_A.log" --guard 80
  stage ${cfg}_pass $SWD --from "$OUT/${cfg}_B.log" --guard 8
  grep -q '^XDIE2 .* PASS$' "$OUT/${cfg}_pass.log" || { echo "XDIE2 ${cfg}_pass did not PASS"; rc=1; }
done
if [ "$WHICH" = all ] || [ "$WHICH" = dsqw ] || [ "$WHICH" = ds ]; then
  stage m_order 333 --from "$OUT/ds_B.log" --guard 8 --mut order
  stage m_flip 333 --from "$OUT/ds_B.log" --guard 8 --mut flip
  stage m_early 333 --from "$OUT/ds_B.log" --guard 8 --release-early 40
  for m in m_order m_flip m_early; do
    if grep -q '^XDIE2 .* FAIL$' "$OUT/$m.log"; then echo "XDIE2_MUTANT $m REJECTED"; else echo "XDIE2_MUTANT $m SURVIVED"; rc=1; fi
  done
  grep -q 'XDIE2_ERR d=1 AR payload mismatch' "$OUT/m_order.log" || { echo "XDIE2_MUTANT m_order: no payload witness"; rc=1; }
  grep -q 'XDIE2_SCHED_FAIL d=1' "$OUT/m_early.log" || { echo "XDIE2_MUTANT m_early: no static-release witness"; rc=1; }
fi
rm -rf "$OUT/obj"
# ---- TOPK_MERGE point on the old transport vehicle (DS, P = 1528, constants of results/rtl/xdie_hbm_1018/run/constants.txt)
if [ "$WHICH" = all ] || [ "$WHICH" = topk ]; then
  OF="$X/tb_xdie_hbm_link.sv $SRC/results/rtl/xdie_hbm_1018/run/src/ot_hgi_coll_link_e_extract.sv $P/ot_hgi_coll_static_capture_ctl.sv
   $P/ot_hgi_coll_static_pinreg_ctl.sv $P/ot_hgi_coll_static_pinreg_store.sv $P/ot_hgi_coll_static_seq_ctl.sv
   $Q/ot_qkvd_d2d_llr.sv $Q/ot_qwen_crc_parallel.sv $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   $E/hfd_ep_static.sv $E/ot_hep_rx_store.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
   $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
  sha256sum $OF > "$OUT/topk_sources.sha256"
  "$V" --binary --timing -O2 -j ${JOBS:-16} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
    -Wno-TIMESCALEMOD -Wno-INITIALDLY +incdir+$L --top-module tb_xdie_hbm_link -GEPMUT_B=0 --Mdir "$OUT/obj_topk" -o tb $OF \
    > "$OUT/build_topk.log" 2>&1 || { tail -30 "$OUT/build_topk.log"; echo "XDIE topk build FAIL"; exit 2; }
  timeout 7200 "$OUT/obj_topk/tb" +verilator+seed+7 +NI=1 +P0=1528 +DRX=16 +LA_PS=359117 +LXB_PS=367447 +GAPB=9 +SWD=333 \
    > "$OUT/topk1528_ds.log" 2>&1
  grep -E 'XDIE_(INST|STATIC|HBM|SCHED|ERR)' "$OUT/topk1528_ds.log" | head
  grep -q '^XDIE_HBM .* PASS$' "$OUT/topk1528_ds.log" || { echo "XDIE topk1528 did not PASS"; rc=1; }
  rm -rf "$OUT/obj_topk"
fi
echo "XDIE2_GATE rc=$rc"
exit $rc
