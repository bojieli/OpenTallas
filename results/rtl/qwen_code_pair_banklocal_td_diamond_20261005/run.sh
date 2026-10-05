#!/bin/bash
set -uo pipefail
job=/srv/opentallas-scratch/codex/pauli-code-banklocal-td-diamond-r2
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export OMP_NUM_THREADS=16 OT_ORFS_NUM_CORES=16 OT_FLOW_TIMEOUT_SECONDS=unlimited
/srv/opentallas-scratch/admit.sh 64 -- docker run --rm --name pauli-code-banklocal-td-diamond-r2 \
  -v "$job/source:/src:ro" -v "$job/orfs:/work" \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh
for stage in do-4_1_cts do-4_cts do-5_1_grt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do
  echo "PAULI_STAGE $stage"
  make -f Makefile -f /work/side_effects.mk -j16 DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 "$stage" || exit $?
done
' > "$job/orfs/route.log" 2>&1
rc=$?
echo "$rc" > "$job/orfs/route.exit"
echo "$rc" > "$job/supervisor.exit"
exit "$rc"
