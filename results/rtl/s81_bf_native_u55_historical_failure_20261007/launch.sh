#!/bin/bash
set -eu
base=/srv/opentallas-scratch/codex-item8-bf-route-93d508997
cd "$base/src"
exec /srv/opentallas-scratch/admit.sh 32 -- env OT_ORFS_NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 python3 tools/s81/run_bf_native_physical.py --work "$base/u55/work" --output "$base/u55/physical.json" --util 55 --tag s81_bf_native_u55
