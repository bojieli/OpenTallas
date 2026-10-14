#!/bin/bash
# run_wfc_hop_ep_gate.sh <src root> <out dir>: exact gate of dsfd_wfc_hop_ep (F4 hop engine at the WFC stage kit):
# base (2 seeds) PASS, MUT 6 (done at the descriptor) FAIL; full-RTL lint of the die kit master (cluster under the die
# name dsfd_wfc_stg).
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
SRC=$1; OUT=$2; mkdir -p $OUT
EP=$(cd $SRC && python3 tools/die_port_bind.py none --closure ot_s81_slab_ep | tr '\n' ' ')
F="$EP $SRC/rtl/dsrom_sys/mtp/dsfd_wfc_stg_cl.sv $SRC/rtl/dsrom_sys/mtp/test/tb_dsfd_wfc_hop_ep.sv"
v=PASS
run() { l=$1; want=$2; shift 2
  verilator --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_dsfd_wfc_hop_ep "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 \
    || { echo "$l BUILD_FAIL"; grep -m3 Error $OUT/build_$l.log; v=FAIL; return; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; r=$(grep TB_DSFD_WFC_HOP_EP $OUT/run_$l.log | tail -1); echo "$l: $r (want $want)"
  case "$r" in *" $want") ;; *) v=FAIL;; esac
}
run base PASS
run base2 PASS -GSEED=9
run mut6 FAIL -GMUT=6
FL=$(cd $SRC && python3 tools/die_port_bind.py none -f physical/s81_die_rtl/layer1.f --closure dsfd_wfc_stg | tr '\n' ' ')
verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH +define+DSFD_WFC_STG_CL_DIE --top-module dsfd_wfc_stg $FL > $OUT/lint_kit.log 2>&1 \
  && echo "dsfd_wfc_stg (die cluster) full-RTL lint PASS" || { echo "kit lint FAIL"; grep -m5 Error $OUT/lint_kit.log; v=FAIL; }
echo "WFC_HOP_EP_GATE $v"; [ $v = PASS ]
