#!/bin/bash
# run_die_fld.sh <src root> <out dir> [modes]: tb_s81_die_fld (Verilator 5; s81-ctl-1011).  Modes: base (PASS),
# mut2 wrong done tag / mut3 early start / mut4 dropped done (each must FAIL).  Verdict line DIE_FLD_GATE PASS|FAIL.
# Fleet hosts only: run through ot-heavy (each build ~20-40 GB peak).
set -u
SRC=$1; OUT=$2; MODES=${3:-"base mut2 mut3 mut4"}; mkdir -p $OUT
S=$SRC/rtl/dsrom_sys
python3 $SRC/tools/s81_ctrl/die_bench_stim.py $OUT/stim --stage ${STAGE:-S001} > $OUT/stim.log 2>&1 || { echo "DIE_FLD_GATE FAIL stim"; exit 1; }
FILES="$SRC/rtl/lib/ot_reset_sync.sv $SRC/rtl/lib/ot_async_fifo.sv $SRC/rtl/lib/ot_skid_buffer.sv $SRC/rtl/common/ot_ratio_cdc_fifo.sv
 $S/s81_ctrl/ot_s81_engine_adapter.sv $S/s81_ctrl/ot_s81_slab_ep.sv
 $S/s81_ctrl/ot_s81_stage_seq.sv $S/s81_ctrl/ot_s81_pkg_ctrl.sv $S/s81_ctrl/ot_s81_stage_guard.sv $S/s81_ctrl/ot_s81_hop_tx.sv
 $S/s81_ctrl/ot_s81_stop.sv $S/s81_ctrl/ot_s81_host_cq.sv $S/s81_ctrl/ot_s81_ctrl.sv $S/ot_dsrom_stall_export.sv
 $S/engram/ot_dsrom_engram_lead_producer.sv $SRC/physical/s81_ctrl/rtl/dsfd_sp_ctrl_core.sv $SRC/physical/s81_ctrl/rtl/dsfd_sp_ctrl_e.sv
 $SRC/rtl/v41rom/ot_v41_ret.sv $SRC/rtl/proto/ot_fp32_add_rne_pipe.sv $SRC/rtl/gpu/ot_fp32_add_rne_deep.sv $SRC/rtl/hdc/ot_hdc_prefix.sv
 $SRC/rtl/hdc/ot_hdc_delay.sv $S/rd64_capture/ot_dsrom_rd64_vm_capture.sv $S/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv
 $S/s81_ph/ot_s81ph_ret_root_p.sv $S/s81_ph/ot_s81ph_root_blk.sv $S/s81_ph/ot_s81ph_root_tile.sv $S/s81_ph/ot_s81ph_gather.sv
 $S/s81_ph/ot_s81ph_cap_p.sv $S/s81_ph/ot_s81ph_capture.sv $S/s81_ph/ot_s81ph_cap_tile.sv
 $S/s81_ph/dsfd_sp_gather.sv $S/s81_ph/dsfd_sp_capture.sv $S/s81_ph/ctrl_c/dsfd_sp_gather_c.sv $S/s81_ph/ctrl_c/dsfd_sp_capture_c.sv
 $S/s81_ctrl/test/tb_s81_die_fld.sv"
sha256sum $FILES > $OUT/sources.sha256
for m in $MODES; do
  case $m in base) P="-GMUT=0";; mut2) P="-GMUT=2";; mut3) P="-GMUT=3";; mut4) P="-GMUT=4";; esac
  ( verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -I$S/s81_ctrl \
      --top-module tb_s81_die_fld $P --Mdir $OUT/obj_$m -o sim $FILES > $OUT/build_$m.log 2>&1 \
    && $OUT/obj_$m/sim +PROG=$OUT/stim/prog.txt +STIM=$OUT/stim/stim.txt > $OUT/run_$m.log 2>&1 ) &
done
wait
rc=0
for m in $MODES; do
  v=$(grep -h "TB_S81_DIE_FLD \(PASS\|FAIL\)" $OUT/run_$m.log 2>/dev/null | tail -1); s=$(grep -h SUMMARY $OUT/run_$m.log 2>/dev/null)
  [ -z "$v" ] && v="NO_RESULT (build: $(grep -m1 -i error $OUT/build_$m.log))"
  exp=FAIL; [ $m = base ] && exp=PASS
  echo "$m expect $exp: $v | $s"
  echo "$v" | grep -q "TB_S81_DIE_FLD $exp" || rc=1
done | tee $OUT/verdicts.log
if grep -q "expect PASS: TB_S81_DIE_FLD PASS" $OUT/verdicts.log && [ $(grep -c "expect FAIL: TB_S81_DIE_FLD FAIL" $OUT/verdicts.log) -eq $(grep -c "expect FAIL" $OUT/verdicts.log) ]; then
  echo "DIE_FLD_GATE PASS" | tee -a $OUT/verdicts.log
else echo "DIE_FLD_GATE FAIL" | tee -a $OUT/verdicts.log; exit 1; fi
