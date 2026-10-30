#!/bin/bash
# DIE-QC-49/gen47: plan_qc49 native target (abstracts landing+reset infra, gen47 kit obs) -> native_target.odb
set -euo pipefail
D=/srv/opentallas-scratch2/claude/die-qc-49/g47src
docker run --rm --name dqc49g47-target-$$ --memory=32g --memory-swap=32g --cpus=8 -v $D/target49:/work openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 /work\" EXIT; openroad -threads 8 -exit /work/grt/grt.tcl >/work/build_target.log 2>&1"
