#!/usr/bin/env bash
# PL-GUNIT (10-18): GUNIT_GATE (test/run_gunit_bench.sh sources, tb_dsdv_gunit.sv vs tools/hdc_golden_v41) on the LANDED
# parent: dsdv_gunit.sv is replaced by dsdv_gunit_x.sv + landed/dsdv_gunit_lp.sv + ot_pl_land.sv + the name wrapper.
# MUT 0 only (the leaf mutants need the soft leaves' MUT, which the hardened parent does not carry; they are the flat bench's).
# Prints GUNIT_LP PASS/FAIL with the router / HC latencies (compare with the flat bench: router 38 / HC 748).
# usage: run_gunit_lp_bench.sh [workdir] [cases] [scomp]   (run on the FLEET; scomp = GUNIT_LP_SCOMP, default 3)
set -u
U=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$U/../../../.." && pwd)
T=${1:-$(mktemp -d)}; N=${2:-8}; SCOMP=${3:-3}; mkdir -p "$T"
eval "$(sed -n '/^SRC="/,/"$/p' "$U/test/run_gunit_bench.sh")"
# STW-S81-COLLA-GUNIT 10-21: the bound native-32 L5 configuration (same defaults as run_gunit_bench.sh)
GUNIT_L5_DEFS="-DOT_S81_GUNIT_PIN_COPY=${GUNIT_PIN_COPY:-1} -DOT_S81_GUNIT_CONTROL_SAFE=${GUNIT_CONTROL_SAFE:-1} -DOT_S81_GUNIT_Q4=${GUNIT_Q4:-1} -DOT_S81_GUNIT_FANOUT_SAFE=${GUNIT_FANOUT_SAFE:-1} -DOT_S81_GUNIT_NAT32=${GUNIT_NAT32:-1} ${GUNIT_DEFS--DOT_S81_VE_LOADSAFE5}"
SRC=$(echo $SRC | sed 's#rtl/dsrom_sys/s81_dv/unit/dsdv_gunit.sv#rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_x.sv rtl/dsrom_sys/s81_dv/unit/landed/dsdv_gunit_lp.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv rtl/dsrom_sys/s81_dv/unit/landed/dsdv_gunit_lpwrap.sv#')
python3 -I "$U/test/gunit_vectors.py" "$T/gv.hex" "$N" 1017 || { echo "GUNIT_LP FAIL vectors"; exit 1; }
( cd "$T" && verilator --cc --exe --build -j 6 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DMUT=0 -DGUNIT_LP_SCOMP=$SCOMP $GUNIT_L5_DEFS \
    --top-module tb_dsdv_gunit -Mdir obj0 $(for f in $SRC; do echo "$R/$f"; done) "$U/test/tb_dsdv_gunit.cpp" \
    -CFLAGS -O1 > build0.log 2>&1 ) || { echo "GUNIT_LP FAIL build"; tail -20 "$T/build0.log"; exit 1; }
out=$(cd "$T" && ./obj0/Vtb_dsdv_gunit +N=$N +SEED=7 | tee run0.log | grep -E '^(GUNIT|ERR)' | head -12); echo "$out"
echo "$out" | grep -q '^GUNIT PASS' && { echo "GUNIT_LP PASS (landed parent, $N golden cases, S-side compensation $SCOMP)"; exit 0; }
echo "GUNIT_LP FAIL (S-side compensation $SCOMP)"; exit 1
