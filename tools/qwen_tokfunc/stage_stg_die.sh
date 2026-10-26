#!/bin/bash
# TOK-QW 10-24 stage "stg_die": the stg pos family set (per layer resid1 resid2 silu qk --rope rx, qkv gu od --arf; lm --arf,
# emb; LGPOS set) on the BOUND compute-die slice row: tb_qfd_dv2 FACE 3 (rtl/test/qwen_dv/s8die/qfd_dv_slice_die.sv: the
# bound_r8 qfd_dv_s8_flat / s8_ce_w5 / s8_ce_l9h / s8_ce_e5 per chain position, DV2_S8DIE=1 source list from
# tools/qwen_tokfunc/s8die_srcs.py).  The bound s8 slice is hardened s5 == slice2 SU_LT 1 / HD_W130 / MU_NU 4 + ARF 1 / RP 1,
# so the expected outcome of every case is the stg pos expected outcome (pos verdicts from the stg stage result.json).
#
#   stage_stg_die.sh E STG_RESULT POS_RUNLIST [--par N]
#     E/tree (patched stg bench tree + FACE 3), E/die/build/obj_n12/Vtb (built, slice/vec calibrated by s8cal*.sh),
#     E/stgdie/fx (the stg fixtures), STG_RESULT = stg result.json, POS_RUNLIST = the stg runlist 'pos' lines with
#     paths relative to the stg stage dir (tree/ pos/build pos/cal_mat fx/).
# Writes E/stgdie/result.json.
set -u
E=$(readlink -f "$1"); STG=$(readlink -f "$2"); RL=$(readlink -f "$3"); shift 3
PAR=24; while [ $# -gt 0 ]; do case "$1" in --par) PAR=$2; shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
T=$E/tree; W=$E/die; S=$E/stgdie
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1
[ -x $W/build/obj_n12/Vtb ] && [ -s $W/build/vec_ages.json ] || { echo "need built + vec-calibrated $W/build"; exit 2; }
grep -q '^rc=0' $W/build/slice_calibrate.out && grep -q '^rc=0' $W/build/calibrate.out || { echo "slice/vec calibration not PASS"; exit 6; }
MB=$T/rtl/test/qwen_dv/dv_lower_mat_bench.py
mkdir -p $W/cal_mat $S/runs; ln -sfn $W/build/obj_n12 $W/cal_mat/obj_n12
cd $T || exit 3
t0=$(date +%s)
[ -s $W/cal_mat/stn_ages.json ] || { DV_LOWER_VFLAGS="$(cat $W/vflags.txt)" python3 $MB --work $W/cal_mat --calibrate > $W/cal_mat/calibrate.out 2>&1; echo "rc=$?" >> $W/cal_mat/calibrate.out; }
echo "matcal $(( $(date +%s)-t0 )) s" > $S/timing.txt
grep -q '^rc=0' $W/cal_mat/calibrate.out || { echo "MAT calibration FAILED (see $W/cal_mat/calibrate.out)"; python3 - "$S" "$W" <<'PY'
import json, sys; from pathlib import Path
S, W = Path(sys.argv[1]), Path(sys.argv[2])
json.dump(dict(stage='stg_die', verdict='FAIL', problems=['MAT calibration failed on the bound s8 row'],
               mat_calibrate_tail=(W / 'cal_mat/calibrate.out').read_text().splitlines()[-15:]), open(S / 'result.json', 'w'), indent=1)
PY
exit 6; }
# runlist: pos lines -> die paths
sed -e "s|^pos |die |" -e "s| tree/| $T/|g" -e "s| pos/build/| $W/build/|g" -e "s| pos/cal_mat/| $W/cal_mat/|g" \
    -e "s| fx/| $S/fx/|g" -e "/ --run lm /s|\$| --slice-ages $W/build/slice_ages.json|" "$RL" > $S/runlist.txt
# lm lowers the RMSNorm ROOT fields with this vehicle's slice ages (dv_lower_bench --calibrate writes build/slice_ages.json)
! grep -q ' --run lm ' $S/runlist.txt || [ -s $W/build/slice_ages.json ] || { echo "lm cases need $W/build/slice_ages.json"; exit 6; }
job() { local name=$2; shift 2; local d=$S/runs/$name; mkdir -p $d; ln -sfn $W/build/obj_n12 $d/obj_n12
  DV_LOWER_VFLAGS="$(cat $W/vflags.txt)" python3 "$@" --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out
  echo "die $name $(head -1 $d/bench.out | cut -c1-160)"; }
export -f job; export S W
xargs -P "$PAR" -L 1 bash -c 'job "$@"' _ < $S/runlist.txt > $S/runs.log 2>&1
echo "runs $(( $(date +%s)-t0 )) s" >> $S/timing.txt
python3 - "$S" "$STG" <<'PY'
import json, re, sys
from pathlib import Path
S = Path(sys.argv[1]); stg = json.loads(Path(sys.argv[2]).read_text())
pos = stg['configs']['pos']['stages']
cases, bad = {}, []
for line in (S / 'runlist.txt').read_text().splitlines():
    name = line.split()[1]; out = S / 'runs' / name / 'bench.out'
    txt = out.read_text() if out.is_file() else ''
    m = re.search(r'\b(PASS|FAIL)\b', txt.splitlines()[0] if txt else '')
    v = m.group(1) if m else 'NO RESULT'
    exp = (pos.get(name) or {}).get('verdict')
    cases[name] = dict(verdict=v, pos_verdict=exp, first=txt.splitlines()[0][:200] if txt else None)
    if v != exp: bad.append(f'{name}: die {v} vs pos {exp}')
res = dict(stage='stg_die', grade='RTL-functional (bound compute-die slice row, source assembly)',
           vehicle='tb_qfd_dv2 FACE 3 = bound_r8 s8 slice row (qfd_dv_slice_die), DV2_S8DIE=1',
           verdict='PASS' if not bad else 'FAIL', cases_total=len(cases),
           matched_pos=sum(1 for c in cases.values() if c['verdict'] == c['pos_verdict']), problems=bad[:50],
           ages=dict(vec=json.loads((S.parent / 'die/build/vec_ages.json').read_text()),
                     stn=json.loads((S.parent / 'die/cal_mat/stn_ages.json').read_text())), cases=cases)
(S / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
print('STG_DIE', res['verdict'], res['matched_pos'], '/', res['cases_total'], bad[:5])
PY
