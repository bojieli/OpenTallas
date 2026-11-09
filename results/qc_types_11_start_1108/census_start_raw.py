import json,re,os,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/qct11/wave/src/tools/die_plan')
Q='/srv/opentallas-scratch3/claude/qct11/start/';R='/srv/opentallas-scratch3/claude/codex-qc-compose-1113/';D=R+'bind_v4n_hc3_fixed2/rtl/'
plan=json.load(open(R+'plan/plan_qc53v4n.json'))['partition_types']
RR=re.compile(r'\bot_dp_landing_relay\s+(u_cland_fstart\w*)\s*\(([^;]*?)\);',re.S)
done=json.load(open(Q+'report.json'));out=[];nof=[];zero=[]
for n,t in plan.items():
    f=D+t['module']+'__'+n+'.sv'
    if not os.path.exists(f): f=D+t['module']+'.sv'
    if not os.path.exists(f): f=D+n+'.sv'
    if not os.path.exists(f): nof.append(n); continue
    b=open(f,errors='ignore').read()
    k=sum(1 for m in RR.finditer(b) if re.search(r'\.rst_raw_n\(\s*cland_start_raw\s*\)',m[2]))
    if k: out.append((n,k,n in done))
    else: zero.append(n)
print('no file',nof);print('with start_raw',len(out),'already in event',sum(1 for x in out if x[2]));print('new',[(a,b) for a,b,c in out if not c]);print('zero',len(zero))
open(Q+'list3.txt','w').write(' '.join(sorted(a for a,b,c in out)))
