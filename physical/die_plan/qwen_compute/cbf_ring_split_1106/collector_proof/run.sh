#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
# Run this under normal ot-run admission (4GB/1T).
docker run --rm --memory=3g --cpus=1 -v "$PWD":/proof -w /proof openroad/orfs:asap7lock bash -lc 'yosys -l proof.log proof.ys > proof.stdout 2>&1 && if yosys -l mutant.log proof_mut.ys > mutant.stdout 2>&1; then exit 2; else grep -q "proof did fail" mutant.log; fi'
