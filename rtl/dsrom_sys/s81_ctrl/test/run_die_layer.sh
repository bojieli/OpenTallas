#!/bin/bash
# run_die_layer.sh <src root> <out dir> [modes] : tb_s81_die_layer (Verilator 5.050; s81die-1011/ctrl bench).
# One DeepSeek layer on the S81 die control plane with real masters (fld gather+capture, hc dsfd_sp_hc_c, coll
# dsfd_sp_collective_c in a 4-die TP4 group), golden-exact at the layer output.  Stimulus: tools/s81_ctrl/die_layer_stim.py
# (CASES = the su_cases pickle hc_gate uses; LAYERS default "L0 L2": base runs every layer, mutants run L0).
# nom (PASS on every layer): base with EPER 0 = no injected link errors (the nominal-latency run the collective and the
# all-reduce + POST pair are timed on; base keeps one flipped bit per 97 frames).  NG=256 is the production HC width
# (1,024 lanes, 20 y beats a block); the default NG 16 is a reduced bench shape and is NOT a throughput measurement of the HC.
# Modes: base (PASS on every layer); mut_ep (gather endpoint wrong done tag), mut_drop (gather dropped done),
# mut_hc (HC core MUT 1: hc_post does not write h back), mut_coll (collective OT_S81PH_MUT_TREP: output slice 1 pops one cycle early), mut_inp (HC
# f_inp tied 1 instead of the VM row-completion state), mut_seqc (TB_SEQC + OT_SSEQC_MUT_DROP_START) -- each must FAIL.
# seqc (PASS): the decision-A sequencer dsfd_stage_seq_c (kit start / done, program on ckv) replaces dsfd_sp_ctrl_e,
# 3 sequential jobs of the layer (the kit lands each HIDDEN payload in the VM).
# HCH=1: the HC slab is the hierarchical production tuple of tools/s81_suhc/hc_gate.py --hier 3 (HIER 1, HALF 1, CSPLIT 1,
# TAIL_SPLIT 2, CNL_PIN 1, CHAIN_STEP 6, HEAD_ROWS 10 at NG 256 / 2 below) with the routed pad split, instead of the flat engine.
# STIMX: extra die_layer_stim.py options (--coef-split: two COEF jobs a block, see the tool).
# Env: CASES (required), NG (16), FP (rtl|dpi, rtl), HCH (0), STIMX, LAYERS, VL (verilator), J (build jobs, 16), ADMIT ("" or
# "/srv/opentallas-scratch/admit.sh <GB> --").  Verdict line: DIE_LAYER_GATE PASS|FAIL.  Fleet hosts only.
# XG: extra -G parameters of the bench for every mode (h transfer, rom-layer-tput 10-13: "-GPIPE=1 -GHST=1 -GHTX=2"; a mode's own
# -G of the same name replaces it).  Negative controls of the h transfer, each must FAIL: mut_pd (POST issue-order done with
# PD 0: the next HC job overtakes the last write-back), mut_hl (landing streamer MUT 1: H rows read from the VM while they
# land), mut_tx (hand-off go at the H_STORE take: rows sent before they are written).
# CHAINS (optional): the HC chain fixture of tools/s81_ctrl/die_layer_chain.py for a layer the pinned CASES pickle does
# not hold (LAYERS=L14, an Engram layer: its eng.* ops are BEHAVIOURAL at program duration, see the stim tool);
# CHAINS may hold "%L", replaced by the layer name.  Unset: L0 / L2 exactly as before.
# SUSNAP (s81-ftok r3): the REAL SU slab (+define+TB_SU_REAL): the layer's SU operand snapshot path, "%N" replaced by the
# two-digit layer number (tools/dsrom_1m_su.py golden --engram snap_L%N.pkl); modes mut_su (slab MUT 4: gain set
# ignored), mut_sux (XMUT 3: QR inverse rotation) and mut_rw (XMUT 4: RW without route_scale) must FAIL.
set -u
SRC=$1; OUT=$2; MODES=${3:-"base seqc mut_ep mut_drop mut_hc mut_coll mut_inp mut_seqc"}
NG=${NG:-16}; FP=${FP:-rtl}; HCH=${HCH:-0}; LAYERS=${LAYERS:-"L0 L2"}; VL=${VL:-verilator}; J=${J:-16}; ADMIT=${ADMIT:-}
mkdir -p $OUT
S=$SRC/rtl/dsrom_sys; P=$S/s81_ph
CHAINS=${CHAINS:-}
for L in $LAYERS; do
  CH=""; case $L in L0|L2) ;; *) [ -n "$CHAINS" ] && CH="--chain ${CHAINS//%L/$L}";; esac
  case $L in M*) CH="$CH --program-layer ${PROGL:-L0}";; esac
  SS=""; if [ -n "${SUSNAP:-}" ]; then f=${SUSNAP//%L/$L}; case $L in L*) f=${f//%N/$(printf %02d ${L#L})};; esac; SS="--su-snap $f"; fi
  MX=""; if [ -n "${MIXSNAP:-}" ]; then f=${MIXSNAP//%L/$L}; case $L in L*) f=${f//%N/$(printf %02d ${L#L})};; esac; MX="--mix-snap $f"; fi
  python3 $SRC/tools/s81_ctrl/die_layer_stim.py $OUT/stim_$L --cases $CASES --layer $L --ng $NG $CH $SS $MX ${STIMX:-} > $OUT/stim_$L.log 2>&1 \
    || { echo "DIE_LAYER_GATE FAIL stim $L: $(tail -2 $OUT/stim_$L.log)" | tee $OUT/verdicts.log; exit 1; }
done
FPF="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv"
[ $FP = dpi ] && FPF="rtl/test/sim_hdc_v41x_fastfp_dpi.sv rtl/test/sim_hdc_v41x_fastfp_wrap.sv rtl/test/sim_hdc_v41x_fastfp_dpi.cpp rtl/test/sim_hdc_fp32_f12_dpi_tops.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp rtl/test/sim_hdc_fp32_lat_tops.sv rtl/test/sim_hdc_prefix_beh.sv rtl/test/sim_dsrom_fp32_add_l6_dpi.sv"
LIST="rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_skid_buffer.sv rtl/common/ot_ratio_cdc_fifo.sv
 rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv rtl/dsrom_sys/s81_ctrl/dsfd_stage_seq_c.sv
 rtl/dsrom_sys/s81_ctrl/ot_s81_pkg_ctrl.sv rtl/dsrom_sys/s81_ctrl/ot_s81_stage_guard.sv rtl/dsrom_sys/s81_ctrl/ot_s81_hop_tx.sv
 rtl/dsrom_sys/s81_ctrl/ot_s81_stop.sv rtl/dsrom_sys/s81_ctrl/ot_s81_host_cq.sv rtl/dsrom_sys/s81_ctrl/ot_s81_ctrl.sv rtl/dsrom_sys/ot_dsrom_stall_export.sv
 rtl/dsrom_sys/engram/ot_dsrom_engram_lead_producer.sv physical/s81_ctrl/rtl/dsfd_sp_ctrl_core.sv physical/s81_ctrl/rtl/dsfd_sp_ctrl_e.sv
 rtl/v41rom/ot_v41_ret.sv rtl/gpu/ot_fp32_add_rne_deep.sv rtl/hdc/ot_hdc_delay.sv
 rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv rtl/dsrom_sys/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_ret_root_p.sv rtl/dsrom_sys/s81_ph/ot_s81ph_root_blk.sv rtl/dsrom_sys/s81_ph/ot_s81ph_root_tile.sv rtl/dsrom_sys/s81_ph/ot_s81ph_gather.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_cap_p.sv rtl/dsrom_sys/s81_ph/ot_s81ph_capture.sv rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv
 rtl/dsrom_sys/s81_ph/dsfd_sp_gather.sv rtl/dsrom_sys/s81_ph/dsfd_sp_capture.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c.sv
 rtl/dsrom_sys/s81_suhc/ot_s81_hc_core.sv rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv rtl/dsrom_sys/s81_suhc/dsfd_sp_hc_c.sv rtl/dsrom_sys/s81_suhc/ot_s81_hc_hland.sv
 rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/hdc/v41x/ot_dsrom_divc.sv
 rtl/dsrom_sys/s81_ph/dsfd_sp_collective.sv rtl/dsrom_sys/s81_ph/coll/dsfd_coll_ck.sv rtl/dsrom_sys/s81_ph/coll/dsfd_coll_core.sv rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_coll_core.sv rtl/dsrom_sys/s81_ph/ot_s81ph_coll_rstc.sv rtl/dsrom_sys/s81_ph/ot_s81_pll_bb.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
 rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_collective_c.sv rtl/dsrom_sys/s81_ph/coll/dsfd_coll_job.sv rtl/dsrom_sys/s81_ctrl/ot_s81_coll_job.sv rtl/dsrom_sys/s81_ph/coll/dsfd_coll_xc.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv
 rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv rtl/link/ot_fifo_sram_fwft.sv rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv
 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/ot_dsrom_link_chan.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 $FPF rtl/dsrom_sys/s81_ctrl/test/tb_s81_die_layer.sv"
if [ -n "${SUSNAP:-}" ]; then
  SUL=$(cd $SRC && python3 -c "import sys; sys.path.insert(0,'tools/s81_suhc'); import su_gate as G; print(' '.join(dict.fromkeys(G.RTL + G.HIER)))")
  LIST="$SUL $LIST"
fi
if [ -n "${MIXSNAP:-}" ]; then
  [ "$FP" = rtl ] || { echo "MIX4 integration requires FP=rtl"; exit 1; }
  LIST="$LIST rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv"
fi
# HCXROM (s81-ftok r10): the REAL HC coefficient chain on port 9 (+define+TB_HCX_REAL; STIMX must carry --hcx-real
# --hcx-issue A,F --hcx-p2p N and XG the measured -GHX_* offsets): HCXROM = a dir holding the 24-row resident fn images
# (hcx_rank_images.py) and the post parameter images hcx_post_p*.  Modes mut_hcxl (HLAYOUT 0 on h_rows) and mut_hcxp
# (post MUT_POST) must FAIL.
if [ -n "${HCXROM:-}" ]; then
  [ "$FP" = rtl ] || { echo "HCX integration requires FP=rtl"; exit 1; }
  LIST="$LIST rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_projection_leaf.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_prefetch.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_controller.sv
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_hrow_transpose.sv rtl/dsrom_sys/s81_hcx/dsfd_sp_hcx_projection.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_gatherpack.sv
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_chain_seq.sv
 rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv
 rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv rtl/hbm_accel/generic/adapters/ot_hgi_hc_record.sv rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv
 rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_wrd.sv rtl/link/ot_fifo_sram_fwft.sv
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_vm_scheduled.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_post_native.sv
 rtl/dsrom_sys/s81_native_head_connect/ot_s81_head_gain_stream.sv rtl/dsrom_sys/s81_hcx/ot_s81_hcx_post_gain_native.sv"
fi
# the hierarchical HC slab modules dsfd_sp_hc.sv names since 10-12 (HIER generate; the bench keeps HIER 0): without them the build fails
FILES=$( (for f in $LIST; do echo $SRC/$f; done; ls $SRC/rtl/dsrom_sys/s81_suhc/hier/*.sv) | awk '!seen[$0]++')
if [ $FP = dpi ]; then
  mkdir -p $OUT/dpi_rest
  ( cd $SRC && python3 -c "import sys; sys.path.insert(0,'tools/s81_suhc'); import hc_gate; from pathlib import Path; [print(p) for p in hc_gate.dpi_rest(Path('$OUT/dpi_rest'))]" ) > $OUT/dpi_rest.list
  FILES="$(cat $OUT/dpi_rest.list) $(echo "$FILES" | grep -v '/rtl/hdc/ot_hdc_prefix.sv')"
fi
sha256sum $FILES $SRC/tools/s81_ctrl/die_layer_stim.py $SRC/tools/s81_suhc/hc_gate.py $SRC/tools/s81_ftok/su_layer.py $SRC/tools/s81_suhc/su_gate.py > $OUT/sources.sha256
SUD=""; [ -n "${SUSNAP:-}" ] && SUD="+define+TB_SU_REAL"
[ -n "${SUSNAP:-}" ] && for L in $LAYERS; do f=${SUSNAP//%L/$L}; case $L in L*) f=${f//%N/$(printf %02d ${L#L})};; esac; sha256sum $f; done >> $OUT/sources.sha256
[ -n "$CHAINS" ] && sha256sum $SRC/tools/s81_ctrl/die_layer_chain.py $(for L in $LAYERS; do f=${CHAINS//%L/$L}; [ -f "$f" ] && echo $f; done | sort -u) >> $OUT/sources.sha256
[ -n "${MIXSNAP:-}" ] && SUD="$SUD +define+TB_MIX4_REAL"
[ -n "${HCXROM:-}" ] && SUD="$SUD +define+TB_HCX_REAL +define+OT_HCX_ROM_HIERLOAD"
SPL="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 +define+OT_S81PH_COLL_OQPIPE +define+OT_S81PH_COLL_QPIPE +define+OT_S81PH_COLL_SPLIT +define+OT_S81PH_COLL_CR +define+OT_S81PH_LANE_CR +define+OT_S81PH_COLL_PULL +define+OT_S81PH_COLL_TREP"
HX=""; [ $HCH = 1 ] && HX="+define+TB_HC_HIER -GHIER=1 -GHALF=1 -GCSPLIT=1 -GTAIL_SPLIT=2 -GCNL_PIN=1 -GCHAIN_STEP=6 -GHEAD_ROWS=$([ $NG = 256 ] && echo 10 || echo 2)"
for m in $MODES; do
  case $m in base) X="";; nom) X="-GEPER=0";; mut_ep) X="-GMUT=2";; mut_drop) X="-GMUT=4";; mut_hc) X="-GHMUT=1";; mut_coll) X="+define+OT_S81PH_MUT_TREP";; mut_inp) X="-GINP1=1";; mut_pd) X="-GPIPE=1 -GPIPE_PD=0";; mut_hl) X="-GHST=1 -GHLMUT=1";; mut_tx) X="-GHTX=3";; mut_su) X="-GSUMUT=4";; mut_sux) X="-GSUXMUT=3";; mut_rw) X="-GSUXMUT=4";; mut_mix) X="-GMXMUT=2";; mut_hcxl) X="-GHXMUT=1 -GHX_FAST=478 -GHX_PROJ_DONE=479";; mut_hcxp) X="-GHXMUT=2";;
    seqc) X="+define+TB_SEQC -GTMAX=110000";; mut_seqc) X="+define+TB_SEQC +define+OT_SSEQC_MUT_DROP_START -GTMAX=110000";; esac
  RUNL=$LAYERS; [ $m = base ] || [ $m = nom ] || [ $m = seqc ] || RUNL=$(echo $LAYERS | awk '{print $1}')
  XGM=""; for g in ${XG:-}; do n=${g%%=*}; case " $X " in *" $n="*) ;; *) XGM="$XGM $g";; esac; done
  ( $ADMIT $VL --binary --timing -j $J -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
      -DOT_S81PH_PLL_MODEL +define+OT_S81PH_COLL_JOB $SPL $SUD -I$S/s81_ctrl --unroll-count 4 -fno-dfg -CFLAGS -O1 \
      --top-module tb_s81_die_layer -GNG=$NG $HX $XGM $X --Mdir $OUT/obj_$m -o sim $FILES > $OUT/build_$m.log 2>&1 \
    && for L in $RUNL; do TX=""; [ -n "${HCXROM:-}" ] && TX="+OT_ROM_DIR=$HCXROM"; [ -n "${VM_TRACE:-}" ] && TX="$TX +VM_TRACE=${VM_TRACE}_${m}_${L}.csv"; /usr/bin/time -v $OUT/obj_$m/sim +DIR=$OUT/stim_$L $TX > $OUT/run_${m}_$L.log 2>&1; done ) &
done
wait
for m in $MODES; do
  RUNL=$LAYERS; [ $m = base ] || [ $m = nom ] || [ $m = seqc ] || RUNL=$(echo $LAYERS | awk '{print $1}')
  for L in $RUNL; do
    v=$(grep -h "TB_S81_DIE_LAYER \(PASS\|FAIL\)" $OUT/run_${m}_$L.log 2>/dev/null | tail -1); s=$(grep -h SUMMARY $OUT/run_${m}_$L.log 2>/dev/null)
    [ -z "$v" ] && v="NO_RESULT (build: $(grep -m1 -i '%Error' $OUT/build_$m.log))"
    exp=FAIL; [ $m = base ] || [ $m = nom ] || [ $m = seqc ] && exp=PASS
    x=$(grep -h "^XFER" $OUT/run_${m}_$L.log 2>/dev/null)
    su=$(grep -h "^SU_REAL" $OUT/run_${m}_$L.log 2>/dev/null)
    echo "$m $L expect $exp: $v | $s | $x | $su"
  done
done | tee $OUT/verdicts.log
if [ $(grep -c "expect PASS: TB_S81_DIE_LAYER PASS" $OUT/verdicts.log) -eq $(grep -c "expect PASS" $OUT/verdicts.log) ] && \
   [ $(grep -c "expect FAIL: TB_S81_DIE_LAYER FAIL" $OUT/verdicts.log) -eq $(grep -c "expect FAIL" $OUT/verdicts.log) ] && \
   grep -q "expect PASS" $OUT/verdicts.log; then
  echo "DIE_LAYER_GATE PASS" | tee -a $OUT/verdicts.log
else echo "DIE_LAYER_GATE FAIL" | tee -a $OUT/verdicts.log; exit 1; fi
