#!/bin/bash
# DIE-RECHECK-1 watcher (ADVISORY, DO_NOT_COUNT; never a gate).  COORD 11-10: re-run after every plan event, like
# lanes/plan-route-1/flags_cron.sh.  Every 30 min:
#  (1) copy the release cache (plans of record = tools/release_tree_plan.py PLANS) + NEAR-CLOSE.tsv to epyc8, move the
#      epyc8 watch checkout to origin/main, run die_recheck.py (--state: re-runs only when a plan sha or the signed-view
#      set changed) -> rows appended to lanes/DIE-RECHECK.tsv, per-die DELTA lines;
#  (2) S81: if the S81 plan sha changed, launch s81_clock_auto.sh through ot-run on epyc8 (balanced die clock +
#      clock-only die route + related-pair die STA); when its clock_summary.json lands, post the clock/STA delta;
#  (3) post one queue line to the die owners whose rows changed, through coord-commit.sh.
# Disable: remove the "die-recheck-1/die_recheck_cron.sh" line from the localhost crontab.
set -u
cd /
W=/srv/opentallas-scratch2/claude/die-recheck-1
C=/home/ubuntu/coord
LOG=/home/ubuntu/.local/state/die-recheck-1.log
LOCK=/home/ubuntu/.local/state/die-recheck-1.lock
SSH="timeout 120 ssh -n -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=20 epyc8"
mkdir -p /home/ubuntu/.local/state
exec 9>"$LOCK"; flock -n 9 || exit 0
S="$(date '+%Y-%m-%d %H:%M %Z')"
timeout 120 scp -q -o ControlPath=none -o BatchMode=yes /home/ubuntu/.local/state/fleet-viz/release_tree_plan_cache.json \
  "$C/lanes/NEAR-CLOSE.tsv" epyc8:$W/scripts/ || { echo "$S scp failed" >> "$LOG"; exit 0; }
$SSH "cd /; git -C $W/src fetch -q origin main 2>/dev/null; git -C $W/watch checkout -q --detach origin/main" >> "$LOG" 2>&1
# hosts that answer now (signoff.json reads go only there)
HOSTS=$($SSH "for h in epyc2 epyc4 epyc7 intel1 intel2; do timeout 15 ssh -n -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=8 \$h true 2>/dev/null && printf '%s,' \$h; done; echo epyc8")
# S81 die clock state -> clock note
S81P=$(python3 -I -c "import json;print([p['plan_src'] for p in json.load(open('/home/ubuntu/.local/state/fleet-viz/release_tree_plan_cache.json'))['plans'].values() if p['die']=='s81'][0])")
S81SHA=$($SSH "sha256sum $W/watch/$S81P | cut -c1-12")
CK=$($SSH "test -f $W/s81/auto/$S81SHA/clock_summary.json && python3 -I -c \"
import json;s=json.load(open('$W/s81/auto/$S81SHA/clock_summary.json'));t=s.get('sta',{});m=(s.get('metrics') or {}).get('TT') or {}
f=lambda k:t.get(k,{})
print('S81 die clock (balanced feed) plan %s: taps TT %s-%s ps; intra TT setup %s / FF hold %s (neg %s); FF kit-contract %s; landed FF verdict %s' % (s['sha'], m.get('tap_arr_min'), m.get('tap_arr_max'), f('TT_intra').get('setup'), f('FF_intra').get('hold'), f('FF_intra').get('hold_neg'), (f('FF_intra').get('kit_contract') or {}).get('hold'), (f('FF_landed').get('landing') or {}).get('verdict')))
\" || { test -d $W/s81/auto/$S81SHA && echo 'S81 die clock on plan $S81SHA RUNNING'; } || echo 'S81 die clock on plan $S81SHA NOT BUILT'")
NOTE=$(python3 -I -c "import json,sys;print(json.dumps({'s81':sys.argv[1],'hbm':'no die clock on plan (HBM.CLK BLOCKED)','qwen_compute':'no die clock on plan','qwen_kvsys':'no die clock on plan','s81_head':'no die clock on plan'}))" "$CK")
OUT=$($SSH "cd $W && python3 -I scripts/die_recheck.py --cache scripts/release_tree_plan_cache.json --repo watch \
  --tools watch/tools/die_plan --near-close scripts/NEAR-CLOSE.tsv --out-dir ledger/auto --local epyc8 --hosts-ok '$HOSTS' \
  --state ledger/state.json --tsv ledger/DIE-RECHECK.tsv --clock-note '$NOTE' 2>&1 | grep -E '^DELTA|nothing to do|Traceback|Error'" 2>&1)
