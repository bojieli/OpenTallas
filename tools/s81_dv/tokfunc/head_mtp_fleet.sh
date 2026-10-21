#!/bin/bash
# head_mtp_fleet.sh PREP FIX OUT  (cwd = staged source root on a fleet host; run through ot-run by run_head_mtp.sh)
# TOK-FUNC-S81/HEADMTP: every leg of the LM head (TOK.DS.LAYER.5) and MTP draft (TOK.DS.LAYER.6) on the existing benches,
# Verilator 5.050, in parallel.  One directory per leg under OUT; the composer (head_mtp_report.py) reads the logs.
#   xfin    tb_s81dv_xfin16: ot_hbm_norm_grp G64 + 16 x ot_s81dv_xfin on the snake ring, HEAD gold (all 80 y vectors)
#           + mutant OT_S81DV_MUT_LEAF (must FAIL)
#   beat    tb_s81sl_beat (vp + vn + vq slice leaves) for ALL 80 beats on the HEAD gold (block a = head hc_pre + norm + XB)
#           + mutant OT_S81SL_VP_MUT_NORMIMM at beat 37 (must FAIL)
#   egress  tools/s81_slice/rstopt_xo_bench.sh none / xooff (current ring-stop master ot_s81sl_rstopt_xo) + latency copy
#   bundle  tools/s81_ftok/live_head_return.py (ot_dsrom_head_bundle, 10 x ot_rom_4096x274_m8, real rank-0 head.weight rows
#           21888..22015, argmax, token return; 3 PASS cases + 3 mutants)
#   dhead   toksim_mtpd_draft_head.py on the bundle build: the 5 MTP draft-head inputs (draft.head{i}.norm.scale)
#   tp4     tools/s81_dv/head_tp4_interim.py: 4-rank fused head argmax + TP4 merge over 129,280 fixture logits (head) and
#           the 5 fused draft heads (Markov add), mutants mut_lg / fh0
#   wave    tools/mtp_wave_bench.py: dsfd_mtp_seq_rtt + MTP lanes + Markov row + commit loop (wave + 2 mutants + smoke)
set -u; PREP=$(readlink -f $1); FIX=$(readlink -f $2); OUT=$3; mkdir -p $OUT; OUT=$(readlink -f $OUT)
VB=$HOME/.local/opentallas-tools/verilator-5.050/bin; export PATH=$VB:$PATH; V=$VB/verilator
$V --version > $OUT/verilator_version.log
P=${P:-40}
NSRC="$(cat physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ')"

leg_xfin() {
  local O=$OUT/xfin; mkdir -p $O
  for M in base mutleaf; do
    D=""; [ $M = mutleaf ] && D="+define+OT_S81DV_MUT_LEAF"
    mkdir -p $O/$M/run
    $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D --top-module tb_s81dv_xfin16 -Mdir $O/$M/obj \
      $NSRC physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
      rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/test/tb_s81dv_xfin16.sv --build-jobs 4 \
      --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/$M/build.log 2>&1 \
      || { echo "BUILD_FAILED" > $O/$M/run.log; continue; }
    cp $PREP/xfin/*.mem $O/$M/run/ && (cd $O/$M/run && ../obj/Vtb_s81dv_xfin16 > ../run.log 2>&1)
  done
}

beat_one() {  # $1 = beat, $2 = mode (base | mutnormimm)
  local B=$1 M=$2 O=$OUT/beat/$2_b$(printf %02d $1); mkdir -p $O/run
  local D=""; [ $M = mutnormimm ] && D="+define+OT_S81SL_VP_MUT_NORMIMM"
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D -GBEAT=$B -GNORMR=1 -GVQ_XMEM=2 --top-module tb_s81sl_beat \
    -Mdir $O/obj $(sort -u physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') rtl/hdc/v41x/ot_dsrom_su_add6.sv \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v rtl/lib/ot_rst_relay.sv \
    rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv \
    rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv \
    rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv --build-jobs 1 -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build.log 2>&1 || { echo "BUILD_FAILED" > $O/run.log; return; }
  cp $PREP/beat/b$(printf %02d $B)/*.mem $O/run/ && (cd $O/run && ../obj/Vtb_s81sl_beat > ../run.log 2>&1)
  rm -rf $O/obj
}
export -f beat_one; export OUT PREP V

leg_beat() {
  mkdir -p $OUT/beat
  ( for b in $(seq 0 79); do echo "$b base"; done; echo "37 mutnormimm" ) | xargs -P $P -n 2 bash -c 'beat_one $0 $1'
}

leg_egress() {
  local O=$OUT/egress; mkdir -p $O
  J=4 bash tools/s81_slice/rstopt_xo_bench.sh $O none > $O/bench_none.log 2>&1; echo "rc $?" >> $O/bench_none.log
  J=4 bash tools/s81_slice/rstopt_xo_bench.sh $O xooff > $O/bench_xooff.log 2>&1; echo "rc $?" >> $O/bench_xooff.log
  python3 tools/s81_dv/tokfunc/rstop_lat_tb.py rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv $O/tb_rstop_lat.sv > $O/lat_patch.log 2>&1
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_s81sl_rstop_xo -Mdir $O/obj_lat \
    rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv $O/tb_rstop_lat.sv --build-jobs 4 > $O/build_lat.log 2>&1 \
    && $O/obj_lat/Vtb_s81sl_rstop_xo > $O/run_lat.log 2>&1
}

leg_bundle() {
  python3 tools/s81_ftok/live_head_return.py --fixture $FIX/HEAD --work $OUT/bundle > $OUT/bundle.log 2>&1; echo "rc $?" >> $OUT/bundle.log
  python3 tools/s81_dv/layer_prog/qf_producer/toksim_mtpd_draft_head.py --mtp $FIX/MTP --base $OUT/bundle --work $OUT/dhead \
    > $OUT/dhead.log 2>&1; echo "rc $?" >> $OUT/dhead.log
}

leg_tp4() {
  python3 tools/s81_dv/head_tp4_interim.py --fix-head $FIX/HEAD --fix-mtp $FIX/MTP --scratch $OUT/tp4 --out $OUT/tp4/record.json \
    > $OUT/tp4.log 2>&1; echo "rc $?" >> $OUT/tp4.log
}

leg_wave() {
  python3 tools/mtp_wave_bench.py run --out $OUT/wave --case wave --case mut_sseq_earlydone --case mut_hep_stale -j 4 --sim verilator \
    > $OUT/wave.log 2>&1; echo "rc $?" >> $OUT/wave.log
  rm -rf $OUT/wave/*/obj
}

leg_xfin & leg_beat & leg_egress & leg_bundle & leg_tp4 & leg_wave &
wait
echo "HEAD_MTP_FLEET DONE"
