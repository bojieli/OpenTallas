#!/bin/bash
# S81-LEPENH2 10-20: LOCAL_WD (00d74ec20 overlay on the Codex d1846d61e source snapshot) -- the Codex standard-LEP chain
# re-run for host / nh: V5.050 component benches + 7 mutants, std phase bench, native synth + census, native floorplan,
# graph export, row-constrained packing model (preflight_src = codex/s81-lep-physical-preflight-1020 @f37aae333).
set -u; R=$(pwd)
python3 benches_v4.py > benches_v4.log 2>&1 &
python3 phase_v4.py > phase_v4.log 2>&1 &
chain() { v=$1
  bash native_synth5.sh $v && python3 run_census5.py $v > census_$v.log 2>&1; echo "census $v rc $?" >> chain.log
  mkdir -p physical_preflight/$v
  docker run --rm -e OT_LEP_VARIANT=$v -v "$R/src:/work:ro" -v "$R/preflight_src:/src:ro" -v "$R:/run" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /src/results/rtl/s81_standard_lep_physical_preflight_1020/floorplan.tcl' > physical_preflight/$v/floorplan.log 2>&1; echo "floorplan $v rc $?" >> chain.log
  docker run --rm -e OT_LEP_VARIANT=$v -v "$R/preflight_src:/src:ro" -v "$R:/run" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /src/results/rtl/s81_standard_lep_physical_preflight_1020/export_graph.tcl' > physical_preflight/$v/export_graph.log 2>&1; echo "export $v rc $?" >> chain.log
  o=physical_preflight/${v}_rowconstrained; mkdir -p $o
  for n in ot_lep_source_mapped_cells.tsv layout.json macro_terminals.tsv native_graph.tsv tracks.tsv; do ln -sf ../$v/$n $o/$n; done
  python3 preflight_src/results/rtl/s81_standard_lep_physical_preflight_1020/packing_model.py $o --roles physical_preflight/library_roles.json > $o/packing_model.log 2>&1; echo "packing $v rc $?" >> chain.log
}
chain host & chain nh &
wait
echo CHAIN_DONE >> chain.log
