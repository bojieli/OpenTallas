#!/bin/bash
# Reproduce TX-only inherited proof. Run through ot-run; do not rerun solely for provenance.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$H/../.." && pwd)
S=$R/rtl/dsrom_sys/s81_link
E=${TX_PROOF_OUT:?set a new scratch output, never overwrite old verdicts}
mkdir -p "$E"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
BASE="-DOT_S81_RCK_REFORM -DOT_S81_RCK_RELAY4 -DOT_S81_KP4_AM_FACE3 -DOT_S81_KP4_SYN_LOCAL"
COMMON="$S/ot_s81_kp4_common.sv $R/rtl/common/landed_parent/ot_pl_land.sv"
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' "$f" | sort -u);do sed -i -E "s/\b$m\b/${m}${sfx}/g" "$f";done; }
for mode in base mutant;do
 D=$E/$mode;mkdir -p "$D"
 defs=();if [ "$mode" = mutant ];then defs+=(-DRCKRF_MUT_PPCYC);fi
 verilator -E -P -I"$S" $BASE $COMMON "$H/old/ot_s81_kp4_enc.sv" "$H/old/ot_s81_rck_reform.sv" > "$D/ref.sv";ren "$D/ref.sv" _r
 verilator -E -P -I"$S" $BASE -DOT_S81_RCK_TX_PPCYC "${defs[@]}" $COMMON "$S/ot_s81_kp4_enc.sv" "$S/col/ot_s81_rck_reform.sv" > "$D/new.sv";ren "$D/new.sv" _n
 verilator --binary --timing -j 6 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --x-initial unique --x-assign unique --top-module tb --Mdir "$D/obj" -o tb "$H/tb_tx.sv" "$D/ref.sv" "$D/new.sv" > "$D/build.log" 2>&1
 for seed in 1 2 3;do
  set +e
  "$D/obj/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$D/seed$seed.log" 2>&1
  rc=$?
  set -e
  tail -5 "$D/seed$seed.log"
  if [ "$mode" = base ];then test "$rc" = 0;else test "$rc" != 0;fi
 done
done
