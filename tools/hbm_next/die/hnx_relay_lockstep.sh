#!/usr/bin/env bash
# HBM-NEXT-DIE 10-19: hnx fork (by copy) of tools/hbm_die_v16/run_relay_lockstep.sh for the P = 4 stand-in die chain.
# Differences: (1) the TB generation runs ON THE FLEET (ot-run, the case host) and the TBs stay there, (2) normal ot-run
# priority (HBM-NEXT rule: never --priority die), (3) hosts = the case host only (data locality), (4) hnx_ out dirs.
#   hnx_relay_lockstep.sh REMOTE_SRC LAYER(remote, abs) REMOTE_OUT LOCAL_LOG_DIR [MAX_BUSES]
set -uo pipefail
S=$1; L=$2; RO=$3; LO=$4; MB=${5:-120}; mkdir -p "$LO"; fail=0
H=${OT_LOCKSTEP_HOST:-ot-epyc4}; OTRUN=${OTRUN:-/home/ubuntu/bin/ot-run}
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator   # fleet 5.050 + NBA guard, never the distro 5.032
D=rtl/hbm_accel/die_glue
src="$D/hbfd_rly_fc_masters.sv $D/hbfd_rly_fcf_masters.sv $D/hbfd_rly_masters.sv $D/ot_hbm_rly_fc.sv $D/ot_hbm_rly_fcf.sv $D/ot_hbm_rly.sv rtl/lib/ot_rst_relay.sv $D/hbfd_lane_masters.sv $D/ot_hbm_lane.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv"
MUTS="pos lane_stage bitswap branch_drop land_k"
gen="mkdir -p $RO && sha256sum $src $L tools/hbm_die_v16/relay_lockstep_bench.py > $RO/sources.sha256 && for m in $MUTS; do X=; [ \$m != pos ] && X=\"--mut \$m\"; python3 tools/hbm_die_v16/relay_lockstep_bench.py --layer $L --out $RO/\$m --max-buses $MB \$X > $RO/\$m.gen.log || exit 4; tail -1 $RO/\$m.gen.log; done; tar -cf - $src | tar -x -C $RO"
$OTRUN --mem 24 --threads 1 --hosts $H --dir $S -- bash -c "$gen" > $LO/gen.log 2>&1 || { echo RELAY_LOCKSTEP_GATE FAIL gen; tail -5 $LO/gen.log; exit 1; }
pids=()
for m in $MUTS; do
  cmd="rm -rf vl_$m && $VL --binary --timing -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast \
--output-split 20000 --output-split-cfuncs 2000 -MAKEFLAGS OPT_FAST=-O1 -MAKEFLAGS OPT_SLOW=-O0 \
--top-module tb_relay_lockstep -j 16 --Mdir vl_$m -o sim $src $m/tb_relay_lockstep.sv > vl_$m.build.log 2>&1 \
|| { tail -20 vl_$m.build.log; exit 3; }; timeout 3000 ./vl_$m/sim; rc=\$?; rm -rf vl_$m; exit \$rc"
  ( $OTRUN --mem 48 --threads 16 --hosts $H --dir $RO -- bash -c "$cmd" > "$LO/$m.run.log" 2>&1; echo "OTRUN_RC $?" >> "$LO/$m.run.log" ) &
  pids+=($!)
done
wait "${pids[@]}"
for m in $MUTS; do
  r=$(grep -E 'RELAY_LOCKSTEP|MISMATCH' "$LO/$m.run.log" | tail -2); echo "$m :: $r"
  if [ $m = pos ]; then echo "$r" | grep -q "RELAY_LOCKSTEP PASS" || fail=1
  else echo "$r" | grep -Eq "RELAY_LOCKSTEP FAIL checks=[0-9]+ errors=[1-9]" || fail=1; fi
done
[ $fail = 0 ] && echo RELAY_LOCKSTEP_GATE PASS || { echo RELAY_LOCKSTEP_GATE FAIL; exit 1; }
