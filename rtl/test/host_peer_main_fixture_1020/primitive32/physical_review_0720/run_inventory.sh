#!/bin/bash
set -euo pipefail
gate=/srv/opentallas-scratch/claude/ref_gate/qkd_hr_core_peer_p32a-20261020-050147
docker run --rm -v "$gate:/gate:ro" -v "$PWD/qkd_hr_core_peer_p32a/classification:/model_src:ro" -v "$PWD:/model_base:ro" -v "$PWD/inventory.py:/audit.py:ro" -v "$PWD/qkd_hr_core_peer_p32a:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py
