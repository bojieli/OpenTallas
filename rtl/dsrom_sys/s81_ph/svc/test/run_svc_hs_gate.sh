#!/bin/bash
# run_svc_hs_gate.sh <src root> <out dir>: exact gate of dsfd_svc_hs (svc HBM-controller status face): base PASS, MUT 8 FAIL;
# plus a full-RTL elaboration (lint) of the dsfd_svc_c slab with the new hs port.
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
v=PASS
run() { l=$1; want=$2; shift 2
  verilator --binary -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsfd_svc_hs "$@" --Mdir $OUT/$l -o tb \
    $SRC/rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv $SRC/rtl/dsrom_sys/s81_ph/svc/test/tb_dsfd_svc_hs.sv > $OUT/build_$l.log 2>&1 \
    || { echo "$l BUILD_FAIL"; v=FAIL; return; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; r=$(grep TB_DSFD_SVC_HS $OUT/run_$l.log | tail -1); echo "$l: $r (want $want)"
  case "$r" in *" $want") ;; *) v=FAIL;; esac
}
run base PASS
run mut8 FAIL -GMUT=8
F=$(cd $SRC && python3 tools/die_port_bind.py none --closure dsfd_svc_c | tr '\n' ' ')
verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module dsfd_svc_c $F > $OUT/lint_svc_c.log 2>&1 \
  && echo "dsfd_svc_c full-RTL lint PASS" || { echo "dsfd_svc_c lint FAIL"; grep -m5 Error $OUT/lint_svc_c.log; v=FAIL; }
echo "SVC_HS_GATE $v"; [ $v = PASS ]
