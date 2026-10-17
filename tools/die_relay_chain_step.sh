#!/bin/bash
# ROOT RELAY-SCHEMA 10-16: die-chain step "die run relay stages == compiled static schedule".
#   die_relay_chain_step.sh RUN_STAGES [SCHEDULE_STAGES] [REPORT.json]
# RUN_STAGES       the die run's opentallas.die_relay_stages.v1 export (S81 a_real/relay_stages.json, Qwen KV
#                  case_kv/relay_stages.json, Qwen compute $OT_DIE_RELAY_STAGES_OUT, HBM relay_stages_export.py --out)
# SCHEDULE_STAGES  the table the compiler / timing model scheduled with (consumer --compiled-out); default
#                  $OT_RELAY_SCHEDULE.  None given -> prints RELAY_CHECK SKIPPED and exits 0 (no schedule to compare yet,
#                  the line says whether the die run table exists / is valid); with a schedule, a missing or invalid
#                  RUN_STAGES FAILS (the die did not export its stages).
# exit 0 PASS / SKIPPED, 1 FAIL.  Prints one line: RELAY_CHECK PASS|FAIL|SKIPPED ...
set -u
H=$(dirname "$(readlink -f "$0")")
RUN=${1:?usage: die_relay_chain_step.sh RUN_STAGES [SCHEDULE_STAGES] [REPORT.json]}
SCHED=${2:-${OT_RELAY_SCHEDULE:-}}
REP=${3:-$(dirname "$RUN")/relay_check.json}
if [ -z "$SCHED" ]; then
  if [ ! -s "$RUN" ]; then st="MISSING"; elif python3 "$H/die_relay_stages.py" "$RUN" >/dev/null 2>&1; then st=valid; else st=INVALID; fi
  echo "RELAY_CHECK SKIPPED no compiled schedule given (OT_RELAY_SCHEDULE); die run table $RUN $st"; exit 0
fi
if [ ! -s "$RUN" ]; then echo "RELAY_CHECK FAIL die run exported no relay stage table: $RUN"; exit 1; fi
OUT=$(python3 "$H/die_relay_check.py" "$RUN" "$SCHED" --json "$REP"); rc=$?
echo "${OUT/DIE_RELAY_CHECK/RELAY_CHECK}" | head -1
exit $rc
