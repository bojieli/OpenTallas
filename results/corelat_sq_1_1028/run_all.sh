#!/bin/bash
# CORELAT-SQ-1: regenerate S81 / QC / KV core-tap tables + per-type deltas (run from the repo root on intel2).
set -euo pipefail
R=results/corelat_sq_1_1028; I=${CORELAT_IN:-/srv/opentallas-scratch2/claude/corelat-sq-1/in}
S81=${S81_PLAN:-/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json}
python3 $R/corelat_table.py $S81 . $R/s81_core_taps --signed $I/s81_signed.json --extra $R/s81_extra.json
python3 $R/corelat_delta.py $R/s81_core_taps.json $S81 . $R/s81_tap_delta.json
python3 $R/corelat_table.py $I/qc_grpP_event.json . $R/qc_core_taps --signed $I/qc_signed.json --bind-signed --extra $R/qc_extra.json
python3 $R/corelat_delta.py $R/qc_core_taps.json $I/qc_grpP_event.json . $R/qc_tap_delta.json
python3 $R/corelat_table.py $I/hm_r26q9b.json . $R/kv_core_taps --extra $R/kv_extra.json
python3 $R/corelat_delta.py $R/kv_core_taps.json $I/hm_r26q9b.json . $R/kv_tap_delta.json
