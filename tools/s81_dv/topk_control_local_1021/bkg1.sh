#!/usr/bin/env bash
# [ELEM-BKG] existing production 796/73-beat bench (MODE=prod) or landing210 causal mutant (MODE=mout) on src_bkg1
set -u -o pipefail
B=/srv/opentallas-scratch/claude/codex-s81-topk-control-local-1021; M=$1
S=$B/src_bkg1; [ "$M" = mout ] && { rm -rf $B/src_bkg1_mout; cp -a $B/src_bkg1 $B/src_bkg1_mout; S=$B/src_bkg1_mout; }
rm -rf $B/stim_bkg1_$M $B/bench_bkg1_$M; mkdir -p $B/stim_bkg1_$M; cp $B/stim_ctl_r1/{stim.txt,exp.txt,meta.json} $B/stim_bkg1_$M/
cd $S
if [ "$M" = mout ]; then python3 - <<'PY'
from pathlib import Path
p=Path('rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bk_sel_pa_n32_lp.sv'); o=p.read_text(); n='assign rung_s_out_d6__l_r37 = lpl_210_o;'
assert o.count(n)==1; p.write_text(o.replace(n,'assign rung_s_out_d6__l_r37 = rung_s_out_d6; // MUTANT'))
PY
fi
bash tools/s81_dv/topk_control_local_1021/run_production.sh $B/bench_bkg1_$M $B/stim_bkg1_$M
echo BKG1_${M}_RC=$?
