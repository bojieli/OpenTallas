#!/bin/bash
# S81-TOPK3 ACC32 suite (Verilator 5.050): successor defines + OT_S81PH_SEL_FAN32 + OT_S81PH_SEL_ACC32 (per-lane KEPT
# copies of the packer accumulate controls ro_v/ro_fl/qf/qc/oflush; exact, 0 added edges).
# 5 positive (legacy, indexed13, ties, ninf, zeros) must PASS; identity/corrupt/early + the ACC32 mutant
# (OT_S81PH_SEL_ACC32_MUT: upper-half lanes drop the running fill) must FAIL.  Run from the source root.
# usage: run_suite.sh <outdir>
set -uo pipefail
O=${1:?out}; mkdir -p "$O"
S=results/arch/s81_topk_final_1019/bench
DEF="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_RST64 -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32"
ALL="legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros indexed13_identity indexed13_corrupt indexed13_early"
for d in $ALL; do rm -rf "$O/$d"; mkdir -p "$O/$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/$d/"; done
for d in legacy indexed13; do rm -rf "$O/mut_acc_$d"; mkdir -p "$O/mut_acc_$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/mut_acc_$d/"; done
VL_EXTRA="$DEF" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build" $(for d in $ALL; do echo "$O/$d"; done) > "$O/suite_positive.log" 2>&1 &
VL_EXTRA="$DEF -DOT_S81PH_SEL_ACC32_MUT" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build_mut_acc" "$O/mut_acc_legacy" "$O/mut_acc_indexed13" > "$O/suite_mutants.log" 2>&1 &
wait
python3 - "$O" <<'PY'
import json,sys
from pathlib import Path
o=Path(sys.argv[1]); r={}
for d in sorted(o.iterdir()):
    v=d/'verdict.txt'
    if v.exists():
        t=v.read_text().split(); r[d.name]=t[1] if len(t)>1 else '?'
pos=['legacy','indexed13','indexed13_ties','indexed13_ninf','indexed13_zeros']
neg=['indexed13_identity','indexed13_corrupt','indexed13_early']
ok=all(r.get(p)=='PASS' for p in pos) and all(r.get(n)=='FAIL' for n in neg) and all(r.get(m)=='FAIL' for m in ('mut_acc_legacy','mut_acc_indexed13'))
print('ACC32_SUITE', 'PASS' if ok else 'FAIL', json.dumps(r))
sys.exit(0 if ok else 1)
PY
