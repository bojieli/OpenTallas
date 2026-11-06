#!/bin/bash
set -eu
cd "$(dirname "$0")"
/usr/bin/time -v yosys -p 'read_rtlil phase_induct.il; sat -tempinduct -seq 2 -maxsteps 10 -set-at 1 rst_n 0 -prove proof_bad 0 -prove proof_invariant_bad 0 -verify -show proof_ready,proof_capture,proof_precompute,proof_accept,proof_gb,proof_pf,proof_saved_gb,proof_saved_pf,_60260_ -dump_vcd phase5_fail.vcd' > phase5.log 2>&1
