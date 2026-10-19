#!/bin/bash
set -eu
for n in original_census control_baseline_census final_census; do
 docker run --rm -v /srv/opentallas-scratch/claude/ref_gate/qfd_d2d_static_safe3-20261019-084003/src:/src:ro -v /srv/opentallas-scratch/claude/ref_gate/qfd_d2d_static_safe3-20261019-084003/routes/gate/work/orfs:/work:ro -v /srv/opentallas-scratch/claude/codex-qw-d2d-clockdiag:/data openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /data/${n}.tcl > ${n}.log 2>&1
done
