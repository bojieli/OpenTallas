#!/usr/bin/env python3
"""gather.py (PRUNE-AUDIT-1 11-07): global blockers for the Codex-tree prune -> $CP_ROOT/global.tsv (kind host target source).

Fixes over CODEX-PRUNE-1 gather.py:
 1. KW was written with r'\\\\b' (a literal backslash + b), so it matched no ordinary prose: no queue line ever became a blocker.
 2. Only the last 24 h of COORD-REVIEW-QUEUE.md was read. Now: the queue back to QDAYS (default 14), plus lanes/**, CODEX-LOG.md,
    CODEX-HANDOFF*, HANDOFF*, handoff/**, and coord/tmp text notes (which is where Codex wrote "retained").
 3. Relative and ellipsized cites ("E6 codex-kv08-observer-1105/cache", "epyc2 .../foo/bar", bare top names) count as QREL.
 4. Posts by the pruners themselves and AUTOPILOT FAILED rows do not count as retention (they name paths they removed or logged).
 5. Live inputs are hard blockers: every path in the spec.json of RUNNING/RETRY rows and of ENQUEUED rows whose queue state is
    live, and every path named on the command line of an ot-run client or scanned on the host's processes (kind A).
"""
import os,re,json,subprocess,glob,sys,time
ROOT=os.environ.get('CP_ROOT','/tmp/cp1106'); COORD=os.environ.get('COORD',os.path.expanduser('~/coord'))
QDAYS=float(os.environ.get('QDAYS','14'))
R=re.compile(r'(?:/srv/opentallas-scratch[0-9]*|/home/ubuntu/scratch-root|/home/ubuntu/scratch|/home/ubuntu)/[^\s"\'`\]\[,;()<>|*{}=:$\\]+')
# single backslash on purpose; test_prune_gather.py pins that this matches ordinary prose
KW=re.compile(r"\b(seed\w*|keep|kept|do not delete|don.t delete|resum\w+|protect\w*|retain\w*|preserv\w*|reus\w+|donor|source of|in use|still needs?|staged?|parked|restor\w+)\b",re.I)
# the old list's weak words (live, running, pending, next, base) still protect an exact absolute path in the window, not a relative cite
KW_WEAK=re.compile(r"\b(base|live|running|pending|next)\b",re.I)
PRUNER=re.compile(r'\[(?:CODEX-PRUNE|ARCHIVE-1106|PRUNE-\d|AUTOCLEAN|RETIRE-|PRUNE-AUDIT)[^\]]*->|AUTOPILOT ->')
BARE=re.compile(r'(?<![\w/.-])((?:wt/)?codex-[\w.+-]+(?:/[\w.+-]+)*)')
ELL=re.compile(r'(?:\.\.\.|…)/((?:[\w.+-]+/)*(?:wt/)?codex-[\w.+-]+(?:/[\w.+-]+)*)')
def line_blockers(l,src,emit):
    """emit blockers from one line of prose"""
    if PRUNER.search(l): return
    for mo in R.finditer(l):
        m=mo.group(0)
        if 'codex' not in m: continue
        w=l[max(0,mo.start()-200):mo.end()+200]
        if KW.search(w) or KW_WEAK.search(w): emit('Q','any',m,src)
    for rx in (BARE,ELL):
        for mo in rx.finditer(l):
            if KW.search(l[max(0,mo.start()-200):mo.end()+200]): emit('QREL','any',mo.group(1),src)
QARCH='lanes/archive/COORD-REVIEW-QUEUE-*.md'
def queue_window(coord,qdays,now=None):
    """(source, line number, line) of the review queue back to qdays: the rotated archives (oldest name first) then the live
    lanes/COORD-REVIEW-QUEUE.md, scanned as one text from the first post dated inside the window.  The live file keeps the
    source name 'queue' (older global.tsv rows use it); an archive line is '<archive basename>:<n>'."""
    lim=time.strftime('%Y-%m-%d %H:%M',time.localtime((time.time() if now is None else now)-qdays*86400))
    rows=[]
    for p in sorted(glob.glob(os.path.join(coord,QARCH)))+[os.path.join(coord,'lanes/COORD-REVIEW-QUEUE.md')]:
        if not os.path.isfile(p): continue
        src='queue' if p.endswith('/lanes/COORD-REVIEW-QUEUE.md') else os.path.basename(p)[:-3]
        with open(p,errors='replace') as f: rows+=[(src,i,l) for i,l in enumerate(f.read().split('\n'))]
    start=len(rows)
    for k,(src,i,l) in enumerate(rows):
        m=re.match(r'- (2026-\d\d-\d\d \d\d:\d\d)',l)
        if m and m.group(1)>=lim: start=k; break
    print('queue from',(rows[start][0],rows[start][1]) if start<len(rows) else None,'of',len(rows),'lines')
    return rows[start:]
