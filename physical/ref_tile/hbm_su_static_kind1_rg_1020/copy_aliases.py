"""Own qcore source prototype: add only addressable aliases, then prove graph/property preservation."""
import argparse,json,re
from collections import defaultdict
from pathlib import Path

def graph(m, original_names=()):
 nodes=defaultdict(set)
 const=[]
 for cn,c in m.get("cells",{}).items():
  for pn,bits in c.get("connections",{}).items():
   for ix,b in enumerate(bits):
    term=(cn,pn,ix)
    if isinstance(b,int):nodes[b].add(term)
    else:const.append((str(b),term))
 for pn,p in m.get("ports",{}).items():
  for ix,b in enumerate(p["bits"]):
   term=("PORT",pn,ix)
   if isinstance(b,int):nodes[b].add(term)
   else:const.append((str(b),term))
 # JSON bit IDs are local to each write_json. Original wire-bit contacts
 # identify even unused bits without relying on these unstable IDs. Exclude
 # newly added aliases so the two graphs have identical terminal inventories.
 for nn in original_names:
  for ix,b in enumerate(m["netnames"][nn]["bits"]):
   term=("WIRE",nn,ix)
   if isinstance(b,int):nodes[b].add(term)
   else:const.append((str(b),term))
 return {b:frozenset(v) for b,v in nodes.items()},frozenset(const)

def main():
 p=argparse.ArgumentParser();p.add_argument("mode",choices=["aliases","verify"]);p.add_argument("before");p.add_argument("after");p.add_argument("--top");p.add_argument("--manifest");a=p.parse_args();b=json.loads(Path(a.before).read_text())
 if a.mode=="aliases":
  m=b["modules"][a.top];cmd=["cd \\"+a.top];rows=[]
  for name,n in sorted(m.get("netnames",{}).items()):
   if "ot_rst_split" not in n.get("attributes",{}):continue
   bits=n["bits"]
   if len(bits)<2 or not all(isinstance(x,int) for x in bits) or len(set(bits))!=len(bits):raise ValueError("bad family "+name)
   if re.search(r"[\s;#\"{}]",name):raise ValueError("unsupported exact wire identifier "+name)
   alias="A_ot_qcore_copy_alias_%05d"%len(rows)
   if alias in m["netnames"]:raise ValueError("alias collision")
   cmd += ["add -wire \\"+alias+" "+str(len(bits)),"connect -set \\"+alias+" \\"+name]
   rows.append({"original":name,"alias":alias,"width":len(bits)})
  cmd += (["setattr -set keep 1 w:A_ot_qcore_copy_alias_*","setattr -set ot_rst_split 1 w:A_ot_qcore_copy_alias_*"] if rows else []);cmd.append("cd ..");Path(a.after).write_text("\n".join(cmd)+"\n");Path(a.manifest).write_text(json.dumps(rows,indent=2)+"\n");print("COPY_ALIASES",len(rows));return
 c=json.loads(Path(a.after).read_text());assert b["modules"].keys()==c["modules"].keys();cells=0
 for mn,old in b["modules"].items():
  new=c["modules"][mn];assert old["cells"].keys()==new["cells"].keys(),mn
  for cn,cell in old["cells"].items():
   for k in ["type","parameters","attributes","port_directions"]:assert cell.get(k)==new["cells"][cn].get(k),(mn,cn,k)
  assert old.get("ports",{}).keys()==new.get("ports",{}).keys(),mn
  names=old.get("netnames",{}).keys()
  og,oc=graph(old,names);ng,nc=graph(new,names);assert frozenset(og.values())==frozenset(ng.values()) and oc==nc,mn
  for pn,x in old.get("ports",{}).items():
   y=new["ports"][pn];assert {k:v for k,v in x.items() if k!="bits"}=={k:v for k,v in y.items() if k!="bits"}
   assert [og.get(v,("const",v)) for v in x["bits"]]==[ng.get(v,("const",v)) for v in y["bits"]]
  for nn,x in old.get("netnames",{}).items():
   y=new["netnames"][nn];assert {k:v for k,v in x.items() if k!="bits"}=={k:v for k,v in y.items() if k!="bits"},(mn,nn)
   assert [og.get(v,("const",v)) for v in x["bits"]]==[ng.get(v,("const",v)) for v in y["bits"]],(mn,nn)
  cells+=len(old["cells"])
 r={"status":"PASS","contract":"Actual cell graph, constant contacts, all cell properties, primary ports and every original named net preserved; only new aliases allowed.","cells":cells};Path(a.manifest).write_text(json.dumps(r,indent=2)+"\n");print("COPY_ALIAS_GRAPH PASS",cells)
if __name__=="__main__":main()
