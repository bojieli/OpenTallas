#!/usr/bin/env bash
# run_bench.sh SRC OUT MLAT ALAT LDCS DM DA LANE_ID CYC MUT [DEFINES]
set -u
SRC=$1; O=$2; shift 2; mkdir -p "$O"
H=$(cd "$(dirname "$0")" && pwd)
python3 -I "$H/mk_bench.py" "$SRC" "$O" "$@" > "$O/gen.log" || { cat "$O/gen.log"; exit 1; }
python3 -I "$SRC/tools/lockstep_gen.py" "$O/spec.json" "$O/tb.sv"
python3 -I "$H/fault_cmp.py" "$O/tb.sv" "$O/map.json"
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
DEF=${9:-}
$V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style $DEF --top-module tb -Mdir "$O/obj" -o sim \
  "$O/tb.sv" "$O/dutw.sv" "$O"/ref_*.sv "$SRC"/new/*.sv "$SRC"/leaf/*.sv "$SRC/tools/sram_bench_model.sv" > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 2; }
"$O/obj/sim" > "$O/sim.log" 2>&1
echo "$(basename $O): $(grep LOCKSTEP "$O/sim.log") $(grep FAULT_SRC "$O/sim.log") | $(cat $O/gen.log)"
rm -rf "$O/obj"
