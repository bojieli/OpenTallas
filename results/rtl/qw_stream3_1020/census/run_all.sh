#!/bin/bash
# QW-STREAM3: benches (Verilator 5.050) for m0 + mutants in parallel, then a quick yosys 0.68 ASAP7 RVT TT mapped census.
set -uo pipefail
cd "$(dirname "$0")/src"
OUT=../out; mkdir -p $OUT
MUTS="${MUTS:-0 2 21 22 31 32 33 34 35 37 38}"
for m in $MUTS; do ( bash rtl/test/qwen_dv/static_stream/run_tile.sh $OUT/bench/m$m $m > $OUT/m$m.log 2>&1; echo "MUT$m exit $?" >> $OUT/m$m.log ) & done
if [ "${CENSUS:-0}" = 1 ]; then
 L=$HOME/.local/opentallas-pdk-asap7/lib/NLDM; Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
 LIBS=$(ls $L/*RVT_TT*.lib); RL=""; AL=""; NL=""
 for f in $LIBS; do RL="$RL read_liberty -lib $f;"; AL="$AL -liberty $f"; NL="$NL --liberty $f"; done
 SEQ=$(ls $L/*SEQ_RVT_TT*.lib)
 mkdir -p $OUT/census
 $Y -q -l $OUT/census/yosys.log -p "$RL read_verilog -sv rtl/qwen_dv/qfd_dv_stream_tile.sv; synth -top qfd_dv_stream_tile -flatten; dfflibmap -liberty $SEQ; abc $AL; opt_clean; stat; write_verilog -noattr $OUT/census/net.v" > /dev/null 2>&1
 echo "yosys exit $?" > $OUT/census/status
 python3 tools/ref_tile/native_census.py --netlist $OUT/census/net.v --top qfd_dv_stream_tile $NL --out $OUT/census/native_census.json > $OUT/census/census.log 2>&1
 echo "census exit $?" >> $OUT/census/status
fi
wait
grep -h "MUT.* exit\|STREAM_TILE" $OUT/m*.log
