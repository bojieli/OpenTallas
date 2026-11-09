set -e
R=/srv/opentallas-scratch3/claude/codex-qc-compose-1113
O=/srv/opentallas-scratch3/claude/qct11/start
mkdir -p $O
cd $O
python3 -I /tmp/qct11_cen.py | grep "^('" | python3 -I -c "
import sys,ast
L=[ast.literal_eval(l) for l in sys.stdin]
print(' '.join(r[0] for r in L if r[2]>0 and not r[4]))" > list.txt
wc -w list.txt
S=$R/src_fixed
nice -n5 python3 -I -B $S/physical/die_plan/qwen_compute/qc_start_1108/plan_start.py $R/plan/plan_qc53v4n.json $S/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json $R/bind_v4n_hc3_fixed2/rtl plan_qc53v4nS.json report.json $(cat list.txt) > run.log 2>&1 || { echo RC=$?; tail -30 run.log; }
tail -5 run.log; ls -la
