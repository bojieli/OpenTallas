#!/bin/bash
set -euo pipefail
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs:asap7lock bash -c 'yosys -p "read_verilog -sv actual_refs.sv miter.sv; prep -top miter -flatten; opt; sat -verify -prove correct 1 -show-inputs -show-outputs" > proof.log 2>&1; yosys -p "read_verilog -sv actual_refs.sv miter.sv; prep -top miter -flatten; opt; sat -prove mutant_correct 1 -show-inputs -show-outputs" > mutant.log 2>&1'
python3 -I - <<'PY'
from pathlib import Path
assert 'SAT proof finished - no model found: SUCCESS!' in Path('proof.log').read_text()
assert 'SAT proof finished - model found: FAIL!' in Path('mutant.log').read_text()
Path('verdict.txt').write_text('PASS: actual pb/pc/pd flattened phase3 D equals native off32 for all arbitrary112 input bits. Partial-output-bit mutant caught by SAT. No multiplier/clock/reset/enable assumptions.\n')
print(Path('verdict.txt').read_text())
PY
