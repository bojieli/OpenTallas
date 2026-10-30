import json,re,hashlib,collections
from pathlib import Path
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path("/tmp/qcclock0336");root=Path("/home/ubuntu/OpenTallas")
plan=json.load(open(r/"plan_qc45.json"));pp=json.load(open(r/"phy_plan_pins.json"))
paths={"phy_serdes":"physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597.lef","phy_serdes_b":"physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597.lef","phy_ucie_kv":"physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy.lef","coll_ucie":"physical/qwen_missing_phy/ot_qfd_ucie_x64_phy/ot_qfd_ucie_x64_phy.lef"}
views={}
for tn,path in paths.items():
 text=(root/path).read_text();size=list(map(float,re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)",text).groups()));pins={}
 for m in re.finditer(r"^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$",text,re.M|re.S):
  n,b=m.groups();rr=re.search(r"RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)",b)
  if not rr:continue
  rect=list(map(float,rr.groups()));layer=re.search(r"LAYER\s+(\S+)",b).group(1);use=re.search(r"USE\s+(\S+)",b).group(1)
  if use in ["SIGNAL","CLOCK"]:pins[n]={"layer":layer,"rect_um":rect,"xy_um":[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],"use":use}
 north={k:v for k,v in pins.items()if abs(v["rect_um"][3]-size[1])<1e-6}
 native_payload={k:v for k,v in pins.items()if re.match(r"^(tx_flit\[\d+\]|rx_flit\[\d+\]|tx_v|rx_v|tx_up)$",k)}
 buses=collections.defaultdict(list)
 for b,i,l,x,y,f in pp[tn]["pins"]:buses[b].append([i,l,x,y,f])
 views[tn]={"path":path,"sha256":hashlib.sha256((root/path).read_bytes()).hexdigest(),"outline_um":size,"clock":pins.get("clk"),"reset":pins.get("rst_n"),"native_signal_clock_pins":len(pins),"native_north_field":{"pins":len(north),"span_x_um":[min(x["rect_um"][0]for x in north.values()),max(x["rect_um"][2]for x in north.values())],"layers":sorted(set(x["layer"]for x in north.values()))},"native_fdi_payload_pins":len(native_payload),"synthetic_plan_slot_um":pp[tn]["outline"],"synthetic_plan_signal_pins":len(pp[tn]["pins"]),"synthetic_clock":pp[tn]["clock"],"plan_buses":{b:{"physical_bits_including_epoch":len(v),"max_bit":max(z[0]for z in v),"layers":sorted(set(z[1]for z in v)),"faces":sorted(set(z[4]for z in v)),"x_range_um":[min(z[2]for z in v),max(z[2]for z in v)],"y_range_um":[min(z[3]for z in v),max(z[3]for z in v)]}for b,v in buses.items()},"pins":pins}
instances={}
for p in plan["partitions"]:
 if p["type"]not in paths:continue
 tn=p["type"];v=views[tn];W,H=pp[tn]["outline"];mw,mh=v["outline_um"];ox,oy=p["origin_um"];ori=p.get("orient","R0")
 def trans(x,y):return [ox+(W-x if ori in ["MY","R180"]else x),oy+(H-y if ori in ["MX","R180"]else y)]
 corners=[trans(x,y)for x,y in[(0,0),(mw,0),(0,mh),(mw,mh)]];xs,ys=zip(*corners)
 instances[p["name"]]={"type":tn,"orient":ori,"slot_origin_um":[ox,oy],"slot_outline_um":[W,H],"native_body_type_origin_um":[0,0],"native_body_type_outline_um":[mw,mh],"proposed_native_body_bbox_um":[min(xs),min(ys),max(xs),max(ys)],"required_leaf_bbox_origin_um":[min(xs),min(ys)],"native_clock_die_xy_um":trans(*v["clock"]["xy_um"]),"native_reset_die_xy_um":trans(*v["reset"]["xy_um"]),"naive_direct_bare_leaf_clock_xy_um":[ox+v["clock"]["xy_um"][0],oy+(mh-v["clock"]["xy_um"][1]if ori=="MX"else v["clock"]["xy_um"][1])]}
note={"scope":"READ-ONLY impact/proposal, no plan/source/RTL changes or new route. Native hard views selected from the exact currently-declared module/lib directory, not substituted nface variants.","target_construction":"target2 uses die_trial.abstract_lef per type; synthetic slot SIZE, plan face pins and synthetic M7 clock/reset taps. No canonical native PHY LEF imported. Slot/body offset and leaf pin routing are absent.","slot_transform_proposal":"Preserve current outer slot/origin/port fields. Declare inner native body origin[0,0], native SIZE, R0, LEF/lib source. Transform inner body corners through parent slot orientation; place native leaf bbox at their minimum, not naively at parent origin under MX/MY. Only after review realize explicit wire-only adapter from native FDI/reset pins to current outer face/epoch pins. Existing registered-hard RTL strips incoming epoch and drives outgoing epoch from delivered reset, no new flops.","clock_proposal":"Bare hard PHY clock access must identify actual native M5 clk rectangle plus source hash, with exact slot/body transform. Any outer M7 clock port/via adapter requires explicit physical wiring; changing clock.tap alone is insufficient because clock_pins still snaps to partition tracks and abstract_lef fabricates M7 pin geometry. coll_ucie is mixed soft logic plus native PHY: preserve top/grid clocks separately, replace only native core entry and remove/reassign glue grid taps/stations inside PHY body before native build.","minimal_guards":["All native PHY cells/clock drivers/START/reset infrastructure must be outside full native body+declaredhalo; no interior die-clock island is opened by inherited contents-only metadata.","Native LEF body SIZE/origin/orient and slot transform must match actual placed bbox; MX body-offset4.104um for current SerDes cannot be dropped.","Native clk/rst terminal rect/layer must match exact source LEF; no lattice snapping or fabricated clock-center claims.","Every current outer payload/epoch port needs exact native-bit/constant wire mapping; all real native PHY pins remain accessible with no synthetic undeclared native epoch pins.","Do not replace coll_ucie soft wrapper by bare PHY; retain native core/body and soft logic/clock roles explicitly.","Physical provider/source promotion waits for reviewed body exclusions+nativeentry+adapter recipe; current graph remains INFRA coupon."]}
receipt={"plan_sha256":hashlib.sha256((r/"plan_qc45.json").read_bytes()).hexdigest(),"views":views,"instances":instances,"proposal":note}
(r/"phy_native_impact.json").write_text(json.dumps(receipt,indent=1)+"\n")
# Geometry/port-field impact, deliberately no proposed point movement.
v=views["phy_serdes"];mw,mh=v["outline_um"];W,H=pp["phy_serdes"]["outline"]
fig,axes=plt.subplots(1,3,figsize=(15,8),dpi=140)
for ax,tn in zip(axes[:2],["phy_serdes","phy_serdes_b"]):
 ax.add_patch(Rectangle((0,0),W,H,fill=False,ec="black",lw=1.5));ax.add_patch(Rectangle((0,0),mw,mh,fc="lightgrey",ec="grey",alpha=.6))
 for b,i,l,x,y,f in pp[tn]["pins"]:ax.plot(x,y,".",color="royalblue",ms=1.8)
 for p in v["pins"].values():ax.plot(*p["xy_um"],".",color="crimson",ms=2)
 ax.plot(*pp[tn]["clock"][0][1:],"x",color="purple",ms=9);ax.plot(*v["clock"]["xy_um"],"o",color="darkorange",ms=7)
 ax.set(xlim=(-60,W+100),ylim=(-60,H+100),title=tn+"\nblue=existing plan face pins; red=native FDI\npurple=synthetic clock; orange=native clk",xlabel="x local (um)",ylabel="y local (um)");ax.set_aspect("equal")
ax=axes[2]
ax.add_patch(Rectangle((0,0),W,H,fill=False,ec="black"));ax.add_patch(Rectangle((0,H-mh),mw,mh,fc="lightgrey",ec="grey",alpha=.6))
for p in v["pins"].values():x,y=p["xy_um"];ax.plot(x,H-y,".",color="crimson",ms=2)
ax.plot(v["clock"]["xy_um"][0],H-v["clock"]["xy_um"][1],"o",color="darkorange",ms=7)
ax.annotate("native bbox lower edge = +4.104 um\nnative clk = +4.200 um\nnaive bare-leaf placement would use +0.096 um",xy=(753,4.2),xytext=(30,330),arrowprops={"arrowstyle":"->"},fontsize=9)
ax.set(xlim=(-60,W+100),ylim=(-60,H+100),title="SerDes MX in unchanged slot\nslot/body height difference must be retained",xlabel="x relative slot (um)",ylabel="y relative slot (um)");ax.set_aspect("equal")
fig.suptitle("QC PHY native-entry impact: current die target is a synthetic slot adapter, not the declared hard LEF")
fig.tight_layout();fig.savefig(r/"phy_native_impact.png")
print({k:{"nativeN":v["native_north_field"],"planpins":v["synthetic_plan_signal_pins"],"nativepayload":v["native_fdi_payload_pins"]}for k,v in views.items()});print(instances["io_serdes"])

