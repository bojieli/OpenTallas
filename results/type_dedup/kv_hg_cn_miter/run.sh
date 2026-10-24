#!/bin/bash
# usage: run.sh [MUT]  -- builds the miter with verilator (--binary) and runs 200k cycles; MUT=1 injects a mutant
# (rotating row consumes [28:24]) that must FAIL.
set -e; mkdir -p ${B:=/tmp/kv_hg_cn_miter_$$}
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../.." && pwd);
CELLS=$R/physical/die_plan/qwen_kvsys/bind/bound_r8/rtl/bind_cells.sv
SRC=$H/kv_hg_cn_miter.sv
if [ "${1:-0}" = 1 ]; then mkdir -p $B; sed 's/assign cfg = q\[29:25\];/assign cfg = q[28:24];/' $SRC > $B/mut.sv; SRC=$B/mut.sv; fi
verilator --binary -Wno-fatal -Wno-lint -Wno-style --top-module tb -Mdir $B/obj $CELLS $SRC >/dev/null
$B/obj/Vtb +NCYC=${NCYC:-200000}
