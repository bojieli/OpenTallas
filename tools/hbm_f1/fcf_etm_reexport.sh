#!/usr/bin/env bash
# H-NETLIST 1815 (DIE-CLOCK request): F1 FORK relay ETM (every clk_out<k>_fwd generated clock removed) with a PLAIN clk_in -> clk_out combinational arc.
# (A) the closure-loop export with the clk_out_fwd generated clock removed (register arcs vs clk_in unchanged);
# (B) the same session with every clock deleted: clk_in -> u_fcb_ck -> clk_out is then a combinational path and the ETM
#     carries its measured delay tables; fcf_merge.py replaces the clk_out pin timing of (A) by (B)'s clk_in arcs.
#   reexport.sh RUN_DIR CELL EXPORT_TCL_DIR OUT
set -euo pipefail
RUN=$1; CELL=$2; TD=$3; OUT=$4; mkdir -p "$OUT"
ORFS=$(dirname $(find "$RUN/routes" -path '*work/orfs/results/*/base/6_final.odb' | head -1)); ORFS=${ORFS%/results/*}
MEAS=$(ls -d $RUN/cl/routed_ioref.a*_meas | sort -V | tail -1)
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
for c in tt ff ss; do
  sed -e "s#^write_timing_model#foreach g [get_clocks -quiet clk_out*_fwd] { delete_generated_clock \$g }; puts OT_FC_GENCLK_REMOVED\nwrite_timing_model#" "$TD/export_$c.tcl" > "$OUT/export_${c}_a.tcl"
  sed -e "s#^write_timing_model.*#foreach g [get_clocks -quiet clk_out*_fwd] { delete_generated_clock \$g }; foreach k [all_clocks] { delete_clock \$k }; puts OT_FC_ALLCLK_REMOVED\nwrite_timing_model -library_name ${CELL}_${c}_comb /out/${CELL}_${c}_comb.lib#" "$TD/export_$c.tcl" > "$OUT/export_${c}_b.tcl"
  for v in a b; do
    docker run --rm -v "$ORFS:/work:ro" -v "$MEAS:/meas:ro" -v "$OUT:/out" openroad/orfs:asap7lock bash -lc \
      "cd /OpenROAD-flow-scripts/flow && $OR -no_init -exit /out/export_${c}_$v.tcl" > "$OUT/export_${c}_$v.log" 2>&1
    grep -q OT_EXPORT_DONE "$OUT/export_${c}_$v.log" || { echo "EXPORT_FAIL $c $v"; tail -15 "$OUT/export_${c}_$v.log"; exit 2; }
  done
  mkdir -p "$OUT/final"; python3 "$(dirname "$0")/fcf_merge.py" "$OUT/${CELL}_${c}.lib" "$OUT/${CELL}_${c}_comb.lib" "$OUT/final/${CELL}_${c}.lib" || exit 2
done
echo REEXPORT_DONE $CELL