echo "$S ledger: $(echo "$OUT" | tr '\n' '|')" >> "$LOG"
# (2) S81 die clock on a new plan
if ! $SSH "test -d $W/s81/auto/$S81SHA"; then
  if $SSH "ls $W/s81/auto/*/RUNNING >/dev/null 2>&1"; then
    echo "$S s81 plan $S81SHA new; previous auto run still RUNNING, next pass" >> "$LOG"
  else
    $SSH "mkdir -p $W/s81/auto/$S81SHA && touch $W/s81/auto/$S81SHA/RUNNING"
    nohup timeout 14400 ssh -n -o ControlPath=none intel2 "~/.local/bin/ot-run --mem 128 --threads 24 --priority die --hosts epyc8 --dir $W -- bash -c '$W/scripts/s81_clock_auto.sh $W/watch $S81P $S81SHA; rm -f $W/s81/auto/$S81SHA/RUNNING'" \
      > /home/ubuntu/.local/state/die-recheck-1-s81-$S81SHA.log 2>&1 &
    echo "$S s81 plan $S81SHA new -> s81_clock_auto launched" >> "$LOG"
  fi
fi
CKPOST=""
if $SSH "test -f $W/s81/auto/$S81SHA/clock_summary.json -a ! -f $W/s81/auto/$S81SHA/posted"; then
  CKPOST=$($SSH "cd $W/s81/auto && python3 -I -c \"
import json, os
new = json.load(open('$S81SHA/clock_summary.json'))
old = json.load(open('last_posted.json')) if os.path.exists('last_posted.json') else None
def flat(s):
    o = {}
    for k, v in (s or {}).get('sta', {}).items():
        for f in ('setup', 'setup_neg', 'hold', 'hold_neg'): o[k + '.' + f] = v.get(f)
        if 'kit_contract' in v: o[k + '.kit_contract_hold'] = v['kit_contract']['hold']; o[k + '.kit_contract_neg'] = v['kit_contract']['neg']
        if 'landing' in v: o[k + '.landing_damage_max'] = v['landing']['damage_max']
    for c, m in ((s or {}).get('metrics') or {}).items():
        for f, x in m.items(): o[c + '.' + f] = x
    return o
a, b = flat(old), flat(new)
print('S81 die clock/STA on plan %s vs %s: ' % (new['sha'], (old or {}).get('sha', 'none')) + '; '.join('%s %s -> %s' % (k, a.get(k), b[k]) for k in sorted(b) if a.get(k) != b[k]))
\" && cp $S81SHA/clock_summary.json last_posted.json && touch $S81SHA/posted")
fi
# post on a plan event or a die-level outcome change; read-count drift (dead hosts, one more signed view) stays in the TSV only
CH=$(echo "$OUT" | grep '^DELTA' | grep -E 'plan_sha|port_hold_below0|worst_port_hold|max_early_tap|worst_xcorner|first run')
[ -n "$CH$CKPOST" ] || exit 0
$SSH "cat $W/ledger/DIE-RECHECK.tsv" > "$C/lanes/DIE-RECHECK.tsv.new" && [ -s "$C/lanes/DIE-RECHECK.tsv.new" ] && \
  mv "$C/lanes/DIE-RECHECK.tsv.new" "$C/lanes/DIE-RECHECK.tsv" || exit 0
TO=$(echo "$CH $CKPOST" | python3 -I -c "
import sys; t = sys.stdin.read(); m = {'s81': 'DIE-S81-85', 'hbm': 'DIE-HBM-97', 'qwen_compute': 'DIE-QC-97', 'qwen_kvsys': 'KV-PLAN-2, DIE-KV-97', 's81_head': 'HEAD-92'}
o = [v for k, v in m.items() if ('DELTA %s:' % k) in t or (k == 's81' and 'S81 die clock' in t)]
print(', '.join(o + ['COORD']))")
{ echo "- $(date '+%Y-%m-%d %H:%M %Z') RESULT [DIE-RECHECK-1 -> $TO] plan event / new sign-off -> die re-check (stamp $S; ADVISORY, DO_NOT_COUNT; automatic, lanes/die-recheck-1/die_recheck_cron.sh; rows lanes/DIE-RECHECK.tsv):"
  echo "$CH" | sed 's/^/    /'
  [ -n "$CKPOST" ] && echo "    $CKPOST"; } >> "$C/lanes/COORD-REVIEW-QUEUE.md"
cd "$C" && timeout 280 "$C/bin/coord-commit.sh" "DIE-RECHECK-1 auto re-check $S

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" lanes/COORD-REVIEW-QUEUE.md lanes/DIE-RECHECK.tsv >> "$LOG" 2>&1
