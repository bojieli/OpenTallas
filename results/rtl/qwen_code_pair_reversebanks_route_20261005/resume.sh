#!/bin/bash
set -uo pipefail
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export OMP_NUM_THREADS=16 OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
job=/srv/opentallas-scratch/codex/kant-code-pair-banklocal-reversebanks-20261005-r1
src=/srv/opentallas/repos/pauli-code-banklocal-route-337969217
/srv/opentallas-scratch/admit.sh 64 -- docker run --rm -v "$src:/src:ro" -v "$job/route:/work" -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh; make -f Makefile -f /work/side_effects.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 -j16 finish' > "$job/route/resume.log" 2>&1
rc=$?
echo "$rc" > "$job/resume.exit"
exit "$rc"
