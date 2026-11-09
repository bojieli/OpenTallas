R=/srv/opentallas-scratch3/claude/rm48; O=/srv/opentallas-scratch3/claude/rm53; W=/srv/opentallas-scratch3/claude/rm49/wp
for p in $(pgrep -u ubuntu . ); do [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$W" ] && { echo BUSY $p; exit 3; }; done
cd $W || exit 1; git status --porcelain | grep -v '^??' | head -3
diff <(git -C $R/repo sparse-checkout list | sort) <(git sparse-checkout list | sort) >/dev/null && echo sparse-same || { echo sparse-differs-setting; git sparse-checkout set --no-cone $(git -C $R/repo sparse-checkout list | tr '\n' ' ') ; }
rm -f tools/die_plan/vclk_measured_band.json
git checkout -q --no-track -B rm53-ab rm53-aa || exit 2
for e in claude/s81-svc-4-rt2-1108:ab2 claude/s81-svc-4-r5-1108:ab1; do b=${e%%:*}; r=${e##*:}
 git merge -q --no-ff --no-edit -m "Merge ROOT-MERGE-53: $b

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" refs/rm53/$r || { git merge --abort; echo CONFLICT $b; exit 4; }; echo "$r -> $(git rev-parse HEAD)"; done
echo DELETED: $(git diff --diff-filter=D --name-only rm53-aa HEAD | wc -l)
python3 -I tools/die_plan/schema.py dump-schema >/dev/null; git diff --quiet && echo schema-in-sync || { git diff --stat | cat; echo SCHEMA-DIFF; }
( cat /tmp/rm53_aa.lst; git diff --name-only rm53-aa HEAD | grep "test_.*\.py$"; for f in $(git diff --name-only rm53-aa HEAD | grep -E "\.(py|tcl|sh)$" | grep -v test_ | xargs -n1 basename | sed "s/\.[a-z]*$//" | sort -u); do git grep -l "$f" -- 'tools/**/test_*.py' 'physical/**/test_*.py' 'tools/test_*.py' 2>/dev/null; done ) | sort -u > /tmp/rm53_ab.lst; wc -l < /tmp/rm53_ab.lst
comm -13 <(sort -u /tmp/rm53_aa.lst) /tmp/rm53_ab.lst > /tmp/rm53_ab_extra.lst; wc -l < /tmp/rm53_ab_extra.lst
rm -rf $O/ab_t; nohup bash -c "bash /tmp/rm48_test.sh $W $O/ab_t /tmp/rm53_ab.lst" >/dev/null 2>&1 &
sleep 1; echo started; git rev-parse --short=11 HEAD
