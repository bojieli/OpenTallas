R=/srv/opentallas-scratch2/claude/kw36/wt
cd $R; git fetch -q origin 2>/dev/null
C=54d0be50304
git cat-file -t $C; git log -1 --format='%h %p %s' $C | cut -c1-150
for s in 5178ea7aa279 e210d04c83; do git merge-base --is-ancestor $s $C && echo "anc $s" || echo "NOT anc $s"; done
git diff --name-only 5178ea7aa279 $C | wc -l
git diff --name-only 5178ea7aa279 $C > /tmp/kw36_paths.txt
python3 -I - <<'PY'
import subprocess,hashlib
R="/srv/opentallas-scratch2/claude/kw36/wt"; C="54d0be50304"
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
    else:
        bad+=1;ex.append((p,a[:8],(tree.get(p) or "-")[:8]))
print("match",ok,"diff",bad,ex[:12])
PY
python3 -I -c "
import json
c=json.load(open('/home/ubuntu/coord/autopilot/kit_wave.json'))
for k,d in c['dies'].items():
    if isinstance(d,dict): print(k,d.get('flow_tag'),d.get('src_sha','')[:11])
print(c.get('flow_tag'))
"
grep -n "flow-20261108-e[a-z]-\|flow_tag" ~/coord/lanes/COORD-REVIEW-QUEUE.md | tail -5 | cut -c1-260
