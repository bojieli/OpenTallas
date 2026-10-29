#!/bin/bash
set -euo pipefail
m="$1"
r=/srv/opentallas-scratch2/claude/codex-s81-cores-1028
k="$r/kits/${m}_current1028"
exec "$HOME/.local/bin/ot-run" --hosts localhost --mem 32 --threads 8 --dir "$r" -- bash "$k/run_kit.sh" "$k" place 32 8
