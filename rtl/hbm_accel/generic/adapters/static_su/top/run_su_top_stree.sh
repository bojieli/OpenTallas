#!/usr/bin/env bash
# HBM-B-RTL1 (d4g plan b): WHOLE-SU exact bench of ot_hbm_su_static_top with RF_TREE=1 (scalar gather/broadcast tree,
# L_TREE = RF_TREE_UP+RF_TREE_DN+4 = 32) against d4f behaviour, via tools/hbm_static/su_top_run.sh (Verilator).
# usage: run_su_top_stree.sh OUT CONFIG   CONFIG in:
#   tree    RF_TREE=1, vectors --rf-relay 32: positive + 4 bench mutants (DATA/ADDR/RF/RED) must FAIL
#   tmutK   RF_TREE=1 RTL tree mutant K (MUT=16+K; 1 q2 down-leg short, 2 root drops source 1, 3 leaf 3 tag swap,
#           4 late copy to quadrant 1), same vectors -> must FAIL
#   d4f32   RF_TREE=0 relay RF_RELAY=32 on the SAME vectors as tree (identical-programme d4f reference)
#   d4f36   RF_TREE=0 relay RF_RELAY=36 (the d4f route plan) on its own vectors
#   summary compares the 32/36 programmes (expected writes/scalars equal except edges) and collects verdicts
set -uo pipefail
O=$(realpath -m "${1:?out}"); C=${2:?config}
R=$(cd "$(dirname "$0")/../../../../../.." && pwd); RUN=$R/tools/hbm_static/su_top_run.sh
mkdir -p "$O"
case "$C" in
 tree)  SU_TOP_RF_TREE=1 SU_TOP_RF_RELAY=32 bash "$RUN" "$O/tree" 0 ;;
 tmut*) k=${C#tmut}; mkdir -p "$O/tmut$k"
        # same programme as tree: generate once per dir (identical compiler input)
        SU_TOP_RF_TREE=1 SU_TOP_RF_RELAY=32 bash "$RUN" "$O/tmut$k" $((16+k)) ;;
 d4f32) SU_TOP_RF_TREE=0 SU_TOP_RF_RELAY=32 bash "$RUN" "$O/d4f32" 0 ;;
 d4f36) SU_TOP_RF_TREE=0 SU_TOP_RF_RELAY=36 bash "$RUN" "$O/d4f36" 0 ;;
 summary)
  python3 - "$O" <<'EOF'
import sys, pathlib, re, collections
O = pathlib.Path(sys.argv[1])
def rd(d, f): p = O / d / 'vec' / f; return p.read_text().split() if p.exists() else None
out = []
a, b = rd('tree', 'expw.mem'), rd('d4f36', 'expw.mem')
if a and b:
    # expw line: edge[319:288] q p sector mask data -> strip the 8-hex-digit edge
    same = len(a) == len(b) and all(x[8:] == y[8:] for x, y in zip(a, b))
    sh = collections.Counter(int(y[:8], 16) - int(x[:8], 16) for x, y in zip(a, b))
    out.append(f'expected VM writes: d4g(32) {len(a)}  d4f(36) {len(b)}  payload identical in order: {same}  edge shift d4f-d4g histogram {dict(sh)}')
    sa, sb = rd('tree', 'exps.mem'), rd('d4f36', 'exps.mem')
    if sa and sb:
        out.append(f'expected scalars: {len(sa)} vs {len(sb)}  payload identical: {[x[8:] for x in sa] == [y[8:] for y in sb]}  '
                   f'edge shifts {[int(y[:8],16)-int(x[:8],16) for x, y in zip(sa, sb)]}')
pa, pb = rd('tree', 'prog.mem'), rd('d4f36', 'prog.mem')
if pa and pb: out.append(f'programme edges: d4g(32) {len(pa)}  d4f(36) {len(pb)}')
for d in sorted(p.name for p in O.iterdir() if p.is_dir()):
    for lg in sorted((O / d).glob('*.log')):
        if lg.name.startswith(('build', 'vec')): continue
        t = lg.read_text(); m = re.search(r'^SU_TOP (PASS|FAIL).*$', t, re.M)
        out.append(f'{d}/{lg.name}: {m.group(0)[:240] if m else "NO VERDICT"}')
print('\n'.join(out))
EOF
  ;;
 *) echo "unknown config $C"; exit 2 ;;
esac
