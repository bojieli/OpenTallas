#!/bin/bash
# run_host_c_gate.sh <src root> <out dir>: F6 gate of dsfd_host_c (layer-die host master): base PASS, MUT 1 / 2 FAIL.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH   # the fleet Verilator (5.050), not the host default
SRC=$1; OUT=$2; mkdir -p $OUT
F=$(cd $SRC && python3 tools/die_port_bind.py none --closure dsfd_host_c | tr '\n' ' ')
run() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT --top-module tb_dsfd_host_c "$@" --Mdir $OUT/$l -o tb $F $SRC/rtl/dsrom_sys/s81_ingest/test/tb_dsfd_host_c.sv > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; return 2; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; grep TB_DSFD_HOST_C $OUT/run_$l.log | tail -1
}
a=$(run base); echo "$a"; m1=$(run mut1 -GMUT=1); echo "$m1"; m2=$(run mut2 -GMUT=2); echo "$m2"
v=PASS
case "$a" in *" PASS") ;; *) v=FAIL;; esac
case "$m1" in *" FAIL") ;; *) v=FAIL;; esac
case "$m2" in *" FAIL") ;; *) v=FAIL;; esac
echo "HOST_C_GATE $v"; [ $v = PASS ]
