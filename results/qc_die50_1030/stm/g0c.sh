#!/bin/bash
# DIE-QC-50/stm G0C plan_qc49 vs plan_qc51 (+ derived infra diff)
set -u
W=/srv/opentallas-scratch2/claude/wt/die-qc-50-stm; O=/srv/opentallas-scratch2/claude/die-qc-50/stm/g0c
mkdir -p $O; cd $W
PR=physical/die_plan/qwen_compute/plan_of_record
python3 tools/die_plan/check.py $PR/plan_qc49.json --completeness --out $O/p49 > $O/p49.log 2>&1 &
python3 tools/die_plan/check.py $PR/plan_qc51.json --completeness --out $O/p51 > $O/p51.log 2>&1 &
python3 results/qc_die50_1030/stm/diff_infra.py $PR/plan_qc49.json $PR/plan_qc51.json $O/diff_infra_49_51.json > $O/diff_infra.log 2>&1 &
wait
tail -2 $O/p49.log; tail -2 $O/p51.log; tail -20 $O/diff_infra.log
python3 - <<'PY'
import json
def keyset(p):
    r=json.load(open(p)); out=set()
    def walk(o):
        if isinstance(o,dict):
            if 'level' in o or 'severity' in o:
                out.add(json.dumps({k:v for k,v in o.items()},sort_keys=True))
            for v in o.values(): walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    walk(r); return r,out
O='/srv/opentallas-scratch2/claude/die-qc-50/stm/g0c'
a,A=keyset(O+'/p49/g0_report.json'); b,B=keyset(O+'/p51/g0_report.json')
print('findings p49',len(A),'p51',len(B),'new',len(B-A),'gone',len(A-B))
for x in sorted(B-A)[:15]: print('NEW',x[:400])
for x in sorted(A-B)[:15]: print('GONE',x[:400])
PY
