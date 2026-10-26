#!/bin/bash
set -eu
docker run --rm -v /srv/opentallas-scratch/claude/ref_gate/qfd_ucie_gearbox_r10-20261016-030510/src:/src:ro -v "$PWD/orfs":/work:ro -v "$PWD":/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/report.tcl > report.log 2>&1
