#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c DEMAND_INPUT_SHA256SUMS
python3 demand_plan.py >demand_plan.log 2>&1
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image" bash -lc 'sha256sum -c kit/lib_SHA256SUMS; PYTHONPATH=/work/kit:/work/kit/vendor python3 kit/tree_demand.py' >demand_refine.log 2>&1
python3 construct_demand.py >demand_construction.log 2>&1
python3 kit/render_demand.py >demand_render.log 2>&1
sha256sum -c DEMAND_INPUT_SHA256SUMS
