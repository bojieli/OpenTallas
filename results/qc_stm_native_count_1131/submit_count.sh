#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-qc-stm-count-1131
[ -s "$B/phys/slw_stm_v3/config.mk" ] || { echo "REFUSE: standard gen phys not complete" >&2; exit 2; }
[ -s "$B/phys/slw_stm_v3/native_bb.py" ] || exit 2
exec /home/ubuntu/.local/bin/ot-run --crit --mem 16 --threads 2 --dir "$B" --stage "$B" -- bash run_synth.sh
