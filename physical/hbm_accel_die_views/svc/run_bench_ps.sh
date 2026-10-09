#!/bin/bash
# hbm-forks 2026-10-09: PS (per-PC stream) successor of the segmented svc.   run_bench_ps.sh <out dir> [quick]
#   lint of every PS segment master (yosys, check -assert);
#   sim_ps_SW / sim_ps_NE   legacy traffic + 12 per-PC streams (KV no-credit, IK credited) on the PS segments: PASS
#   ls_SW / ls_NE           CF-1: PS segments in LOCKSTEP with the legacy segments on legacy traffic (no streams): PASS
#   neg_slot                mutant: the sector slot ignores the row's bank XOR (beat order) -> must FAIL
#   neg_done                mutant: a PC reports done without its sectors -> must FAIL
#   neg_pc                  mutant: PC collapse (only PC 0 streams; I2 lane-drop) -> must FAIL
# (run from the source snapshot root)
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/svc; T=$V/tb
rm -f $O/summary.txt
# PS modules get a _ps suffix so the legacy segments can share one simulation (lockstep)
mkdir -p $O/ps
for f in $V/rtl/seg_ps/*.sv; do
  sed -E 's/\b(hfd_svc_(SW|SE)_s[0-9]+)\b/\1_ps/g; s/\b(hfd_svc_(SW|SE|NW|NE)_seg)\b/\1_ps/g' $f > $O/ps/$(basename $f .sv)_ps.sv
done
LIB="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv"
PSLIB=$V/rtl/ot_hbm_svc_ps_lib.sv
rc=0
if [ "${2:-}" != quick ] && command -v yosys >/dev/null; then
  for f in $V/rtl/seg_ps/hfd_svc_S[WE]_s[0-9].sv; do
    m=$(basename $f .sv)
    yosys -q -p "read_verilog -sv $LIB $PSLIB $f; hierarchy -check -top $m; proc; flatten; opt_clean; check -assert" > $O/lint_$m.log 2>&1
    r=$?; echo "lint_$m rc=$r" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
  done
fi
sim() {   # sim <label> <st> <fam> <ps lib file> <defines...>
  local L=$1 S=$2 F=$3 PL=$4; shift 4
  iverilog -g2012 "$@" -o $O/$L.vvp -I $T -s tb_svc_ps_$S $LIB $PL $O/ps/hfd_svc_${F}_s[0-9]_ps.sv $O/ps/hfd_svc_${S}_seg_ps.sv \
    $V/rtl/seg/hfd_svc_${F}_s[0-9].sv $V/rtl/seg/hfd_svc_${S}_seg.sv $T/tb_svc_physide.sv $T/tb_svc_ps_$S.sv > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
  vvp -n $O/$L.vvp > $O/$L.log 2>&1
}
for st in SW:SW NE:SE; do
  s=${st%:*}; f=${st#*:}
  sim sim_ps_$s $s $f $PSLIB -DPS_STREAMS; r=$?
  echo "sim_ps_$s rc=$r $(grep SVC_BENCH $O/sim_ps_$s.log | tail -1)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
  sim ls_$s $s $f $PSLIB -DLOCKSTEP; r=$?
  echo "ls_$s rc=$r $(grep SVC_BENCH $O/ls_$s.log | tail -1)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
sed 's/wire \[1:0\] slot = bb_r\[1:0\] ^ rr\[1:0\];/wire [1:0] slot = bb_r[1:0];/' $PSLIB > $O/ps_mut_slot.sv
cmp -s $O/ps_mut_slot.sv $PSLIB && { echo "slot mutant not applied" >> $O/summary.txt; rc=1; }
sim neg_slot SW SW $O/ps_mut_slot.sv -DPS_STREAMS; r=$?
echo "neg_slot rc=$r (must be nonzero) $(grep SVC_BENCH $O/neg_slot.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
sed 's/&& pdone && !di_v;/\&\& !di_v;/' $PSLIB > $O/ps_mut_done.sv
cmp -s $O/ps_mut_done.sv $PSLIB && { echo "done mutant not applied" >> $O/summary.txt; rc=1; }
sim neg_done SW SW $O/ps_mut_done.sv -DPS_STREAMS; r=$?
echo "neg_done rc=$r (must be nonzero) $(grep SVC_BENCH $O/neg_done.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
# PC-collapse negative (CF-SVC; Codex I2's lane-drop check folded in): only PC 0 of each stack streams
sed 's/mine <= di_d\[PCID\]; act <= di_d\[PCID\];/mine <= di_d[PCID] \&\& PCID == 0; act <= di_d[PCID] \&\& PCID == 0;/' $PSLIB > $O/ps_mut_pc.sv
cmp -s $O/ps_mut_pc.sv $PSLIB && { echo "pc mutant not applied" >> $O/summary.txt; rc=1; }
sim neg_pc SW SW $O/ps_mut_pc.sv -DPS_STREAMS; r=$?
echo "neg_pc rc=$r (must be nonzero) $(grep SVC_BENCH $O/neg_pc.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
echo "overall rc=$rc" >> $O/summary.txt; cat $O/summary.txt; exit $rc
