#!/bin/bash
# TR3-KV-LEC 2026-10-25: unit lockstep bench (head_master_miter.py, PATH-KV tool) of each odd head strap master kit RTL
# against each old constant variant kit RTL, >= 2 strap values per master, plus one wrong-strap mutant that must FAIL.
#   miter.sh SCRATCH  (SCRATCH/kits/{m_e1,m_e5,old_e1,old_e3,old_e5,old_e7}/kv3_head_eighth_e*__216x216)
# Heavy (Verilator): run through ot-run.  Writes SCRATCH/miter/<case>/{gen,build,sim}.log; prints CORE MITER lines.
set -u
S=$1; HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../../../.." && pwd)
T=$REPO/physical/die_plan/qwen_kvsys/cores/harden/head_master_miter.py
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
declare -A LANES=([1]="2 3" [3]="6 7" [5]="10 11" [7]="14 15")
run() {  # case master variant bsel
  local C=$1 M=$2 N=$3 B=$4 D=$S/miter/$1
  local OK=$(ls -d $S/kits/old_e$N/kv3_head_eighth_e${N}__*) MK=$(ls -d $S/kits/m_e$M/kv3_head_eighth_e${M}__*)
  mkdir -p $S/miter; rm -rf $D
  python3 - "$OK/core.json" "$S/miter/pm_$C.json" ${LANES[$N]} ${LANES[$M]} <<'PY'
import json, re, sys
cj, out, a0, a1, b0, b1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:])
m = {a0: b0, a1: b1}
pm = {p: re.sub(r"^g_t_(\d+)_", lambda x: f"g_t_{m.get(int(x.group(1)), int(x.group(1)))}_", p) for p in json.load(open(cj))["port_decl"]}
json.dump(pm, open(out, "w"), indent=0)
PY
  python3 $T $OK $MK $D --port-map $S/miter/pm_$C.json --new-mod kv3_head_eighth_e$M --strap "strap_bsel=2'b$B" > $S/miter/$C.gen.log 2>&1 || { echo "CASE $C GEN FAIL"; tail -3 $S/miter/$C.gen.log; return; }
  ( cd $D && verilator --binary --timing -j 8 -MAKEFLAGS OBJCACHE= -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f > build.log 2>&1 && ./obj/Vtb > sim.log 2>&1 )
  echo "CASE $C master=e$M variant=e$N strap_bsel=2'b$B: $(grep "CORE MITER" $D/sim.log 2>/dev/null || tail -2 $D/build.log)"
  verilator --version | sed "s/^/  /"
}
run m1_e1 1 1 00 & run m1_e3 1 3 01 & run m5_e5 5 5 10 & run m5_e7 5 7 11 & run mut_m1_e3_00 1 3 00 &
wait
