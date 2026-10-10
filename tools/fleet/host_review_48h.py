#!/usr/bin/env python3
"""Capacity and 48h retirement, payload on stdin; never prints argv or env."""
import json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path

cfg=json.load(sys.stdin); now=time.time(); cutoff=now-48*3600
apply=cfg.get('apply', False); protected=set(cfg['protected']); used=set()
audit=[]; old=[]; clk=os.sysconf('SC_CLK_TCK')
uptime=float(Path('/proc/uptime').read_text().split()[0])
tools={'yosys','openroad','verilator','verilator_bin','iverilog','vvp','g++','gcc','cc1plus','cc1','ld','make','ninja','sta'}
def run(args):
    return subprocess.run(args, capture_output=True, text=True, errors='replace')
def paths(raw):
    return re.findall(r'/(?:srv|home/ubuntu|tmp)/[^\s\x00"\x27;]+',raw)
def identity(p):
    data=(p/'stat').read_text(); return data[data.rfind(')')+2:].split()[19]
for p in Path('/proc').glob('[0-9]*'):
    try:
        stat=(p/'stat').read_text(); fields=stat[stat.rfind(')')+2:].split()
        start=fields[19]; age=uptime-float(start)/clk
        cwd=os.readlink(p/'cwd'); used.add(cwd)
        for fd in (p/'fd').iterdir():
            try: used.add(os.readlink(fd))
            except OSError: pass
        argv=(p/'cmdline').read_bytes().decode(errors='replace'); env=(p/'environ').read_bytes().decode(errors='replace')
        used.update(paths(argv+' '+env))
        comm=(p/'comm').read_text().strip(); uid=p.stat().st_uid
        project=any(t in cwd+' '+argv for t in ('opentallas','OpenTallas','/claude/','claude-1000','closure-loop'))
        if uid==cfg['uid'] and age>48*3600 and comm in tools and project:
            old.append({'pid':int(p.name),'start':start,'age_h':round(age/3600,2),'tool':comm,'cwd':cwd})
    except (OSError,ValueError): pass
docker=run(['docker','ps','-q'])
if docker.returncode==0 and docker.stdout.split():
    mounts=run(['docker','inspect','-f','{{range .Mounts}}{{.Source}}\n{{end}}',*docker.stdout.split()])
    used.update(mounts.stdout.splitlines())
for row in old:
    p=Path('/proc')/str(row['pid'])
    try:
        if identity(p)!=row['start']: continue
        if apply:
            os.kill(row['pid'],signal.SIGCONT); os.kill(row['pid'],signal.SIGTERM)
        audit.append(dict(row,action='TERM' if apply else 'STALE_COMPUTE'))
    except (OSError,ValueError): pass
if apply and old:
    time.sleep(5)
    for row in old:
        p=Path('/proc')/str(row['pid'])
        try:
            if identity(p)==row['start']:
                os.kill(row['pid'],signal.SIGKILL)
                audit.append(dict(row,action='KILL_AFTER_TERM'))
        except (OSError,ValueError): pass

def overlap(d, refs):
    return any(d==p or d.startswith(p.rstrip('/')+'/') or p.startswith(d+'/') for p in refs if p.startswith('/'))
def reason(d):
    if overlap(d,protected): return 'pinned evidence/job/source reference'
    if overlap(d,used): return 'live cwd/fd/argv/env/container mount'
    try:
        device=os.stat(d).st_dev
        for base,dirs,files in os.walk(d,followlinks=False):
            if '.git' in dirs or '.git' in files: return 'git checkout retained; refs+patch required before removal'
            if '.keep' in files or '.keep' in dirs: return '.keep'
            if any(f in files for f in ('STATUS.md','terminal.json','SOURCE_COMMIT')): return 'registered source/evidence'
            if any(f.endswith(('.v','.sv','.py','.tcl','.cpp','.c','.h','.patch')) for f in files): return 'source retained; preservation review required'
            if any(f.startswith(('corner_sta','verdict','failure')) and f.endswith('.json') for f in files): return 'immutable pass/failure evidence'
            for name in dirs+files:
                st=os.lstat(os.path.join(base,name))
                if st.st_dev!=device: return 'nested filesystem retained'
                if max(st.st_mtime,st.st_ctime)>cutoff: return 'touched within 48h'
        st=os.stat(d)
        if max(st.st_mtime,st.st_ctime)>cutoff: return 'touched within 48h'
    except OSError: return 'incomplete traversal; retained'
    return None
for root in cfg['roots']:
    try: children=list(Path(root).iterdir())
    except OSError: continue
    for child in children:
        d=str(child)
        if not child.is_dir() or child.is_symlink() or child.name.startswith('.') or child.name in ('closure-loop','docker','exactness','fixtures','token-exact','exactness-fixtures','realmem-ctx8k','hbm-sim'): continue
        why=reason(d)
        if why:
            audit.append({'path':d,'action':'KEEP','reason':why}); continue
        size=run(['du','-sk','--',d]); kib=int(size.stdout.split()[0]) if size.returncode==0 else None
        # Re-read process and mount dependencies before removal: a new job may have started.
        if apply:
            refreshed=set()
            incomplete=False
            for p in Path('/proc').glob('[0-9]*'):
                try:
                    refreshed.add(os.readlink(p/'cwd'))
                    refreshed.update(paths((p/'cmdline').read_bytes().decode(errors='replace')+' '+(p/'environ').read_bytes().decode(errors='replace')))
                    for fd in (p/'fd').iterdir():
                        try: refreshed.add(os.readlink(fd))
                        except OSError: pass
                except FileNotFoundError: pass
                except PermissionError: incomplete=True
                except OSError: pass
            containers=run(['docker','ps','-q'])
            if containers.returncode!=0: incomplete=True
            elif containers.stdout.split():
                mounts=run(['docker','inspect','-f','{{range .Mounts}}{{.Source}}\n{{end}}',*containers.stdout.split()])
                if mounts.returncode: incomplete=True
                else: refreshed.update(mounts.stdout.splitlines())
            if incomplete or overlap(d,refreshed) or reason(d):
                audit.append({'path':d,'action':'KEEP','reason':'recheck active, changed, or inaccessible process'}); continue
            # Owner-approved scratch units only; git/evidence units are never removed here.
            shutil.rmtree(d)
        audit.append({'path':d,'action':'DELETE' if apply else 'DELETE_CANDIDATE','kib':kib,'reason':'idle >48h; no live use, .keep, git, evidence or source reference'})
mem={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
disks=[]
for root in cfg['disk_roots']:
    try:
        s=shutil.disk_usage(root); disks.append({'path':root,'free_gib':round(s.free/2**30,1),'used_pct':round(100*s.used/s.total,1)})
    except OSError: pass
print(json.dumps({'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cores':os.cpu_count(),'load':os.getloadavg(),'mem_available_gib':round(mem['MemAvailable']/2**20,1),'disks':disks,'audit':audit}))
