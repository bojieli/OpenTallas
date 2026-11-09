R=/srv/opentallas-scratch3/claude/rm48; O=/srv/opentallas-scratch3/claude/rm53; mkdir -p $O; cd $R/repo || exit 1
BASE=d28cf565d0f
rm -f tools/die_plan/vclk_measured_band.json
timeout 500 git fetch -q origin +refs/heads/main:refs/remotes/origin/main +refs/heads/claude/hbm-hard-6-ep-1108:refs/rm53/ep_src || { echo FETCHFAIL; exit 2; }
[ "$(git rev-parse --short=11 origin/main)" = $BASE ] || { echo MAINMOVED $(git rev-parse --short=11 origin/main); exit 3; }
# EP: only the recipes commit
git checkout -q --detach origin/main
git cherry-pick -x c0501e8f63 >/dev/null 2>&1 || { git cherry-pick --abort; echo EP-CHERRY-CONFLICT; exit 4; }
git diff --stat HEAD~1 HEAD | tail -2
timeout 200 git push -q origin HEAD:refs/heads/claude/root-merge-53-ep-1108 || { echo EP-PUSHFAIL; exit 2; }
EP=$(git rev-parse HEAD); echo EP $EP
L="claude/die-head-87-coretap-esc-1108:aa1:cb13e19342a claude/kw-fix-35cv-autoviews-1108:aa2:18e54f8be90 codex/qc-lec-escidx-1113:aa3:a5644801c46 codex/qc-hc-kwrs-comments-1113:aa4:ab748ad669 codex/hbm-gen-budget-1113:aa5:a056e5a54e codex/hbm-unbound-input-1113:aa6:224a127d48 codex/kit-gen-vehicle-1113:aa7:7cb02e70902 codex/wave-claims-1113:aa8:5382e2a0ad0 claude/die-kv-93-dieclockpath-1108:aa9:251b11706a3"
RS=""; for e in $L; do RS="$RS +refs/heads/${e%%:*}:refs/rm53/$(echo $e|cut -d: -f2)"; done
RS="$RS +refs/remotes/origin/codex/clock-density-f4-1113:refs/rm53/aa10 +refs/heads/claude/root-merge-53-ep-1108:refs/rm53/aa11"
timeout 400 git fetch -q origin $RS || { echo FETCHFAIL2; exit 2; }
L="$L codex/clock-density-f4-1113:aa10:55bd0e1c2b3 claude/root-merge-53-ep-1108:aa11:$(git rev-parse --short=11 $EP)"
for e in $L; do b=${e%%:*}; r=$(echo $e|cut -d: -f2); s=${e##*:}; t=$(git rev-parse refs/rm53/$r)
 case $t in $s*) ;; *) echo "MOVED $b $(echo $t|cut -c1-11)"; git merge-base --is-ancestor $s refs/rm53/$r || { echo NOTANC $b; exit 3; }; git update-ref refs/rm53/$r $(git rev-parse $s);; esac
 for bad in e305445bcb0 41b142a837b8 50de7435dc03 232da12b e5f7db2cb1 2b30f1fa0f 70aabf189f 99460b9df5c 7795a0b7964 85fa5e3902d b6bec7107c3 f43c321a2fa ab3e8c8cfae ad9b9cee600 f6cb13df; do git merge-base --is-ancestor $bad refs/rm53/$r 2>/dev/null && ! git merge-base --is-ancestor $bad origin/main 2>/dev/null && { echo NEVERTAKE $b $bad; exit 5; }; done
 echo "== $r $b n=$(git rev-list --count origin/main..refs/rm53/$r) $(git diff --stat origin/main...refs/rm53/$r | tail -1)"; done
git checkout -q --no-track -B rm53-aa origin/main
for e in $L; do b=${e%%:*}; r=$(echo $e|cut -d: -f2)
 git merge -q --no-ff --no-edit -m "Merge ROOT-MERGE-53: $b

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" refs/rm53/$r || { git merge --abort; echo CONFLICT $b; exit 4; }; echo "$r -> $(git rev-parse HEAD)"; done
echo DELETED: $(git diff --diff-filter=D --name-only origin/main HEAD | wc -l)
python3 -I tools/die_plan/schema.py dump-schema >/dev/null; git diff --quiet && echo schema-in-sync || { git diff --stat | cat; echo SCHEMA-DIFF; }
( git ls-files "tools/**/test_*.py" "tools/test_*.py" "physical/**/test_*.py"; ls tools/autopilot/test_*.py tools/die_plan/test_*.py tools/s81_suhc/test_*.py physical/die_plan/hbm_arch_cores/test_*.py tools/qwen_compute/test_*.py physical/die_plan/qc/test_*.py 2>/dev/null; for f in $(git diff --name-only origin/main HEAD | grep -E "\.(py|tcl|sh)$" | grep -v test_ | xargs -n1 basename | sed "s/\.[a-z]*$//" | sort -u); do git grep -l "$f" -- 'tools/**/test_*.py' 'physical/**/test_*.py' 'tools/test_*.py' 2>/dev/null; done; git diff --name-only origin/main HEAD | grep "test_.*\.py$" ) | sort -u > /tmp/rm53_aa.lst; wc -l < /tmp/rm53_aa.lst
rm -rf $O/aa_t $O/aa_b; nohup bash -c "bash /tmp/rm48_test.sh $R/repo $O/aa_t /tmp/rm53_aa.lst" >/dev/null 2>&1 &
cd ../base; rm -f tools/die_plan/vclk_measured_band.json; timeout 120 git fetch -q origin +refs/heads/main:refs/remotes/origin/main; git checkout -q --detach origin/main; git rev-parse --short=11 HEAD; git status --porcelain | head -3
nohup bash -c "bash /tmp/rm48_test.sh $R/base $O/aa_b /tmp/rm53_aa.lst" >/dev/null 2>&1 &
sleep 1; echo started
