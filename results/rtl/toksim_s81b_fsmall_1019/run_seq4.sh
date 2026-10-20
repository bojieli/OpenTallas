#!/bin/bash
# TOKSIM-S81B/FSMALL 10-19: tb_toksim_fgu_seq ties the spine's return port (r_v 0): no op ever retires, so its 4 op tags
# fill and the 5th go waits forever (GO_LATE, hang; same cause as FGU's experts_gu 24-phase NO_END).  Bench limit, not
# RTL.  This runs the first <=4 phases of the op's sequence (no retirement needed) swept over the go period.
# usage: run_seq4.sh <layer> <frame> <op tail> ["PERS"]
set -u
R=/srv/opentallas-scratch/claude/toksim-s81b-fsmall; L=$1; F=$2; T_=$3; PERS=${4:-"600 400 300 260 220 200 180 160 140"}
V=$R/vec/$L/$F; O=$R/run/$L/$F/seq4_$T_; mkdir -p $O; Q=tools/s81_dv/layer_prog/qf_producer
case $F in u_f_?L00|u_f_?R00) B=s_h9nx_e5;; u_f_?L01|u_f_?R01) B=s_h10_e2;; u_f_?L02|u_f_?R02) B=s_h9MX_e1;; u_f_?L03|u_f_?R03) B=s_h9nx_e2;; esac
X=$R/$B/obj/Vtb_toksim_fgu_seq; cd $R/src
S=$V/seq4_$T_; rm -rf $S; cp -r $V/seq_$T_ $S; head -n 4 $V/seq_$T_/seq.hex > $S/seq.hex
python3 -c "import json;d=json.load(open('$S/seq.json'));[d.__setitem__(k,d[k][:4]) for k in ('phases','rows','vectors')];json.dump(d,open('$S/seq.json','w'))"
read NPH K OPS PH0 < <(python3 -c "import json;d=json.load(open('$S/seq.json'));print(len(d['phases']),d['K'],max(d['rows']),d['phases'][0])")
REF=$(zcat -f $R/run/$L/$F/run_p$PH0.log* 2>/dev/null | grep -m1 -oP '^GO 0 \K\d+'); REF=${REF:-63}
for P in $PERS; do
  timeout 600 stdbuf -oL $X +OT_ROM_DIR=$S +T=1200 +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P > $O/run_seq_P$P.log 2>&1
  echo "FSMALL_SEQ4 $L $F $T_ $(python3 $Q/toksim_fgu_check.py seq --seq $S --vec $V --log $O/run_seq_P$P.log --out $O/res_seq_P$P.json --per $P --ref-go $REF 2>&1 | tail -1)"
done
gzip -f $O/run_*.log; echo FSMALL_SEQ4_DONE $L $F
