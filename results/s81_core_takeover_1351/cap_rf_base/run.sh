#!/bin/bash
set -euo pipefail
B=$(cd "$(dirname "$0")" && pwd)
for case in base6 short5 wrongbit6;do
 docker run --rm --user "$(id -u):$(id -g)" -v "$B:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -s /work/$case.ys > "$B/$case.log" 2>&1
done
grep -q 'SUCCESS' "$B/base6.log"
grep -q 'FAIL' "$B/short5.log"
grep -q 'FAIL' "$B/wrongbit6.log"
echo CAP_RF_UNIVERSAL_BASE6_PROVED_SHORT5_AND_WRONGBIT_REFUTED
