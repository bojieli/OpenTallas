#!/bin/bash
# DIE-QC-58 10-31 KV_WR_PIPE evidence: (1) yosys SAT proof fp8r_fin(fp8r_pre(v)) == fp8r(v) for all 2^32 v,
# (2) iverilog random+edge equivalence, (3) cycle-exact lockstep of qfd_dv_lane_h_safe2 KV_WR_PIPE 0 vs 1 (all outputs,
# random fp32 operands, KV writes), (4) mutant must FAIL.  Run in docker (verilator/verilator:v5.032, openroad/orfs:asap7lock).
set -eu
P=$(realpath -m "${1:?usage: run.sh OUTPUT [SOURCE_TREE]}"); T=$(realpath "${2:-$(dirname "$0")/../../../..}")
mkdir -p "$P"; H=$T/rtl/qwen_dv/qfd_dv_head_safe1.sv; D=$T/rtl/test/qwen_dv/kv_wr_pipe
python3 -I $D/mk_fp8r_eq.py $H $P/eq.sv $P/tb_eq.sv
printf "read_verilog -sv /p/eq.sv\nprep -top eqv\nflatten\nopt\ntee -o /p/sat.txt sat -prove ok 1 -verify -show-ports\n" > $P/p.ys
docker run --rm --memory=8g -v $P:/p openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -s /p/p.ys" >/dev/null
grep "SAT proof" $P/sat.txt
iverilog -g2012 -o $P/tb_eq.vvp $P/eq.sv $P/tb_eq.sv && vvp -n $P/tb_eq.vvp | grep RANDOM_EQ
python3 -I - "$T" "$P" <<PY
import sys
from pathlib import Path
T,P=map(Path,sys.argv[1:]);sys.path.insert(0,str(T/rtl/test/qwen_dv));import dv_bench2 as B
src=list(dict.fromkeys(B.SRCS2+B.XSRCS+[physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v]))
(P/sources.f).write_text(n.join(/t/+s for s in src if not s.endswith(/qfd_dv_head_safe1.sv))+n)
PY
docker run --rm --memory=16g --cpus=8 -v $T:/t:ro -v $P:/p -w /p --entrypoint bash verilator/verilator:v5.032 -c "verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 --top-module tb_kvpipe -f /p/sources.f /t/rtl/qwen_dv/qfd_dv_head_safe1.sv /t/rtl/test/qwen_dv/kv_wr_pipe/tb_kvpipe.sv -Mdir /p/obj >/p/build.log 2>&1; /p/obj/Vtb_kvpipe > /p/run.log 2>&1" ; grep "KVPIPE" $P/run.log | tail -2
