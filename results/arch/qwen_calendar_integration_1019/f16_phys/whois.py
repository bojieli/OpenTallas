import json,re,sys
j=json.load(open("native.json"))["modules"]["qfd_dv_typed_witness_control"]
g=json.load(open("generic.json"))["modules"]["qfd_dv_typed_witness_control"]
gnm={}
for nn,v in g["netnames"].items():
  if nn.startswith("$"): continue
  for i,b in enumerate(v["bits"]): gnm.setdefault(b,"%s[%d]"%(nn,i))
gff={}
for n,c in g["cells"].items():
  if "Q" in c["connections"]: gff[n]=gnm.get(c["connections"]["Q"][0],n)
drv={}
for n,c in j["cells"].items():
  for p,bs in c["connections"].items():
    if c["port_directions"].get(p)=="output":
      for b in bs: drv[b]=(n,c)
pn={}
for p,v in j["ports"].items():
  for i,b in enumerate(v["bits"]): pn[b]="port:%s[%d]"%(p,i)
def ffname(n):
  # native cell name -> generic slice name via netnames of its output
  c=j["cells"][n]
  for p,bs in c["connections"].items():
    if c["port_directions"].get(p)=="output":
      for nn,v in j["netnames"].items():
        if bs[0] in v["bits"] and "slice$" in nn:
          m=re.search(r"(\$auto\$ff\.cc:337:slice\$\d+)",nn)
          k=[x for x in gff if x.endswith(m.group(1))] if m else []
          if k: return gff[k[0]]
  return n
for w in sys.argv[1:]:
  bit=[v["bits"][0] for nn,v in j["netnames"].items() if nn.endswith(w)][0]
  seen=set();q=[bit];roots=set()
  while q:
    b=q.pop()
    if b in seen or isinstance(b,str): continue
    seen.add(b)
    if b not in drv: roots.add(pn.get(b,str(b))); continue
    n,c=drv[b]
    if re.search("DFF",c["type"]): roots.add(ffname(n)); continue
    for p,bs in c["connections"].items():
      if c["port_directions"].get(p)=="input": q.extend(bs)
  print(w,len(roots),sorted(roots)[:30])
