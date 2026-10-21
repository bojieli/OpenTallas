#!/usr/bin/env bash
# [ELEM-BKG] landing210 causal mutant on new TOPK control source 47c980070 (existing mutant, adapted path only)
set -u -o pipefail
B=/srv/opentallas-scratch/claude/codex-s81-topk-control-local-1021
rm -rf $B/src_ctl_mout $B/stim_ctl_mout $B/bench_ctl_mout
cp -a $B/src_ctl_r1 $B/src_ctl_mout
mkdir -p $B/stim_ctl_mout && cp $B/stim_ctl_r1/{stim.txt,exp.txt,meta.json} $B/stim_ctl_mout/
cd $B/src_ctl_mout
python3 - <<'PY'
import hashlib,json
from pathlib import Path
p=Path('rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/dsdv_bk_sel_pa_n32_lp.sv')
o=p.read_text(); n='assign rung_s_out_d6__l_r37 = lpl_210_o;'
assert o.count(n)==1
m=o.replace(n,'assign rung_s_out_d6__l_r37 = rung_s_out_d6; // MUTANT: omit final +2-edge landing')
p.write_text(m)
Path('output_landing_mutant.json').write_text(json.dumps({'mutation':'final southbound landing210 bypassed (n32 lp)','source_sha256':hashlib.sha256(o.encode()).hexdigest(),'mutant_sha256':hashlib.sha256(m.encode()).hexdigest(),'expected_effect':'southbound output beats two edges early; fixed calendar must reject'},indent=2))
PY
bash tools/s81_dv/topk_control_local_1021/run_production.sh $B/bench_ctl_mout $B/stim_ctl_mout
echo MOUT_RC=$?
