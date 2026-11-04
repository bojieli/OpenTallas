#!/usr/bin/env python3
# PRUNE-1104M: COORD 05:36 (2)(b). Attempts whose ONLY autopilot citations may go: job record DONE-CRASH, WITHDRAWN, CANCELLED, or a citation naming another host (any status except RUNNING).
# Blocks: RUNNING on any host; same-host DONE-STRUCTURAL, NEAR-MISS or any other status; same-host stage row unless SUPERSEDED or FAIL with a non-structural class; same-host queue or structural row with no terminal job.
# Output /tmp/p1104m_term_<host>.txt. usage: term.py host. Other corpora (plan cache, lane text, live) are checked by cands.py and del.py.
import json,re,os,sys,collections
h=sys.argv[1]; A=os.path.expanduser('~/coord/autopilot/')
OK={'DONE-CRASH','WITHDRAWN','CANCELLED'}
PAT=re.compile(r'(?:([\w-]+):)?(/srv/opentallas-scratch2?/\S*?/items/[^/\s\'"]+/attempt_\d+)(?![\w.-])')
cit=collections.defaultdict(list)  # path -> (src, host or None, status)
for jid,j in json.load(open(A+'state.json'))['jobs'].items():
    s=json.dumps(j); st=j.get('status'); jh=j.get('ran_on') or j.get('host')
    for m in PAT.finditer(s):
        cit[m.group(2).replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/')].append(('job',m.group(1) or jh,st))
rows=list(open(A+'kit_wave_stages.tsv',errors='replace')); hdr=rows[0].rstrip('\n').split('\t'); ist=hdr.index('status'); icl=hdr.index('class')
for l in rows[1:]:
    f=l.rstrip('\n').split('\t')
    if len(f)<=icl: continue
    for m in PAT.finditer(l): cit[m.group(2).replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/')].append(('stage',m.group(1),f[ist]+'/'+f[icl]))
for fn,src in (('queue.tsv','queue'),('structural.tsv','structural')):
    for l in open(A+fn,errors='replace'):
        for m in PAT.finditer(l): cit[m.group(2).replace('/srv/opentallas-scratch/','/srv/opentallas-scratch2/')].append((src,m.group(1),'?'))
allow=[];why=collections.Counter()
for p,cs in cit.items():
    terminal_job=any(c[0]=='job' and c[1]==h and c[2] in OK for c in cs)
    bad=None
    for src,ch,st in cs:
        if 'RUNNING' in str(st): bad='running';break
        if ch!=h and ch is not None: continue
        if src=='job' and st not in OK: bad='job:'+str(st);break
        if src=='stage':
            s0,_,cl=st.partition('/')
            if not(s0=='SUPERSEDED' or (s0=='FAIL' and cl not in('STRUCTURAL','NEAR-MISS'))): bad='stage:'+st;break
        if src=='structural': bad='structural';break
        if src=='queue' and not terminal_job: bad='queue-no-terminal-job';break
    if bad: why[bad.split(':')[0]+':'+bad.split(':')[-1] if ':' in bad else bad]+=1
    else: allow.append(p)
open(f'/tmp/p1104m_term_{h}.txt','w').write(''.join(x+'\n' for x in allow))
print(h,'autopilot-cited attempts',len(cit),'allowed',len(allow),'blocked',dict(why.most_common(12)))
