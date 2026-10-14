#!/bin/bash
# run_coll_xc_gate.sh <src root> <out dir>: exact gate of dsfd_coll_xc (collective die-client adapter, F2): base PASS
# (two seeds, two ts delays), mutants 1 (y word order) / 2 (hop-in drop) / 3 (host credits lost) FAIL; then a full-RTL
# lint of the collective die master dsfd_sp_collective_c with the adapter.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH   # the fleet Verilator (5.050), not the host default
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv $SRC/rtl/dsrom_sys/s81_ph/coll/dsfd_coll_xc.sv $SRC/rtl/dsrom_sys/s81_ph/coll/test/tb_dsfd_coll_xc.sv"
v=PASS
run() { l=$1; want=$2; shift 2
  verilator --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_dsfd_coll_xc "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 \
    || { echo "$l BUILD_FAIL"; tail -5 $OUT/build_$l.log; v=FAIL; return; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; r=$(grep TB_DSFD_COLL_XC $OUT/run_$l.log | tail -1); echo "$l: $r (want $want)"
  case "$r" in *" $want") ;; *) v=FAIL; grep -m5 ERR $OUT/run_$l.log;; esac
}
run base PASS
run base_s2 PASS -GSEED=7 -GDTS=7
run slowhc PASS -GSEED=3 -GDTS=7 -GHCSLOW=1
run mut1 FAIL -GMUT=1
run mut2 FAIL -GMUT=2
run mut3 FAIL -GMUT=3
if [ "${LINT:-1}" = 1 ]; then
  FL=$(cd $SRC && python3 tools/die_port_bind.py none -f physical/s81_die_rtl/layer1.f --closure dsfd_sp_collective_c | tr '\n' ' ')
  verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH +define+OT_S81PH_COLL_JOB --top-module dsfd_sp_collective_c $FL > $OUT/lint_coll_c.log 2>&1 \
    && echo "dsfd_sp_collective_c full-RTL lint PASS" || { echo "dsfd_sp_collective_c lint FAIL"; grep -m5 Error $OUT/lint_coll_c.log; v=FAIL; }
fi
echo "COLL_XC_GATE $v"; [ $v = PASS ]
