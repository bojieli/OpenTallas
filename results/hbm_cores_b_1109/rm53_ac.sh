R=/srv/opentallas-scratch3/claude/rm48; O=/srv/opentallas-scratch3/claude/rm53; cd $R/repo || exit 1
BASE=d28cf565d0f
rm -f tools/die_plan/vclk_measured_band.json
timeout 200 git fetch -q origin +refs/heads/main:refs/remotes/origin/main || { echo FETCHFAIL; exit 2; }
[ "$(git rev-parse --short=11 origin/main)" = $BASE ] || { echo MAINMOVED; exit 3; }
L="claude/die-head-87-coretap-esc-1108:aa1 claude/kw-fix-35cv-autoviews-1108:aa2 codex/qc-lec-escidx-1113:aa3 codex/qc-hc-kwrs-comments-1113:aa4 codex/hbm-gen-budget-1113:aa5 codex/hbm-unbound-input-1113:aa6 codex/kit-gen-vehicle-1113:aa7 claude/die-kv-93-dieclockpath-1108:aa9 codex/clock-density-f4-1113:aa10 claude/root-merge-53-ep-1108:aa11"
git checkout -q --no-track -B rm53-ac origin/main
for e in $L; do b=${e%%:*}; r=${e##*:}
 git merge -q --no-ff --no-edit -m "Merge ROOT-MERGE-53: $b

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" refs/rm53/$r || { git merge --abort; echo CONFLICT $b; exit 4; }; echo "$r -> $(git rev-parse --short=11 HEAD)"; done
echo "AA vs AC:"; git diff --stat rm53-aa rm53-ac | cat
echo DELETED: $(git diff --diff-filter=D --name-only origin/main HEAD | wc -l)
python3 -I tools/die_plan/schema.py dump-schema >/dev/null; git diff --quiet && echo schema-in-sync || echo SCHEMA-DIFF
git grep -lE "kit_wave|wave_claims" -- 'tools/**/test_*.py' 'physical/**/test_*.py' 'tools/test_*.py' | sort -u > /tmp/rm53_ac.lst; ls tools/autopilot/test_*.py >> /tmp/rm53_ac.lst; sort -u -o /tmp/rm53_ac.lst /tmp/rm53_ac.lst; comm -12 /tmp/rm53_ac.lst <(sort -u /tmp/rm53_aa.lst) > /tmp/rm53_ac2.lst; wc -l < /tmp/rm53_ac2.lst
rm -rf $O/ac_t; nohup bash /tmp/rm48_test.sh $R/repo $O/ac_t /tmp/rm53_ac2.lst >/dev/null 2>&1 &
sleep 1; echo started
