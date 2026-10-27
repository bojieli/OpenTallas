#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-idxnet/src
O=/srv/opentallas-scratch2/claude/codex-s81-idxnet/debug
mkdir -p "$O"
SL=rtl/dsrom_sys/s81_dv/slice
eval "$(sed -n '/^V=verilator/,/^D=/p' $SL/test/run_lep_idx_bench.sh)"
eval "$(sed -n '/^build() {/,/^}/p' $SL/test/run_lep_idx_bench.sh)"
build debug tb_s81sl_lep_idxnet tb_s81sl_lep_idxnet.sv
"$O/debug/Vtb_s81sl_lep_idxnet" > "$O/run.log" 2>&1
