import sys,json,re
from pathlib import Path
sys.path.insert(0,"tools/hier_contract")
import pinreg_audit as PA
def m(vd,cell,corner="tt"):
    lp=Path(vd)/f"{cell}_{corner}.lib"
    ins=json.loads((Path(vd)/"insertion.json").read_text())
    lib=PA.parse_lib(lp); refs=PA.clock_refs(lib,ins,corner)
    return PA.pin_metrics(lib,refs)
ROOT=sys.argv[1] if len(sys.argv)>1 else "."
V={"xl":("physical/ref_tile/smh_fcxl_ref_p40/views/ot_hbm_accel_smh_fc_xl","ot_hbm_accel_smh_fc_xl"),
   "b":("physical/ref_tile/smh_fcb_ref_p40/views/ot_hbm_accel_smh_fc_b","ot_hbm_accel_smh_fc_b"),
   "xr2":("physical/ref_tile/smn_fcxr2_ref_fa/views/ot_hbm_accel_smh_fc_xr2","ot_hbm_accel_smh_fc_xr2")}
M={k:m(*v) for k,v in V.items()}
def bits(d,base,key):
    out={}
    for n,x in d.items():
        mm=re.fullmatch(re.escape(base)+r"\[(\d+)\]",n)
        if mm and x.get(key) is not None: out[int(mm.group(1))]=x[key]
    return out
res={}
for name,(a,pa,b,pb) in {"xl.xw_w->xr2.xi":("xl","xw_w","xr2","xi"),"xr2.xo->b.xi":("xr2","xo","b","xi")}.items():
    L=bits(M[a],pa,"out"); C=bits(M[b],pb,"inp")
    common=sorted(set(L)&set(C)); sums=sorted(((L[i]+C[i],i,round(L[i],1),round(C[i],1)) for i in common),reverse=True)
    res[name]=dict(n=len(common),nL=len(L),nC=len(C),worst=[(round(s,1),i,l,c) for s,i,l,c in sums[:5]],over410=sum(1 for s in sums if s[0]>410),
                   maxL=round(max(L.values()),1),maxC=round(max(C.values()),1))
print(json.dumps(res,indent=1))
