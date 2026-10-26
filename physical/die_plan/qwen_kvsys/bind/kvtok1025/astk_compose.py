"""TOK-SCHED 10-25: compose the 4 ASTK corner cores (astk_EN/ES/WN/WS -> plan master kv3_astk) the same way as
Codex all_head_compose.py composes the 1024 head eighths: exact member leaves from the plan note "astk_core: a + b + ...",
every member terminal whose net leaves the member set becomes a composite port bit (one endpoint), and the declared
ID strap strap_corner[b] = {ctl.st[b], zn_k.zc[b] k=1..3} (astk_strap_master.py: st=2b{E}{N}, zc=4b{k}{E}{N}).
Every strap endpoint must be a constant and equal the plan value; no other constant is turned into a port."""
import json,sys,re,collections
from pathlib import Path
R=Path("/srv/opentallas-scratch2/claude/tok-sched/kvbind");tree=R/"tree";sys.path.insert(0,str(tree/"tools/die_plan"))
import bind,bind_compose
plan=tree/"physical/die_plan/qwen_kvsys/die_plan.json";bind._AB_OVERRIDE["path"]=str(R/"recipe_b1.json")
p=bind.load_plan(plan);b=bind.Binder(p,json.load(open(R/"b1/asbuilt.json")),plan.parent,bind.plan_base(plan,p));b.map_cells();F=b.F
outside=collections.defaultdict(set)
for ci,c in enumerate(F.cells):
  for pn,bs in c.ports.items():
    for x in bs: outside[x].add(ci)
topnets={x for d,bs in F.top_ports.values() for x in bs}
cores=[];mapping={};audit=[]
for part,ps in b.parts.items():
  t=p["partition_types"][ps["type"]]
  for hc in t.get("hard_cores",[]):
    if hc.get("module")!="kv3_astk": continue
    mt=re.match(r"astk_core: ([^;|]+)",hc.get("note",""));assert mt,(part,hc["inst"])
    prefixes=[x.strip() for x in mt.group(1).split("+")]
    mine={ci:b.rel_of(ci) for ci in b.members[part] if any(b.rel_of(ci)==x or b.rel_of(ci).startswith(x+"__") for x in prefixes)}
    assert mine and len(set(mine.values()))==len(mine),(part,hc["inst"])
    found={x for x in prefixes if any(v==x or v.startswith(x+"__") for v in mine.values())}
    assert found==set(prefixes),(part,hc["inst"],set(prefixes)-found)
    (sd,)=hc["straps"];assert sd["port"]=="strap_corner" and sd["width"]==2
    val=int(sd["value"].split("b")[1],2)
    head=hc["inst"];ports={};strap=[[],[]];consts=0
    driven={x for ci in mine for pn,bs in F.cells[ci].ports.items() if b.G.dirs[ci].get(pn)=="output" for x in bs if not isinstance(x,str)}
    for ci,local in sorted(mine.items(),key=lambda kv:kv[1]):
      c=F.cells[ci]
      for pn,bs in c.ports.items():
        ctl=local.endswith("u_ctl") and pn=="st"
        zn=re.search(r"g_zn_([123])__u_zn$",local) and pn=="zc"
        if ctl or zn:
          take=[0,1]
          for i in take:
            x=bs[i];assert x in ("0","1"),(c.path,pn,i,x)
            assert int(x)==(val>>i)&1,(c.path,pn,i,x,sd["value"])
            strap[i].append(dict(member=c.path,port=pn,bit=i))
          if zn:
            k=int(re.search(r"g_zn_([123])__",local).group(1))
            assert all(bs[i] in ("0","1") for i in (2,3)) and int(bs[3]+bs[2],2)==k,(c.path,bs)
          groups=[];indices=[]
          for i,x in enumerate(bs):
            if i in take or isinstance(x,str) or not (x in topnets or outside[x]-set(mine)): continue
            if b.G.dirs[ci].get(pn)=="input" and x in driven: continue
            indices.append(i);groups.append([dict(member=c.path,port=pn,bit=i)])
          if groups:
            ports[local.removeprefix(head+"__").replace("__","_")+"__"+pn]=dict(dir=b.G.dirs[ci].get(pn,"unknown"),bits=groups,indices=indices)
          continue
        groups=[];indices=[]
        for i,x in enumerate(bs):
          if isinstance(x,str) or not (x in topnets or outside[x]-set(mine)): continue
          if b.G.dirs[ci].get(pn)=="input" and x in driven: continue
          indices.append(i);groups.append([dict(member=c.path,port=pn,bit=i)])
        if not groups: continue
        ports[local.removeprefix(head+"__").replace("__","_")+"__"+pn]=dict(dir=b.G.dirs[ci].get(pn,"unknown"),bits=groups,indices=indices)
    assert [len(s) for s in strap]==[4,4],(head,[len(s) for s in strap])
    ports["strap_corner"]=dict(dir="input",bits=strap,indices=[0,1])
    path="native_composite_"+part+"_"+head;mapping[path]=[part,head];b.R.parts[path]=mapping[path]
    cores.append(dict(inst=path,module="kv3_astk",members=[F.cells[ci].path for ci in mine],ports=ports))
    audit.append(dict(inst=path,part=part,members=len(mine),ports=len(ports),port_bits=sum(len(v["bits"]) for v in ports.values()),strap=sd["value"]))
assert len(cores)==4,len(cores)
heads=json.load(open(R/"compose/composition_all_heads.json"));hmap=json.load(open(R/"compose/composition_all_heads_map.json"))
assert not set(mapping)&set(hmap)
out=R/"compose2";out.mkdir(exist_ok=True)
(out/"composition_heads_astk.json").write_text(json.dumps(dict(cores=heads["cores"]+cores),indent=1))
(out/"composition_heads_astk_map.json").write_text(json.dumps({**hmap,**mapping},indent=1))
(out/"astk_audit.json").write_text(json.dumps(audit,indent=1))
print("ASTK_SCHEMA",json.dumps(audit),flush=True)
print("SPEC_WRITTEN")
