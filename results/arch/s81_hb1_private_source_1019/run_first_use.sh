#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
test "${HB1_ROOT_INITIAL_RELATION_APPROVED:-0}" = 1
test ! -e out_first01
python3 first_use.py
mkdir out_first01
hostname > out_first01/host.txt
free -b > out_first01/free_before.txt
df -B1 . > out_first01/disk_before.txt
iverilog -V > out_first01/iverilog_version.txt 2>&1
sha256sum generated01/*.sv ../s81_hb1_cell_semantics_1019/functional_projection.v > out_first01/inputs.sha256
/usr/bin/time -v -o out_first01/build_resources.txt iverilog -g2012 -s tb_first_use -o out_first01/sim ../s81_hb1_cell_semantics_1019/functional_projection.v generated01/reset.sv generated01/anchor_private.sv generated01/select.sv generated01/retained_graph.sv generated01/native_reference.sv generated01/tb_first_use.sv > out_first01/build.log 2>&1
set +e
/usr/bin/time -v -o out_first01/run_resources.txt vvp out_first01/sim > out_first01/run.log 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > out_first01/exit.txt
cat out_first01/run.log
exit "$rc"
