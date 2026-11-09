W=/srv/opentallas-scratch3/claude/rm49/wp; R=/srv/opentallas-scratch3/claude/rm48; O=/srv/opentallas-scratch3/claude/rm53
# stop only my AB run: processes whose cwd is W and the xargs feeding it from my list
for p in $(pgrep -u ubuntu xargs); do c=$(tr "\0" " " </proc/$p/cmdline 2>/dev/null); cw=$(readlink /proc/$p/cwd); [ "$cw" = "$W" ] && { echo kill-xargs $p; kill $p; }; done
sleep 1
for p in $(pgrep -u ubuntu -x python3) $(pgrep -u ubuntu -x bash) $(pgrep -u ubuntu timeout); do [ "$p" = "$$" ] && continue; [ "$(readlink /proc/$p/cwd 2>/dev/null)" = "$W" ] && { echo kill $p $(tr "\0" " " </proc/$p/cmdline | cut -c1-70); kill $p; }; done
sleep 2
cd $W || exit 1
git -C $R/repo sparse-checkout list > /tmp/rm53_sp.txt; wc -l < /tmp/rm53_sp.txt
git sparse-checkout set --no-cone --stdin < /tmp/rm53_sp.txt
ls tools/die_plan/schema.py || exit 2
git status --porcelain | grep -v '^??' | head -3
rm -rf $O/ab_t
python3 -I tools/die_plan/schema.py dump-schema >/dev/null; git diff --quiet && echo schema-in-sync || { git diff --stat | tail -3; echo SCHEMA-DIFF; }
( cat /tmp/rm53_aa.lst; git diff --name-only rm53-aa HEAD | grep "test_.*\.py$"; for f in $(git diff --name-only rm53-aa HEAD | grep -E "\.(py|tcl|sh)$" | grep -v test_ | xargs -n1 basename | sed "s/\.[a-z]*$//" | sort -u); do git grep -l "$f" -- 'tools/**/test_*.py' 'physical/**/test_*.py' 'tools/test_*.py' 2>/dev/null; done ) | sort -u > /tmp/rm53_ab.lst; wc -l < /tmp/rm53_ab.lst
comm -13 <(sort -u /tmp/rm53_aa.lst) /tmp/rm53_ab.lst > /tmp/rm53_ab_extra.lst; head /tmp/rm53_ab_extra.lst
nohup bash /tmp/rm48_test.sh $W $O/ab_t /tmp/rm53_ab.lst >/dev/null 2>&1 &
sleep 2; echo started; git rev-parse --short=11 HEAD; wc -l $O/aa_t/results.txt $O/aa_b/results.txt
