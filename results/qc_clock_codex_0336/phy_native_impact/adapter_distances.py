import json,collections,math,gzip,statistics
from pathlib import Path
r=Path(__file__).parent;receipt=json.load(open(r/"phy_native_impact.json"));pp=json.load(open(r/"phy_plan_pins.json"));rows=[];summary={}
def stats(d):
 s=sorted(d);return dict(bits=len(s),min_um=min(s),median_um=statistics.median(s),p90_um=s[math.ceil(.9*len(s))-1],max_um=max(s),over30=sum(x>30 for x in s),over405=sum(x>405 for x in s))
for tn in["phy_serdes","phy_serdes_b","phy_ucie_kv"]:
 vals=collections.defaultdict(list)
 for b,i,l,x,y,f in pp[tn]["pins"]:
  key=b if b in["tx_v","rx_v","tx_up"]and i==0 else f"{b}[{i}]"
  pin=receipt["views"][tn]["pins"].get(key)
  if pin is None:continue
  nx,ny=pin["xy_um"];d=abs(x-nx)+abs(y-ny);vals[b].append(d)
  rows.append(dict(type=tn,outer_bus=b,bit=i,outer_layer=l,outer_face=f,outer_xy_um=[x,y],native_pin=key,native_layer=pin["layer"],native_xy_um=[nx,ny],minimum_adapter_wire_um=d,registered_pin_R2_proxy_um=d))
 summary[tn]=dict(all_payload=stats([d for v in vals.values()for d in v]),buses={k:stats(v)for k,v in vals.items()})
receipt["native_to_outer_adapter"]=summary
(r/"phy_native_impact.json").write_text(json.dumps(receipt,indent=1)+"\n")
with gzip.open(r/"phy_native_to_outer_bits.json.gz","wt")as f:json.dump(dict(scope=receipt["R2_metric_scope"],bits=rows),f)
print(json.dumps(summary,indent=1))

