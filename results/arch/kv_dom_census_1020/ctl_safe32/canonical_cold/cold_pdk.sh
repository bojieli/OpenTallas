#!/bin/bash
set -euo pipefail
G=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu6c-20261019-230301
I=$(cat image_id.txt)
docker run --rm --network none -v "$PWD:/work" -v "$G/src:/src:ro" -v "$G/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_ctl_asap7_ref_gate/base:/original:ro" "$I" python3 /work/ctl_cold_pdk.py
