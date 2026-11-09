import json,re,collections
Q='/srv/opentallas-scratch3/claude/qct11/start/';W='/srv/opentallas-scratch2/claude/qct11/wave/';import os
A='/srv/opentallas-scratch3/claude/codex-qc-compose-1113/bind_v4n_hc3_fixed2/rtl/'
plan=json.load(open(W+'plan/plan_qc53v4nS.json'))['partition_types']
rep=json.load(open(Q+'report.json'))
RR=re.compile(r'ot_dp_(?:landing_relay|rrelay)\s+(\w+)\s*\(([^;]*?)\);',re.S)
def pins(b): 
    return {m[1]:m[2].strip() for m in re.finditer(r'\.(\w+)\(([^()]*)\)',b)}
tot=collections.Counter();bad=[]
for n in rep:
    c=plan[n]['clock'];m_=plan[n]['module'];fn=next(x for x in (n+'.sv',m_+'__'+n+'.sv',m_+'.sv') if os.path.exists(W+'bind_v4nS/rtl/'+x));t=open(W+'bind_v4nS/rtl/'+fn,errors='ignore').read();o=open(A+fn,errors='ignore').read()
    def cnt(x): return sum(1 for m in RR.finditer(x) if m[1].startswith('u_cland_fstart') and pins(m[2]).get('rst_raw_n')=='cland_start_raw')
    a,b=cnt(o),cnt(t); tot['old_fstart_on_start_raw']+=a; tot['new_fstart_on_start_raw']+=b
    if b: bad.append((n,'fstart still on cland_start_raw',b))
    rr={m[1]:pins(m[2]) for m in RR.finditer(t)}
    # every START-chain reset is a local registered raw or a local copy, and per-net fanout on fstart resets
    fan=collections.Counter(p.get('rst_raw_n') for k,p in rr.items() if k.startswith('u_cland_fstart'))
    tot['max_fstart_reset_fanout']=max(tot['max_fstart_reset_fanout'],max(fan.values(),default=0))
    for kind,cfg in (('writer',c.get('landing_writer_start')),('reader',c.get('landing_reader_start'))):
        if not cfg: continue
        D=int(cfg['depth']);ph=D-int(bool(cfg.get('reuse_relay_origin')))
        for bus,br in cfg['branches'].items():
            names=[f'u_cland_{kind}_start_{bus}_{i}' for i in range(len(br['stages']))]
            miss=[x for x in names if x not in rr]
            tot[kind+'_stages']+=len(names)
            if miss: bad.append((n,kind,bus,'missing',miss[:2])); continue
            if len(br['stages'])!=ph: bad.append((n,kind,bus,'depth',len(br['stages']),ph))
            for i,x in enumerate(names[1:],1):
                if rr[x]['d']!=f'cland_{kind}_start_{bus}_{i-1}': bad.append((n,kind,bus,'chain',i,rr[x]['d']))
            for i,x in enumerate(names):
                if rr[x]['rst_raw_n']!=br['stages'][i]['raw_reset']: bad.append((n,kind,bus,'raw',i))
            last=f'cland_{kind}_start_{bus}_{len(names)-1}'
            if len(re.findall(r'\b'+last+r'\b',t))<2: bad.append((n,kind,bus,'last unused'))
print(dict(tot));print('BAD',len(bad),bad[:12])
