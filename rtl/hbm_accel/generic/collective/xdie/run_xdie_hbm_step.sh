#!/usr/bin/env bash
# run_xdie_hbm_step.sh <src root> <out dir> [qw|ds|mut|all]   (XDIE-HBM3 2026-10-19; Verilator 5.050, on the fleet via ot-run)
# Two-die HBM d4g GEN2 cross-die collective STEP co-sim, VM-SOURCED, production frame counts (tb_xdie_hbm_step.sv header):
# per die hb_coll_NE ot_hfd_coll_q2_hard_v8g (static_issuer_v6 LOOP programme, F20-loaded) + hcollgi_NE + cp_ep_NE/epcal_NE
# + lane relays + ep_N2 hfd_ep_static + lk_N2 ot_pdie_serdes; programmes by tools/xdie_hbm_step_compile.py.
# Configs (Qwen package SWD 4 = 3.3 ns; DS switch SWD 333 = 250 + 27.6 ns):
#   qw: ag64 ag32 ag16 (the hypercube TP8 all-reduce gather steps, 64/32/16 frames a link) + ag4 rs4 (reduce-step delta)
#   ds: ag48 (production P of the DS gathers) + ag4 rs4
#   Each: stage A probe (assumed K1/K2/gcL/READY) -> B (measured, release READY+80) -> pass (release READY+8, MUST PASS).
#   mut (qw ag16 / rs4 pass constants, each MUST FAIL): vmstep (die 1 TX VM sector step +1), flip (die 1 first rx_expect
#   bit), early (die 1 release 40 cycles early), rsrc (rs4: die 1 frame 1 local operand from frame 5's sector).
# The rs step at production P does NOT fit one 64-row static_issuer_v6 programme (reduce tags are not iterated; 2 reduce
# inputs a frame): compiler capacity assert at rs8 (70 rows) -- recorded as a finding, rs measured at P = 4.
set -u
SRC=$(realpath "$1"); OUT=$(realpath -m "$2"); WHICH=${3:-all}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
"$V" --version | tee "$OUT/verilator.version"
X=$SRC/rtl/hbm_accel/generic/collective/xdie; P=$SRC/rtl/hbm_accel/generic/collective/p2p; T=$SRC/rtl/hbm_accel/generic/collective/tkm
E=$SRC/rtl/hbm_accel/tu/ep_static_20261015; L=$SRC/rtl/dsrom_sys/s81_link; Q=$SRC/rtl/qwen_sys/split_20261014
VS=$SRC/rtl/hbm_accel/generic/vm/static; M=$SRC/physical/asap7_memory_macros; H=$SRC/rtl/hdc
C="python3 $SRC/tools/xdie_hbm_step_compile.py"
F="$X/tb_xdie_hbm_step.sv
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
 $E/hfd_ep_static.sv $E/ot_hep_rx_store.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_bm.sv
 $L/ot_pdie_serdes.sv
 $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
sha256sum $F $SRC/tools/xdie_hbm_step_compile.py $P/static_uop_layout_v4.json > "$OUT/sources.sha256"
"$V" --binary --timing -O1 -j ${JOBS:-16} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT +incdir+$L --top-module tb_xdie_hbm_step \
  --Mdir "$OUT/obj" -o tb $F > "$OUT/build.log" 2>&1 || { tail -60 "$OUT/build.log"; echo "XDIE3 build FAIL"; exit 2; }
echo "XDIE3 build ok"
stage() {  # tag swd compile-args...
  local tag=$1 swd=$2 args; shift 2
  $C "$OUT/$tag" --swd "$swd" "$@" > "$OUT/$tag.compile.log" 2>&1 || { cat "$OUT/$tag.compile.log"; echo "XDIE3 compile $tag FAIL"; return 3; }
  cp "$OUT/$tag.compile.log" "$OUT/$tag/compile.log"
  args=$(grep -o '^XDIE2_ARGS .*' "$OUT/$tag.compile.log" | cut -d' ' -f2-)
  { cat "$OUT/$tag.compile.log"; timeout 7200 "$OUT/obj/tb" +verilator+seed+7 +DIR="$OUT/$tag" +SWD=$swd $args; } > "$OUT/$tag.log" 2>&1
  grep -E '^XDIE2 |XDIE3_(STEP|E|ADR)|XDIE2_(FAULT|SCHED_FAIL|ERR)' "$OUT/$tag.log" | head -8
}
rc=0
run_cfg() {  # name swd kind frames
  local n=$1 swd=$2 k=$3 p=$4
  stage ${n}_A $swd --kind $k --frames $p --from -
  stage ${n}_B $swd --kind $k --frames $p --from "$OUT/${n}_A.log" --guard 80
  stage ${n}_pass $swd --kind $k --frames $p --from "$OUT/${n}_B.log" --guard 8
  if grep -q '^XDIE2 .* PASS$' "$OUT/${n}_pass.log"; then echo "XDIE3_CFG $n PASS"; else echo "XDIE3_CFG $n FAIL"; rc=1; fi
}
if [ "$WHICH" = all ] || [ "$WHICH" = qw ]; then
  for c in "qw_ag64 ag 64" "qw_ag32 ag 32" "qw_ag16 ag 16" "qw_ag4 ag 4" "qw_rs4 rs 4"; do set -- $c; run_cfg $1 4 $2 $3; done
fi
if [ "$WHICH" = all ] || [ "$WHICH" = ds ]; then
  for c in "ds_ag48 ag 48" "ds_ag4 ag 4" "ds_rs4 rs 4"; do set -- $c; run_cfg $1 333 $2 $3; done
fi
if [ "$WHICH" = all ] || [ "$WHICH" = mut ]; then
  [ -f "$OUT/qw_ag16_B.log" ] || run_cfg qw_ag16 4 ag 16
  [ -f "$OUT/qw_rs4_B.log" ] || run_cfg qw_rs4 4 rs 4
  stage m_vmstep 4 --kind ag --frames 16 --from "$OUT/qw_ag16_B.log" --guard 8 --mut vmstep
  stage m_flip 4 --kind ag --frames 16 --from "$OUT/qw_ag16_B.log" --guard 8 --mut flip
  stage m_early 4 --kind ag --frames 16 --from "$OUT/qw_ag16_B.log" --guard 8 --release-early 40
  stage m_rsrc 4 --kind rs --frames 4 --from "$OUT/qw_rs4_B.log" --guard 8 --mut rsrc
  for m in m_vmstep m_flip m_early m_rsrc; do
    if grep -q '^XDIE2 .* FAIL$' "$OUT/$m.log"; then echo "XDIE3_MUTANT $m REJECTED"; else echo "XDIE3_MUTANT $m SURVIVED"; rc=1; fi
  done
  grep -q 'XDIE2_ERR d=0 link frame' "$OUT/m_vmstep.log" || { echo "XDIE3_MUTANT m_vmstep: no link payload witness"; rc=1; }
  grep -q 'XDIE2_SCHED_FAIL d=1' "$OUT/m_early.log" || { echo "XDIE3_MUTANT m_early: no static-release witness"; rc=1; }
  grep -q 'XDIE2_ERR d=1 delivery 1 payload mismatch' "$OUT/m_rsrc.log" || { echo "XDIE3_MUTANT m_rsrc: no reduce payload witness"; rc=1; }
fi
rm -rf "$OUT/obj"
echo "XDIE3_GATE rc=$rc"
exit $rc
