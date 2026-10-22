#!/bin/bash
set -uo pipefail
D=$(pwd)
mkdir -p source28ad73b
tar -xf source28ad73b.tar -C source28ad73b
for v in buf inv chain; do
 python3 source28ad73b/tools/tt_views/view_export.py --orfs-dir "$D/$v/orfs" --name fc_coupon --out "$D/$v/export28ad73b" --no-verdict --forwarded-clock ck:ck_o --corners ss,ff,tt --image openroad/orfs:asap7lock > "$D/$v/export28ad73b.log" 2>&1
 rc=$?; printf '%s EXPORT_RC %s\n' "$v" "$rc"
done
