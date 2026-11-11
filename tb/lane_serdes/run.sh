#!/bin/bash
# CPL-HBM-B1: EQ bench for the DEC12 multi-beat lane endpoints (ot_lane_ser -> lane pipe -> ot_lane_deser
# == parallel pipe delayed by N-1). Positive runs must PASS; both negative controls (NEG_SWAP beat order,
# NEG_LAT reference latency N-2) must FAIL. Exit 0 only if all of that holds.
set -u
D=$(cd "$(dirname "$0")" && pwd); R=$D/../../rtl/common; T=$(mktemp -d); rc=0
for cfg in "4 2745" "2 2745" "8 2745" "4 1383" "3 1001"; do
  set -- $cfg
  for neg in POS NEG_SWAP NEG_LAT; do
    def=""; [ $neg != POS ] && def="-D$neg"
    iverilog -g2012 $def -Ptb.N=$1 -Ptb.W=$2 -o $T/tb $D/tb_lane_ser_eq.sv $R/ot_lane_ser.sv $R/ot_lane_deser.sv || { rc=1; continue; }
    out=$(vvp -n $T/tb | grep -E "^(PASS|FAIL)" | tail -1); echo "N=$1 W=$2 $neg: $out"
    if [ $neg = POS ]; then [[ $out == PASS* ]] || rc=1; else [[ $out == FAIL* ]] || rc=1; fi
  done
done
rm -rf $T; echo "bench rc=$rc"; exit $rc
