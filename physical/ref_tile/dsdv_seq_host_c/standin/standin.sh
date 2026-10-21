#!/usr/bin/env bash
# stand-in export (copied from PL-GUNIT dsdv_gunit_lp/standin, S81-GUSEQ 10-18) (diagnostic, NOT a view): abstract LEF + TT/FF/SS timing models from a leaf's --cts gate odb.
# usage: standin.sh GATE_DIR DESIGN OUT_DIR [sram]
set -eu
G=$1; N=$2; O=$3; SR=${4:-}
mkdir -p "$O"
B=$(ls -d $G/routes/gate/work/orfs/results/asap7/*/base | head -1); BR=${B#$G/}
P=/OpenROAD-flow-scripts/flow/platforms/asap7
for C in tt ff ss; do
  CU=$(echo $C | tr a-z A-Z)
  {
  echo "read_lef $P/lef/asap7_tech_1x_201209.lef"; echo "read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef"
  [ -n "$SR" ] && echo "read_lef /g/src/physical/asap7_memory_macros_v2/$SR/$SR.lef"
  for f in AO_RVT_${CU}_nldm_211120.lib.gz INVBUF_RVT_${CU}_nldm_220122.lib.gz OA_RVT_${CU}_nldm_211120.lib.gz SEQ_RVT_${CU}_nldm_220123.lib SIMPLE_RVT_${CU}_nldm_211120.lib.gz; do echo "read_liberty $P/lib/NLDM/asap7sc7p5t_$f"; done
  [ -n "$SR" ] && echo "read_liberty /g/src/physical/asap7_memory_macros_v2/$SR/${SR}_$C.lib"
  echo "read_db /g/$BR/4_1_cts.odb"; echo "read_sdc /g/$BR/4_cts.sdc"
  echo "source $P/setRC.tcl"; echo "estimate_parasitics -placement"; echo "set_propagated_clock [all_clocks]"
  echo "puts \"OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]\""
  echo "write_timing_model -library_name ${N}_$C /out/${N}_$C.lib"
  [ $C = tt ] && echo "write_abstract_lef /out/$N.lef"
  echo 'puts OT_EXPORT_DONE'; echo exit
  } > "$O/export_$C.tcl"
  docker run --rm -v "$G:/g:ro" -v "$O:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/export_$C.tcl > "$O/export_$C.log" 2>&1 || { echo "EXPORT FAIL $N $C"; tail -5 "$O/export_$C.log"; exit 1; }
  grep -q OT_EXPORT_DONE "$O/export_$C.log" || { echo "EXPORT INCOMPLETE $N $C"; tail -5 "$O/export_$C.log"; exit 1; }
  grep OT_WS "$O/export_$C.log"
done
cp "$G/ck.json" "$O/insertion.json"
echo "diagnostic stand-in from the --cts gate odb $G (placement-estimated parasitics, NOT routed, NOT closed); never bind" > "$O/STANDIN_NOT_A_VIEW"
echo "STANDIN DONE $N"
