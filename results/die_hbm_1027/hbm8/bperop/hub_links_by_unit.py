import json,sys,collections
P=json.load(open(sys.argv[1]))
UNIT=[("hb_coll","COLL"),("hcollg","COLL"),("cij","COLL"),("cxij","COLL"),("cxrc","SU"),("sucore","SU"),("pgp","SU"),("sfu","SU"),
      ("svg","SM"),("smw","SM"),("xl_","SM"),("xq_","SM"),("wbk","SM"),("dbk","DMA"),("hb_idx","IDX"),("mu_","FUSED"),("quant","FUSED"),
      ("hc_","HC"),("vmb","VM"),("vmks","VM"),("vmdel","VM"),("vms","VM"),("vmfc","VM"),("calendar","VM"),("ctl_Q","VM")]
def unit(n):
  for k,u in UNIT:
    if k in n: return u
  return "UNK" if not n.startswith("face bus") else "FACE"
t=P["partition_types"]["q_hub_nw"]
print(list(t["internal_stations"][0].keys()))
agg=collections.defaultdict(lambda:[0,0,collections.Counter()])
for s in t["internal_stations"]:
  a,b=s["launch"].split(".")[0],s["capture"].split(".")[0]
  key=(unit(s["launch"]),unit(s["capture"]))
  g=agg[key];g[0]+=s["bits"];g[1]+=1;g[2][(a[:28],b[:28],s.get("serial_k") or 1)]+=s["bits"]
for k,(bits,n,c) in sorted(agg.items(),key=lambda x:-x[1][0]):
  print(k,bits,n)
  for kk,v in c.most_common(6): print("    ",kk,v)
