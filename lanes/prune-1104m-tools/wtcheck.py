#!/usr/bin/env python3
# PRUNE-1103K per-worktree checks a,b,d,e-local (read-only, runs on the host). usage: check.py name...  -> JSON lines
import os,sys,re,json,subprocess,time
ROOT=os.environ.get('WT_ROOT','/home/ubuntu/scratch-root/claude/')
VIEW=re.compile(r'(^|/)([^/]*signoff\.json)$|\.(odb|spef|lef|lib)(\.gz)?$',re.I)
def sh(*a,t=1800):
    p=subprocess.run(a,capture_output=True,text=True,timeout=t,errors='replace'); return p.returncode,p.stdout,p.stderr
def holders(names):
    H={n:[] for n in names}
    pat={n:ROOT+n for n in names}
    alias={n:'/srv/opentallas-scratch3/claude/'+n for n in names}
    def hit(s,why,pid):
        for n in names:
            for q in (pat[n],alias[n]):
                if s==q or (q+'/') in s or re.search(re.escape(q)+r'(?![\w.-])',s): H[n].append(f'{why}:{pid}:{s[:160]}'); break
    # sudo so root container processes are visible too; read-only
    code=r'''
import os,sys
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    try:
        for x in('cwd','root','exe'):
            try: print('L',pid,x,os.readlink(f'/proc/{pid}/{x}'))
            except OSError: pass
        try:
            for fd in os.listdir(f'/proc/{pid}/fd'):
                try: print('L',pid,'fd',os.readlink(f'/proc/{pid}/fd/{fd}'))
                except OSError: pass
        except OSError: pass
        for f in ('cmdline','environ'):
            try: print('T',pid,f,open(f'/proc/{pid}/{f}','rb').read().replace(b'\0',b' ').decode('utf8','replace').replace('\n',' '))
            except OSError: pass
        try:
            for l in open(f'/proc/{pid}/maps'):
                if '/' in l: print('L',pid,'map',l.split(None,5)[-1].strip())
        except OSError: pass
    except OSError: pass
'''
    r=subprocess.run(['sudo','-n','python3','-c',code],capture_output=True,text=True,errors='replace',timeout=900)
    if r.returncode!=0 or len(r.stdout)<1000: sys.exit('holder scan failed rc=%s'%r.returncode)
    ms=os.getpid()
    for l in r.stdout.splitlines():
        f=l.split(' ',3)
        if len(f)<4: continue
        if f[1]==str(ms): continue
        if 'p1104m' in f[3] or 'prune-1103k' in f[3] or 'sudo -n python3' in f[3] or 'import os,sys' in f[3]: continue
        hit(f[3],f[2],f[1])
    c,o,_=sh('docker','ps','-q',t=120)
    ids=o.split()
    if ids:
        c,o,_=sh('docker','inspect',*ids,t=300)
        for x in json.loads(o):
            b=json.dumps({'m':[m.get('Source') for m in x.get('Mounts',[])],'c':x['Config'].get('Cmd'),'e':x['Config'].get('Entrypoint'),'w':x['Config'].get('WorkingDir'),'env':x['Config'].get('Env')})
            hit(b,'docker',x['Id'][:12])
    return H
names=sys.argv[1:]
H=holders(names)
now=time.time()
for n in names:
    p=ROOT+n; o={'name':n,'path':p,'host':os.uname().nodename}
    if not os.path.isdir(p): o['missing']=True; print(json.dumps(o),flush=True); continue
    c,head,_=sh('git','-C',p,'rev-parse','HEAD'); o['head']=head.strip()
    c,br,_=sh('git','-C',p,'rev-parse','--abbrev-ref','HEAD'); o['branch']=br.strip()
    c,_,_=sh('git','-C',p,'merge-base','--is-ancestor',o['head'],'origin/main'); o['ancestor']=(c==0)
    c,cm,_=sh('git','-C',p,'rev-parse','--git-common-dir'); o['common']=cm.strip()
    c,st,e=sh('git','-C',p,'status','--porcelain','--ignored','--untracked-files=normal'); o['status_rc']=c
    lines=[l for l in st.splitlines() if l]
    mod=[l for l in lines if l[:2] not in('??','!!')]; unt=[l[3:].strip('"') for l in lines if l[:2]=='??']; ign=[l[3:].strip('"') for l in lines if l[:2]=='!!']
    o['modified']=mod[:30]; o['n_modified']=len(mod); o['untracked']=unt[:30]; o['n_untracked']=len(unt); o['ignored']=ign[:30]; o['n_ignored']=len(ign)
    views=[];ub=0
    for rel in unt+ign:
        fp=os.path.join(p,rel)
        if os.path.isdir(fp) and not os.path.islink(fp):
            for dp,dn,fn in os.walk(fp):
                if '.git' in dn: dn.remove('.git')
                for f in fn:
                    q=os.path.join(dp,f)
                    try: ub+=os.lstat(q).st_blocks*512
                    except OSError: pass
                    if VIEW.search(f): views.append(os.path.relpath(q,p))
        else:
            try: ub+=os.lstat(fp).st_blocks*512
            except OSError: pass
            if VIEW.search(rel): views.append(rel)
    o['untracked_bytes']=ub; o['untracked_views']=views[:40]; o['n_untracked_views']=len(views)
    # tree: newest mtime, size, .keep
    nw=0;sz=0;keeps=[];newest=''; recent=[]
    for dp,dn,fn in os.walk(p):
        for x in fn+dn:
            q=os.path.join(dp,x)
            try: st_=os.lstat(q)
            except OSError: continue
            sz+=st_.st_blocks*512 if x in fn else 0
            if st_.st_mtime>nw: nw=st_.st_mtime;newest=q
            if now-st_.st_mtime<24*3600 and len(recent)<10: recent.append(q)
        for f in fn:
            if f=='.keep': keeps.append(os.path.relpath(os.path.join(dp,f),p))
    o['size_gb']=round(sz/1e9,1);o['newest']=time.strftime('%F %H:%M',time.localtime(nw));o['newest_path']=newest;o['age_h']=round((now-nw)/3600,1);o['recent']=recent
    untr=[]
    for k in keeps:
        c,_,_=sh('git','-C',p,'ls-files','--error-unmatch',k)
        if c!=0: untr.append(k)
    o['keeps']=len(keeps);o['keeps_untracked']=untr
    c,sg,_=sh('git','-C',p,'ls-files','*signoff.json'); o['tracked_signoff']=len(sg.splitlines())
    c,wl,_=sh('git','-C',p,'worktree','list','--porcelain')
    bl=[b for b in wl.split('\n\n') if b.startswith('worktree '+p+'\n') or b.startswith('worktree '+p)]
    o['wt_entry']=bl[0].replace('\n',' | ') if bl else ''
    o['holders']=H[n][:20]; o['n_holders']=len(H[n])
    print(json.dumps(o),flush=True)
