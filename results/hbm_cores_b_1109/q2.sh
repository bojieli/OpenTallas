R=/srv/opentallas-scratch2/claude/kw36/wt
cd $R; git version
A=$(git rev-parse 5178ea7aa279); B=$(git rev-parse e210d04c83)
T=$(git merge-tree --write-tree $A $B 2>&1 | head -1); echo tree $T
git rev-parse --verify -q $T^{tree} >/dev/null || { git merge-tree --write-tree $A $B 2>&1 | head -10 | cut -c1-160; exit 3; }
git diff --name-only $A $T > /tmp/kw36_paths.txt; wc -l < /tmp/kw36_paths.txt
python3 -I - "$T" <<'PY'
import subprocess,sys
R="/srv/opentallas-scratch2/claude/kw36/wt"; C=sys.argv[1]
paths=[l.strip() for l in open("/tmp/kw36_paths.txt") if l.strip()]
out=subprocess.run(["ssh","-o","ControlPath=none","epyc6","cd /srv/opentallas-scratch2/claude/kw35/src_e2rd && while read p; do if [ -e \"$p\" ]; then echo \"$(git hash-object --no-filters \"$p\") $p\"; else echo \"MISSING $p\"; fi; done"],input="\n".join(paths)+"\n",capture_output=True,text=True,timeout=120).stdout
tree={}
for p in paths:
    r=subprocess.run(["git","-C",R,"ls-tree",C,"--",p],capture_output=True,text=True).stdout.split()
    tree[p]=r[2] if len(r)>=3 else None
ok=bad=0;ex=[]
for l in out.splitlines():
    a,p=l.split(" ",1)
    if tree.get(p)==(None if a=="MISSING" else a): ok+=1
    else: bad+=1;ex.append((p,a[:8],(tree.get(p) or "-")[:8]))
print("match",ok,"diff",bad,ex[:12])
sys.exit(1 if bad or not ok else 0)
PY
rc=$?; echo verify_rc=$rc
[ $rc -eq 0 ] || exit 4
C=$(printf 'KW-FIX-36: exact identity of the KV wave source src_e2rd (5178ea7aa279 + e210d04c83)\n\nThe tree equals the composed source the KV wave kits are built from, for queue_src_exact.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n' | git commit-tree $T -p $A -p $B)
git push -q origin $C:refs/heads/claude/kw-fix-36-kv-e2rd-exact-1108 2>&1 | tail -1
echo COMMIT $C; git ls-remote origin claude/kw-fix-36-kv-e2rd-exact-1108 | cut -c1-60
