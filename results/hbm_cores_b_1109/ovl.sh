#!/bin/bash
cd /
set -eu
R=$(readlink -f /srv/opentallas-scratch2/claude/kw35/src_e2rd)
O=/srv/opentallas-scratch3/claude/kv-types-6/src_rs
W=/srv/opentallas-scratch2/claude/kv-types-6/wt
test -L $O && { echo O_IS_LINK; exit 2; }
ls $O/physical/die_plan/qwen_kvsys/plan_of_record/sink_bins/kv3_pv_v2.json
rm -f $O/tools/die_plan/reset_tree.py
python3 -I - "$R/tools/die_plan/reset_tree.py" "$O/tools/die_plan/reset_tree.py" "$W/tools/die_plan/reset_tree.py" <<'PY'
import sys,re
src,out,mine=sys.argv[1:4]
s=open(src).read(); m=open(mine).read()
a='''                 type=tn, start=start_broadcast(P), relay_driver=bool(P.reset.get("relay_driver")))\n'''
assert s.count(a)==1
add1='''        raw_used = start_raw_requests(P.types[tn])\n        if raw_used:\n            T["start_raw_used"] = raw_used\n'''
assert add1 in m
s=s.replace(a,a+add1)
b='''    used = {raw(r["d"]) for r in T["relays"]} | {f"rr_t{i}" for i in outs}\n'''
assert s.count(b)==1
add2='''    used |= set(T.get("start_raw_used", ()))     # plan START stages that name a raw wavefront tap (mission types)\n'''
assert add2 in m
s=s.replace(b,b+add2)
i=m.index('def start_raw_requests(t):'); j=m.index('def start_relays(T):')
c='def start_relays(T):\n'
assert s.count(c)==1
s=s.replace(c,m[i:j]+c)
open(out,'w').write(s)
PY
for f in kv_start_corridor_event.py start_obstacle_path.py; do rm -f $O/tools/die_plan/$f; cp $W/tools/die_plan/$f $O/tools/die_plan/$f; done
python3 -I -B -c "import ast,sys;ast.parse(open('$O/tools/die_plan/reset_tree.py').read());print('ok')"
stat -c '%h %n' $O/tools/die_plan/reset_tree.py $O/tools/die_plan/bind.py
diff <(sed -n 1,1p $R/tools/die_plan/reset_tree.py) <(sed -n 1,1p $O/tools/die_plan/reset_tree.py) && diff $R/tools/die_plan/reset_tree.py $O/tools/die_plan/reset_tree.py | grep -c '^[<>]'
sed -i 's#^cd \$W$#cd $O#; s#python3 -I -B tools/die_plan/kv_start_corridor_event.py#python3 -I -B $O/tools/die_plan/kv_start_corridor_event.py#g' /srv/opentallas-scratch2/claude/kv-types-6/pv/chain.sh
grep -n 'cd \$O\|cd \$W\|kv_start_corridor' /srv/opentallas-scratch2/claude/kv-types-6/pv/chain.sh | cut -c1-110
