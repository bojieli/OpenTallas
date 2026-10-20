#!/usr/bin/env bash
# Run on the fleet. Source-faithful write-state induction cut, not full group/native equivalence.
set -euo pipefail
ROOT=$PWD
OUT=$(mkdir -p "${1:?out}" && cd "$1" && pwd)
python3 tools/s81_dv/svc_rs/svc8_write_cut.py --out "$OUT/write_cut.v" > "$OUT/cut_identity.log"
cp rtl/hdc/v41x/ot_hdc_v41x_kreg.sv "$OUT/kreg.sv"
docker run --rm -v "$OUT:/out" -w /out openroad/orfs:latest bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 yosys -l formal.log -p "read_verilog -sv kreg.sv write_cut.v; hierarchy -top write_miter; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; prep -top write_miter -flatten; async2sync; opt_clean; sat -seq 3 -set-at 2 same_state 1 -prove-skip 2 -prove same_state 1 -verify -show-inputs -show-outputs"
' > "$OUT/formal.stdout" 2>&1
grep -E 'SAT proof|SUCCESS|FAIL' "$OUT/formal.log"
