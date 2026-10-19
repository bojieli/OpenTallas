#!/bin/bash
# AD3-KV-PARENTS 10-18: qkd_seq_static_s (die slot seq) die-placed-leaf trial on a COPY of kvs14p-fa7fe4ff9 (ot-epyc5).
# Overlay: the kvs14p source tree (READ-ONLY symlinks) + this branch's tools/qwen_kv_die/kv_expand.py (SEQ_S_PLAN).
set -u
R=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14p-fa7fe4ff9
P=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14p-fa7fe4ff9
B=/srv/opentallas-scratch/claude/ad3-kvpar
T=$B/src_overlay; O=$B/seq_expand_trial
rm -rf $T $O; mkdir -p $T $O
lnall() { local src=$1 dst=$2; shift 2; mkdir -p $dst; for e in $src/* $src/.[!.]*; do [ -e "$e" ] || continue; n=$(basename $e); case " $* " in *" $n "*) mkdir -p $dst/$n;; *) ln -s $e $dst/$n;; esac; done; }
lnall $P $T tools physical
lnall $P/physical $T/physical ref_tile
lnall $P/physical/ref_tile $T/physical/ref_tile qkd_seq_core_st_s qkd_seq_xs_s qkd_seq_fan_s
rmdir $T/physical/ref_tile/qkd_seq_core_st_s $T/physical/ref_tile/qkd_seq_xs_s $T/physical/ref_tile/qkd_seq_fan_s
tar -xzf $B/seqviews.tgz -C $T   # the 3 CLOSED leaf views (main; the kvs14p tree predates them)
lnall $P/tools $T/tools qwen_kv_die
lnall $P/tools/qwen_kv_die $T/tools/qwen_kv_die kv_expand.py; rmdir $T/tools/qwen_kv_die/kv_expand.py
cp $B/kv_expand.py $T/tools/qwen_kv_die/kv_expand.py
cp -a $R/case_kv $R/libs $R/kv_flags.env $O/
for f in $R/*.json; do cp -a $f $O/; done; rm -f $O/expand.json
cd $T || exit 2
export PYTHONDONTWRITEBYTECODE=1
set -a; . $O/kv_flags.env; set +a
echo "SEQ TRIAL start $(date) kv_expand sha $(sha256sum tools/qwen_kv_die/kv_expand.py | cut -c1-12)"
python3 -c "import sys; sys.path[:0]=['tools','tools/qwen_kv_die']; import kv_die as K; b=K.BINDINGS.get('qkd_seq_st'); print('BINDING qkd_seq_st', b and b['module'], b and b['file'])"
python3 tools/qwen_kv_die/kv_expand.py --run $O --only qkd_seq_st > $O/expand_seq.log 2>&1; rc=$?
echo "EXPAND rc=$rc"; tail -20 $O/expand_seq.log
[ -f $O/expand.json ] && python3 -c "import json;d=json.load(open('$O/expand.json'));print(json.dumps(d['frames']));print(json.dumps(d['leaves']))"
grep -n "findInst seq__" $O/case_kv/place.tcl
