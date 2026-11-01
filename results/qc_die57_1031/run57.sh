#!/bin/bash
# DIE-QC-57 BIND chain (DIE-QC-33 run.sh recipe, steps 1-5; step 0 latency done in the plan commit; elab reused):
#   S sidecar +1 (mk_sidecar57.py)  1 probe bind -> bus_groups  2 gen.py latency --groups -> fresh R8
#   3 base bind  4 cb16_pads.py -> fresh CB16  5 final strict bind
set -u
W=$1; R=$2; ELAB=$3; BASEPLAN=$4
D=results/qc_die57_1031/bind; Q=results/qc_die33_1029/bind; P=physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json
cd $W; mkdir -p $D $R
S=$R/status; say(){ echo "$* $(date)" | tee -a $S; }
say "START tree $(git rev-parse --short=10 HEAD)"
python3 -I results/qc_die57_1031/mk_sidecar57.py $Q/sidecar.json $D/sidecar.json $BASEPLAN $P > $R/sidecar.log 2>&1; say "S SIDECAR rc=$? $(tail -1 $R/sidecar.log)"
python3 -I - $Q/asbuilt.json $D/asbuilt.json $D <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); r["clock_landing_table"]=sys.argv[3]+"/sidecar.json"; json.dump(r,open(sys.argv[2],"w"),indent=1)
PY
mk(){ python3 -I - "$@" <<'PY'
import json,sys
src,dst,mode,D=sys.argv[1:5]
r=json.load(open(src))
inner='results/token_pass/qc_head_loop_1029/candidate_inner.json'
if mode=='probe':
    for k in ('land_align','land_r8_extra','param_regen'): r.pop(k,None)
elif mode=='base':
    r['land_r8']=D+'/r8/qwen_compute_r8_landing.json'; r['land_r8_extra']=[inner]
elif mode=='final':
    r['land_r8']=D+'/r8/qwen_compute_r8_landing.json'; r['land_r8_extra']=[D+'/cb16_pads.json',inner]
r['note']=r.get('note','')+f' | DIE-QC-57 BIND {mode} recipe (+1 CA cycles; fresh latency/R8/CB16 regen)'
json.dump(r,open(dst,'w'),indent=1)
PY
}
for d in probe base final; do mkdir -p $R/$d; for f in asbuilt.json asbuilt_sources.json; do cp $ELAB/$f $R/$d/$f; done; done
run_bind(){ python3 -I tools/die_plan/bind.py bind $P --asbuilt $D/$1_asbuilt.json --out $R/$1 $2 > $R/$1.log 2>&1; local rc=$?
  say "BIND $1 $2 rc=$rc $(grep -m1 '"errors"' $R/$1.log | cut -c1-300)"; }
mk $D/asbuilt.json $D/probe_asbuilt.json probe $D; run_bind probe ""
python3 -I tools/die_plan/gen.py latency $P --groups $R/probe/bus_groups.json --out $D/r8 > $R/r8.log 2>&1; say "2 R8 rc=$? $(tail -1 $R/r8.log|cut -c1-300)"
mk $D/asbuilt.json $D/base_asbuilt.json base $D; run_bind base ""
python3 -I physical/die_plan/qwen_compute/bind/cb16_pads.py $R/base $D/r8/qwen_compute_r8_landing.json $D/cb16_pads.json > $R/cb16.log 2>&1; say "4 CB16 rc=$? $(tail -1 $R/cb16.log|cut -c1-300)"
mk $D/asbuilt.json $D/final_asbuilt.json final $D; run_bind final --strict
say DONE
