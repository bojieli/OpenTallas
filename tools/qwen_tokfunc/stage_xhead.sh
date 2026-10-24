#!/bin/bash
# TOK-QW 10-24 stage "xhead": the x-consumer column-head lowering (QW-XHEAD dv_lower_xhead) on the 12-slice qfd_dv_slice2
# die chain, ON THE SOURCE ASSEMBLY (RUNROOT/src), Verilator 5.050.  Same bench/protocol as TOKe-QW 10-23
# (results/rtl/tokd_qw_1022/xhead_cons_1023/xhead_cons_job.sh, then on the tokqw4 tree only): calibrate (x_tap, d_head,
# read_tail, global go_lag / xpf_lead) -> per-consumer go_lag / xpf_lead sweep (o, down, qkv) -> merge -> the 4 consumer
# cases qkv / gu / o / down with the merged ages + 10 mutants (goearly / xpflate / isaxbase, each must FAIL).
#
#   stage_xhead.sh RUNROOT [--par N] [--reuse]
#
# --reuse: keep an existing RUNROOT/xhead/tree + out/build/obj_xh (cached executable) and recalibrate into out/cal_r<N>
# (the previous out/cal is preserved).  The global go_lag sweep starts at OT_XH_GO_MIN (default -8 here: on the
# 10-24 main tree -2..6 all PASSed, i.e. no FAIL edge; 10-23 found the edge at -3/-4).
#
# Inputs: RUNROOT/src (assembly), RUNROOT/stg/fx_res/results (the committed bench data files, == the assembly commit) and
# RUNROOT/xhead/fx/results (results/rtl/qlb_c4b_1018/xhead + results/rtl/qwen_q_export_1014/xpf, git archive of the
# assembly commit).  Ends with RUNROOT/xhead/result.json.
set -u
RUNROOT=$(readlink -f "$1"); shift
PAR=24; REUSE=0
while [ $# -gt 0 ]; do case "$1" in --par) PAR=$2; shift 2;; --reuse) REUSE=1; shift;; *) echo "bad arg $1"; exit 2;; esac; done
export OT_XH_GO_MIN=${OT_XH_GO_MIN:--8}
SRC=$RUNROOT/src; S=$RUNROOT/xhead; T=$S/tree; O=$S/out
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
[ -d "$RUNROOT/stg/fx_res/results" ] && [ -d "$S/fx/results" ] || { echo "missing bench data (stg/fx_res, xhead/fx)"; exit 2; }
if [ $REUSE = 1 ]; then
  [ -x "$O/build/obj_xh/Vtb" ] && [ -d "$T" ] || { echo "--reuse needs $T and $O/build/obj_xh/Vtb"; exit 5; }
  for d in cal pts run; do   # keep earlier attempts
    [ -e "$O/$d" ] && { k=1; while [ -e "$O/${d}_r$k" ]; do k=$((k+1)); done; mv "$O/$d" "$O/${d}_r$k"; }
  done
  [ -f "$O/calibrate.out" ] && mv "$O/calibrate.out" "$O/calibrate.prev.$(date +%s).out"
  mkdir -p "$O/cal" "$O/pts" "$O/run"
else
  [ ! -e "$T" ] || { echo "preserve $T"; exit 5; }
  mkdir -p "$T" "$O/cal" "$O/pts" "$O/run" "$O/build"
  # real copy (the bench resolves ROOT from its own path)
  for d in rtl tools configs; do cp -r "$SRC/$d" "$T/"; done
  cp -as "$SRC/physical" "$T/" 2>/dev/null
  cp -r "$RUNROOT/stg/fx_res/results" "$T/"; cp -rn "$S/fx/results/." "$T/results/"
fi
echo "OT_XH_GO_MIN=$OT_XH_GO_MIN reuse=$REUSE" > "$O/params.txt"
cd "$T" || exit 3
B=rtl/test/qwen_dv/xhead_bench.py
verilator --version > "$O/verilator.version" 2>&1
sha256sum $B tools/qwen_layerbench/dv_lower_xhead.py tools/qwen_layerbench/dv_lower_vec.py tools/qwen_layerbench/dv_lower.py \
  rtl/test/qwen_dv/dv_lower_vec_bench.py rtl/test/qwen_dv/dv_lower_bench.py rtl/test/qwen_dv/dv_bench.py \
  rtl/test/qwen_dv/dv_bench2.py rtl/test/qwen_dv/tb_qfd_dv2.sv rtl/test/qwen_dv/main2.cpp rtl/qwen_dv/*.sv \
  rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv tools/qwen_layerbench/ctlm_image.py \
  results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex > "$O/source.sha256"
t0=$(date +%s)
# 1. calibrate (builds the ONE obj_xh executable in $O/build)
python3 $B --calibrate --work "$O/cal" --build-dir "$O/build" > "$O/calibrate.out" 2>&1; echo "rc=$?" >> "$O/calibrate.out"
A0=$O/cal/xhead_ages.json
[ -f "$A0" ] || { echo "calibrate produced no ages (see $O/calibrate.out)"; tail -20 "$O/calibrate.out"; exit 3; }
# 2. per-consumer sweep (the 10-23 point set) + merge
{
for c in o down; do for g in $(seq -6 12); do echo "$c $g 12"; done; for l in $(seq -2 8); do echo "$c 20 $l"; done; done
for g in $(seq -6 2); do echo "qkv $g 12"; done; for l in $(seq -1 6); do echo "qkv 20 $l"; done
} > "$O/points.txt"
xargs -P "$PAR" -L 1 sh -c 'python3 '"$B"' --work '"$O"'/pts --build-dir '"$O"'/build --ages '"$A0"' --point $0 --go-lag $1 --xpf-lead $2 > '"$O"'/pts/pt_$0_g$1_x$2.out 2>&1' < "$O/points.txt"
python3 $B --work "$O/pts" --ages "$A0" --merge "$O/xhead_ages.json" > "$O/merge.out" 2>&1; echo "rc=$?" >> "$O/merge.out"
A=$O/xhead_ages.json
[ -f "$A" ] || { echo "no merged ages"; exit 3; }
# 3. the 4 cases + mutants on the merged ages
printf '%s\n' "gu -" "qkv -" "o -" "down -" "gu goearly" "gu xpflate" "gu isaxbase" "qkv goearly" "o goearly" "o xpflate" \
  "o isaxbase" "down goearly" "down xpflate" "down isaxbase" | xargs -P 14 -L 1 sh -c '
  if [ "$1" = - ]; then tag=$0_m0; ma=""; else tag=$0_$1; ma="--mutant $1"; fi
  python3 '"$B"' --work '"$O"'/run --build-dir '"$O"'/build --run $0 $ma --ages '"$A"' > '"$O"'/$tag.out 2>&1; echo "rc=$?" >> '"$O"'/$tag.out'
echo "total $(( $(date +%s) - t0 )) s" > "$S/timing.txt"
# 4. verdict: 4 cases PASS, 10 mutants FAIL
python3 - "$S" "$(cat "$SRC/ASM_COMMIT" 2>/dev/null)" <<'PY'
import json, re, sys
from pathlib import Path
S = Path(sys.argv[1]); O = S / 'out'
def line(tag):
    p = O / f'{tag}.out'
    if not p.is_file(): return None
    m = [l for l in p.read_text().splitlines() if l.startswith('XHEAD ')]
    return m[-1] if m else None
cases, muts, bad = {}, {}, []
for c in ('qkv', 'gu', 'o', 'down'):
    l = line(f'{c}_m0'); cases[c] = l
    if not l or ' PASS ' not in l: bad.append(f'{c}: {l}')
for t in ('gu_goearly', 'gu_xpflate', 'gu_isaxbase', 'qkv_goearly', 'o_goearly', 'o_xpflate', 'o_isaxbase',
          'down_goearly', 'down_xpflate', 'down_isaxbase'):
    l = line(t); muts[t] = 'FAIL as required' if l and ' FAIL ' in l else f'NOT CAUGHT ({l})'
    if not (l and ' FAIL ' in l): bad.append(f'{t} not caught')
ages = json.loads((O / 'xhead_ages.json').read_text()) if (O / 'xhead_ages.json').is_file() else None
res = dict(stage='xhead', grade='RTL-functional (source assembly)', src_commit=sys.argv[2] or None,
           verdict='PASS' if not bad else 'FAIL', problems=bad, cases=cases, mutants=muts,
           summary=f"{sum(1 for v in cases.values() if v and ' PASS ' in v)}/4 cases PASS, "
                   f"{sum(1 for v in muts.values() if v == 'FAIL as required')}/10 mutants FAIL",
           consumer_ages=(ages or {}).get('consumer'), merge=(O / 'merge.out').read_text().splitlines()[:4]
           if (O / 'merge.out').is_file() else None,
           bench='rtl/test/qwen_dv/xhead_bench.py (tb_qfd_dv2 N 12 +DV2_XHEAD), protocol = TOKe-QW 10-23 xhead_cons_job.sh')
(S / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
print('XHEAD STAGE', res['verdict'], bad[:5])
PY
