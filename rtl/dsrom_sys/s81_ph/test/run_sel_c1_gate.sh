#!/bin/bash
# run_sel_c1_gate.sh <src root> <out dir>: F5 selector gate: dsfd_bk_selector_c1 (1-stack die master: SW lane + absent
# quarters synthesised empty) word-for-word against the 4-lane reference dsfd_bk_selector fed with explicit empty
# quarters (2 seeds PASS); MUT 1 (synthesised qslot collides with SW) FAIL.
set -u
# 3rd arg 'mut': run only the MUT 1 build expecting PASS (a closure-loop expect=fail bench).
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
SRC=$1; OUT=$2; mkdir -p $OUT
FL=$(cd $SRC && python3 tools/die_port_bind.py none -f physical/s81_die_rtl/layer1.f --closure dsfd_bk_selector_c1 | tr '\n' ' ')
v=PASS
run() { l=$1; want=$2; shift 2
  verilator --binary -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_sel_c1 "$@" --Mdir $OUT/$l -o tb $FL $SRC/rtl/dsrom_sys/s81_ph/test/tb_sel_c1.sv > $OUT/build_$l.log 2>&1 \
    || { echo "$l BUILD_FAIL"; grep -m3 Error $OUT/build_$l.log; v=FAIL; return; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1; r=$(grep TB_SEL_C1 $OUT/run_$l.log | tail -1); echo "$l: $r (want $want)"
  case "$r" in *" $want") ;; *) v=FAIL; grep -m3 ERR $OUT/run_$l.log;; esac
}
if [ "${3:-}" = mut ]; then
  # negative-control job bench: the MUT 1 (qslot collision) build judged as a positive -> must FAIL
  run mut1 PASS -GMUT=1
else
run base PASS
run base2 PASS -GSEED=21
run mut1 FAIL -GMUT=1
fi
echo "SEL_C1_GATE $v"; [ $v = PASS ]
