#!/usr/bin/env bash
# run_xdie_hbm_step4.sh <src root> <out dir> [reg|qw|ds|mut|all]   (XDIE-HBM4 2026-10-19; Verilator 5.050, fleet via ot-run)
# The XDIE-HBM3 step vehicle (tb_xdie_hbm_step.sv) built with the v8g COLL parent at AR_ITER=1 (iterated reduce tags:
# iter_ar_tag_step in the reserved word[717:714]) and ROWS=128 (static_issuer_v6 / programme target 128 rows), so the
# production-P REDUCE-SCATTER step runs as one static programme (tools/xdie_hbm_step_compile.py --ar-iter --rows 128):
#   reg: XDIE-HBM3 programmes (step 0, 64-row metadata) on the new build: qw_ag16 / qw_rs4 / ds_rs4 must PASS with the
#        XDIE-HBM3 cycle counts (199 / 190 / 519): default behaviour unchanged.
#   qw : rs64 rs32 rs16 (the hypercube TP8 all-reduce reduce steps) + rs4, iterated tags.   ds: rs48 (DS production P).
#   mut (each MUST FAIL): arstep (die 1 RS loop body tag step +1), rsrc (die 1 frame 1 local operand from frame 5),
#        nostep (RTL mutant OT_COLL_ARITER_MUT_NOSTEP: the iteration product dropped, rs16 pass programme).
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
build() {  # objdir extra-defines...
  local o=$1; shift
  "$V" --binary --timing -O1 -j ${JOBS:-16} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
    -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT +incdir+$L --top-module tb_xdie_hbm_step \
    +define+XDIE_AR_ITER=1 +define+XDIE_ROWS=128 "$@" --Mdir "$OUT/$o" -o tb $F > "$OUT/$o.build.log" 2>&1 \
    || { tail -60 "$OUT/$o.build.log"; echo "XDIE4 build $o FAIL"; exit 2; }
  echo "XDIE4 build $o ok"
}
build obj
TB=obj
stage() {  # tag swd compile-args...
  local tag=$1 swd=$2 args; shift 2
  $C "$OUT/$tag" --swd "$swd" "$@" > "$OUT/$tag.compile.log" 2>&1 || { cat "$OUT/$tag.compile.log"; echo "XDIE4 compile $tag FAIL"; return 3; }
  cp "$OUT/$tag.compile.log" "$OUT/$tag/compile.log"
  args=$(grep -o '^XDIE2_ARGS .*' "$OUT/$tag.compile.log" | cut -d' ' -f2-)
  { cat "$OUT/$tag.compile.log"; timeout 7200 "$OUT/$TB/tb" +verilator+seed+7 +DIR="$OUT/$tag" +SWD=$swd ${ADR:+$ADRARG} $args; } > "$OUT/$tag.log" 2>&1
  grep -E '^XDIE2 |XDIE3_(STEP|E|ADR)|XDIE2_(FAULT|SCHED_FAIL|ERR)' "$OUT/$tag.log" | head -8
}
rc=0
run_cfg() {  # name swd kind frames [compile flags]
  local n=$1 swd=$2 k=$3 p=$4; shift 4
  stage ${n}_A $swd --kind $k --frames $p --from - "$@"
  stage ${n}_B $swd --kind $k --frames $p --from "$OUT/${n}_A.log" --guard 80 "$@"
  stage ${n}_pass $swd --kind $k --frames $p --from "$OUT/${n}_B.log" --guard 8 "$@"
  if grep -q '^XDIE2 .* PASS$' "$OUT/${n}_pass.log"; then echo "XDIE4_CFG $n PASS"; else echo "XDIE4_CFG $n FAIL"; rc=1; fi
}
AI="--ar-iter --rows 128"; ADRARG=+ADRCHK; ADR=
if [ "$WHICH" = all ] || [ "$WHICH" = reg ]; then
  run_cfg reg_qw_ag16 4 ag 16; run_cfg reg_qw_rs4 4 rs 4; run_cfg reg_ds_rs4 333 rs 4
fi
if [ "$WHICH" = all ] || [ "$WHICH" = qw ]; then
  for c in "qw_rs64 rs 64" "qw_rs32 rs 32" "qw_rs16 rs 16" "qw_rs4 rs 4"; do set -- $c; run_cfg $1 4 $2 $3 $AI; done
fi
if [ "$WHICH" = all ] || [ "$WHICH" = ds ]; then
  run_cfg ds_rs48 333 rs 48 $AI
fi
if [ "$WHICH" = adr ]; then   # item 3: del_obase one row after the sink row, delivery offset CHECKED (+ADRCHK)
  ADR=1
  for c in "qa_ag16 4 ag 16" "qa_rs64 4 rs 64" "qa_rs32 4 rs 32" "qa_rs16 4 rs 16" "da_rs48 333 rs 48" "da_ag48 333 ag 48"; do
    set -- $c; run_cfg $1 $2 $3 $4 $AI --del-edge 1; done
  stage m_adr0 4 --kind rs --frames 16 --from "$OUT/qa_rs16_B.log" --guard 8 $AI     # del-edge 0 MUST FAIL under +ADRCHK
  if grep -q '^XDIE2 .* FAIL$' "$OUT/m_adr0.log"; then echo "XDIE4_MUTANT m_adr0 REJECTED"; else echo "XDIE4_MUTANT m_adr0 SURVIVED"; rc=1; fi
fi
if [ "$WHICH" = all ] || [ "$WHICH" = mut ]; then
  [ -f "$OUT/qw_rs16_B.log" ] || run_cfg qw_rs16 4 rs 16 $AI
  stage m_arstep 4 --kind rs --frames 16 --from "$OUT/qw_rs16_B.log" --guard 8 $AI --mut arstep
  stage m_rsrc 4 --kind rs --frames 16 --from "$OUT/qw_rs16_B.log" --guard 8 $AI --mut rsrc
  build obj_nostep +define+OT_COLL_ARITER_MUT_NOSTEP
  TB=obj_nostep; stage m_nostep 4 --kind rs --frames 16 --from "$OUT/qw_rs16_B.log" --guard 8 $AI; TB=obj
  for m in m_arstep m_rsrc m_nostep; do
    if grep -q '^XDIE2 .* FAIL$' "$OUT/$m.log"; then echo "XDIE4_MUTANT $m REJECTED"; else echo "XDIE4_MUTANT $m SURVIVED"; rc=1; fi
  done
fi
rm -rf "$OUT/obj" "$OUT/obj_nostep"
echo "XDIE4_GATE rc=$rc"
exit $rc
