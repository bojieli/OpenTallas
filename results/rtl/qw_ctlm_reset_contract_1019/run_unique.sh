#!/bin/bash
set -u
verilator --binary --timing --x-initial unique --x-assign unique --top-module tb_root_contract -Wno-fatal -j 2 tb_root_contract.sv qfd_link_slots.sv ot_qwen_rst_rep.sv ot_pl_land.sv -Mdir obj_unique > unique_build.log 2>&1 || exit 1
: > unique_statuses.tsv
for seed in 1 17 131; do
 ./obj_unique/Vtb_root_contract +phase=0 +release=100000 +verilator+seed+"$seed" +verilator+rand+reset+2 > "unique_seed${seed}.log" 2>&1
 printf 'seed%s\t%s\n' "$seed" "$?" >> unique_statuses.tsv
done
cat unique_statuses.tsv
