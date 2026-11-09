import json,hashlib,subprocess,sys
repo=sys.argv[1]; inv=json.load(open(sys.argv[2]))['files']; commits=sys.argv[3:]
def blob(c,p):
    r=subprocess.run(['git','-C',repo,'show',f'{c}:{p}'],capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode==0 else None
res={}
for p,s in inv.items():
    hit=None
    for c in commits:
        if blob(c,p)==s: hit=c;break
    if not hit:
        revs=subprocess.run(['git','-C',repo,'rev-list','--all','--',p],capture_output=True,text=True).stdout.split()[:300]
        for c in revs:
            if blob(c,p)==s: hit=c;break
    res[p]=hit; print(p, hit, flush=True)
json.dump(res,open('/tmp/ctlm_inv_map.json','w'),indent=1)
