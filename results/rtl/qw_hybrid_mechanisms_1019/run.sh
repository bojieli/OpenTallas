#!/bin/bash
set -euo pipefail
verilator --version
verilator --binary --timing --top-module tb -Wno-fatal -DOT_MEM_NO_INIT --x-initial unique --x-assign unique -j 8 --Mdir obj tb.sv qfd_d8_mechanism.sv ot_sram_1r1w2c_32x64_m1.v > build.log 2>&1
./obj/Vtb > baseline.log 2>&1
cat baseline.log
