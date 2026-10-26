#!/bin/bash
# qwendie-1011: rule-H1 padded die STA after die_chain.sh (pads sized from the FF hold report, x PAD_SCALE at TT).
# usage: pad_chain.sh <die: kv|r22k> <run dir>   (sta_<die>_{ff,tt} done; writes sta_<die>_{ff,tt}_pad + STATUS.log lines)
set -u
DIE=$1; R=$(readlink -f $2)
H=$(dirname $(readlink -f $0))
ADMIT=/srv/opentallas-scratch/admit.sh
case $DIE in kv) P4=40;; r22k) P4=110;; *) echo bad die; exit 2;; esac
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
E=$R/sta_${DIE}_ff/grt_ff_ends.rpt
[ -s $E ] || { say "PAD: no $E"; exit 1; }
python3 $H/pad_from_ends.py $E --out $R/pads_ff.json --summary $R/pads_ff_summary.json > /dev/null
say "PAD: $(python3 -c "import json;s=json.load(open('$R/pads_ff_summary.json'));print('violators',s['endpoints_violated'],'pads',s['pads'],'over_cap',s['over_cap_n'])")"
for c in ff tt; do S=$R/sta_${DIE}_$c; D=$R/sta_${DIE}_${c}_pad; mkdir -p $D/libs
  ln -f $S/ckpt_grt.odb $S/die_grt.spef $D/; cp $S/libs/* $D/libs/; [ -f $S/clock_lat_$c.tcl ] && cp $S/clock_lat_$c.tcl $D/
  python3 $H/pad_sta.py $S/grt_$c.tcl $R/pads_ff.json $c $D/grt_$c.tcl
  $ADMIT $P4 -- $H/dietop_run.sh $D grt_$c.tcl 8 $((P4+60))
  say "STA $c pad: $(grep -E 'OT_CLOCK_PLAN|OT_HOLD_PADS|^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')"
done
say "pad chain done"
