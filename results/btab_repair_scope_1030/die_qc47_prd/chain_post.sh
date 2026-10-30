#!/bin/bash
# DIE-QC-47 BTAB PRD: after the route stage of pass D -> finish (ot-run), clock-freeze check, kit sign-off TT/FF, post-route LEC.
# Writes D/CHAIN.txt (one line per step). Collect: D/CHAIN.txt, D/signoff/signoff.json, D/lec_post/lec.json.
set -uo pipefail
D=$(cd "$1" && pwd); H=/srv/opentallas-scratch2/claude/die-qc-47/btab; L=$D/run_route.log
until grep -q "^RC " $L 2>/dev/null; do sleep 60; done
st(){ echo "$(date "+%F %T %Z") $*" >> $D/CHAIN.txt; }
grep -q "^RC 0" $L || { st "ROUTE FAIL $(tail -1 $L)"; exit 1; }
st "ROUTE OK $(grep "Number of violations" $D/run/logs/asap7/*/base/5_2_route.log | tail -1)"
~/.local/bin/ot-run --mem 32 --threads 8 --hosts localhost --dir $D -- bash $H/run_stage.sh $D do-finish finish > $D/otrun_finish.log 2>&1
grep -q "^RC 0" $D/run_finish.log 2>/dev/null || { st "FINISH FAIL"; exit 1; }
st "FINISH OK"
bash $D/clk_freeze_check.sh $D > $D/clk_freeze_check.log 2>&1; st "CLK_FREEZE rc $? $(tail -1 $D/clk_freeze_check.log)"
SIGNOFF_DOCKER=docker python3 -I $D/signoff.py run --run-dir $D/run --kit $D --corners tt,ff --out $D/signoff --image openroad/orfs:asap7lock > $D/signoff.log 2>&1
st "SIGNOFF rc $? $(grep -E "^SIGNOFF" $D/signoff.log | head -1)"
NY=$(ls $D/run/results/asap7/*/base/6_final.v 2>/dev/null | head -1)
python3 -I $D/lec.py $D --netlist $NY --out $D/lec_post --image openroad/orfs:asap7lock > $D/lec_post_run.log 2>&1; st "LEC_POST rc $? $(tail -1 $D/lec_post_run.log)"
