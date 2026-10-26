#!/bin/bash
# Strict re-check (no new sims) of the ec43 NX replays with the fresh native-HOST entry proof (entry_ec43c).
S=/srv/opentallas-scratch2/claude/tok-ds; T=/srv/opentallas-scratch2/claude/wt/codex-tok-ds-1025; N=$S/runs/claude_dsk/nx/L0
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,SVCQ_ENG_FG3
export OT_S81_SELECTED_SOURCE_ROOT=$S/stw-s81d-tok/layers/root31dsk OT_SVC_ALLQ=1 OT_XS_FRAME_SCHEDULE_DIR=$S/fc31/layers_fc31/frame_schedules
export OT_S81_XRT_RUNTIME_PROOF=$S/runs/claude_dsk/entry_ec43c/entry_replay.json
cd /srv/opentallas-scratch2/claude/tok-ds/recheck_root  # copy of codex-tok-ds-1025 (7e0b8a97a+dirty, as gen) with the fdb954df3 tuple-key fix only
for CUT in cut_0S cut_0N; do for M in base mut_in mut_ex; do
  R=$N/$CUT/$M; RUN=$R/run; [ $M = mut_ex ] && RUN=$N/$CUT/base/run
  python3 tools/s81_dv/dv_cut_replay.py check --replay $R --run $RUN --out $R/check_strict2.json > $R/check_strict2.log 2>&1; rc=$?
  echo "$CUT $M rc $rc | $(tail -1 $R/check_strict2.log | cut -c1-300)"
done; done
