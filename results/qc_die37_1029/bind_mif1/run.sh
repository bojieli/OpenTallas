#!/bin/bash
# DIE-QC-37 MIF1 BIND (QC-020 plan event, = DIE-QC-33 chain + OT_QC_SRAM_MIF + fresh elab): canonical regen chain for the approved QC functional candidate (codex/qc-functional-0845@63d7fd532 inputs)
#   0 gen.py latency --inplace on a copy of the candidate plan (rebuild latency.lanes after the native CA count update)
#   1 probe bind (recipe minus land_align/land_r8_extra/param_regen) -> bus_groups
#   2 gen.py latency --groups -> fresh R8 landing table
#   3 base bind (land_align r8 + fresh R8 + INNER witness extra + param_regen)
#   4 cb16_pads.py on base -> fresh CB16 pads
#   5 final strict bind (fresh R8 + fresh CB16 + INNER witness)
# Recipes/plan/tables live repo-relative in $D (manifest path gate); bind outputs in run dir $R.
set -u
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/die-qc37-mif1-bind; W=/srv/opentallas-scratch2/claude/wt/die-qc-37-mif
D=results/qc_die37_1029/bind_mif1; Q=$D
cd $W; mkdir -p $D
S=$R/status; say(){ echo "$* $(date)" | tee -a $S; }
say "START tree $(git rev-parse --short=10 HEAD) run ${1:-all}"
[ "${1:-all}" = all ] && { python3 -I $D/prepare_paired.py $D > $R/prepare.log 2>&1; say "P PREPARE rc=$? $(tail -1 $R/prepare.log|cut -c1-600)"; }
P=$D/plan.json
# DIE-QC-37 QC-020 plan event: prepare_paired.py rewrites $D/asbuilt.json from the candidate inputs; add OT_QC_SRAM_MIF
# (qfd_dv_s8_flat S8_SRAM_MIF=1 -> suvm_rp1/vm8q_rp1 MIF=1) to that manifest of record before elaboration.
python3 -I - $D/asbuilt.json <<PY
import json,sys
p=sys.argv[1]; s=json.load(open(p)); d=s.setdefault("defines",[])
if "OT_QC_SRAM_MIF" not in d: d.append("OT_QC_SRAM_MIF")
n=" | DIE-QC-37 QC-020 MIF1 plan event (COORD 14:18 [DIE-QC-36-PARK] 1): defines += OT_QC_SRAM_MIF (S8_SRAM_MIF=1)"
if n not in s.get("note",""): s["note"]=s.get("note","")+n
json.dump(s,open(p,"w"),indent=1)
PY
say "M MIF1 defines $(python3 -c "import json;print(json.load(open(/asbuilt.json))[defines])")"
# DIE-QC-37: fresh elaboration of the MIF1 manifest (DIE-QC-33 reused the Codex elab2 MIF0 elaboration)
if [ "${1:-all}" = all ]; then
python3 -I tools/die_plan/bind.py elab $P --asbuilt $D/asbuilt.json --out $R/elab --mem 32 > $R/elab.log 2>&1; say "E ELAB rc=$? $(tail -1 $R/elab.log|cut -c1-400)"
fi
if [ "${1:-all}" = all ]; then
python3 -I tools/die_plan/gen.py latency $P --inplace --out $D/lat0 > $R/lat0.log 2>&1; say "0 LATENCY rc=$? $(tail -1 $R/lat0.log|cut -c1-200)"
fi
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
r['note']=r.get('note','')+f' | DIE-QC-37 MIF1 BIND {mode} recipe (fresh latency/R8/CB16 regen)'
json.dump(r,open(dst,'w'),indent=1)
PY
}
for d in probe base final; do mkdir -p $R/$d; for f in asbuilt.json asbuilt_sources.json; do [ -e $R/$d/$f ] || cp $R/elab/$f $R/$d/$f; done; done
run_bind(){ # name strict
  python3 -I tools/die_plan/bind.py bind $P --asbuilt $D/$1_asbuilt.json --out $R/$1 $2 > $R/$1.log 2>&1; local rc=$?
  say "BIND $1 $2 rc=$rc $(grep -m1 '"errors"' $R/$1.log | cut -c1-300)"; }
mk $Q/asbuilt.json $D/probe_asbuilt.json probe $D; run_bind probe ""
python3 -I tools/die_plan/gen.py latency $P --groups $R/probe/bus_groups.json --out $D/r8 > $R/r8.log 2>&1; say "2 R8 rc=$? $(tail -1 $R/r8.log|cut -c1-300)"
mk $Q/asbuilt.json $D/base_asbuilt.json base $D; run_bind base ""
python3 -I physical/die_plan/qwen_compute/bind/cb16_pads.py $R/base $D/r8/qwen_compute_r8_landing.json $D/cb16_pads.json > $R/cb16.log 2>&1; say "4 CB16 rc=$? $(tail -1 $R/cb16.log|cut -c1-300)"
mk $Q/asbuilt.json $D/final_asbuilt.json final $D; run_bind final --strict
say DONE
