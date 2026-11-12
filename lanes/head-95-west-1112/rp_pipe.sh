#!/bin/bash
# rp_pipe.sh TAG : hd_lep0N re-pack pipeline on epyc4: repack_lep.py -> reach_fix fix -> street_rule resetfix -> G0 diff + gen phys
set -u; H=/srv/opentallas-scratch2/claude/head-95; P=$H/pd; T=/srv/opentallas-scratch2/claude/wt/head-95-rfsr; R=/srv/opentallas-scratch3/claude/head-94/wtM8; G=$1
cd $P && python3 -I ../repack_lep.py k1_plan.json ${G}.json | grep -i "reset\|moved\|UNRES"
cd $T && python3 -I tools/die_plan/street_rule.py check $P/${G}.json --types hd_lep0N --die s81_head --repo $R --out $H/sr_${G}.json 2>&1 | grep hd_lep0N
python3 -I tools/die_plan/reach_fix.py fix $P/${G}.json --out-plan $P/${G}_rf.json --event $H/rf_${G}_event.json --repo $R --types '^hd_lep0N$' >/dev/null 2>&1
python3 -I -c "import json,sys; [print('reach_fix', json.dumps(r.get('after'))) for r in json.load(open(sys.argv[1]))['rows']]" $H/rf_${G}_event.json
python3 -I tools/die_plan/street_rule.py resetfix $P/k1_plan.json $P/${G}_rf.json $P/${G}_final.json --repo $R 2>&1 | tail -2
python3 -I tools/die_plan/check.py $P/${G}_final.json --out $H/g0rf_${G} --quiet > $H/g0rf_${G}.log 2>&1; tail -1 $H/g0rf_${G}.log | cut -c1-120
cd $H && python3 -I g0diff.py g0rf_k1/g0_report.json g0rf_${G}/g0_report.json | head -4
python3 -I -c "
import json,sys
w=lambda p:[(f['check'],f['msg']) for f in json.load(open(p))['findings'] if f.get('level')=='WARN']
a=set(w(sys.argv[1])); print('WARN new', len([x for x in w(sys.argv[2]) if x not in a]))" g0rf_k1/g0_report.json g0rf_${G}/g0_report.json
./genchk.sh $T $P/${G}_final.json $P/sidecar.json hd_lep0N
sha256sum $P/${G}_final.json | cut -c1-16
echo PIPE_DONE
