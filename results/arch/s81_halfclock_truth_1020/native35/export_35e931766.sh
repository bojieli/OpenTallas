#!/bin/bash
set -uo pipefail
D=$(pwd)
mkdir -p source35e931766
tar -xf source35e931766.tar -C source35e931766
for v in buf inv chain; do
 python3 source35e931766/tools/tt_views/view_export.py --orfs-dir "$D/$v/orfs" --name fc_coupon --out "$D/$v/export35e931766" --no-verdict --forwarded-clock ck:ck_o --corners ss,ff,tt --image openroad/orfs:asap7lock > "$D/$v/export35e931766.log" 2>&1
 rc=$?; printf '%s EXPORT_RC %s\n' "$v" "$rc"
done
