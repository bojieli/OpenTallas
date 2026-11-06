#!/usr/bin/env bash
set -euo pipefail
ROOT=/srv/opentallas-scratch2/claude/codex-q3-clockport-1106
KIT=$ROOT/kit_A
RS=$KIT/run/results/asap7/hbc_ot_hfd_coll_q3_edge_link/base
test ! -e "$RS/6_final.pre_clockrect.odb"
docker run --rm --name codex-q3-clockrect-$$ --cpus=1 --memory=2g --memory-swap=2g \
 -e Q3_SOURCE_ODB=/work/run/results/asap7/hbc_ot_hfd_coll_q3_edge_link/base/6_final.odb \
 -e Q3_OUTPUT_ODB=/work/clockrect.odb -e Q3_CLK_FREEZE_TCL=/clk_freeze.tcl \
 -v "$KIT:/work" -v "$ROOT/tools_bg/tools/die_plan/clk_freeze.tcl:/clk_freeze.tcl:ro" -v "$ROOT/q3_clockport_rectangle.tcl:/construct.tcl:ro" openroad/orfs:asap7lock \
 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /construct.tcl' > "$ROOT/construction.log" 2>&1
grep -q 'Q3_CLOCK_RECTANGLE PASS' "$ROOT/construction.log"
mv "$RS/6_final.odb" "$RS/6_final.pre_clockrect.odb"
mv "$KIT/clockrect.odb" "$RS/6_final.odb"
cat "$ROOT/construction.log"
