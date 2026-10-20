#!/bin/bash
set -u
verilator --version > version.txt
verilator --binary --timing --top-module tb_root_contract -Wno-fatal -j 2 tb_root_contract.sv qfd_link_slots.sv ot_qwen_rst_rep.sv ot_pl_land.sv -Mdir obj > build.log 2>&1 || exit 1
: > statuses.tsv
for phase in -2000 -1000 -500 0 500 1000 2000; do
  for release in 100000 102000; do
    tag="p${phase}_r${release}"
    ./obj/Vtb_root_contract +phase="$phase" +release="$release" > "$tag.log" 2>&1
    rc=$?
    printf '%s\t%s\n' "$tag" "$rc" >> statuses.tsv
  done
done
./obj/Vtb_root_contract +negative=1 > leaf_negative.log 2>&1
printf 'leaf_negative\t%s\n' "$?" >> statuses.tsv
cat statuses.tsv
