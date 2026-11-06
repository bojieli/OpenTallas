#!/bin/bash
set -eu
cd "$(dirname "$0")"
/usr/bin/time -v yosys -p 'read_verilog -sv phase_mutant.sv; hierarchy -top phase_actual; proc; opt; async2sync; opt_clean; sat -seq 12 -set-at 1 rst_n 0 -prove proof_bad 0 -show proof_ready,proof_capture,proof_precompute,proof_accept,proof_gb,proof_pf -dump_vcd phase_mutant.vcd' > phase_mutant.log 2>&1
grep -q 'SAT proof finished - model found: FAIL!' phase_mutant.log
