#!/bin/bash
# KV-BIND6 10-20: replay of the d5p diagnostic case (Codex copy, 54e9d9c39 + ledger) from its PRE-HEALTH netlist with the
# abbb4391c tools: health install (transport nets n_hpt_*) + strict port bind v2. Diagnostic only, not a die result.
set -euo pipefail
X=/srv/opentallas-scratch/claude/kv-bind6-1020/replay
SRC=/srv/opentallas-scratch/claude/ref_gate/codex_health_parameters_1020/actual_d5p/diagnostic_run
S=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-abbb4391c-gen9d7p
for i in $(seq 60); do [ -f $S/tools/qwen_kv_die/kv_health_plane.py ] && break; sleep 10; done
rm -rf $X/run; mkdir -p $X; cp -a $SRC $X/run; R=$X/run
rm -rf $R/port_bind_v2
for f in die.v place.tcl elements.lef die.v.pads.json; do cp $R/case_kv/$f.prehealth $R/case_kv/$f; done
python3 - $R <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1])
p=r/'case_kv/die.v.params.json'; d=json.loads(p.read_text()); n=len(d)
d={k:v for k,v in d.items() if not k.startswith('hp_')}; p.write_text(json.dumps(d,indent=1)+'\n')
e=r/'expand.json'; j=json.loads(e.read_text()); pi=j.get('parameter_instances',{}); m=len(pi)
j['parameter_instances']={k:v for k,v in pi.items() if not k.startswith('hp_')}; e.write_text(json.dumps(j,indent=1)+'\n')
print('stripped hp_ rows params',n-len(d),'expand',m-len(j['parameter_instances']))
PY
set -a; . $R/kv_flags.env; set +a
export PYTHONDONTWRITEBYTECODE=1 OT_KV_PARAM_DIAG=1 OT_BIND_DIAGNOSTIC=1
cd $S
python3 tools/qwen_kv_die/kv_health_plane.py install --run $R > $R/health_plane.log 2>&1 || { tail -5 $R/health_plane.log; exit 11; }
grep '^KV_HEALTH' $R/health_plane.log | cut -c1-600
grep -c 'n_hpt_' $R/case_kv/die.v || true
bash tools/qwen_kv_die/kv_port_bind_v2.sh $R/case_kv/die.v $R/port_bind_v2 $R/case_kv/qkd_kv_relays.sv $R/expand.json > $R/port_bind_v2.log 2>&1 || true
tail -n 5 $R/port_bind_v2.log
