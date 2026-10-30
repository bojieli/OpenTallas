#!/bin/bash
# DIE-QC-50/gen47b: export -> main provider_clock_loads (graph extension check) -> main plan_provider_clock_access (lower M1..M7 access)
set -uo pipefail
Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47b; S=$Q/wt/die-qc-50-gen47b/results/qc_die50_1030/gen47b/scripts; T=$R/tools_main/tools/clk
mkdir -p $R/access
docker run --rm --name dqc50g47b-exp-$$ --memory=48g --memory-swap=48g --cpus=2 -v $Q:$Q openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit $S/export_access47b.py $R/import/provider.odb $R/access > $R/access/export.log 2>&1; r=\$?; chown -R 1000:1000 $R/access; exit \$r"
echo "EXPORT rc=$? $(date)"; tail -1 $R/access/export.log
docker run --rm --name dqc50g47b-acc-$$ --memory=96g --memory-swap=96g --cpus=2 -v $Q:$Q -w $T python:3.12 bash -c "pip -q install shapely numpy >/dev/null 2>&1; python $T/provider_clock_loads.py --graph $R/access/graph_raw.json --loads $R/import/clock_loads.json --bindings $R/bound/bindings.json --out $R/access/leaf > $R/access/leaf.log 2>&1; echo LEAF_rc=\$?; python $T/plan_provider_clock_access.py --geometry $R/access/geometry.json --loads $R/import/clock_loads.json --graph $R/access/graph_actual.json --via-facts $R/access/via_facts.json --out $R/access/plan > $R/access/plan.log 2>&1; echo ACCESS_rc=\$?; chown -R 1000:1000 $R/access"
echo "DONE $(date)"; tail -2 $R/access/leaf.log; tail -2 $R/access/plan.log
