#!/usr/bin/env bash
set -eu
G=$1; N=$2; O=$3; SR=${4:-}
B=$(ls -d $G/routes/gate/work/orfs/results/asap7/*/base | head -1); BR=${B#$G/}
P=/OpenROAD-flow-scripts/flow/platforms/asap7
{ echo "read_lef $P/lef/asap7_tech_1x_201209.lef"; echo "read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef"
  [ -n "$SR" ] && echo "read_lef /g/src/physical/asap7_memory_macros_v2/$SR/$SR.lef"
  echo "read_db /g/$BR/4_1_cts.odb"; echo "write_abstract_lef /out/$N.exact.lef"; echo 'puts OT_EXPORT_DONE'; echo exit; } > "$O/export_lef_exact.tcl"
docker run --rm -v "$G:/g:ro" -v "$O:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/export_lef_exact.tcl > "$O/export_lef_exact.log" 2>&1
grep -q OT_EXPORT_DONE "$O/export_lef_exact.log" && ls -la "$O/$N.exact.lef"
