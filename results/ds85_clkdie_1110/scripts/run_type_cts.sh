#!/bin/bash
# DS85 CLKDIE-S81: type_clk_cts.tcl on one type dir D holding stage.odb (a 4_cts / 5_1_grt odb copy), TT and FF.
set -uo pipefail
D=$(readlink -f "$1"); S=$(readlink -f "$(dirname "$0")")
for C in TT FF; do
  L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
  LIBS="$L/asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz $L/asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz $L/asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz $L/asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib $L/asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz"
  for x in "$D"/extra_libs/${C}/*; do [ -e "$x" ] && LIBS="$LIBS /d/extra_libs/${C}/$(basename "$x")"; done
  docker run --rm --name "ds85-clk-cts-$(basename "$D")-$C" --memory=32g --cpus=2 -v "$D:/d" -v "$S:/s:ro" \
    -e CORNER=$C -e ODB=/d/stage.odb -e LIBS="$LIBS" -e OUT=/d/arr_$C.txt -e TAPSLEW=40 openroad/orfs:asap7lock \
    /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/type_clk_cts.tcl > "$D/sta_$C.log" 2>&1 || echo "FAIL $C" >> "$D/sta_$C.log"
done
