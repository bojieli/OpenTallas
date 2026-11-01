"""Export only completely snapshotted PASS slots for the parent one-event composer.
Usage: emit_patch.py RUN_DIR OUT.json. No source plan is mutated.
"""
import json,sys,hashlib
from pathlib import Path
r=Path(sys.argv[1]);base=json.load(open(r/"base.json"));new=json.load(open(r/"repaired.json"));ledger=json.load(open(r/"ledger.json"));patch=[]
allowed={"regs_um","bit_sites_um","bit_site_cell_um","note"}
for rec in ledger:
 if rec["status"]!="PASS":continue
 tn,name=rec["type"],rec["slot"]
 a=next(s for s in base["partition_types"][tn]["ft_slots"] if s["name"]==name);b=next(s for s in new["partition_types"][tn]["ft_slots"] if s["name"]==name)
 if b["regs_um"]!=rec["new_regs_um"]:continue # current type has not reached its atomic snapshot yet
 changed={k for k in set(a)|set(b) if a.get(k)!=b.get(k)}
 assert changed<=allowed,(tn,name,changed)
 assert a["stations"]==b["stations"] and a["width"]==b["width"]
 patch.append(dict(type=tn,slot=name,old_stations=a["stations"],new_stations=b["stations"],added_cycles=0,replace={k:b[k] for k in changed}))
out=dict(schema="opentallas.hbm_station_repair_patch.v1",source_plan_sha256=hashlib.sha256((r/"base.json").read_bytes()).hexdigest(),patches=patch,added_cycles=0,complete=(r/"DONE").exists(),unresolved=[x for x in ledger if x["status"]!="PASS"])
p=Path(sys.argv[2]);tmp=p.with_suffix(p.suffix+".tmp");tmp.write_text(json.dumps(out,separators=(",",":")));tmp.replace(p);print(len(patch),"slots;0cycles;complete",out["complete"])
