set -eu
cd /srv/opentallas-scratch2/claude/qct11/repo
git fetch -q origin main
git sparse-checkout set physical/die_plan/qwen_compute/qc_start_1108 results/qc_types_11_start_1108
git checkout -q -B claude/qc-types-11-start-1108 origin/main
mkdir -p results/qc_types_11_start_1108
Q=/srv/opentallas-scratch3/claude/qct11/start
for f in bench_start.py report.json list_final.txt price45.json wc3.sh stage6.sh g0c2.sh; do scp -q -o ControlPath=none epyc6:$Q/$f results/qc_types_11_start_1108/$f; done
scp -q -o ControlPath=none epyc6:/tmp/qct11_st2.py results/qc_types_11_start_1108/struct_census.py
scp -q -o ControlPath=none epyc6:/tmp/qct11_ex.py results/qc_types_11_start_1108/census_start_raw.py
scp -q -o ControlPath=none epyc6:$Q/bench_out/bench.json results/qc_types_11_start_1108/bench.json
scp -q -o ControlPath=none epyc6:/tmp/qct11_ps.py /tmp/qct11_ps_local.py
F=physical/die_plan/qwen_compute/qc_start_1108/plan_start.py
sed "s#^p='.*#p='$F'#" /tmp/qct11_ps_local.py > /tmp/qct11_ps_l2.py
python3 -I /tmp/qct11_ps_l2.py
scp -q -o ControlPath=none epyc6:/srv/opentallas-scratch2/claude/qct11/wave/src/$F /tmp/qct11_e6_ps.py
cmp $F /tmp/qct11_e6_ps.py && echo SAME_AS_STAGED
git add $F results/qc_types_11_start_1108
git commit -q -m "QC START transport event 98 types: constructor reader depth 0, bench and census

plan_qc53v4nS 7e4789251637 = plan_qc53v4n + qc_start_1108/plan_start.py on 98 types.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log -1 --format=%H
git diff --stat HEAD~1 | tail -3
git push -q origin HEAD:refs/heads/claude/qc-types-11-start-1108 2>&1 | tail -1
git ls-remote origin refs/heads/claude/qc-types-11-start-1108 | cut -c1-12
