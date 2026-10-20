#!/bin/bash
set -euo pipefail
lane=$PWD
mkdir -p gridout
docker run --rm -v /srv/opentallas-scratch/claude/ref_gate/qkd_kvs_grp_s6a-20261020-024704:/gate:ro -v "$lane/grid.py:/audit.py:ro" -v "$lane/gridout:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py
