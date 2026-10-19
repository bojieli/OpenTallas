#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
sha256sum -c REFINEMENT_INPUT_SHA256SUMS
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image" bash -lc 'sha256sum -c kit/lib_SHA256SUMS;PYTHONPATH=/work/kit:/work/kit/vendor python3 kit/tree_refinement.py' >refinement.log 2>&1
sha256sum out/WIRE_REFINEMENT.json out/native_RMST_tree_ledger.json.gz out/all_FF_CQ_domain_ledger.json.gz >REFINEMENT_OUTPUT_SHA256SUMS
sha256sum -c REFINEMENT_INPUT_SHA256SUMS
