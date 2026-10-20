#!/usr/bin/env bash
# HBM-PRETREE2 collection (after run_all_pt.sh): copy results, update units/su.json in the worktree, census --measured, tok/s
set -u
L=/home/ubuntu/scratch/hbm-pretree2; W=/home/ubuntu/wt/codex-hbm-pretree-pickup-1020; B=/srv/opentallas-scratch/claude/hbm-pretree2/suvop
T=/srv/opentallas-scratch/claude/toksim-hbm; P=$W/results/token_pass/measured_hbm_1019/pretree2
mkdir -p $L/res && cd $L/res
for d in vec_pt vec_ptreg mutw; do rsync -a -e "ssh -o ControlPath=none" --include='*/' --include='programme.json' --include='sim_mr10*.log' --include='compile.txt' --exclude='*' ot-epyc5:$B/$d/ $d/; done
grep -h "SU_TOP PASS\|SU_TOP FAIL" vec_pt/*/sim_mr10_pt.log vec_ptreg/*/sim_mr10_pt.log | cut -c1-60 | sort | uniq -c
python3 - "$L/res" <<'CHECK'
import sys,re,json
from pathlib import Path
root=Path(sys.argv[1]); failures=[]; rows=[]
for category,expected in [('vec_pt',12),('vec_ptreg',4)]:
    dirs=sorted(p for p in (root/category).iterdir() if p.is_dir())
    if len(dirs)!=expected:failures.append(f'{category}: expected {expected} records, got {len(dirs)}')
    for d in dirs:
        p=d/'sim_mr10_pt.log'; t=p.read_text() if p.exists() else ''
        ok=bool(re.search(r'^SU_TOP PASS\b',t,re.M)) and not re.search(r'^SU_TOP (FAIL|ERROR)\b',t,re.M)
        rows.append({'record':str(d.relative_to(root)),'expected':'PASS','ok':ok})
        if not ok:failures.append(f'{d.name}: positive not bit-exact')
for kind in ['data','m1024','pt0']:
    for record in ['qw_softmax_exp_sum_r1','ds_q_norm_ss']:
        d=root/'mutw'/f'{kind}_{record}'; logs=list(d.glob('sim_mr10*.log'));t='\n'.join(p.read_text() for p in logs)
        ok=bool(re.search(r'^SU_TOP FAIL\b',t,re.M)) and bool(re.search(r'^SU_TOP ERROR\b',t,re.M)) and not re.search(r'^SU_TOP PASS\b',t,re.M)
        rows.append({'record':str(d.relative_to(root)),'expected':'causal FAIL','ok':ok})
        if not ok:failures.append(f'{d.name}: causal rejection not established')
(root/'codex_acceptance.json').write_text(json.dumps({'accepted':not failures,'failures':failures,'records':rows},indent=2)+'\n')
if failures:raise SystemExit('PRETREE_ACCEPTANCE_FAIL: '+'; '.join(failures))
print('PRETREE_ACCEPTANCE_PASS: 16 bit-exact records and 6 causal mutant failures')
CHECK
[ $? -eq 0 ] || { echo 'COLLECT_STOPPED: correctness/witnesses incomplete; no timing adoption'; exit 4; }
echo 'PRETREE_RECORDS_VALIDATED: raw exactness collected; automatic unit/rate update HELD'
echo '8-row affine law has no admitted atomic programme; actual phased4 proof and timing integration required'
exit 6
python3 $P/update_su_pt.py $L/res/vec_pt claude/hbm-pretree2-1020@a5cc6f083 || { echo UPDATE_FAIL; exit 3; }
python3 $P/make_measured_pt.py $L/m_pt.json
ssh -o ControlPath=none ot-epyc6 "mkdir -p $T/pretree2" && scp -o ControlPath=none -q $L/m_pt.json ot-epyc6:$T/pretree2/m_pt.json
/home/ubuntu/bin/ot-run --mem 48 --threads 4 --dir $T -- bash -c "cd $T/src && PYTHONPATH=tools python3 -c \"
import sys
from hgi_sim import toksim_hbm_census_1019 as C
C.ONLY='info_banklat_all'
sys.argv=['x','--out','$T/pretree2/pt.json','--measured','$T/pretree2/m_pt.json','--bw','98','--bridge','1']
C.main()\" > $T/pretree2/pt.log 2>&1; ls $T/pretree2/pt_jobs"
rsync -a -e "ssh -o ControlPath=none" ot-epyc6:$T/pretree2/ $L/census/
python3 $P/tok_from_sched.py $L/census/pt_jobs | tee $L/tok_pt.json
echo COLLECT_DONE
