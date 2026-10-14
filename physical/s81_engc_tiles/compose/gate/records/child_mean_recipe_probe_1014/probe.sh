#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch/claude/engc-clock1014/child-recipe-probe
B=/srv/opentallas-scratch2/claude/closure-loop/el1013-engc-io-rv-22566e03c-tc-cl/routes/el1013_engc_io_rv_22566e03c_tc_cl/work/orfs/results/asap7/opentallas_ot_engc_t_io_asap7_qdm_el1013_engc_io_rv_22566e03c_tc_cl/base
sha256sum "$B/6_final.odb" "$B/6_final.sdc" "$B/6_final.spef" > "$D/inputs.before"
for C in TT FF SS; do
 docker run --rm -e CORNER="$C" -v "$B":/base:ro -v "$D":/recipe:ro openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /recipe/probe.tcl' > "$D/$C.out" 2>&1
 grep -q "CHILD_RECIPE_DONE $C" "$D/$C.out"
done
sha256sum "$B/6_final.odb" "$B/6_final.sdc" "$B/6_final.spef" > "$D/inputs.after"
cmp "$D/inputs.before" "$D/inputs.after"
