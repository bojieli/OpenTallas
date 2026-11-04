import json,re,collections,subprocess as sp
s=json.load(open('/tmp/p1104n_ap/kit_wave_state.json'))['items']
by=collections.defaultdict(list)
for v in s.values(): by[(v['die'],v['item'],v['event'])].append(v)
LIVE={'RUNNING','WAITING','LAUNCHING','ENQUEUED'}
hdr=None; out=[]
L=list(open('/tmp/p1104n_ltc_epyc2.tsv')); hdr=L[0].rstrip('\n')
for l in L[1:]:
    f=l.rstrip('\n').split('\t')
    if f[4]!='no-record' or float(f[1])<0.01 or 'codex-kv-wave-1131' in f[0]: continue
    die,ev,it=f[6],f[7],f[8]; m=re.search(r'attempt_(\d+)$',f[0]); n=int(m.group(1)) if m else 0
    rows=by.get((die,it,ev),[])
    if not rows: continue
    v=max(rows,key=lambda x:x.get('attempt') or 0); k=str(v.get('kit') or v.get('evidence') or ''); h=k.split(':')[0]; a=v.get('attempt') or 0
    if not h or h=='epyc2' or ':' not in k: continue
    fail=(v.get('status')=='FAIL')  # COORD ruled on my table: row FAIL. ENQUEUED with queue FAIL stays, asked separately
    if fail and a>=n: out.append((f,'FAIL',h,k)); continue
    if a>n:
        p=k.split(':',1)[1]; ok=sp.run(['ssh','-n','-o','ControlPath=none',h,f'test -e {p} && echo y'],capture_output=True,text=True).stdout.strip()
        if ok=='y': out.append((f,f'higher attempt_{a}',h,k))
        else: print('no copy',f[0][-60:],k[-70:])
tot=sum(float(o[0][1]) for o in out); print(len(out),round(tot,1))
with open('/home/ubuntu/coord/lanes/PRUNE-1104N-epyc2-lt3.tsv','w') as w:
    w.write(hdr+'\twhy\tother_host_record\n')
    for f,y,h,k in sorted(out,key=lambda o:-float(o[0][1])): w.write('\t'.join(f)+f'\t{y}\t{k}\n')
open('/tmp/p1104n_lt3.txt','w').write(''.join(o[0][0].split(':',1)[1]+'\n' for o in out))
for f,y,h,k in sorted(out,key=lambda o:-float(o[0][1]))[:14]: print(f[1],y,h,f[0].split('/claude/')[1][-70:])
