import os,re,subprocess,time,csv,collections,glob
C=os.path.expanduser('~/coord'); now=time.time()
q=[l for l in open(C+'/lanes/COORD-REVIEW-QUEUE.md',errors='replace') if 'UNOWNED-SWEEP' not in l and 'KIT-WAVE [' not in l and not l.startswith('FAILED') and 'AUTOPILOT' not in l]
# last ~6h of queue: keep last 1500 lines (cheap proxy)
qt='\n'.join(q[-1500:])
hand=''
for f in glob.glob(C+'/lanes/handoff/*.md'):
    if f.endswith('UNOWNED-SWEEP.md'):continue
    if now-os.path.getmtime(f)<6*3600: hand+=open(f,errors='replace').read()
fam=[k for k in ('S81-STALE-RELAUNCH','TYPE-S81-FLOWERR','TYPE-QC-FLOWERR','S81-COL-INHERIT') if k in qt or k in hand]
print('family lanes seen:',fam)
rows=list(csv.reader(open(C+'/lanes/STALE.tsv'),delimiter='\t'))[2:]
out=collections.defaultdict(list); cnt=collections.Counter()
for r in rows:
    if r[0]=='hbm' or len(r)<4:continue
    item=r[2]; named= item in qt or item in hand
    cnt[(r[0],'named' if named else 'UNNAMED')]+=1
    if not named: out[(r[0],r[1],r[3],r[5] if len(r)>5 else '')].append(item)
print(dict(cnt))
for k,v in out.items(): print(k,len(v),' '.join(x[:48] for x in v[:6]))
