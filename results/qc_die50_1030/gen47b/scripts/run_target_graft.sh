#!/bin/bash
# DIE-QC-50/gen47b: (1) build the island-holed plan_qc49 native target (target49 grt.tcl, write_db only)
# (2) main tools/clk/native_clock_source.py graft of the gen47 kit ctree.v/tree.json (same as DIE-QC-49 build2)
set -euo pipefail
R=/srv/opentallas-scratch2/claude/die-qc-50/gen47b
K=/srv/opentallas-scratch2/claude/die-qc-49/gen47k/kit/clock
echo "START $(date)"
docker run --rm --name dqc50g47b-target-$$ --memory=32g --memory-swap=32g --cpus=8 -v $R/target:/work openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 /work\" EXIT; openroad -threads 8 -exit /work/grt/grt.tcl >/work/build_target.log 2>&1"
echo "TARGET $(date)"; tail -1 $R/target/build_target.log
mkdir -p $R/build
docker run --rm --name dqc50g47b-graft-$$ --memory=32g --memory-swap=32g --cpus=4 -v /srv/opentallas-scratch2/claude:/srv/opentallas-scratch2/claude openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $R/build\" EXIT; openroad -python -exit $R/tools_main/tools/clk/native_clock_source.py --target $R/target/native_target.odb --netlist $K/ctree.v --tree $K/tree.json --out $R/build > $R/build/graft.log 2>&1"
echo "GRAFT $(date)"; tail -2 $R/build/graft.log
