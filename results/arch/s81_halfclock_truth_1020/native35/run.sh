#!/bin/bash
set -uo pipefail
D=$(pwd)
for v in buf inv chain; do
 docker run --rm --user "$(id -u):$(id -g)" --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v "$D:/coupon" -e "COUPON_VARIANT=$v" openroad/orfs:asap7lock -threads 1 -no_init -exit /coupon/build.tcl > "$D/$v/build.log" 2>&1
 rc=$?; printf '%s BUILD_RC %s\n' "$v" "$rc"; [ "$rc" -eq 0 ] || exit "$rc"
done
