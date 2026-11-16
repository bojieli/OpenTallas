import os,sys,glob,time,re,subprocess as S
apply=sys.argv[1]=='apply'; MIN=int(sys.argv[2]); R='/srv/opentallas-scratch2/claude'
CUR=re.compile(r'B6gslsw|B6gE|B6gF1|B6gErr|TRIDX2|S4Q3B|S4q3c|S4Q3CB|S4q4c|S4Q3BSC|kvgeom6|kvgeom7|7u\b|7r\b|NF6|NF8|b6g|b6-|clk-s81-b6',re.I)
refs=[l.strip() for l in open('/tmp/scrrefs.txt') if l.strip()]
MREF=[l.split('\t')[0].replace('/srv/opentallas-scratch/claude','/srv/opentallas-scratch2/claude').replace('/srv/opentallas-scratch3/claude','/srv/opentallas-scratch2/claude').rstrip('/') for l in open('/tmp/refs.tsv')]

me=os.getpid(); T=[]
for p in glob.glob('/proc/[0-9]*'):
    if int(p[6:])==me: continue
    try: c=open(p+'/cmdline','rb').read().decode('latin1')
    except Exception: continue
    if 'gwt.py' in c or 'dd2.py' in c or 'dd3.py' in c: continue
    T.append(c)
    try: T.append(os.readlink(p+'/cwd'))
    except Exception: pass
    try:
        for f in os.listdir(p+'/fd'):
            try: T.append(os.readlink(p+'/fd/'+f))
            except Exception: pass
    except Exception: pass
    try: T.append(open(p+'/environ','rb').read().decode('latin1'))
    except Exception: pass
for r in ['/home/ubuntu/.local/state/ot-run','/home/ubuntu/.config/systemd/user']:
    for b,ds,fs in os.walk(r):
        for f in fs:
            try:
                if os.path.getsize(b+'/'+f)<5e6: T.append(open(b+'/'+f,errors='ignore').read())
            except Exception: pass
T='\n'.join(T)
def g(d,*a): return S.run(['git','-C',d]+list(a),capture_output=True,text=True,timeout=600)
cands=[]
OK=set(open('/tmp/okheads.txt').read().split()) if os.path.exists('/tmp/okheads.txt') else set()
def walk(d,dep):
    try: ents=sorted(os.scandir(d),key=lambda e:e.name)
    except OSError: return
    for e in ents:
        if e.is_symlink() or not e.is_dir(follow_symlinks=False): continue
        if os.path.exists(e.path+'/.git'): cands.append(e.path)
        elif dep<2: walk(e.path,dep+1)
walk(R,0)
tot=0
for d in cands:
    out=S.run(['du','-xsm',d],capture_output=True,text=True).stdout.split()
    sz=int(out[0]) if out else 0
    if sz<MIN: continue
    why=None
    name=d[len(R)+1:]
    if os.path.realpath(d)!=d: why='realpath differs'
    elif d in T or d+'/' in T: why='proc/queue/unit ref'
    elif any(p==d or p.startswith(d+'/') or d.startswith(p+'/') for p in MREF): why='live manifest ref'
    elif CUR.search(name): why='current-plan name'
    else:
        isdir=os.path.isdir(d+'/.git')
        hd=g(d,'rev-parse','HEAD').stdout.strip(); lr=g(d,'ls-remote','origin').stdout
        if (not hd or hd not in lr) and name not in OK: why='HEAD not on origin'
        elif g(d,'status','--porcelain','--untracked-files=no').stdout.strip() and not re.match(r'^(kw3[78]_src|kw41|kw43|kw32|dkv97|dq97|kv-plan-2)/src_',name): why='tracked dirty'
        else:
            # newest non-git mtime among tracked top-level: use find -mmin
            r=S.run(['find',d,'-path',d+'/.git','-prune','-o','-mmin','-1440','-print','-quit'],capture_output=True,text=True).stdout.strip()
            if r: why='<24h: '+r[len(d):][:60]
            else:
                oth=g(d,'ls-files','--others','--exclude-standard','-z').stdout.split('\0')
                oth=[x for x in oth if x]
                nb=0; bad=0
                for x in oth:
                    try: nb+=os.lstat(d+'/'+x).st_size
                    except OSError: pass
                ign=g(d,'ls-files','--others','--ignored','--exclude-standard','-z').stdout.split('\0')
                ign=[x for x in ign if x]
                for x in ign:
                    try: nb+=os.lstat(d+'/'+x).st_size
                    except OSError: pass
                if any(os.path.basename(x) in ('signoff.json','PROVENANCE.json') or x.endswith(('.odb','.def.gz','.gds')) for x in oth+ign): why='untracked signed/db files'
                elif nb>(700<<20 if re.match(r'^(kw3[78]_src|kw41|kw43|kw32|dkv97|dq97|kv-plan-2)/src_',name) else 200<<20): why='untracked/ignored %d MB'%(nb>>20)
                elif isdir:
                    if len(g(d,'worktree','list').stdout.splitlines())>1: why='hosts worktrees'
                    elif g(d,'rev-parse','--is-bare-repository').stdout.strip()=='true': why='bare'
                    elif g(d,'stash','list').stdout.strip(): why='stash'
                    elif name not in OK:
                        for s in g(d,'for-each-ref','refs/heads','--format=%(objectname)').stdout.split():
                            if s not in lr: why='unpushed branch head'; break
    if why: print('KEEP %7dMB %s: %s'%(sz,name,why),flush=True); continue
    print('DEL  %7dMB %s'%(sz,name),flush=True)
    if apply:
        if os.path.isfile(d+'/.git'):
            S.run(['git','-C',d,'worktree','remove','--force',d],capture_output=True)
        if os.path.exists(d) and os.path.realpath(d)==d: S.run(['rm','-rf',d])
        if not os.path.exists(d): tot+=sz
print('freed MB',tot)
