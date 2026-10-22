#!/bin/bash
# KV-AHUB9: every qkd_ahub_static_dw bench on branch claude/kv-ahub8-1020 @b4197ae74 (a7 RTL + main's ot_qkd_ahub_core.sv / ot_rst_pipe.sv), Verilator 5.050
cd "$(dirname "$0")/src"
J=""
for m in 0 1 2 3 4 5 6 7 8 9 10 11 12; do J="$J s4o:$m"; done
for m in 0 1 2 3 4 5 6 7; do J="$J s4:$m"; done
for m in 0 1 2 3; do J="$J dw:$m"; done
J="$J bo:0"
one(){ b=${1%%:*}; m=${1##*:}; case $b in s4o) sh=ahub_static_dw_s4o_bench.sh;; s4) sh=ahub_static_dw_s4_bench.sh;; dw) sh=ahub_static_dw_bench.sh;; bo) sh=ahub_static_dw_bo_bench.sh;; esac
  out=../out/$b/m$m; mkdir -p $out; bash tools/qwen_kv_die/$sh $out $m > ../out/${b}_m$m.log 2>&1; echo "$b m$m rc=$? $(grep -E '^AHUB_DW (PASS|FAIL)' ../out/${b}_m$m.log | tail -1)"; }
export -f one
printf '%s\n' $J | xargs -P 10 -I{} bash -c 'one {}' | sort > ../summary.txt
cat ../summary.txt
