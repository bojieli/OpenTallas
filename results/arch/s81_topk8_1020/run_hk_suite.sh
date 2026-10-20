#!/bin/bash
# S81-TOPK8 hard-child quarter suite (= TOPK7 HQ suite + HK_EXTRA defines, e.g. -DOT_HARD_CHILDREN [-DOT_S81PH_HQ_INPUT_RAW]) (Verilator 5.050 = the closure daemon's pin): successor defines + OT_S81PH_SEL_HQ (the
# hierarchical, native-census-clean quarter dsfd_selt_q_hq; same edges as dsfd_selt_q2).  The production bk-layer
# bench (tb_bk_layer: 4 quarters + control, cycle-exact against the compiler's expected vo_s edges).
# 5 positive (legacy, indexed13, ties, ninf, zeros) must PASS; identity / corrupt / early must FAIL; the four causal HQ
# mutants (OT_S81PH_SEL_HQ_MUT 1..4, see ot_s81ph_hq_slice.sv) must FAIL on indexed13 and legacy.  Run from the source
# root.  usage: run_hq_suite.sh <outdir>
set -uo pipefail
O=${1:?out}; mkdir -p "$O"
S=results/arch/s81_topk_final_1019/bench
R=results/arch/s81_topk7_1020/run_hq_layer.sh
DEF="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 -DOT_S81PH_SEL_ILD -DOT_S81PH_SEL_FRPR -DOT_S81PH_SEL_HQ ${HK_EXTRA:-}"
ALL="legacy indexed13 indexed13_ties indexed13_ninf indexed13_zeros indexed13_identity indexed13_corrupt indexed13_early"
for d in $ALL; do rm -rf "$O/$d"; mkdir -p "$O/$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/$d/"; done
for m in 1 2 3 4; do for d in legacy indexed13; do rm -rf "$O/mut${m}_$d"; mkdir -p "$O/mut${m}_$d"; cp $S/$d/stim.txt $S/$d/exp.txt $S/$d/meta.json "$O/mut${m}_$d/"; done; done
VL_EXTRA="$DEF" J=8 bash $R "$O/build" $(for d in $ALL; do echo "$O/$d"; done) > "$O/suite_positive.log" 2>&1 &
for m in 1 2 3 4; do
  VL_EXTRA="$DEF -DOT_S81PH_SEL_HQ_MUT=$m" J=6 bash $R "$O/build_mut$m" "$O/mut${m}_legacy" "$O/mut${m}_indexed13" > "$O/suite_mut$m.log" 2>&1 &
done
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
mut=[f'mut{m}_{d}' for m in (1,2,3,4) for d in ('legacy','indexed13')]
okp=all(r.get(p)=='PASS' for p in pos); okn=all(r.get(n)=='FAIL' for n in neg)
okm={m: any(r.get(f'mut{m}_{d}')=='FAIL' for d in ('legacy','indexed13')) for m in (1,2,3,4)}
ok=okp and okn and all(okm.values())
print('HQ_SUITE', 'PASS' if ok else 'FAIL', json.dumps(dict(r=r, positive=okp, negative=okn, mutants=okm)))
sys.exit(0 if ok else 1)
PY
