"""CLEAN-ALL-1115 (COORD r178): cleanup guard.  python3 -I ot_cleanup_refguard.py OUT.tsv writes every path named by a live (<7 d) asbuilt_run/asbuilt_sources/bind_report/src_manifest/bind.f/filelist under claude/*; any cleanup must keep those paths.  ot_cleanup_delchk.py EPOCH checks the day autoclean manifests against /tmp/refs.tsv."""
import os,re,sys,glob,time
R='/srv/opentallas-scratch2/claude'
PAT=re.compile(r'(/srv/opentallas-scratch[23]?/claude/[A-Za-z0-9._+/@=-]+|/home/ubuntu/[A-Za-z0-9._+/@=-]+)')
NAMES=re.compile(r'^(asbuilt_run\.json|asbuilt_sources\.json|bind_report\.json|src_manifest.*|bind\.f|.*filelist.*|sources\.f|bind_manifest.*)$')
now=time.time(); refs={}
def scan(top,maxdep):
    for r,ds,fs in os.walk(top):
        dep=r[len(top):].count('/')
        if dep>=maxdep: ds[:]=[]
        ds[:]=[d for d in ds if d not in('.git','objects','results','logs')]
        for f in fs:
            if NAMES.match(f):
                p=r+'/'+f
                try:
                    st=os.stat(p)
                    if now-st.st_mtime>7*86400 or st.st_size>20e6: continue
                    for m in PAT.findall(open(p,errors='ignore').read()):
                        refs.setdefault(m.rstrip('/.,'),p)
                except OSError: pass
for d in sorted(os.listdir(R)):
    p=R+'/'+d
    if os.path.isdir(p) and not os.path.islink(p): scan(p,6)
PV=os.path.join(os.path.dirname(os.path.abspath(__file__)),'provrefs.txt')
if os.path.exists(PV):
    for l in open(PV):
        l=l.strip()
        if l: refs.setdefault(l,'provenance-view-source')
out=open(sys.argv[1],'w')
for k,v in sorted(refs.items()): out.write(k+'\t'+v+'\n')
print(len(refs),'referenced paths')
