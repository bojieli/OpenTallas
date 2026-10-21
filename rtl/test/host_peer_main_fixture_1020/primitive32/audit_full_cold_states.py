import json
from pathlib import Path
r=json.loads(Path("qkd_hr_core_peer_n32.json").read_text())
pre=json.loads(Path("cold_pre.json").read_text())["modules"]["proof"]
post=json.loads(Path("cold_post.json").read_text())["modules"]["proof"]
preinit={n:d["attributes"]["init"] for n,d in pre["netnames"].items() if "init" in d.get("attributes",{})}
assert not preinit,preinit
state=[]
for row in r["copied_cells"]:
 if row["kind"]!="ff":continue
 for k in range(row["copies"]):
  suffix=f"u.u{row['cell']}_c{k}.u_cell.QN#sampled$"
  found=[(n,d)for n,d in post["netnames"].items() if "sample_data$" in n and suffix in n and set(d.get("attributes",{}).get("init","x"))<={"x"}]
  assert len(found)==1,(suffix,len(found))
  n,d=found[0];init=d.get("attributes",{}).get("init","x");assert set(init)<={"x"},(n,init)
  assert len(d["bits"])==1 and isinstance(d["bits"][0],int)
  bit=d["bits"][0]
  drivers=[name for name,c in post["cells"].items()if c["type"]=="$ff" and c["connections"].get("Q")==[bit]]
  assert len(drivers)==1,(n,drivers)
  state.append(dict(cell=row["cell"],copy=k,type=row["type"],sampled_state=n,bit=bit,init=init,driver=drivers[0]))
assert len({x["bit"]for x in state})==len(state),"physical states merged"
result=dict(passed=True,physical_copy_states=len(state),independent_distinct_ff_drivers=len(state),all_init_unknown=True,pretransform_physical_init={},note="Fixed sampled D/control-history helpers are not the physical state; every copied primitive QN sampled state independently unconstrained.",states=state)
Path("physical_state_audit.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items()if k!="states"}))
