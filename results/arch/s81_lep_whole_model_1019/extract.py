#!/usr/bin/env python3
"""Small read-only source/receipt inventory. No synthesis or P&R."""
import hashlib,json,re,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
BASE=ROOT/"results/arch/s81_endpoint_physical_pickup_1019"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
paths=["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv","rtl/lib/ot_sram_oldread_wreg.sv","rtl/lib/ot_sram_showahead_1r1w.sv","rtl/lib/ot_rst_relay_tree3.sv"]
d={"schema":"opentallas.s81.lep.source_model.v1","verdict":"HOLD_MODEL_ONLY","source_commit":"d37b5dae18f9dbc9c68dce5a10ac12a8092f7c24","kit_commit":"66a0feffc6596158f7611a8fbf919d619eb61d23","receipt_commit":"15729fb15b6c7f3f6d05839c05d8d4adffc4d550","parent_fit":None,"token_delta":None,"hashes":{p:sha(ROOT/p) for p in paths},"macros":[],"variants":{},"source_shape":{"NL":2,"W":553,"DT":512,"DR":8,"SB":8,"GA":4,"TX_slices_per_lane":70,"TX_address_groups_per_lane":18,"TX_reset_stride":106,"frame_slices":138,"RX_slices_per_lane":70,"RX_local_hit_groups_per_lane":5,"TXRP":1,"RX_SRAM":1,"TX_helper_GROUP_IO":1},"capacity":{"TX_useful_bits":2*512*553,"RX_useful_bits":2*8*553,"TX_physical_bits":10*512*128,"RX_physical_bits":10*32*128,"total_useful_bits":2*(512+8)*553,"total_physical_bits":10*(512+32)*128},"no_new_runs":True}
for fam,rel in [("TX","physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2"),("RX","physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1")]:
 p=ROOT/rel; lef=next(p.glob("*.lef")); s=lef.read_text(); w,h=map(float,re.search(r"SIZE ([0-9.]+) BY ([0-9.]+)",s).groups()); j=json.loads(next(p.glob("*.json")).read_text()); contacts={"W":[],"E":[]}; supplies={}; pitch={}
 for name,body in re.findall(r"  PIN (\S+)\n(.*?)  END \1",s,re.S):
  rects=[tuple(map(float,x)) for x in re.findall(r"RECT ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+)",body)]
  if "USE POWER" in body or "USE GROUND" in body: supplies[name]={"rectangles":len(rects),"layer":re.findall(r"LAYER (\S+)",body)}; continue
  for x1,y1,x2,y2 in rects:
   face="W" if x1==0 else "E" if abs(x2-w)<1e-6 else "interior"
   if face in contacts: contacts[face].append({"pin":name,"xy":[(x1+x2)/2,(y1+y2)/2]})
 for face,cs in contacts.items():
  ys=sorted(c["xy"][1] for c in cs); pitch[face]=min(b-a for a,b in zip(ys,ys[1:]))
 md={"role":fam,"master":p.name,"count":10,"size_um":[w,h],"area_um2":w*h,"face_contacts":{k:len(v) for k,v in contacts.items()},"face_density_per_um":{k:len(v)/h for k,v in contacts.items()},"pin_pitch_um":pitch,"clock":next(c for cs in contacts.values() for c in cs if c["pin"]=="clk"),"supplies":supplies,"obs":s[s.index("  OBS"):s.index("END "+p.name,s.index("  OBS"))].strip(),"timing":{c:{k:t[k] for k in ["clk_cap_ff","clk_to_q_ps","setup_ps","hold_ps","min_period_ps","min_pulse_ps"]} for c,t in j["timing"].items()},"contacts":contacts,"hashes":{str(x.relative_to(ROOT)):sha(x) for x in sorted(p.iterdir()) if x.is_file()},"qualified_pin_density":False,"legal_contact_via_PG_escape":None}
 d["macros"].append(md)
for kind,pins,ffs,area,movable in [("A",6717,16926,7879.4,12475.76),("H",7424,18298,8516.8,13412.94)]:
 name="lepmua" if kind=="A" else "lepmuh"; kit=ROOT/f"physical/ref_tile/s81sl_{name}_sf"; fp=json.loads((kit/"floorplan.json").read_text()); gate=BASE/f"s81sl_{name}_sf/gate_result.json"; reg=593 if kind=="A" else 647; groups=(reg+31)//32
 d["variants"][kind]={"pins":pins,"ff":ffs,"macro_clocks":20,"std_synth_um2":area,"DPL_movable_um2":movable,"observed_area_multiplier":movable/area,"band":[2.16,259.2,473.04,291.6],"band_height_um":32.4,"band_area_um2":470.88*32.4,"DPL_area_over_band":movable/(470.88*32.4),"nominal_clock_root_sinks":ffs+20,"reset_tree":{"face_stages":2,"internal_tree_stages":3,"regions":reg,"groups":groups,"internal_reset_FF":reg+groups+1,"conditional_release_edges_if_face_feeds_tree":5,"conditional_first_consumer_edge":6,"native_face_ancestry":None,"asynchronous_assertion":"internal tree cascaded async reset; emitted face wrapper and external stopped-clock assertion OPEN"},"macro_positions":fp["blocks"],"gate_sha256":sha(gate),"DPL_log_sha256":sha(BASE/f"{name}_cts.log.gz"),"source_keep_roles":{"A":"four host-only names absent because HOST_EN=0; remove inapplicable keep entries only after source-role proof","H":"host-only modules instantiated; exact keep semantics still required"}[kind]}
d["sizing_only"]={"same_outline_64p8_band":{"area_um2":470.88*64.8,"A_observed_mass_util":12475.76/(470.88*64.8),"H_observed_mass_util":13412.94/(470.88*64.8),"legal_macro_band_overlap":False,"status":"NOT A FIX: existing macro rows216/302.4 collide with widened central band plus halo; relocation and actual reach required"},"whole_register_footprint_inventory":"native totals exact; per-family mapped mass unavailable without hierarchy extraction; no inferred disjoint subtotal claim","regional_landing_lower_bound":{"streams":4,"widths":[553,553,559,559],"slots":4,"logical_payload_bits":4*(553*2+559*2),"single_clock_32x128_bank_count_lower_bound":20,"physical_SRAM_bits_lower_bound":20*32*128,"dual_domain_storage_macro":None,"capture_payload_FF_lower_bound":2*(553*2+559*2),"pointer_reset_identity_logic_area":None,"clock_phase_and_exact_hop_edges":None,"full_latency_delta":None,"status":"NOT READY: lower bound only, does not select single-clock SRAM for independently rooted crossings"}}
(OUT/"model.json").write_text(json.dumps(d,indent=2)+"\n")
print("MODEL_WRITTEN",OUT/"model.json")