def main():
    OUT=open(ROOT+'/global.tsv','w'); seen=set()
    def emit(k,h,t,s):
        t=os.path.normpath(t.rstrip('.:'))
        if (k,h,t) in seen: return
        seen.add((k,h,t)); OUT.write('%s\t%s\t%s\t%s\n'%(k,h,t,s[:80]))
    for f in [COORD+'/PROTECTED-DBS.txt',COORD+'/lanes/PROTECTED-DBS.txt',COORD+'/lanes/RETIRED-PROTECTION-EXTRAS.tsv',os.environ.get('UNION','/tmp/arch1106b/protected_union.tsv')]:
        n=0
        for l in open(f,errors='replace'):
            if l.startswith('#'): continue
            c=l.rstrip('\n').split('\t')
            if len(c)>=2 and c[1].startswith('/'):
                h=c[0] if c[0] in('epyc2','epyc4','epyc5','epyc6','intel1','intel2','local','localhost') else 'any'
                emit('P',h,c[1],os.path.basename(f)); n+=1
        print(f,n)
    def hub(cmd): return subprocess.run(['ssh','-n','-o','ControlPath=none','intel2',cmd],capture_output=True,text=True,timeout=300).stdout
    for f in 'kit_wave.json kit_wave_pending.tsv auto_resign.tsv auto_resign_suggest.tsv auto_resign_state.json OWNERS.tsv signed.tsv provisional.tsv codex_current_types_1105.json WATCHDOG.skip'.split():
        t=hub('cat ~/coord/autopilot/'+f); ms=R.findall(t)
        for m in set(ms): emit('A','any',m,f)
        print(f,len(ms))
    st=json.loads(hub('cat ~/coord/autopilot/kit_wave_state.json'))
    json.dump(st,open(ROOT+'/kit_wave_state.json','w'))
    open(ROOT+'/kit_wave_stages.tsv','w').write(hub('cat ~/coord/autopilot/kit_wave_stages.tsv'))
    # live wave specs
    LIVE=('RUNNING','QUEUED','PENDING','ENQUEUED')
    dirs=[v['dir'] for v in st['items'].values() if v.get('dir') and (v.get('status') in('RUNNING','RETRY-INFRA') or (v.get('status')=='ENQUEUED' and v.get('q_status') in LIVE))]
    r=subprocess.run(['ssh','-o','ControlPath=none','intel2','while read d; do cat "$d/spec.json" 2>/dev/null; echo; done'],input='\n'.join(dirs)+'\n',capture_output=True,text=True,timeout=300)
    n=0
    for m in set(R.findall(r.stdout)):
        emit('A','any',m,'live wave spec.json'); n+=1
    print('live wave specs',len(dirs),'paths',n)
    # queue: the rotated archives (lanes/archive/COORD-REVIEW-QUEUE-*.md, COORD-COMMIT-SPEED-1 11-13) and the live file
    for src,i,l in queue_window(COORD,QDAYS): line_blockers(l,'%s:%d'%(src,i),emit)
    # other notes
    TXT=('.md','.txt')
    docs=[p for p in glob.glob(COORD+'/lanes/**',recursive=True) if p.endswith(TXT) and not p.endswith('COORD-REVIEW-QUEUE.md') and not os.path.basename(p).startswith('COORD-REVIEW-QUEUE-') and '/lanes/prune/' not in p and os.path.basename(p)!='PROTECTED-DBS.txt']
    docs+=glob.glob(COORD+'/CODEX-LOG.md')+glob.glob(COORD+'/CODEX-HANDOFF*')+glob.glob(COORD+'/HANDOFF*')+glob.glob(COORD+'/handoff/**',recursive=True)+glob.glob(COORD+'/tmp/**/*.md',recursive=True)+glob.glob(COORD+'/tmp/**/*.txt',recursive=True)
    for p in sorted(set(docs)):
        if not os.path.isfile(p) or os.path.getsize(p)>64<<20: continue
        src=os.path.relpath(p,COORD)
        with open(p,errors='replace') as f:
            for i,l in enumerate(f,1): line_blockers(l,'%s:%d'%(src,i),emit)
    print('docs',len(docs))
    OUT.close()
if __name__=='__main__': main()
