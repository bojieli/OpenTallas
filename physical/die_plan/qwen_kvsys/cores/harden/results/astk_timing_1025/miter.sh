#!/bin/bash
T=/srv/opentallas-scratch2/claude/kv-cores-1025r/astk/tb
SRC=/srv/opentallas-scratch2/claude/kv-cores-1025r/astk/A/kv3_astk_WN__190.08x181.44/rtl
export PATH=/srv/opentallas-scratch2/claude/kv-cores-1025r/bin:$PATH
for m in nom mut; do
  rm -rf $T/$m; python3 $T/prep.py $SRC $T/$m $m || exit 1
  cd $T/$m && verilator --binary --timing -j 4 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style --top-module tb --Mdir obj qkd_astk_static_leaves.sv qkd_astk_leaves.sv qkd_astk_zn_head_p.sv ot_hdc_*.sv ot_fp32_add_rne_pipe.sv ot_dp_efault.sv ot_dp_id.sv orig_mods.sv ../tb.sv > build.log 2>&1 || { echo BUILD FAIL $m; tail -20 build.log; continue; }
  docker run --rm -u $(id -u):$(id -g) -v $T:$T -w $T/$m --entrypoint ./obj/Vtb verilator/verilator:v5.032 > sim.log 2>&1
  echo "== $m"; tail -n 4 sim.log
done
