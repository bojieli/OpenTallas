"""INFRA-FIRST-QC-R30: compose the R29 FT delta (2b588c310c) SLOT-WISE onto the QC clock-basis plan
(native100 geometry = canonical68 + R16/R17 centre clock channel + island class split; dry14 plan adds R28 VSS cut + M9 .672).
Only slots the delta changes are replaced (and only when the class slot still equals the canonical original);
every other slot (incl. n100 sle_su_l1 rsn/rsf sites) is kept.
Audit: each bank cell of each replaced slot vs outline, row/site grid, macro boxes, clock die islands; row overlaps of all slots.
usage: compose_n100_ft.py REPO BASE18C_PLAN CLOCK_BASIS_PLAN FT_DELTA OUT"""
import json,sys,hashlib,copy
from collections import defaultdict
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import schema as S
base18=json.load(open(sys.argv[2])); plan=json.load(open(sys.argv[3])); delta=json.load(open(sys.argv[4])); out=sys.argv[5]
h=lambda x: hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
led=[];errors=[];cells=0
for row in delta["types"]:
    tn=row["type"]; old={s["name"]:s for s in base18["partition_types"][tn]["ft_slots"]}
    assert h(base18["partition_types"][tn]["ft_slots"])==row["original_slots_sha256"]
    changed={s["name"]:s for s in row["ft_slots"] if s!=old[s["name"]]}
    cls=[k for k in plan["partition_types"] if k==tn or k.startswith(tn+"__cl")]
    assert cls,tn
    for k in cls:
        t=plan["partition_types"][k]; new=[]
        for s in t["ft_slots"]:
            if s["name"] in changed:
                if s!=old[s["name"]]:
                    errors.append([k,s["name"],"class slot differs from canonical original"]); new.append(s); continue
                assert s["stations"]==changed[s["name"]]["stations"]
                new.append(copy.deepcopy(changed[s["name"]]))
            else: new.append(s)
        t["ft_slots"]=new; led.append(dict(cls=k,type=tn,replaced=sorted(changed)))
        w,hh=t["outline_um"]; boxes=S.placed_macro_boxes(t,halo=0.)
        isl=(t.get("clock") or {}).get("die_islands_um") or []
        rows=defaultdict(list)
        for slot in t["ft_slots"]:
            cw,ch=slot.get("bit_site_cell_um",[1.404,.27])
            for j,bank in enumerate(slot.get("bit_sites_um",[]),1):
                for bit,(x,y) in enumerate(bank):
                    lab="%s/%d/%d"%(slot["name"],j,bit); rows[round(y/.27)].append((x,x+cw,lab))
                    if slot["name"] not in changed: continue
                    cells+=1
                    if x<0 or y<0 or x+cw>w+1e-6 or y+ch>hh+1e-6: errors.append([k,lab,"outside"])
                    if abs(y/.27-round(y/.27))>1e-5 or abs(x/.054-round(x/.054))>1e-5: errors.append([k,lab,"off-row/site"])
                    for name,b in boxes.items():
                        if x<b[2]-1e-6 and x+cw>b[0]+1e-6 and y<b[3]-1e-6 and y+ch>b[1]+1e-6: errors.append([k,lab,"macro",name])
                    for r in isl:
                        if x<r[2]-1e-6 and x+cw>r[0]+1e-6 and y<r[3]-1e-6 and y+ch>r[1]+1e-6: errors.append([k,lab,"island",r])
        for rr,ints in rows.items():
            ints.sort()
            for a,b in zip(ints,ints[1:]):
                if b[0]<a[1]-1e-6: errors.append([k,"overlap",a[2],b[2]])
json.dump(plan,open(out,"w"),indent=0)
from collections import Counter
rep=dict(classes=len(led),changed_cells_checked=cells,errors=len(errors),by_kind=Counter(e[2] if e[1]!="overlap" else "overlap" for e in errors),
         by_class=Counter(e[0] for e in errors),first=errors[:30],ledger=led,plan_sha256=hashlib.sha256(open(out,"rb").read()).hexdigest())
json.dump(rep,open(out.replace(".json","_audit.json"),"w"),indent=1,default=str); print(json.dumps({k:v for k,v in rep.items() if k!="ledger"},indent=1,default=str))
