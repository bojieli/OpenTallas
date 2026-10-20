#!/bin/bash
set -euo pipefail
docker run --rm -v "$PWD:/work" -w /work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -c '
set -euo pipefail
/usr/bin/time -v -o receipts/native_semantics_time.txt python3 native_proof.py > receipts/native_semantics.log 2>&1
for WHICH in original candidate; do
  /usr/bin/time -v -o mapped_$WHICH/proof_time.txt yosys -Q -T -s mapped_$WHICH/native_proof.ys > mapped_$WHICH/proof.log 2>&1
done
echo NATIVE_ALL_OUTPUT_PROOF_COMPLETE
'
