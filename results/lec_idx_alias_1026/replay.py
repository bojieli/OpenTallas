from pathlib import Path
import json,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools/die_plan"))
import lec
r=Path(sys.argv[1]).resolve()
L=lec.Lec(lec.read_aig(r/"gold.aig"),lec.read_map(r/"gold.map"),lec.read_aig(r/"gate.aig"),lec.read_map(r/"gate.map"))
for sd,k,h in json.load(open(r/"hyp.json")):
 if k in (L.gp if sd=="gold" else L.tp if sd=="gate" else set(L.gp)&set(L.tp)):
  L.hyp[(sd,k)]=tuple(h)
print("KEYS",len(L.matched),len(L.gonly),len(L.tonly),len(L.hyp),flush=True)
log=[]
print("TWINS",lec.structural_twin_closure(L,log),flush=True)
print("CF_HYP",[([sd,k],h) for (sd,k),h in L.hyp.items() if ".cf" in str((k,h))],flush=True)
m,kind=L.build(with_compare=True,with_hyp=True)
print("PROVING",len(m.outs),flush=True)
s=lec.prove(m,r,1000,log,tag="idx_alias_target")
(r/"target.log").write_text("\n".join(log))
rec={"counts":{k:list(s.values()).count(k) for k in set(s.values())},"failing":{k:v for k,v in s.items() if v!="proved"},"hypotheses":len(L.hyp),"note":"reused immutable AIG/maps + all re-proved old obligations; no re-elaboration; current KEEP1215/1215 from original"}
(r/"target.json").write_text(json.dumps(rec,indent=2));print(json.dumps(rec),flush=True)
