#!/bin/bash
# etm_tt.sh RESULTS_DIR DESIGN [extra .lib ...]: TT ETM (<DESIGN>_TT.lib) of a routed ORFS block, same steps as
# ORFS generate_abstract.tcl but with the TT libraries (ORFS asap7 default CORNER=BC builds an FF model).
set -euo pipefail
R=$1; N=$2; shift 2
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
T=$R/etm_tt.tcl
{
  for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120; do
    echo "read_liberty $L/asap7sc7p5t_$f.lib.gz"; done
  echo "read_liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
  echo "read_liberty $L/asap7sc7p5t_DFFHQNV2X_RVT_TT_nldm_FAKE.lib"
  echo "read_liberty $L/asap7sc7p5t_DFFHQNH2V2X_RVT_TT_nldm_FAKE.lib"
  for x in "$@"; do echo "read_liberty $x"; done
  echo "read_db $R/6_final.odb"
  echo "read_sdc $R/6_final.sdc"
  echo "read_spef $R/6_final.spef"
  echo "set_propagated_clock [all_clocks]"
  echo "set_clock_latency -source 0 [all_clocks]"
  echo "write_timing_model $R/${N}_TT.lib"
} > "$T"
docker run --rm --memory 8g --user "$(id -u):$(id -g)" -v "$R:$R" openroad/orfs:asap7lock \
  bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -no_splash -exit $T" > "$R/etm_tt.log" 2>&1
grep -c "^Error" "$R/etm_tt.log" || true
ls -la "$R/${N}_TT.lib"
