#!/bin/bash
set -euo pipefail
k="$1"; goal="$2"; mem="$3"; threads="$4"
test "$goal" = grt || { echo 'GRT-only runner refuses other goals' >&2; exit 2; }
exec bash "$k/run_kit.sh" "$k" grt "$mem" "$threads"
