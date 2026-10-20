#!/bin/bash
# QW-SLICE7-LEAVES/SUVM pre-gate native census: ASAP7 RVT TT mapped synthesis of a suvm leaf (SRAM macros blackbox),
# then the strict mapped fanout census (raw ports + reset counted, BUF/INV collapsed). Usage: native.sh OUT TOP "SRCS..." [DEFS]
set -euo pipefail
O=$1; TOP=$2; SRCS=$3; DEFS=${4:-}
mkdir -p "$O"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
BB=$(ls physical/asap7_memory_macros_v2/ot_sram_1r1w_{1024x256_m2,128x256_m1,256x256_m2}_r2c2/*_bb.v | tr "\n" " ")
python3 rtl/test/qwen_dv/s5/suvm7/merge_lib.py "$FLOW" "$O/cells.lib"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -lib $BB; read_verilog -sv $DEFS $SRCS; hierarchy -check -top $TOP; synth -top $TOP -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; opt_clean; rename -wire; stat -liberty $O/cells.lib; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
python3 rtl/test/qwen_dv/s5/suvm7/native_census.py "$O/mapped.v" > "$O/census.json"
python3 - "$O/census.json" <<'PY'
import json,sys;d=json.load(open(sys.argv[1]));print('CENSUS',d['verdict'],'over32',d['nonclock_drivers_over32'],'flop',d['flop_drivers_over32'],'ports',d['raw_ports_over32'],'max',d['max_nonclock_loads']);[print(' ',r['loads'],r['driver']) for r in d['violations'][:60]]
PY
gzip -kf "$O/mapped.v"
