#!/bin/bash
# DIE-QC-59Q cseq proof bench: REF = ot_qwen_d2d_cal_seq + non-OVL qfd_d2d_static (kvs_compute_end form, EP_SKEW 0);
# DUT = wrapper input reg -> qfd_sysface_cseq_single -> wrapper output reg -> bindC as-built ot_dp_dly landings -> OVL master.
# pass / pass_e2 must print VERDICT PASS; pad0 / skew0 are mutants and must FAIL.
set -e
S=$(cd $(dirname $0) && pwd); W=${W:-$(git -C $S rev-parse --show-toplevel)}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd $W
for v in pass pad0 skew0; do
  def=""; [ $v = pad0 ] && def="+define+MUT_PAD0"; [ $v = skew0 ] && def="+define+MUT_SKEW0"
  $VL --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Irtl/qwen_sys/d2d_static_20261015 --top-module tb_qc59q $def -f $S/files.f -Mdir $S/obj_$v -o vtb >/dev/null 2>$S/build_$v.log &
done
wait
cd $S
( ./obj_pass/vtb +NC=640000 > run_pass.log 2>&1 ) &
( ./obj_pass/vtb +NC=960000 +E2=650000 > run_pass_e2.log 2>&1 ) &
( ./obj_pad0/vtb +NC=640000 > run_pad0.log 2>&1 ) &
( ./obj_skew0/vtb +NC=640000 > run_skew0.log 2>&1 ) &
wait
grep -H -E "RESULT|VERDICT|^CAL " run_*.log
