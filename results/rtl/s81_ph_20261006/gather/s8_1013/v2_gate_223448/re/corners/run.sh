#!/bin/bash
set -euo pipefail
for s81_corner in tt ss ff; do
 docker run --rm -v /srv/opentallas-scratch/claude/ref_gate/dsfd_gth_re-20261013-223448/src:/src:ro -v /srv/opentallas-scratch/claude/ref_gate/dsfd_gth_re-20261013-223448/routes/gate/work/orfs:/work:ro -v /srv/opentallas-scratch/claude/ref_gate/dsfd_gth_re-20261013-223448/diagnostic_corners:/probe:ro openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/${s81_corner}.tcl > /srv/opentallas-scratch/claude/ref_gate/dsfd_gth_re-20261013-223448/diagnostic_corners/${s81_corner}.log 2>&1
 echo "ACTUAL_CORNER_COMPLETE $s81_corner"
done
