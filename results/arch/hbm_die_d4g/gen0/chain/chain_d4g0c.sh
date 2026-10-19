#!/bin/bash
# H-D4G3b 10-18 03:10: continuation of chain_d4g0b.sh. b's retry left: argmax_sw_vm + qdq_host missing 2 src files (now added to
# all 3 fleet src trees), idx_score ETM OOM at 112 GB (541 ETM clocks), serdes OOM at 48 GB. Re-drive every non-OK SYNTH cell
# at raised memory (jobs.tsv: idx_score 400, topk_link 320, hc_eng 320, serdes 160), then S3 fetch, S4 GEN0, S5 GRT0 (as b).
set -o pipefail
W=/home/ubuntu/wt/hd4g; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; B=/srv/opentallas-scratch/claude/hd4g/gen0; OTRUN=/home/ubuntu/bin/ot-run
V=$A/vplan; H=839b75eed
step() { echo "STEP $* $(date -Is)"; }
step S2c wait_chain_b
while kill -0 1840340 2>/dev/null; do sleep 120; done
CELLS=$(python3 -c "import json; V=json.load(open('$V/views.json')); print(' '.join(sorted(c for c,v in V.items() if v['kind']=='SYNTH')))")
for pass in 1 2; do
  RETRY=$(python3 -c "
import json,os
for c in '$CELLS'.split():
    p='$V/drive/'+c+'.json'
    ok=os.path.exists(p) and json.load(open(p)).get('ok')
    if not ok: print(c)" | tr '\n' ' ')
  echo "RETRY pass $pass: $RETRY"
  [ -z "${RETRY// /}" ] && break
  cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $V --commit $H --remote-root $B $RETRY > $A/drive_retry_c$pass.log 2>&1; grep -E ' (OK|FAIL) ' $A/drive_retry_c$pass.log
done
step S3 fetch
python3 $W/tools/hbm_die_v15/v16_fetch.py --views $V --remote-root $B --commit $H --contract $A/contract.json $CELLS > $A/fetch.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch.log
MISS=""; for c in $CELLS; do [ -f $V/synth/$c/meta.json ] || MISS="$MISS $c"; done
[ -n "$MISS" ] && { echo "SYNTH_MISSING$MISS"; echo "S3_FAIL: GEN needs every SYNTH view (no stubs)"; exit 13; }
step S4 gen
ssh ot-epyc4 "rm -rf $B/views && mkdir -p $B/views" && rsync -a $V/synth $V/views.json ot-epyc4:$B/views/ && scp -q $A/contract.json ot-epyc4:$B/views/contract.json \
  && scp -q $A/gen_d4g0.sh ot-epyc4:$B/gen_d4g0.sh || exit 14
$OTRUN --mem 64 --threads 2 --hosts ot-epyc4 --priority die --dir $B -- bash $B/gen_d4g0.sh > $A/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $A/gen.otrun
grep -q GEN_OK $A/gen.otrun || exit 14
scp -q ot-epyc4:$B/overreach.json ot-epyc4:$B/case/layout.png $A/ 2>/dev/null
ssh ot-epyc4 "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
step S5 grt
$OTRUN --mem 160 --threads 16 --hosts ot-epyc4 --priority die --dir $B/case -- env CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh ot-epyc4 "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log" > $A/grt_summary.txt 2>&1
cat $A/grt_summary.txt
echo CHAIN_D4G0_DONE
