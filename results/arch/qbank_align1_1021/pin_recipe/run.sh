#!/bin/bash
set -euo pipefail
for tag in e f; do
 sha256sum "input_${tag}.odb" > "input_${tag}.sha256"
 docker run --rm -v "$PWD:/src:ro" -v "$PWD:/work" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/src/check_${tag}.tcl" > "pin_${tag}.log" 2>&1
 python3 fp_margin_lint.py pins "corrected_${tag}.json" --out "pin_${tag}_geometry.json" > "pin_${tag}_geometry.log" 2>&1
 sha256sum -c "input_${tag}.sha256"
 cat "pin_${tag}_geometry.log"
done
