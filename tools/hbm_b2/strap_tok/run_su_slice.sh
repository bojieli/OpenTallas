#!/bin/bash
# TOK-HBM-SUV 2026-10-26: SU Q0 slice strap vehicle (B2n q_su00 + q_su01 hard cores composed, strap pins tied to the plan).
#   tools/hbm_b2/strap_tok/run_su_slice.sh OUT [EDGES] [NRST]      (heavy: run under ot-run; 4 Verilator builds in parallel)
# Rule 3: refuses a dirty tracked tree, records source_commit; every input is repo-relative at that commit.
#  1 rest_extract.sh (yosys, docker): ot_hbm_su_static_pgslice_lg_s #(plan params) flattened, 66 member cells kept
#  2 su_slice_vehicle.py: asm_{canon,strap,old,mut}.v + report.json (strap ties vs master constants, wiring findings)
#  3 tb_suv_slice.sv: each assembly vs the unsplit twin, every output every serial/stream edge; mut must FAIL
set -u
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel) || exit 2
OUT=$1; EDGES=${2:-1500}; NRST=${3:-3}
git -C "$R" diff --quiet HEAD -- || { echo "REFUSE: dirty tracked tree in $R"; exit 3; }
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd -P)
[ -e "$OUT/summary.json" ] && { echo "REFUSE: $OUT already holds a summary"; exit 3; }
git -C "$R" rev-parse HEAD > "$OUT/source_commit.txt"
cd "$R" || exit 2
D=tools/hbm_b2/strap_tok/suv
PRM=QID=0,G=0,MLAT=4,ALAT=3,LEAF=1,MULTIRATE=1,COLLPORT=1,RF_LOCAL=1,PIN_REG=1,RSYNC=1,PRETREE=1
FILES=$R/$D/pgslice_lg_s.files PARAMS=$PRM bash physical/die_plan/hbm/cores/harden/rest_extract.sh "$R" "$OUT/rest" suv_glue \
  ot_hbm_su_static_pgslice_lg_s ot_hbm_su_static_lane_pinreg,ot_hbm_su_static_pinned_bank,ot_hbm_su_red_pretree_s,ot_hbm_su_static_side_softplus_s \
  "c:u_slice.*u_lane,c:u_slice.*u_bank,c:u_slice.*u_pt,c:u_slice.*u_sp" 32 > "$OUT/rest_extract.log" 2>&1
[ -s "$OUT/rest/suv_glue.parent.v" ] || { echo "FAIL: rest_extract"; exit 4; }
mkdir -p "$OUT/asm"
python3 -I tools/hbm_b2/strap_tok/su_slice_vehicle.py "$OUT/rest/suv_glue.parent.v" "$OUT/asm" --repo . | tee "$OUT/compose.log"
grep -q '"verdict": "PASS"' "$OUT/compose.log" || { echo "FAIL: composition"; exit 5; }
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version > "$OUT/verilator_version.txt"
SRC="$(grep -v '^#' $D/pgslice_lg_s.files | grep -v '^macro:') $(grep '^macro:' $D/pgslice_lg_s.files | sed 's/^macro://' | sed 's#.*#physical/asap7_memory_macros/&/&.v#')"
SRC="$SRC $(python3 -c "import json;print(' '.join(s for s in json.load(open('$OUT/asm/report.json'))['sources'] if s.endswith('.sv')))")"
echo $SRC $D/tb_suv_slice.sv | tr ' ' '\n' | sort -u | xargs sha256sum > "$OUT/sources.sha256"
for k in canon strap old mut; do
  ( "$vl" --binary --timing -O1 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
      +define+SUV_DUT=suv_asm_$k --top-module tb_suv_slice -GEDGES=$EDGES -GNRST=$NRST --Mdir "$OUT/obj_$k" $SRC "$OUT/asm/asm_$k.v" \
      $D/tb_suv_slice.sv > "$OUT/build_$k.log" 2>&1 && { /usr/bin/time -v "$OUT/obj_$k/Vtb_suv_slice" > "$OUT/sim_$k.log" 2> "$OUT/time_$k.log"; }
    echo "$k rc=$?" ) &
done | tee "$OUT/runs.log"
wait
python3 - "$OUT" <<'PY'
import json, re, sys, os
o = sys.argv[1]; res = {}
for k in ('canon', 'strap', 'old', 'mut'):
    t = open(f'{o}/sim_{k}.log').read() if os.path.exists(f'{o}/sim_{k}.log') else ''
    m = re.search(r'SUV_SLICE (PASS|FAIL)(.*)', t)
    res[k] = dict(result=m.group(1) if m else 'NO_RESULT', line=m.group(0) if m else open(f'{o}/build_{k}.log').read()[-600:],
                  first_mismatch=[l for l in t.splitlines() if 'MISMATCH' in l][:2])
ok = res['canon']['result'] == res['strap']['result'] == res['old']['result'] == 'PASS' and res['mut']['result'] == 'FAIL'
rep = json.load(open(f'{o}/asm/report.json'))
straps = [dict(inst=n['inst'], **s) for n in rep['vehicles']['strap'] for s in [dict(port=p, **v) for p, v in n.get('straps', {}).items()]]
json.dump(dict(source_commit=open(f'{o}/source_commit.txt').read().strip(), runs=res, plan_strap_ties_in_vehicle=len(straps),
               distinct_values=len({(s['port'].startswith('strap_lane_') and 'exp' or 'l4', s['plan']) for s in straps}),
               strap_ties=straps, compose_verdict=rep['verdict'], skipped=rep['skipped'],
               verdict='PASS' if ok else 'FAIL'), open(f'{o}/summary.json', 'w'), indent=1)
print('SUV', 'PASS' if ok else 'FAIL', {k: v['result'] for k, v in res.items()})
PY
grep -q '"verdict": "PASS"' "$OUT/summary.json" && { echo SUV_PASS > "$OUT/done"; exit 0; }
echo SUV_FAIL > "$OUT/done"; exit 1
