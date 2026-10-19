#!/bin/bash
# OWN-QWEN/KV-PARENTS 10-18: trial expansion of the PV pair frames (qkd_pvw_s/n = qkd_pvw_die_t) into the kvs14p die
# netlist on a COPY of the kvs14p-fa7fe4ff9 run (read-only use of its source tree; no git).  Question: can the die be the
# parent of qkd_pvw_die_t (kv_expand frames qkd_pvw_s/n), with every leaf bound to a closed view and the real ctl_t view
# (OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95 = the AGE-96 a96 closure f0be3773d) instead of the stand-in?
set -u
R=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14p-fa7fe4ff9
S=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14p-fa7fe4ff9
O=/srv/opentallas-scratch/claude/ownq-kvpar/pvw_expand_trial
rm -rf $O; mkdir -p $O
cp -a $R/case_kv $R/libs $R/kv_flags.env $O/ 2>/dev/null
for f in $R/*.json; do cp -a $f $O/; done
rm -f $O/static_bind.json
# restore the pre-expansion netlist / place / lef: expand appends to them; start from the frames-as-run state
cd $S || exit 2
export PYTHONDONTWRITEBYTECODE=1
set -a; . $O/kv_flags.env; set +a
export OT_KV_PV_T_CTL_KIT=qkd_pv_ctl_t_d54f58a95
echo "TRIAL start $(date) src=$(cat $O/case_kv/SOURCE_COMMIT 2>/dev/null) PV_T=${OT_KV_PV_T:-} CTL_KIT=$OT_KV_PV_T_CTL_KIT STANDIN=${OT_KV_PV_T_CTL_STANDIN:-}"
grep -c "" $O/case_kv/die.v
python3 tools/qwen_kv_die/kv_expand.py --run $O --only qkd_pvw_s,qkd_pvw_n > $O/expand_pvw.log 2>&1; rc=$?
echo "EXPAND rc=$rc"; tail -40 $O/expand_pvw.log
ls -la $O/standin 2>/dev/null
python3 - $O <<'PY'
import json,sys,os
p=os.path.join(sys.argv[1],'expand.json')
if os.path.exists(p):
    d=json.load(open(p)); print('EXPAND_JSON keys', list(d)[:20])
    for k in ('qkd_pvw_s','qkd_pvw_n','standin','open_inputs'):
        if k in d: print(k, json.dumps(d[k])[:1500])
PY
