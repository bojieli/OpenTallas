#!/usr/bin/env bash
# H-NETLIST/D4F-RELAY: per-lane lockstep bench of a d4f relay layer: positive PASS, mutants lane_stage / bitswap / branch_drop FAIL.
#   run_relay_lockstep.sh LAYER.json.gz OUT [MAX_BUSES]
# The bench is one flat module of ~10^5 relay instances (18 MB of SV at 120 buses): Icarus sat >80 min in the compile
# alone (run8b, 10-17), so the four legs run under Verilator 5 (--binary --timing) on the fleet via ot-run, in parallel.
# The TBs are generated locally; RTL + TB are copied to every Verilator host (ot-run syncs nothing).
#   OT_LOCKSTEP_SIM=icarus  -> the old local iverilog/vvp path (small layers / debugging only).
#   OT_LOCKSTEP_HOSTS       -> fleet hosts (default all three; each has the guarded 5.050 install).
# Verilator is the fleet 5.050 behind the NBA-loop guard shim (tools/fleet/install_verilator_nba_guard.sh): the bench's
# history shift registers are NBA loops, exactly the miscompile the guard refuses (exit 86).  Never the distro 5.032.
set -uo pipefail
L=$1; OUT=$(realpath -m "$2"); MB=${3:-0}; mkdir -p "$OUT"; fail=0
SIM=${OT_LOCKSTEP_SIM:-verilator}; HOSTS=${OT_LOCKSTEP_HOSTS:-ot-epyc4,ot-agidock128,ot-pve1}
VL=${OT_LOCKSTEP_VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}; OTRUN=${OTRUN:-/home/ubuntu/bin/ot-run}
D=rtl/hbm_accel/die_glue
src=($D/hbfd_rly_fc_masters.sv $D/hbfd_rly_fcf_masters.sv $D/hbfd_rly_masters.sv $D/ot_hbm_rly_fc.sv $D/ot_hbm_rly_fcf.sv $D/ot_hbm_rly.sv rtl/lib/ot_rst_relay.sv)
MUTS=(pos lane_stage bitswap branch_drop)
# HBM-LANDING 10-18: a --land layer (half-cycle lane stations + landings) adds the lane RTL and the land_k mutant
if python3 -c "import gzip,json,sys; L=json.load(gzip.open(sys.argv[1]) if sys.argv[1].endswith('.gz') else open(sys.argv[1])); sys.exit(0 if any(i['master'].startswith(('hbfd_lh','hbfd_land')) for i in L['instances']) else 1)" "$L"; then
  src+=($D/hbfd_lane_masters.sv $D/ot_hbm_lane.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv); MUTS+=(land_k)
fi
sha256sum "${src[@]}" "$L" tools/hbm_die_v16/relay_lockstep_bench.py "$0" > "$OUT/sources.sha256"
for m in "${MUTS[@]}"; do
  X=; [ $m != pos ] && X="--mut $m"
  python3 tools/hbm_die_v16/relay_lockstep_bench.py --layer "$L" --out "$OUT/$m" --max-buses $MB $X > "$OUT/$m.gen.log" || { cat "$OUT/$m.gen.log"; fail=1; }
done
[ $fail = 0 ] || { echo RELAY_LOCKSTEP_GATE FAIL; exit 1; }
judge() {  # m result-lines
  local m=$1 r=$2; echo "$m $SIM $(tail -1 $OUT/$m.gen.log) :: $r"
  if [ $m = pos ]; then echo "$r" | grep -q "RELAY_LOCKSTEP PASS" || return 1
  else echo "$r" | grep -Eq "RELAY_LOCKSTEP FAIL checks=[0-9]+ errors=[1-9]" || return 1; fi
}
if [ "$SIM" = icarus ]; then
  for m in "${MUTS[@]}"; do
    iverilog -g2012 -o "$OUT/$m/sim" "${src[@]}" "$OUT/$m/tb_relay_lockstep.sv" > "$OUT/$m.build.log" 2>&1 || { tail -5 "$OUT/$m.build.log"; fail=1; continue; }
    r=$(timeout 3000 vvp "$OUT/$m/sim" | grep -E 'RELAY_LOCKSTEP|MISMATCH' | tail -2); judge $m "$r" || fail=1
  done
else
  # remote dir keyed by OUT so concurrent chains never collide
  R=/srv/opentallas-scratch/claude/relay_lockstep/$(basename "$OUT")_$(echo -n "$OUT" | sha1sum | cut -c1-10)
  for h in ${HOSTS//,/ }; do
    { tar -cf - "${src[@]}"; } | ssh -o BatchMode=yes $h "rm -rf $R && mkdir -p $R && tar -x -C $R" || echo "LOCKSTEP_SYNC_FAIL $h"
    tar -C "$OUT" -cf - $(printf '%s/tb_relay_lockstep.sv ' "${MUTS[@]}") | ssh -o BatchMode=yes $h "tar -x -C $R" || echo "LOCKSTEP_SYNC_FAIL $h"
  done
  pids=()
  for m in "${MUTS[@]}"; do
    # the flat TB makes one ~235k-line nba function: without --output-split-cfuncs g++ -Os sat >16 min on one file
    # 2-state is fine here: every check starts after the bus latency (cyc > lat), so no X compare is ever made
    cmd="rm -rf vl_$m && $VL --binary --timing -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
--output-split 20000 --output-split-cfuncs 2000 -MAKEFLAGS OPT_FAST=-O1 -MAKEFLAGS OPT_SLOW=-O0 \
--top-module tb_relay_lockstep -j 16 --Mdir vl_$m -o sim ${src[*]} $m/tb_relay_lockstep.sv > vl_$m.build.log 2>&1 \
|| { tail -20 vl_$m.build.log; exit 3; }; timeout 3000 ./vl_$m/sim; rc=\$?; rm -rf vl_$m; exit \$rc"
    ( $OTRUN --mem 48 --threads 16 --hosts "$HOSTS" --dir "$R" --priority die -- bash -c "$cmd" > "$OUT/$m.run.log" 2>&1
      echo "OTRUN_RC $?" >> "$OUT/$m.run.log" ) &
    pids+=($!)
  done
  wait "${pids[@]}"
  for m in "${MUTS[@]}"; do
    r=$(grep -E 'RELAY_LOCKSTEP|MISMATCH' "$OUT/$m.run.log" | tail -2)
    judge $m "$r" || { fail=1; grep -E 'ot-run:|OTRUN_RC|%Error' "$OUT/$m.run.log" | tail -6; }
  done
fi
[ $fail = 0 ] && echo RELAY_LOCKSTEP_GATE PASS || { echo RELAY_LOCKSTEP_GATE FAIL; exit 1; }
