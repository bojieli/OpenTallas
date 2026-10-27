import json,sys,hashlib,math
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/die_plan"))
import schema as S
R=Path("/srv/opentallas-scratch2/claude/codex-qc-event-1351-1027")
raw=json.load(open(ROOT/"physical/die_plan/qwen_compute/die_plan.json"))
hard=json.load(open(R/"hard2/plan.json"));soft=json.load(open(R/"soft3/plan.json"))
led=json.load(open(R/"hard2/ledger.json"))+json.load(open(R/"soft3/ledger.json"))
types=sorted({r["type"]for r in led});delta=[]
for tn in types:
 source=soft if tn.startswith("coll_")else hard
 old=raw["partition_types"][tn]["ft_slots"];new=source["partition_types"][tn]["ft_slots"]
 assert [s["stations"]for s in old]==[s["stations"]for s in new]
 delta.append(dict(type=tn,original_slots_sha256=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest(),ft_slots=new))
 raw["partition_types"][tn]["ft_slots"]=new
# Check every explicit bank (new and inherited) in every changed type, not
# just the new groups. Existing input face flops are checked after placement.
errors=[];cells=0
for tn in types:
 t=raw["partition_types"][tn];w,h=t["outline_um"]
 boxes=S.placed_macro_boxes(t,halo=0.)
 rows=defaultdict(list)
 for slot in t["ft_slots"]:
  cw,ch=slot.get("bit_site_cell_um",[1.404,.27])
  for j,bank in enumerate(slot.get("bit_sites_um",[]),1):
   for bit,(x,y)in enumerate(bank):
    cells+=1;label=f'{slot["name"]}/{j}/{bit}'
    if x<0 or y<0 or x+cw>w+1e-6 or y+ch>h+1e-6:errors.append([tn,label,"outside"])
    if abs(y/.27-round(y/.27))>1e-5 or abs(x/.054-round(x/.054))>1e-5:errors.append([tn,label,"off-row/site"])
    for name,b in boxes.items():
     if x<b[2]-1e-6 and x+cw>b[0]+1e-6 and y<b[3]-1e-6 and y+ch>b[1]+1e-6:errors.append([tn,label,"macro",name])
    rows[round(y/.27)].append((x,x+cw,label))
 for row,ints in rows.items():
  ints.sort()
  for a,b in zip(ints,ints[1:]):
   if b[0]<a[1]-1e-6:errors.append([tn,"overlap",a[2],b[2]])
out=R/"combined";out.mkdir(exist_ok=True)
(out/"plan.json").write_text(json.dumps(raw,indent=0)+"\n")
summary=dict(types=types,slots=len(led),explicit_cells_checked=cells,errors=errors,added_cycles=sum(r["added_cycles"]for r in led),added_flops=sum(r["added_flops"]for r in led),max_hop_um=max(r.get("max_hop_um",r.get("worst_paired_bit_um",0))for r in led))
(out/"audit.json").write_text(json.dumps(summary,indent=1)+"\n")
(Path(__file__).parent/"ft_delta.json").write_text(json.dumps(dict(base_commit="18c6286d88387ac812ac0a74920fa8c4f275e1b5",types=delta),separators=(",",":"))+"\n")
(Path(__file__).parent/"ledger.json").write_text(json.dumps(led,indent=1)+"\n")
print(json.dumps({**summary,"errors":errors[:15]}),flush=True)
raise SystemExit(bool(errors))
