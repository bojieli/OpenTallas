#!/bin/bash
# S81-TOPK FAN32 suite (Verilator 5.050): successor defines + OT_S81PH_SEL_FAN32 (KEPT copies of the histogram clear /
# update enable / group select and the packer rotate shift amounts; exact, 0 added edges).
# 5 positive (legacy, indexed13, ties, ninf, zeros) must PASS; identity/corrupt/early + the FAN32 group-select mutant
# (OT_S81PH_SEL_FAN32_MUT_GS) must FAIL.  Run from the source root.  usage: run_suite.sh <outdir>
set -uo pipefail
O=${1:?out}; mkdir -p "$O"
S=results/arch/s81_topk_final_1019/bench
DEF="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_RST64 -DOT_S81PH_SEL_FAN32"
ALL="legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros indexed13_identity indexed13_corrupt indexed13_early"
[ "${RERUN_POS:-0}" = 1 ] && for d in $ALL; do rm -rf "$O/$d"; mkdir -p "$O/$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/$d/"; done
for m in gs clr; do for d in legacy indexed13; do rm -rf "$O/mut_${m}_$d"; mkdir -p "$O/mut_${m}_$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/mut_${m}_$d/"; done; done
# positives already proven in the first run (out/build) are re-run only when RERUN_POS=1
[ "${RERUN_POS:-0}" = 1 ] && VL_EXTRA="$DEF" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build" $(for d in $ALL; do echo "$O/$d"; done)
VL_EXTRA="$DEF -DOT_S81PH_SEL_FAN32_MUT_GS" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build_mut_gs" "$O/mut_gs_legacy" "$O/mut_gs_indexed13" &
VL_EXTRA="$DEF -DOT_S81PH_SEL_FAN32_MUT_CLR" bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh "$O/build_mut_clr" "$O/mut_clr_legacy" "$O/mut_clr_indexed13" &
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
ok=all(r.get(p)=='PASS' for p in pos) and all(r.get(n)=='FAIL' for n in neg) and any(r.get(m)=='FAIL' for m in ('mut_gs_legacy','mut_gs_indexed13','mut_clr_legacy','mut_clr_indexed13'))
print('FAN32_SUITE', 'PASS' if ok else 'FAIL', json.dumps(r))
sys.exit(0 if ok else 1)
PY
