R=/srv/opentallas-scratch3/claude/rm48; O=/srv/opentallas-scratch3/claude/rm53; cd $R/repo || exit 1
BASE=c4d305902e0
rm -f tools/die_plan/vclk_measured_band.json
L="claude/kw-fix-36-wave-claims-1108:e1:eb85ff859b5 claude/kw-fix-36-eco-census-1108:e2:53e79ea9417 claude/kw-fix-36-queue-src-1108:e3:d4c56145f16 codex/eco-prerouted-clock-1113:e4:f79c00b83ca claude/kw-fix-36-gen-floor-1108:e5:0efc6e43a2b claude/head-forms-4-dsrep-1108:e6:ec3ebad7ba2"
RS="+refs/heads/main:refs/remotes/origin/main"; for e in $L; do RS="$RS +refs/heads/${e%%:*}:refs/rm53/$(echo $e|cut -d: -f2)"; done
timeout 400 git fetch -q origin $RS || { echo FETCHFAIL; exit 2; }
[ "$(git rev-parse --short=11 origin/main)" = $BASE ] || { echo MAINMOVED $(git rev-parse --short=11 origin/main); exit 3; }
for e in $L; do b=${e%%:*}; r=$(echo $e|cut -d: -f2); s=${e##*:}; t=$(git rev-parse refs/rm53/$r)
 case $t in $s*) ;; *) echo "MOVED $b $(echo $t|cut -c1-11)"; git merge-base --is-ancestor $s refs/rm53/$r || { echo NOTANC $b; exit 3; }; git update-ref refs/rm53/$r $(git rev-parse $s);; esac
 for bad in e305445bcb0 41b142a837b8 50de7435dc03 232da12b e5f7db2cb1 2b30f1fa0f 70aabf189f 99460b9df5c 7795a0b7964 85fa5e3902d b6bec7107c3 f43c321a2fa ab3e8c8cfae ad9b9cee600 f6cb13df; do git merge-base --is-ancestor $bad refs/rm53/$r 2>/dev/null && ! git merge-base --is-ancestor $bad origin/main 2>/dev/null && { echo NEVERTAKE $b $bad; exit 5; }; done
 echo "== $r $b n=$(git rev-list --count origin/main..refs/rm53/$r) $(git diff --stat origin/main...refs/rm53/$r | tail -1)"; git diff --name-only origin/main...refs/rm53/$r | cut -d/ -f1-3 | sort | uniq -c | sort -rn | head -5; done
git checkout -q --no-track -B rm53-e origin/main
for e in $L; do b=${e%%:*}; r=$(echo $e|cut -d: -f2)
 git merge -q --no-ff --no-edit -m "Merge ROOT-MERGE-53: $b

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" refs/rm53/$r || { git merge --abort; echo CONFLICT $b; exit 4; }; echo "$r -> $(git rev-parse --short=11 HEAD)"; done
echo DELETED: $(git diff --diff-filter=D --name-only origin/main HEAD | wc -l)
python3 -I tools/die_plan/schema.py dump-schema >/dev/null; git diff --quiet && echo schema-in-sync || { git diff --stat | cat; echo SCHEMA-DIFF; }
( git ls-files "tools/**/test_*.py" "tools/test_*.py" "physical/**/test_*.py"; ls tools/autopilot/test_*.py tools/die_plan/test_*.py tools/s81_suhc/test_*.py physical/die_plan/hbm_arch_cores/test_*.py tools/qwen_compute/test_*.py physical/die_plan/qc/test_*.py 2>/dev/null; for f in $(git diff --name-only origin/main HEAD | grep -E "\.(py|tcl|sh)$" | grep -v test_ | xargs -n1 basename | sed "s/\.[a-z]*$//" | sort -u); do git grep -l "$f" -- 'tools/**/test_*.py' 'physical/**/test_*.py' 'tools/test_*.py' 2>/dev/null; done; git diff --name-only origin/main HEAD | grep "test_.*\.py$" ) | sort -u > /tmp/rm53_e.lst; wc -l < /tmp/rm53_e.lst
rm -rf $O/e_t $O/e_b; nohup bash /tmp/rm48_test.sh $R/repo $O/e_t /tmp/rm53_e.lst >/dev/null 2>&1 &
cd ../base; rm -f tools/die_plan/vclk_measured_band.json; timeout 120 git fetch -q origin +refs/heads/main:refs/remotes/origin/main; git checkout -q --detach origin/main; git rev-parse --short=11 HEAD; git status --porcelain | head -3
nohup bash /tmp/rm48_test.sh $R/base $O/e_b /tmp/rm53_e.lst >/dev/null 2>&1 &
sleep 1; echo started
