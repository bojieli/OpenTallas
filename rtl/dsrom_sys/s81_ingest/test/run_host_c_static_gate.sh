#!/bin/bash
# run_host_c_static_gate.sh <src root> <out dir>: S-BIND r6 gate of the STATIC layer-die host dsfd_host_c
# (+DSFD_HOST_C_STATIC: no credit bits, f_collective 515 / t_collective 77, lane faults f_lf): base PASS, MUT 1 / 4 FAIL.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
SRC=$1; OUT=$2; mkdir -p $OUT
F=$(cd $SRC && python3 tools/die_port_bind.py none --closure dsfd_host_c | tr '\n' ' ')
run() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +define+DSFD_HOST_C_STATIC --top-module tb_dsfd_host_c_static "$@" --Mdir $OUT/$l -o tb $F $SRC/rtl/dsrom_sys/s81_ingest/test/tb_dsfd_host_c_static.sv > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; return 2; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; grep TB_DSFD_HOST_C_STATIC $OUT/run_$l.log | tail -1
}
a=$(run base); echo "$a"; m1=$(run mut1 -GMUT=1); echo "$m1"; m4=$(run mut4 -GMUT=4); echo "$m4"
v=PASS
case "$a" in *" PASS") ;; *) v=FAIL;; esac
case "$m1" in *" FAIL") ;; *) v=FAIL;; esac
case "$m4" in *" FAIL") ;; *) v=FAIL;; esac
echo "HOST_C_STATIC_GATE $v"; [ $v = PASS ]
