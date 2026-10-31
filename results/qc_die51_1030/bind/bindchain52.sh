#!/bin/bash
# DIE-QC-51: DIE-QC-33 canonical bind regen chain on plan_qc52 (latency already regenerated in the plan; sidecar
# collector re-synced for the 87 event-changed slice types).  probe -> R8 regen -> base -> CB16 regen -> final --strict
set -u
R=/srv/opentallas-scratch2/claude/die-qc-51/bc52; W=/srv/opentallas-scratch2/claude/wt/die-qc-51
D=results/qc_die51_1030/bind; Q=results/qc_die33_1029/bind
cd $W; mkdir -p $D $R
S=$R/status; say(){ echo "$* $(date)" | tee -a $S; }
P=physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json
say "START tree $(git rev-parse --short=10 HEAD) plan $(sha256sum $P|cut -c1-8)"
mk(){ python3 -I - "$@" <<'PY'
import json,sys
src,dst,mode,D=sys.argv[1:5]
r=json.load(open(src))
inner='results/token_pass/qc_head_loop_1029/candidate_inner.json'
r['clock_landing_table']=D+'/sidecar.json'
if mode=='probe':
    for k in ('land_align','land_r8_extra','param_regen'): r.pop(k,None)
elif mode=='base':
    r['land_r8']=D+'/r8/qwen_compute_r8_landing.json'; r['land_r8_extra']=[inner]
elif mode=='final':
    r['land_r8']=D+'/r8/qwen_compute_r8_landing.json'; r['land_r8_extra']=[D+'/cb16_pads.json',inner]
r['note']=r.get('note','')+f' | DIE-QC-51 BIND {mode} recipe on plan_qc52 (fresh R8/CB16 regen, synced collector sidecar)'
json.dump(r,open(dst,'w'),indent=1)
PY
}
for d in probe base final; do mkdir -p $R/$d; for f in asbuilt.json asbuilt_sources.json; do cp /srv/opentallas-scratch2/claude/die-qc-51/bind52/$f $R/$d/$f; done; done
run_bind(){ python3 -I tools/die_plan/bind.py bind $P --asbuilt $D/$1_asbuilt.json --out $R/$1 $2 > $R/$1.log 2>&1; local rc=$?
  say "BIND $1 $2 rc=$rc $(python3 -c "import json;r=json.load(open('$R/$1/bind_report.json'));print(r['n_errors'],[e[:160] for e in r['errors'][:6]])" 2>&1|cut -c1-1200)"; }
mk $Q/asbuilt.json $D/probe_asbuilt.json probe $D; run_bind probe ""
python3 -I tools/die_plan/gen.py latency $P --groups $R/probe/bus_groups.json --out $D/r8 > $R/r8.log 2>&1; say "2 R8 rc=$? $(tail -1 $R/r8.log|cut -c1-400)"
mk $Q/asbuilt.json $D/base_asbuilt.json base $D; run_bind base ""
python3 -I physical/die_plan/qwen_compute/bind/cb16_pads.py $R/base $D/r8/qwen_compute_r8_landing.json $D/cb16_pads.json > $R/cb16.log 2>&1; say "4 CB16 rc=$? $(tail -1 $R/cb16.log|cut -c1-300)"
mk $Q/asbuilt.json $D/final_asbuilt.json final $D; run_bind final --strict
say DONE
