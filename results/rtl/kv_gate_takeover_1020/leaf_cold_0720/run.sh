#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version > version.txt
for variant in positive wrong bypass reset late; do
 core=core.sv;top=top.sv
 case $variant in wrong|bypass|reset)top=top_$variant.sv;;late)core=core_late.sv;;esac
 mkdir -p "$variant"
 verilator --binary --timing --public-flat-rw --x-initial unique --x-assign unique -Wno-fatal -Wno-BLKANDNBLK --top-module tb --Mdir "$variant/build" -j 8 tb.sv "$core" "$top" > "$variant/build.log" 2>&1
 for seed in 17 1020;do
  set +e
  "$variant/build/Vtb" +SEED=$seed +verilator+rand+reset+2 +verilator+seed+$seed > "$variant/seed_$seed.log" 2>&1
  rc=$?
  set -e
  echo "$variant seed=$seed rc=$rc" | tee -a status.txt
  if [ "$variant" = positive ];then [ "$rc" = 0 ] && grep -q LEAF_COLD_PASS "$variant/seed_$seed.log" || exit 3
  else [ "$rc" != 0 ] && grep -q MISMATCH "$variant/seed_$seed.log" || exit 4;fi
 done
done
