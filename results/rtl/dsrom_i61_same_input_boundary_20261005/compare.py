from pathlib import Path
import numpy as np,re,json,hashlib
r=Path("/srv/opentallas-scratch/jobs/arch-qk-su-pv-minimum-20261005")
q=np.fromfile(r/"captured/QK.u32",dtype="<u4").reshape(16,640)
a=np.fromfile(r/"captured/Sscaled.u32",dtype="<u4").reshape(16,640)
m=np.fromfile(r/"captured/MAX.u32",dtype="<u4")
line=next(x for x in (r/"source/literals.hpp").read_text().splitlines() if x.startswith("{2532,"))
w=sum(int(s,16)<<(32*i) for i,s in enumerate(re.findall(r"0x([0-9a-f]+)u",line)))
scale=(w>>1149)&0xffffffff
s=(q.view(np.float32)*np.array([scale],dtype=np.uint32).view(np.float32)[0]).astype(np.float32)
s[s==0]=np.float32(0)
sm=s.view(np.uint32);mx=s.max(axis=1).astype(np.float32).view(np.uint32)
def comp(a,b,n):
 ix=np.flatnonzero(a.ravel()!=b.ravel());first=None
 if ix.size:
  i=int(ix[0]);first={"index":i,"head":i//n,"row":i%n,"actual":f"{a.ravel()[i]:08x}","golden":f"{b.ravel()[i]:08x}"}
 return {"words":a.size,"mismatches":int(ix.size),"first":first}
print(json.dumps({"scope":"closedI61 only","scale_bits":f"{scale:08x}","scale":float(np.array([scale],dtype=np.uint32).view(np.float32)[0]),"Sscaled":comp(a,sm,640),"MAX":comp(m,mx,1),"nonfinite_input":int(np.count_nonzero(~np.isfinite(q.view(np.float32))))},indent=2))
