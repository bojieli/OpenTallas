#!/bin/bash
# H-D4G chain gen0b (continuation of chain_d4g0.sh after its S2; H-D4G2 10-17 23:50) (local driver): S1 src trees on the fleet -> S2 SYNTH of every SYNTH cell -> S3 fetch -> S4 GEN on E4 -> S5 GRT on E4.
set -o pipefail
W=/home/ubuntu/wt/hd4g; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; B=/srv/opentallas-scratch/claude/hd4g/gen0; OTRUN=/home/ubuntu/bin/ot-run
V=$A/vplan
step() { echo "STEP $* $(date -Is)"; }
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
H=839b75eed; echo "HEAD $H (pinned: gen0 src tree on the fleet)"
step S2b wait_drive_then_retry
# H-D4G2 23:50: the first drive (pid 1471300) runs on; its ETM OOM-kills at 48 GB (idx_score, idx_topk_link, rc 137) are
# re-driven at 112 GB (vplan/jobs.tsv). Any other FAIL is re-driven once at its own size.
while kill -0 1471300 2>/dev/null; do sleep 120; done
CELLS=$(python3 -c "import json; V=json.load(open('$V/views.json')); print(' '.join(sorted(c for c,v in V.items() if v['kind']=='SYNTH')))")
RETRY=$(awk '$2=="FAIL"{print $1}' $A/drive.log | sort -u | tr '\n' ' ')
for c in $CELLS; do grep -q "^$c " $A/drive.log || RETRY="$RETRY $c"; done
echo "RETRY $RETRY"
if [ -n "${RETRY// /}" ]; then cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $V --commit $H --remote-root $B $RETRY > $A/drive_retry.log 2>&1; cat $A/drive_retry.log | grep -E ' (OK|FAIL) '; fi
step S3 fetch
python3 $W/tools/hbm_die_v15/v16_fetch.py --views $V --remote-root $B --commit $H --contract $A/contract.json $CELLS > $A/fetch.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch.log
MISS=""; for c in $CELLS; do [ -f $V/synth/$c/meta.json ] || MISS="$MISS $c"; done
[ -n "$MISS" ] && echo "SYNTH_MISSING$MISS"
[ -n "$MISS" ] && { echo "S3_FAIL: GEN needs every SYNTH view (no stubs)"; exit 13; }
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
