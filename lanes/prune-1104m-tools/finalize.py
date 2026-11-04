#!/usr/bin/env python3
# PRUNE-1104M: lane-text word check on dir-class candidates, drop fragments, write manifests.
import re,glob,os,sys,time
H=os.path.expanduser('~')
LOG=re.compile(r'KIT-WAVE \[|\bLAUNCH\b|\bFAIL\b.*\bevid\b')
words=set()
files=[f for f in glob.glob(H+'/coord/lanes/*')+glob.glob(H+'/coord/*.md')+glob.glob(H+'/coord/*.txt')+glob.glob(H+'/coord/*.tsv')+glob.glob(H+'/coord/autopilot/*') if os.path.isfile(f) and os.path.getsize(f)<50e6 and 'PRUNE-' not in os.path.basename(f) and not f.endswith('log.txt')]
files.append(H+'/.local/state/fleet-viz/release_tree_plan_cache.json')
for f in files:
    try:
        for line in open(f,errors='replace'):
            if f.endswith('COORD-REVIEW-QUEUE.md') and LOG.search(line): continue
            words.update(re.findall(r'[\w.+=-]+',line))
    except OSError: pass
GEN=re.compile(r'^(attempt_\d+|run|runs|out|kit|kits|gen|lec|results|logs|reports|src|work|tmp|rtl|build|\d+|.{0,5})$')
for h in sys.argv[1:]:
    keep=[];drop=[];tot={'attempt':0,'dir':0,'wt':0}
    for l in open(f'/tmp/p1104m_cand_{h}.tsv'):
        host,p,gb,mt,cl,why=l.rstrip('\n').split('\t'); gb=float(gb)
        b=os.path.basename(p)
        if cl!='attempt':
            if gb<0.05: continue
            if not GEN.match(b) and b in words: drop.append((p,gb)); continue
        keep.append((host,p,gb,mt,cl,why)); tot[cl]+=gb
    with open(f'{H}/coord/lanes/PRUNE-1104M-{h}'+('-'+os.environ['TAG'] if os.environ.get('TAG') else '')+'.tsv','w') as o:
        o.write('path\tsize_GB\tlast_mtime\treason\tclass\n')
        for host,p,gb,mt,cl,why in keep: o.write(f'{host}:{p}\t{gb:.2f}\t{mt}\t{why}; idle rule met, unsigned, no .keep, unreferenced, no live process\t{cl}\n')
    print(h,'manifest rows',len(keep),{k:round(v,1) for k,v in tot.items()},'dropped by word check',len(drop),round(sum(x[1] for x in drop),1),'GB; top dropped',[(os.path.relpath(p,'/srv/opentallas-scratch2/claude'),g) for p,g in sorted(drop,key=lambda x:-x[1])[:6]])
