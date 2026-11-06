#!/bin/bash
set -eu
cd "$(dirname "$0")"
/usr/bin/time -v yosys -p 'read_rtlil phase_actual.il; sat -seq 12 -set-init-undef -set-def-inputs -set-at 1 rst_n 0 -set rst_n 1 -prove proof_bad 0 -verify -show proof_ready,proof_capture,proof_precompute,proof_accept,proof_gb,proof_pf,proof_saved_gb,proof_saved_pf -dump_vcd phase2_fail.vcd' > phase2.log 2>&1
