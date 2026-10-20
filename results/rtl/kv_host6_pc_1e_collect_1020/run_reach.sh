#!/bin/bash
set -euo pipefail
docker run --rm -v "$PWD:/work" -v /srv/opentallas-scratch/claude/ref_gate/qkd_hr_cdc_pc_sram1e-20261020-030933/routes/gate/work/orfs:/input:ro -w /work openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python reach.py
