#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
ROOT=$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)
cd "$ROOT"
O=${1:?fresh repo-relative output directory}
case "$O" in /*) echo 'output must be repo-relative' >&2;exit 2;;esac
if [ -e "$O" ];then echo 'refusing existing output' >&2;exit 2;fi
mkdir -p "$O"
p=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
mkdir -p "$(dirname "$p")"
git show "HEAD:$p" > "$p"
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_idxnet_tx_contract --Mdir "$O/obj" --build-jobs 8 rtl/lib/ot_rst_relay.sv "$p" rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv tools/s81_dv/layer_prog/tb_idxnet_tx_contract.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_idxnet_tx_contract" > "$O/positive.log" 2>&1
"$O/obj/Vtb_idxnet_tx_contract" +LANE=0 > "$O/lane0.log" 2>&1
set +e
"$O/obj/Vtb_idxnet_tx_contract" +POISON=1 > "$O/alias.log" 2>&1
r=$?
set -e
test "$r" != 0
grep IDXNET_SCORE_ALIAS "$O/alias.log"
echo IDXNET_ALIAS_REPRODUCED
