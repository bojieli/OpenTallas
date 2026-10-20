#!/bin/bash
# TOKSIM-S81B/FWOA 10-19: every phase of attn.wo_a / attn.wo_b on ONE die frame (real rank-local rows the frame's slice
# owns, real K, ROM images from the released L0 fixture), release RTL (19bf4121e rtl/ + physical macros), tools origin/main.
# Frame bench (xs_bench.sh: frame _l4 successor + forwarded lanes) and xs-slice bench (xs_slice_bench.sh: real ot_s81sl_xs
# streamer + calendar ROMs, spine lockstep reference). One run per phase; per-row golden check (lower_xs.check_words).
# usage: run_frame_ops.sh TAG FRAME MASTER LK LDLY OP...
set -uo pipefail
TAG=$1 FRAME=$2 MASTER=$3 LK=$4 LDLY=$5; shift 5; OPS="$@"
D=/srv/opentallas-scratch/claude/toksim-s81b-fwoa; R=$D/root; O=$D/$TAG; rm -rf $O; mkdir -p $O; cd $R
L=tools/s81_dv/layer_prog
# frame return topology records are hash-guarded against the frame wrapper RTL: re-derive them from the RELEASE frame RTL
# (release col_h9/col_h10 differ from main only in the element RSTP parameter) and record whether the topology changed
TR=results/arch/s81_dv_1016/frame/return_plan
for m in col_h9 col_h10 col_h9_MX; do [ -f $TR/topology_$m.json ] || [ -f $TR/topology_$m.main.json ] || continue
  [ -f $TR/topology_$m.main.json ] || cp $TR/topology_$m.json $TR/topology_$m.main.json
  python3 tools/s81_dv/frame_return_plan.py topo --master $m --write > $O/topo_$m.log 2>&1 || echo "TOPO_FAIL $m"
  python3 -c "
import json;a=json.load(open('$TR/topology_$m.main.json'));b=json.load(open('$TR/topology_$m.json'))
k=[x for x in set(a)|set(b) if x not in ('rtl_sha256',) and a.get(x)!=b.get(x)];print('TOPO_RELEASE_VS_MAIN $m differs_in',k)"
done
python3 $L/xs_place.py frame --frame $FRAME --out $O/frame --fixtures $D/fixtures/L0 --die-src $D/dieref --ops $OPS > $O/frame.log 2>&1 || { echo FRAME_FAIL; tail -20 $O/frame.log; exit 2; }
tail -1 $O/frame.log
PH=$(python3 -c "
import json,sys;r=json.load(open('$O/frame/frame.json'))
print('MASTER',r['master'],'lk',r['lk'],file=sys.stderr)
print(' '.join(str(p['phase']) for p in r['phases'] if p['op'] in ('attn.wo_a','attn.wo_b') and p['rows']>0))")
echo "PHASES $PH"
python3 $L/xs_place.py gen --frame $FRAME --phase $PH --out $O/vec --fixtures $D/fixtures/L0 --die-src $D/dieref --ops $OPS > $O/gen.log 2>&1 || { echo GEN_FAIL; tail -20 $O/gen.log; }
grep XS_PLACE_GEN $O/gen.log
python3 $L/xs_place.py tie --fixtures $D/fixtures/L0 --ops $OPS > $O/tie.log 2>&1; echo "tie rc=$? $(tail -1 $O/tie.log)"
VS=""; XV=""
for p in $PH; do
  [ -f $O/vec/p$p/ARGS ] || continue; VS="$VS $O/vec/p$p"
  python3 $L/xs_calendar.py gen --vec $O/vec/p$p --out $O/xvec/p$p > $O/xvec_p$p.log 2>&1 && XV="$XV $O/xvec/p$p" || { echo "XSCAL_GEN_FAIL p$p"; tail -3 $O/xvec_p$p.log; }
done
MASTER=$MASTER LK=$LK LDLY=$LDLY J=32 bash $L/xs/xs_bench.sh $O/fb $VS
for v in $VS; do n=$(basename $v); python3 $L/xs_place.py check --dir $v --log $O/fb/run_$n.log --fixtures $D/fixtures/L0 > $O/fb/check_$n.out 2>&1; echo "FB_CHECK $n rc=$? $(tail -1 $O/fb/check_$n.out)"; done
if [ -n "$XV" ]; then
MASTER=$MASTER LK=$LK LDLY=$LDLY J=32 bash $L/xs/xs_slice_bench.sh $O/xb $XV
for v in $XV; do n=$(basename $v); python3 $L/xs_calendar.py check --dir $v --log $O/xb/run_$n.log > $O/xb/check_$n.out 2>&1; echo "XB_CHECK $n rc=$? $(tail -1 $O/xb/check_$n.out)"; done
fi
echo FWOA_DONE $TAG
