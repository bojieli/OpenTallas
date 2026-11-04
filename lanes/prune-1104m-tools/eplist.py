#!/usr/bin/env python3
# PRUNE-1104M read-only: largest idle dirs with no SIGNED record on a host walk. usage: eplist.py walk.tsv host min_gb idle_h
import sys,os,re,time,collections,subprocess
w,host,ming,idle=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]); now=time.time(); ROOT='/srv/opentallas-scratch2/claude'
rows={};kids=collections.defaultdict(list)
for l in open(w):
    d,p,kb,nw,sig,keep,fl,git=l.rstrip('\n').split('\t'); rows[p]=(int(kb),int(nw),int(sig),int(keep),int(git)); kids[os.path.dirname(p)].append(p)
cache=open(os.path.expanduser('~/.local/state/fleet-viz/release_tree_plan_cache.json'),errors='replace').read()
live=[l.strip().rstrip('/;') for l in open(f'/tmp/p1104m_live_{host}.txt') if l.strip()]
NEVER=re.compile(r'(^|/)(tok-[^/]*|kv-fn-[^/]*|codex-ds-[^/]*|[^/]*veh[^/]*|moved|rescue|hub-[^/]*)(/|$)')
out=[]
def visit(p):
    kb,nw,sig,keep,git=rows[p]; rel=p[len(ROOT)+1:]
    if NEVER.search(rel) and rel: return
    age=(now-nw)/3600
    if p!=ROOT and sig==0 and age>=idle:
        if kb>=ming*1e6: out.append((kb,age,keep,git,rel))
        return
    for c in kids.get(p,()): visit(c)
visit(ROOT)
out.sort(reverse=True)
own=collections.Counter()
Q=[l for l in open(os.path.expanduser('~/coord/lanes/COORD-REVIEW-QUEUE.md'),errors='replace').readlines()[-4000:] if 'PRUNE-11' not in l]; Q=''.join(Q)
print('size_GB\tidle\tlast_mtime\towner\tpath\tflags')
def owner(r):
    t=r.split('/')[0]
    if t.startswith('codex-') and 'wave' not in t: return 'Codex (.keep or owner release)'
    if t.startswith('codex-kv-wave') or r.startswith('kit-wave/qwen_kvsys'): return 'autopilot KV: KW-FIX-6, DIE-KV-67'
    if r.startswith('kit-wave/hbm'): return 'autopilot HBM: KW-FIX-6, DIE-HBM-63'
    if r.startswith('kit-wave/s81') or 'wave' in t: return 'autopilot: KW-FIX-6'
    if t.startswith('flow'): return 'FLOW-27'
    if t=='wt': return 'wt: '+re.sub(r'-?\\d*$','',r.split('/')[1])[:14]
    if re.match(r'(s81|die-s81|ds5)',t): return 'DIE-S81-53'
    if re.match(r'(dkv|die-kv)',t): return 'DIE-KV-67'
    if re.match(r'(hbm|die-hbm|dh6)',t): return 'DIE-HBM-63'
    if re.match(r'(dh|die-head|head)',t): return 'DIE-HEAD-60'
    if re.match(r'(dq|die-qc|qc)',t): return 'DIE-QC-68'
    return 'unowned: '+t
summ=collections.Counter()
for kb,age,keep,git,rel in out:
    summ[owner(rel)]+=kb
for kb,age,keep,git,rel in out:
    p=ROOT+'/'+rel
    fl=[]
    if keep: fl.append('keep-inside')
    if git: fl.append('git')
    if rel in cache: fl.append('plan-cache')
    if any(x==p or x.startswith(p+'/') for x in live): fl.append('LIVE')
    if rel in Q: fl.append('lane-text')
    print(f"{kb/1e6:.1f}\t{age:.1f}h\t{time.strftime('%m-%d %H:%M',time.localtime(now-age*3600))}\t{owner(rel)}\t{rel}\t{','.join(fl)}")
print('# TOTAL rows',len(out),'GB %.1f'%(sum(x[0] for x in out)/1e6))
for k,v in summ.most_common(): print('# OWNER',k,'GB %.1f'%(v/1e6))
