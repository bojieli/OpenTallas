#!/bin/bash
# DIE-QC-50/gen47A: export (export_access47A.py) -> leaf A-pin loads (DIE-QC-39 leaf_inventory.py)
# -> main provider_clock_loads (graph extension) -> main plan_provider_clock_access (lower M1..M7 access)
# usage: run_access_leaf.sh [SRC_ODB] [OUTDIR]   (defaults: import/provider.odb, access)
set -uo pipefail
Q=/srv/opentallas-scratch2/claude; A=$Q/die-qc-50/gen47A; W=$Q/wt/die-qc-50-gen47A
M=$W/results/qc_die50_1030/gen47A/scripts; T=$W/tools/clk; B=$Q/die-qc-50/gen47b
SRC=${1:-$A/import/provider.odb}; O=${2:-$A/access}
mkdir -p $O
docker run --rm --name dqc50g47A-exp-$$ --memory=48g --memory-swap=48g --cpus=2 -v $Q:$Q openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit $M/export_access47A.py $SRC $O > $O/export.log 2>&1; r=\$?; chown -R 1000:1000 $O; exit \$r"
echo "EXPORT rc=$? $(date)"; tail -1 $O/export.log
docker run --rm --name dqc50g47A-acc-$$ --memory=96g --memory-swap=96g --cpus=2 -v $Q:$Q -w $T python:3.12 bash -c "pip -q install shapely numpy >/dev/null 2>&1; python $M/leaf_inventory.py $O/geometry.json $A/leaf/leaf_clusters.json $A/leaf/provider_cells_leaf.json $O/leaf_loads.json > $O/leaf_inv.log 2>&1; echo LEAFINV_rc=\$?; python $T/provider_clock_loads.py --graph $O/graph_raw.json --loads $O/leaf_loads.json --bindings $B/bound/bindings.json --out $O/leaf > $O/leaf.log 2>&1; echo LEAF_rc=\$?; python $T/plan_provider_clock_access.py --geometry $O/geometry.json --loads $O/leaf_loads.json --graph $O/graph_actual.json --via-facts $O/via_facts.json --out $O/plan > $O/plan.log 2>&1; echo ACCESS_rc=\$?; chown -R 1000:1000 $O"
echo "DONE $(date)"; cat $O/leaf_inv.log; tail -2 $O/leaf.log; tail -3 $O/plan.log
