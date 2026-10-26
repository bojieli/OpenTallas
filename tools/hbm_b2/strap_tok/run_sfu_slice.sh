#!/bin/bash
# TOK-HBM-SUV 2026-10-26: SFU strap vehicle = the 16 B2n lane cores of q_b110..q_b113 (ot_hgi_sfu_split3_lane_core_strap,
# strap_map_lane_j tied to die_plan.json) composed into the extracted ot_hgi_sfu_core_split3_sp2 #(LWB 15, LG_PATH 31) glue
# (opstore_a/b + ctl stay glue), lock-stepped against the unsplit twin.
#   tools/hbm_b2/strap_tok/run_sfu_slice.sh OUT [CYCLES] [SEEDS]      (heavy: run under ot-run; 4 Verilator builds in parallel)
# Rule 3: refuses a dirty tracked tree, records source_commit; every input is repo-relative at that commit (old kits
# regenerated from the repo with gen_core_kit_hbm.py views_b2n.json, as run_strap_tok.sh).
set -u
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel) || exit 2
OUT=$1; CYC=${2:-4000}; SEEDS=${3:-"1 2"}
git -C "$R" diff --quiet HEAD -- || { echo "REFUSE: dirty tracked tree in $R"; exit 3; }
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd -P)
[ -e "$OUT/summary.json" ] && { echo "REFUSE: $OUT already holds a summary"; exit 3; }
git -C "$R" rev-parse HEAD > "$OUT/source_commit.txt"
cd "$R" || exit 2
D=tools/hbm_b2/strap_tok/suv; H=results/type_reduce3_1025/hbm
FILES=$R/$D/sfu_split3_sp2.files PARAMS=LWB=15,LG_PATH=31 bash physical/die_plan/hbm/cores/harden/rest_extract.sh "$R" "$OUT/rest" sfu_glue \
  ot_hgi_sfu_core_split3_sp2 ot_hgi_sfu_lane_map,ot_su12_sfu_sp2 "c:*g_lane*u_map,c:*g_lane*u_sfu" 48 > "$OUT/rest_extract.log" 2>&1
[ -s "$OUT/rest/sfu_glue.parent.v" ] || { echo "FAIL: rest_extract"; exit 4; }
mkdir -p "$OUT/old" "$OUT/asm"
python3 -c "import json;[print(v['old_view']) for v in json.load(open('$H/variants.json'))['ot_hgi_sfu_split3_lane_core_strap']]" |
  (cd physical/die_plan/hbm_arch_cores && xargs -P 8 -I{} sh -c 'python3 -E -s gen_core_kit_hbm.py --views views_b2n.json --view "{}" --out '"$OUT"'/old --hold-margin 0 --face-shell on --face-shell-drop off --core-insertion none --clock-taps density > /dev/null 2>&1; echo "genold {} rc=$?"') > "$OUT/genold.log"
python3 -I tools/hbm_b2/strap_tok/su_slice_vehicle.py "$OUT/rest/sfu_glue.parent.v" "$OUT/asm" --repo . --design sfu --old-dir "$OUT/old" | tee "$OUT/compose.log"
grep -q '"verdict": "PASS"' "$OUT/compose.log" || { echo "FAIL: composition"; exit 5; }
python3 -I $D/gen_lockstep_tb.py "$OUT/rest/sfu_glue.parent.v" ot_hgi_sfu_core_split3_sp2 LWB=15,LG_PATH=31 "$OUT/tb_sfu.sv" > "$OUT/tb.log"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version > "$OUT/verilator_version.txt"
SRC="$(grep -v '^#' $D/sfu_split3_sp2.files | grep -v '^macro:') $(grep '^macro:' $D/sfu_split3_sp2.files | sed 's/^macro://' | sed 's#.*#physical/asap7_memory_macros/&/&.v#')"
SRC="$SRC $(python3 -c "import json;print(' '.join(s for s in json.load(open('$OUT/asm/sfu_report.json'))['sources'] if s.endswith('.sv')))")"
OLDW=$(ls "$OUT"/old/*/rtl/*__wrap.sv)
echo $SRC $D/gen_lockstep_tb.py | tr ' ' '\n' | sort -u | xargs sha256sum > "$OUT/sources.sha256"; sha256sum $OLDW "$OUT/tb_sfu.sv" >> "$OUT/sources.sha256"
for k in canon strap old mut; do
  ( "$vl" --binary --timing -O1 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
      +define+SUV_DUT=suv_sfu_asm_$k --top-module tb_suv_lockstep --Mdir "$OUT/obj_$k" $SRC $([ $k = old ] && echo $OLDW) \
      "$OUT/asm/sfu_asm_$k.v" "$OUT/tb_sfu.sv" > "$OUT/build_$k.log" 2>&1 &&
    for s in $SEEDS; do "$OUT/obj_$k/Vtb_suv_lockstep" +seed=$s +cycles=$CYC +dens=$((s*3)) > "$OUT/sim_${k}_s$s.log" 2>&1; done
    echo "$k rc=$?" ) &
done | tee "$OUT/runs.log"
wait
python3 - "$OUT" "$SEEDS" <<'PY'
import json, re, sys, os, glob
o = sys.argv[1]; res = {}
for k in ('canon', 'strap', 'old', 'mut'):
    rs = []
    for f in sorted(glob.glob(f'{o}/sim_{k}_s*.log')):
        m = re.search(r'LOCKSTEP (PASS|FAIL).*', open(f).read()); rs.append(m.group(0) if m else 'NO_RESULT')
    if not rs:
        rs = ['NO_RESULT build: ' + open(f'{o}/build_{k}.log').read()[-400:]]
    res[k] = dict(result='PASS' if all(r.startswith('LOCKSTEP PASS') for r in rs) else ('FAIL' if all(r.startswith('LOCKSTEP FAIL') for r in rs) else 'MIXED/NO_RESULT'), runs=rs)
ok = res['canon']['result'] == res['strap']['result'] == res['old']['result'] == 'PASS' and res['mut']['result'] == 'FAIL'
rep = json.load(open(f'{o}/asm/sfu_report.json'))
straps = [dict(inst=n['inst'], port=p, **v) for n in rep['vehicles']['strap'] for p, v in n.get('straps', {}).items()]
json.dump(dict(source_commit=open(f'{o}/source_commit.txt').read().strip(), runs=res, plan_strap_ties_in_vehicle=len(straps),
               distinct_values=len({s['plan'] for s in straps}), strap_ties=straps, compose_verdict=rep['verdict'],
               skipped=rep['skipped'], verdict='PASS' if ok else 'FAIL'), open(f'{o}/summary.json', 'w'), indent=1)
print('SFU', 'PASS' if ok else 'FAIL', {k: v['result'] for k, v in res.items()})
PY
grep -q '"verdict": "PASS"' "$OUT/summary.json" && { echo SFUV_PASS > "$OUT/done"; exit 0; }
echo SFUV_FAIL > "$OUT/done"; exit 1
