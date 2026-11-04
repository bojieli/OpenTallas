#!/usr/bin/env python3
# PRUNE-1103J: build the reference corpus (read-only). strong = counter cache, fleet-viz state, autopilot state, protected list.
# lane = coord text files minus autopilot KIT-WAVE FAIL/LAUNCH log lines (COORD ruling 20:54).
import os,re,glob,json
H=os.path.expanduser('~')
strong=[H+'/.local/state/fleet-viz/release_tree_plan_cache.json',H+'/coord/PROTECTED-DBS.txt']
strong+=glob.glob(H+'/.local/state/fleet-viz/*.json')
strong+=[f for f in glob.glob(H+'/coord/autopilot/*') if os.path.isfile(f) and not f.endswith(('log.txt','.lock'))]
strong+=glob.glob(H+'/.local/state/ot-run/spill_pending/*')
lane=[f for f in glob.glob(H+'/coord/lanes/*')+glob.glob(H+'/coord/*.md')+glob.glob(H+'/coord/*.txt')+glob.glob(H+'/coord/*.tsv') if os.path.isfile(f) and os.path.getsize(f)<50e6 and not re.search(r'PRUNE-',os.path.basename(f))]
LOG=re.compile(r'KIT-WAVE \[|\bLAUNCH\b|\bFAIL\b.*\bevid\b')
T=re.compile(r'[\w.+=@-]+(?:/[\w.+=@-]+)+')
out={}
for kind,fs in (('S',strong),('L',lane)):
    for f in fs:
        try:
            for line in open(f,errors='replace'):
                if kind=='L' and f.endswith('COORD-REVIEW-QUEUE.md') and LOG.search(line): continue
                for t in T.findall(line):
                    if t.count('/')>=1 and len(t)<400:
                        k=t.strip('/.')
                        if kind=='S' or k not in out: out[k]=kind
        except OSError: pass
with open('/tmp/p1103j_refs.tsv','w') as o:
    for k,v in out.items(): o.write(f'{v}\t{k}\n')
print(len(out),sum(1 for v in out.values() if v=='S'))
