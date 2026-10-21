#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version > verilator.version
# Same-edge comparison to the original W64 FIFO, including complete credit pulses.
for cfg in a4m0 a2m0 a4m1;do
 aw="${cfg:1:1}";mut="${cfg:3:1}"
 verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -j 2 --Mdir "obj_$cfg" --top-module tb -GAW="$aw" -GMUT="$mut" ot_link_afifo.sv qkc_afifo_bits_1021.sv tb.sv > "build_$cfg.log" 2>&1
 if "./obj_$cfg/Vtb" > "$cfg.log" 2>&1;then test "$mut" = 0;grep -q '^CX_BITS PASS .*delta_cycles=0' "$cfg.log";
 else test "$mut" = 1;grep -q '^CX_BITS FAIL .*MUT=1' "$cfg.log";fi
done
# Unequal legal synchronizer visibility: coordinated admission must keep whole
# word pointers aligned. The uncoordinated admission mutant must be rejected.
for mut in 0 1;do
 verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -j 2 --Mdir "obj_atomic$mut" --top-module tb_atomic -GMUT="$mut" ot_link_afifo.sv qkc_afifo_bits_1021.sv tb_atomic.sv > "build_atomic$mut.log" 2>&1
 if "./obj_atomic$mut/Vtb_atomic" > "atomic$mut.log" 2>&1;then test "$mut" = 0;grep -q '^CX_BITS_ATOMIC PASS MUT=0' "atomic$mut.log";
 else test "$mut" = 1;grep -q '^CX_BITS_ATOMIC FAIL MUT=1' "atomic$mut.log";fi
done
echo CX_BITS_ATOMIC_EQUIVALENCE_AND_MUTANTS_DONE
