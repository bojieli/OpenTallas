import sys,json
sys.path.insert(0,sys.argv[1]+"/tools/hier_contract")
import native_pin_audit as N, pinreg_audit as PA
from pathlib import Path
S=Path(sys.argv[2]); rows=[l.rstrip("\n").split("\t") for l in open(S/"views.tsv")]
V={r[1]+("@"+r[0]):r for r in rows}
def find(cell): return [r for r in rows if r[1]==cell]
def audit(r,comp=None):
    c,blk,vd,_,_=r
    return N.audit_one((str(S/"v"/c),blk,vd) + ((comp,) if comp else ()))
pairs=json.loads(sys.argv[3])
for tgt,nbs in pairs:
    for t in find(tgt):
        base=audit(t); print("==",tgt,t[2].split('/')[2],"own R",base.get("R_ps"),"L",base["launch_ps"],base["launch_pin"],"C",base["capture_ps"],base["capture_pin"],base["pass"])
        for nb in nbs:
            for n in find(nb):
                comp=PA.compensation(str(S/"v"/n[0]/n[2]))
                r=audit(t,comp)
                print("   vs",n[2].split('/')[2],"C tt %.1f ff %.1f"%(comp.get('tt',0),comp.get('ff',0)),"L",r["launch_ps"],r["launch_pin"],r["launch_over"],"Cap",r["capture_ps"],r["capture_pin"],r["capture_over"],"PASS" if r["pass"] else "FAIL: "+r["fail_why"])
