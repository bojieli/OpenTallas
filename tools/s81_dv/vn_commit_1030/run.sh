#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030/inventory_vn.json')
r=json.loads(p.read_text());groups={}
def num(v):
 s=str(v)
 if "'"in s:
  w,b=s.split("'",1);return int(b[1:],{'b':2,'d':10,'h':16,'o':8}[b[0]])
 return int(s)
for n,u in r['units'].items():
 if u['master']not in('ot_s81sl_vn_a','ot_s81sl_vn_b'):continue
 expected=dict(LM=5,LA=6)
 if u['master']=='ot_s81sl_vn_b':expected['HW_STAGE']=0
 actual={k:num(u.get('params',{}).get(k,v))for k,v in expected.items()}
 if actual!=expected:raise ValueError('current VN parameter differs: '+n+str(actual))
 groups[u['master']]=groups.get(u['master'],0)+1
assert groups=={'ot_s81sl_vn_a':80,'ot_s81sl_vn_b':80},groups
print('ACTUAL_VN_PARAMS',groups,'LM5 LA6 HW_STAGE0')
PY
rc=$?;if [ "$rc" -ne 0 ];then exit "$rc";fi
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_vn_commit --Mdir obj -f defines.f -f source.f tb_vn_commit.sv >build.log 2>&1
rc=$?;echo BUILD_RC=$rc >>status.txt
if [ "$rc" -ne 0 ];then tail -15 build.log;exit "$rc";fi
obj/Vtb_vn_commit >base.log 2>&1
rc=$?;echo BASE_RC=$rc >>status.txt
obj/Vtb_vn_commit +bad_payload >payload.log 2>&1
p=$?;echo PAYLOAD_RC=$p >>status.txt
obj/Vtb_vn_commit +bad_age >age.log 2>&1
a=$?;echo AGE_RC=$a >>status.txt
cat status.txt
if [ "$rc" -eq 0 ]&&[ "$p" -ne 0 ]&&[ "$a" -ne 0 ];then echo GATE_PASS >>status.txt;else exit 1;fi
