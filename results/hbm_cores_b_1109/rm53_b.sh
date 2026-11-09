R=/srv/opentallas-scratch3/claude/rm48; cd $R/repo || exit 1
BASE=fed824b630c
rm -f tools/die_plan/vclk_measured_band.json
timeout 200 git fetch -q origin +refs/heads/main:refs/remotes/origin/main || { echo FETCHFAIL; exit 2; }
[ "$(git rev-parse --short=11 origin/main)" = $BASE ] || { echo MAINMOVED; exit 3; }
for r in ab1 ab2; do for bad in e305445bcb0 41b142a837b8 50de7435dc03 232da12b e5f7db2cb1 2b30f1fa0f 70aabf189f 99460b9df5c 7795a0b7964 85fa5e3902d b6bec7107c3 f43c321a2fa ab3e8c8cfae ad9b9cee600 f6cb13df; do git merge-base --is-ancestor $bad refs/rm53/$r 2>/dev/null && ! git merge-base --is-ancestor $bad origin/main 2>/dev/null && { echo NEVERTAKE $r $bad; exit 5; }; done; done
git checkout -q --no-track -B rm53-b origin/main
for e in claude/s81-svc-4-rt2-1108:ab2 claude/s81-svc-4-r5-1108:ab1; do b=${e%%:*}; r=${e##*:}
 git merge -q --no-ff --no-edit -m "Merge ROOT-MERGE-53: $b

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" refs/rm53/$r || { git merge --abort; echo CONFLICT $b; exit 4; }; echo "$r -> $(git rev-parse --short=11 HEAD)"; done
echo "AB-tested vs B:"; git diff --stat rm53-ab rm53-b | cat
echo DELETED: $(git diff --diff-filter=D --name-only origin/main HEAD | wc -l)
python3 -I tools/die_plan/schema.py dump-schema >/dev/null; git diff --quiet && echo schema-in-sync || echo SCHEMA-DIFF
timeout 200 git push -q origin rm53-b:refs/heads/claude/root-merge-53-train-b-1108 && echo pushed; git rev-parse HEAD
