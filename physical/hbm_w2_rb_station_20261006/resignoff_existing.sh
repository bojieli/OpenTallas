#!/bin/bash
# Re-sign-off an EXISTING routed W2 rb station (no re-route): copy <src route dir> to <dst route dir> without its
# sign-off evidence (signoff.json / signoff_*.log / signoff.sdc / 6_signoff.sdc), so signoff.py runs fresh with the
# current make_sdc.py (POLICY-HOLD 2026-10-11).  The source run is never modified.
set -euo pipefail
src=$1; dst=$2
test -s "$src/terminal.json" && grep -q '"exit_code": 0' "$src/terminal.json"
ls "$src"/work/orfs/results/asap7/*/base/6_final.odb >/dev/null
test ! -e "$dst" || { echo "refusing: $dst exists"; exit 2; }
mkdir -p "$(dirname "$dst")"
rsync -a --exclude '/signoff.json' --exclude '/signoff_*.log' --exclude '/work/orfs/signoff.sdc' \
      --exclude '6_signoff.sdc' --exclude '*.pre_eco' "$src/" "$dst/"
echo "{\"resignoff_of\": \"$src\"}" > "$dst/resignoff_of.json"
echo RESIGNOFF_COPY_OK
