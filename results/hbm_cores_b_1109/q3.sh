cd /srv/opentallas-scratch2/claude/kw36/wt
A=$(git rev-parse cad9c038fb); B=$(git rev-parse 9ba1e6f86e2)
T=$(git merge-tree --write-tree --merge-base=$B^ $A $B | head -1); git rev-parse --verify -q $T^{tree} >/dev/null || { echo conflict; exit 3; }
git diff --name-only $A $T | tee /tmp/kw36_p2.txt | cut -c1-80
for h in epyc6 epyc4 epyc5 intel1; do
  S=/srv/opentallas-scratch2/claude/kw35/src_cad9p
  ssh -n -o ControlPath=none $h "test -d $S && echo $h has_src || echo $h no_src"
done
H=$(for h in epyc6 epyc4 epyc5 intel1; do ssh -n -o ControlPath=none $h "test -f /srv/opentallas-scratch2/claude/kw35/src_cad9p/tools/autopilot/prov_view.py && echo $h" ; done | head -1)
ok=1
for p in $(cat /tmp/kw36_p2.txt); do
  a=$(ssh -n -o ControlPath=none $H "git hash-object --no-filters /srv/opentallas-scratch2/claude/kw35/src_cad9p/$p")
  b=$(git rev-parse $T:$p)
  [ "$a" = "$b" ] && echo "same $p" | cut -c1-70 || { echo "DIFF $p $a $b" | cut -c1-120; ok=0; }
done
[ $ok = 1 ] || exit 4
C=$(printf 'KW-FIX-36: exact identity of the HBM wave source src_cad9p (cad9c038fb + providx 9ba1e6f86e2)\n\nThe tree equals the composed source of the kits pinned to that string, for queue_src_exact.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n' | git commit-tree $T -p $A -p $B)
git push -q origin $C:refs/heads/claude/kw-fix-36-hbm-cad9p-exact-1108 2>&1 | tail -1
echo COMMIT $C
