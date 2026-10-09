#!/bin/bash
# old vs new ctl_stop on the multi-step transaction bench; PASS iff every case's TX log is identical and non-trivial
set -u
WT=$(cd "$(dirname "$0")/../../../.." && pwd)
D=/tmp/claude-1000/hfdpipe/ms; rm -rf $D; mkdir -p $D
git -C $WT show origin/main:rtl/hbm_accel/control/ot_dshbm_dspark_ctl_stop.sv > $D/ctl_old.sv
cp $WT/rtl/hbm_accel/control/ot_dshbm_dspark_ctl_stop.sv $D/ctl_new.sv
COMMON="$WT/rtl/hdc/ot_hdc_prefix.sv $WT/rtl/hdc/ot_hdc_accept.sv $WT/rtl/gpu/dshbm/ot_dshbm_accept_port.sv $WT/rtl/test/hbm_accel/tb_ctl_stop_multistep.sv"
ok=1
for c in "40 0 103 1048576 0 1" "40 0 103 1048576 2 1" "40 1 113 1048576 0 1" "60 0 103 17 0 1" "60 0 103 23 2 1" "20 1 102 1048576 0 1" "6 0 103 1048576 0 1" "40 0 103 1048576 0 0" "60 0 103 19 2 0" "40 1 104 1048576 0 0"; do
  set -- $c; tag="ngen$1_eos$2-$3_mp$4_prl$5_f$6"
  for v in old new; do
    iverilog -g2012 -s tb_ctl_stop_multistep -Ptb_ctl_stop_multistep.NGEN=$1 -Ptb_ctl_stop_multistep.EOS_EN=$2 \
      -Ptb_ctl_stop_multistep.EOS=$3 -Ptb_ctl_stop_multistep.MAXPOS_CFG=$4 -Ptb_ctl_stop_multistep.PRL=$5 -Ptb_ctl_stop_multistep.FORCE=$6 \
      -o $D/$tag.$v.vvp $D/ctl_$v.sv $COMMON || { echo "COMPILE FAIL $tag $v"; ok=0; continue; }
    vvp -n $D/$tag.$v.vvp > $D/$tag.$v.log 2>&1
    grep '^TX' $D/$tag.$v.log > $D/$tag.$v.tx
  done
  steps=$(grep -c '^TX STEP' $D/$tag.new.tx); ems=$(grep -c '^TX EMIT' $D/$tag.new.tx)
  co=$(grep '^CYCLES' $D/$tag.old.log | awk '{print $2}'); cn=$(grep '^CYCLES' $D/$tag.new.log | awk '{print $2}')
  err=$(grep -ci 'error\|fatal' $D/$tag.new.log)
  if cmp -s $D/$tag.old.tx $D/$tag.new.tx && [ "$steps" -ge 1 ] && [ "$err" = 0 ]; then r=SAME; else r=DIFF; ok=0; fi
  echo "$tag $r steps=$steps emits=$ems cycles_old=$co cycles_new=$cn delta=$((cn-co)) errors=$err $(tail -1 $D/$tag.new.tx)"
done
[ $ok = 1 ] && echo "MULTISTEP_EQUIV PASS" || echo "MULTISTEP_EQUIV FAIL"
