"""Review-only exact-source boundary inventory; never changes gate policy."""
import importlib.util,sys,json,re,hashlib,collections
from pathlib import Path
sp=importlib.util.spec_from_file_location("tl","textbook_lint.py");m=importlib.util.module_from_spec(sp);sys.modules["tl"]=m;sp.loader.exec_module(m)
r=json.loads(Path("qkd_hr_core_peer_n32.json").read_text());raw=Path("resynth.v").read_bytes();g,_=m.flatten(m.parse_verilog(raw.decode()),r["top"]);a=m.build(g,None)
clock=g.ports["ck_core"][1]
def resolve(net):
 inv=False;seen=set()
 while net in a["driver"]:
  ci,pn=a["driver"][net]
  if ci<0 or a["kind"][ci]!="buf":break
  assert net not in seen;seen.add(net)
  typ,_,pins=g.cells[ci];ins=[b for p,bs in pins.items()if a["pin_dir"][ci][p]=="in" for b in bs];assert len(ins)==1
  inv^=bool(re.match(r"^(INV|CKINV)",typ,re.I));net=ins[0]
 return net,inv
loads=collections.defaultdict(list)
for ci,(typ,name,pins)in enumerate(g.cells):
 if a["kind"][ci]=="buf":continue
 for pn,bs in pins.items():
  if a["pin_dir"][ci][pn]=="in":
   for b in bs:
    root,inv=resolve(b);loads[root].append((ci,pn,inv))
rows=[];problems=[]
for port,(direction,net)in g.ports.items():
 if port=="ck_core":continue
 if direction=="input":
  root,_=resolve(net);captures=[]
  for ci,pn,inv in loads[root]:
   typ,name,pins=g.cells[ci]
   plain=(a["kind"][ci]=="ff" and pn=="D" and pins.get("CLK")==[clock] and typ=="DFFHQNx1_ASAP7_75t_R" and set(pins)<={"CLK","D","QN","Q"})
   captures.append(dict(instance=name,type=typ,pin=pn,unary_inversion=inv,plain_posedge_core_D_capture=plain))
  ok=bool(captures) and all(x["plain_posedge_core_D_capture"] for x in captures)
  if not ok:problems.append(dict(port=port,problem="input has no capture or nonplain/noncore/nonD endpoint",endpoints=captures))
  rows.append(dict(port=port,direction=direction,kind="input_capture",passed=ok,captures=captures))
 else:
  root,inv=resolve(net);ci,pn=a["driver"].get(root,(-1,None));kind="unproved";details={}
  if root<=3:kind="constant";details=dict(value=["0","1","x","z"][root],inverted=inv)
  elif ci>=0:
   typ,name,pins=g.cells[ci]
   if a["kind"][ci]=="tie":
    kind="reserved_constant_candidate";details=dict(instance=name,type=typ,unary_inversion=inv)
   elif a["kind"][ci]=="ff" and pn in ("Q","QN") and pins.get("CLK")==[clock]:
    kind="output_register";details=dict(instance=name,type=typ,pin=pn,unary_inversion=inv,clock="ck_core")
  ok=kind in ("constant","reserved_constant_candidate","output_register")
  if not ok:problems.append(dict(port=port,problem="output is not direct core FF or explicitly inventoried constant"))
  rows.append(dict(port=port,direction=direction,kind=kind,passed=ok,details=details))
summary=dict(collections.Counter(x["kind"]for x in rows));result=dict(schema="peer.exact_boundary_inventory.review_only.v1",top=r["top"],source_sha256=r["generated_sha256"],mapped_sha256=hashlib.sha256(raw).hexdigest(),params={},defines=[],passed_structural_boundary_inventory=not problems,counts=summary,problems=problems,ports=rows,scope="No wrapper-suppression authority or generic reset waiver. Reserved constants still need source inventory exact-set match. Actual reset age/polarity and downstream three-edge observer contract remain separately pinned.")
Path("review_input_capture.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps({k:v for k,v in result.items()if k!="ports"}))
raise SystemExit(bool(problems))
