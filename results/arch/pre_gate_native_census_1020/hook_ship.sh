#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/codex-native-census-1020
for n in 32 33; do
 mkdir -p "$R/coupon$n/work"
 set +e
 docker run --rm -e COUPON_N=$n -v "$R:/audit" -v "$R/completecand:/src:ro" -v "$R/coupon$n/work:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/hook_coupon.tcl > "$R/hookship$n.log" 2>&1
 rc=$?;set -e;echo "$rc" > "$R/hookship$n.rc"
done
python3 - <<'END'
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/codex-native-census-1020')
assert (r/'hookship32.rc').read_text().strip()=='0'
assert 'PLACEMENT_STARTED' in (r/'hookship32.log').read_text()
assert (r/'hookship33.rc').read_text().strip()!='0'
assert 'PLACEMENT_STARTED' not in (r/'hookship33.log').read_text()
print('HOOK_ADMISSION_BEFORE_PLACEMENT_PASS_32_REFUSE_33')
END
