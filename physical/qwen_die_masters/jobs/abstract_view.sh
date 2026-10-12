#!/bin/bash
# el1011-q-tile 2026-10-11: hardened-leaf views of a routed Qwen die master, for a parent route's --macro-view:
#   <route>/views/<TOP>.lef (write_abstract_lef) and <TOP>_{tt,ss,ff}.lib (write_timing_model on the
#   routed odb + spef, propagated clock at the sign-off period).  Usage: abstract_view.sh ROUTE_DIR TOP
set -euo pipefail
R=$(readlink -f "$1"); TOP=$2; O=$R/work/orfs
mkdir -p $R/views
for c in tt ss ff; do
  C=${c^^}
  {
    echo "set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7"
    echo "read_lef \$PLAT/lef/asap7_tech_1x_201209.lef"; echo "read_lef \$PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef"
    for l in AO_RVT_${C}_nldm_211120.lib.gz INVBUF_RVT_${C}_nldm_220122.lib.gz OA_RVT_${C}_nldm_211120.lib.gz SEQ_RVT_${C}_nldm_220123.lib SIMPLE_RVT_${C}_nldm_211120.lib.gz; do
      echo "read_liberty \$PLAT/lib/NLDM/asap7sc7p5t_$l"
      for v in LVT SLVT; do echo "catch {read_liberty \$PLAT/lib/NLDM/asap7sc7p5t_${l/_RVT_/_${v}_}}"; done
    done
    echo "set base [lindex [glob /work/results/asap7/*/base] 0]"
    echo "read_db \$base/6_final.odb"; echo "read_spef \$base/6_final.spef"
    echo "create_clock -name core_clk -period 833.333 [get_ports clk]"; echo "set_propagated_clock [all_clocks]"
    echo "write_timing_model -library_name ${TOP}_$c /work/views_${TOP}_$c.lib"
    [ $c = tt ] && echo "write_abstract_lef /work/views_${TOP}.lef"
    echo "exit"
  } > $O/abstract_$c.tcl
  docker run --rm -v $O:/work openroad/orfs:asap7lock bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/abstract_$c.tcl" > $R/views/abstract_$c.log 2>&1
  cp $O/views_${TOP}_$c.lib $R/views/${TOP}_$c.lib
done
cp $O/views_${TOP}.lef $R/views/${TOP}.lef
grep -q "MACRO ${TOP}" $R/views/${TOP}.lef && grep -q "cell *(${TOP})\|cell (\"${TOP}\")" $R/views/${TOP}_tt.lib
echo "views_rc=0 $(ls $R/views | tr '\n' ' ')"
