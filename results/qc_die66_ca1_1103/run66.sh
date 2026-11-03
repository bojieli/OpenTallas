#!/bin/bash
# DIE-QC-66/CLK CA +1 event BIND chain = DIE-QC-57 run57.sh recipe on the as-built of record (qc_die63_red_1102 final):
#   E fresh elab  B0 base strict bind (base plan, as-built of record)  S sidecar +1 (mk_sidecar66.py)
#   1 probe bind -> bus_groups  2 gen.py latency --groups -> fresh R8  3 base bind  4 cb16_pads.py -> fresh CB16
#   5 final strict bind  G G0C base vs new
set -u
W=$1; R=$2; BASEPLAN=$3
D=results/qc_die66_ca1_1103/bind; Q=results/qc_die63_red_1102/bind; P=physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json
cd $W; mkdir -p $D $R
S=$R/status; say(){ echo "$* $(date)" | tee -a $S; }
say "START tree $(git rev-parse --short=10 HEAD) plan $(sha256sum $P|cut -c1-12) base $(sha256sum $BASEPLAN|cut -c1-12)"
python3 -I results/qc_die66_ca1_1103/mk_sidecar66.py $Q/sidecar.json $D/sidecar.json $BASEPLAN $P > $R/sidecar.log 2>&1; say "S SIDECAR rc=$? $(tail -1 $R/sidecar.log)"
python3 -I - $Q/final_asbuilt.json $D/asbuilt.json $D <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); r["clock_landing_table"]=sys.argv[3]+"/sidecar.json"; json.dump(r,open(sys.argv[2],"w"),indent=1)
PY
mkdir -p $R/elab; python3 -I tools/die_plan/bind.py elab $P --out $R/elab --asbuilt $D/asbuilt.json --mem 28 > $R/elab.log 2>&1; say "E ELAB rc=$?"
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
r['note']=r.get('note','')+f' | DIE-QC-66/CLK BIND {mode} recipe (CA +1 on 30 v3 low-side crossings; fresh latency/R8/CB16 regen, DIE-QC-57 chain)'
json.dump(r,open(dst,'w'),indent=1)
PY
}
for d in b0 probe base final; do mkdir -p $R/$d; for f in asbuilt.json asbuilt_sources.json; do cp $R/elab/$f $R/$d/$f; done; done
python3 -I tools/die_plan/bind.py bind $BASEPLAN --asbuilt $Q/final_asbuilt.json --out $R/b0 --strict > $R/b0.log 2>&1; say "B0 BASE-OF-RECORD strict rc=$? $(grep -m1 '"errors"' $R/b0.log | cut -c1-300)"
run_bind(){ python3 -I tools/die_plan/bind.py bind $P --asbuilt $D/$1_asbuilt.json --out $R/$1 $2 > $R/$1.log 2>&1; local rc=$?
  say "BIND $1 $2 rc=$rc $(grep -m1 '"errors"' $R/$1.log | cut -c1-300)"; }
mk $D/asbuilt.json $D/probe_asbuilt.json probe $D; run_bind probe ""
python3 -I tools/die_plan/gen.py latency $P --groups $R/probe/bus_groups.json --out $D/r8 > $R/r8.log 2>&1; say "2 R8 rc=$? $(tail -1 $R/r8.log|cut -c1-300)"
mk $D/asbuilt.json $D/base_asbuilt.json base $D; run_bind base ""
python3 -I physical/die_plan/qwen_compute/bind/cb16_pads.py $R/base $D/r8/qwen_compute_r8_landing.json $D/cb16_pads.json > $R/cb16.log 2>&1; say "4 CB16 rc=$? $(tail -1 $R/cb16.log|cut -c1-300)"
mk $D/asbuilt.json $D/final_asbuilt.json final $D; run_bind final --strict
for t in base:$BASEPLAN new:$P; do n=${t%%:*}; mkdir -p $R/g0c_$n; python3 -I tools/die_plan/check.py ${t#*:} --out $R/g0c_$n --completeness > $R/g0c_$n/check.log 2>&1; say "G G0C $n rc=$? $(grep -m1 'G0C FAIL\|G0C PASS' $R/g0c_$n/check.log|cut -c1-200)"; done
say DONE
