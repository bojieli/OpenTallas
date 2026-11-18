#!/bin/bash
# hold_after_tt.sh (HOLD-AFTER-TT 11-17, COORD from FABLE-FIX-QC-N): the GRT-stage order setup repair FIRST, hold repair AFTER it.
# Measured on 20 routed QC L2 kits: the FF GRT hold repair ends at ~0 and the post-GRT gate a few lines later reads -23..-31 ps, because the
# TT setup repair (tt_setup_repair.tcl, grt mode) runs after the hold repair and spends its margin.  This step (opt-in, config.mk
# OT_HOLD_AFTER_TT = 1, kits with tt_setup_repair.on grt|both) runs after that TT repair: the TT-repaired DB goes through the kit's own FF GRT
# hold step once more ($MF grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=$HM, every kit hook and the OT_HOLD_SETUP_GUARD_PS guard in it), then
# keep-or-restore on the gate's own numbers (postcts_gate.tcl, GRT RC): keep only when FF hold wns improved and TT setup wns did not fall
# below its value before the step by more than OT_HOLD_AFTER_TT_SETUP_TOL_PS (0.5).  Any failure restores 5_1_grt.odb and 4_cts.odb unchanged.
# env: M, MF (make commands of run_kit.sh), HM (hold margin).  Always exits 0; every decision is one OT_HOLD_AFTER_TT line.
R=$(ls -d /work/run/results/asap7/*/base 2>/dev/null | head -1)
G=$R/5_1_grt.odb; C=$R/4_cts.odb
MF=${MF:-$M}
if [ -z "$R" ] || [ ! -s "$G" ] || [ ! -s "$C" ]; then echo "OT_HOLD_AFTER_TT SKIP no 5_1_grt.odb / 4_cts.odb"; exit 0; fi
measure() {   # $1 odb, $2 tag -> writes /work/hat_$2.txt "hold setup"
  for c in TT FF; do
    OT_POSTCTS_BAND_GATE=0 OT_POSTCTS_GRT=1 OT_CORNER=$c ODB="$1" openroad -exit /work/postcts_gate.tcl > /work/hat_gate_${2}_$c.log 2>&1 || return 1
  done
  python3 -I -c 'import json,sys; t=json.load(open("/work/postcts_gate_tt.json")); f=json.load(open("/work/postcts_gate_ff.json")); print(f["hold_wns_est_ps"], t["setup_wns_est_ps"])' > /work/hat_$2.txt
}
if ! measure "$G" before; then echo "OT_HOLD_AFTER_TT SKIP measure failed (hat_gate_before_*.log)"; exit 0; fi
cp -p "$G" /work/5_1_grt_pre_hat.odb; cp -p "$C" /work/4_cts_pre_hat.odb
cp "$G" "$C"; rm -f "$G"
OT_VCLK_CORNER=ff $MF grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=$HM > /work/hold_after_tt_grt.log 2>&1; rc=$?
restore() { cp -p /work/4_cts_pre_hat.odb "$C"; [ "$1" = keep ] || cp -p /work/5_1_grt_pre_hat.odb "$G"; }
if [ $rc != 0 ] || [ ! -s "$G" ]; then restore restore; echo "OT_HOLD_AFTER_TT RESTORE grt step rc $rc (hold_after_tt_grt.log): 5_1_grt.odb unchanged"; exit 0; fi
if ! measure "$G" after; then restore restore; echo "OT_HOLD_AFTER_TT RESTORE measure failed after the step"; exit 0; fi
python3 -I /work/hold_after_tt_keep.py /work/hat_before.txt /work/hat_after.txt "${OT_HOLD_AFTER_TT_SETUP_TOL_PS:-0.5}" | tee -a /work/hold_after_tt.log; k=$?
if [ $k = 0 ]; then restore keep; else restore restore; fi
exit 0
