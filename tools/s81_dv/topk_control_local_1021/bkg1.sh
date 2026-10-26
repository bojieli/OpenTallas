#!/usr/bin/env bash
# [ELEM-BKG] existing production 796/73-beat bench (MODE=prod) or landing210 causal mutant (MODE=mout) on src_bkg1
set -u -o pipefail
export VL_EXTRA="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 -DOT_S81PH_SEL_HQ -DOT_HARD_CHILDREN -DOT_S81PH_HQ_INPUT_RAW -DOT_S81PH_SEL_ILD -DOT_S81PH_SEL_FRPR"  # exact defines of the 47c98 production build (bench_ctl_r1 verFiles)
SRC=${SRC:-src_bkg1}
B=/srv/opentallas-scratch/claude/codex-s81-topk-control-local-1021; M=$1
S=$B/$SRC; [ "$M" = mout ] && { rm -rf $B/${SRC}_mout; cp -a $B/$SRC $B/${SRC}_mout; S=$B/${SRC}_mout; }
rm -rf $B/stim_${SRC}_$M $B/bench_${SRC}_$M; mkdir -p $B/stim_${SRC}_$M; cp $B/stim_ctl_r1/{stim.txt,exp.txt,meta.json} $B/stim_${SRC}_$M/
cd $S
if [ "$M" = mout ]; then python3 - <<'PY'
from pathlib import Path
p=Path('rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bk_sel_pa_n32_lp.sv'); o=p.read_text(); n='assign rung_s_out_d6__l_r37 = lpl_210_o;'
assert o.count(n)==1; p.write_text(o.replace(n,'assign rung_s_out_d6__l_r37 = rung_s_out_d6; // MUTANT'))
PY
fi
bash tools/s81_dv/topk_control_local_1021/run_production.sh $B/bench_${SRC}_$M $B/stim_${SRC}_$M
echo BKG1_${M}_RC=$?
