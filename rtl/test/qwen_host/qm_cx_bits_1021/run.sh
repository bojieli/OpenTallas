#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version > verilator.version
for cfg in a4m0 a2m0 a4m1;do
 aw="${cfg:1:1}";mut="${cfg:3:1}"
 verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -j 2 --Mdir "obj_$cfg" --top-module tb -GAW="$aw" -GMUT="$mut" ot_link_afifo.sv qkc_afifo_bits_1021.sv tb.sv > "build_$cfg.log" 2>&1
 if "./obj_$cfg/Vtb" > "$cfg.log" 2>&1;then
   test "$mut" = 0;grep -q '^CX_BITS PASS .*delta_cycles=0' "$cfg.log"
 else
   test "$mut" = 1;grep -q '^CX_BITS FAIL .*MUT=1' "$cfg.log"
 fi
done
printf '%s\n' 'CX_BITS_EQUIVALENCE_AND_MUTANT_DONE'
