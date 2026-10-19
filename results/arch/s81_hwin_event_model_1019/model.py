#!/usr/bin/env python3
"""Source-bound structural screening, not RTL or physical qualification."""
import argparse, collections, gzip, hashlib, json, math, re
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument("--packet",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
p=a.packet
roots=json.load(gzip.open(p/"endpoint_roots.json.gz","rt"))
summary=json.loads((p/"endpoint_summary.json").read_text())
pairs=json.loads((p/"overreach_pairs.json").read_text())
macros=json.loads((p/"endpoint_macros.json").read_text())
assert len(macros)==84 and len(pairs)==93 and len(roots)==49834
assert len(summary["over32_nonclock"])==9
# Native endpoint coordinates, not macro origins: collect all actual pins.
def event(s):
 m=re.search(r"g_event_mem\[(\d+)\]",s.replace("\\", ""))
 return int(m[1]) if m else None
contacts=collections.defaultdict(dict)
for r in roots:
 for s in [r["driver"]]+r["sinks"]:
  e=event(s["pin"])
  if e is not None and s["role"]=="macro": contacts[e][s["pin"]]=s["xy"]
# Candidate FF Q anchor in existing band. Legal ROW/SITE placement of cells,
# halo, PG and routed path remain separate requirements.
regions=[]
for e in range(16):
 points=list(contacts[e].values())
 best=min((max(abs(x-X)+abs(270-Y) for X,Y in points),x) for x in [43.2*i for i in range(1,9)])
 regions.append(dict(event=e,macro_count=sum(event(m["name"])==e for m in macros),signal_contact_count=len(points),candidate_q_xy=[best[1],270],max_manhattan_contact_um=best[0],routed_reach_qualified=False))
assert all(x["macro_count"]==5 for x in regions)
fanout=[]
for x in summary["over32_nonclock"]:
 pin=x["driver"]["pin"]; n=x["count"]
 fanout.append(dict(driver=pin,role=x["driver"]["role"],old_native_sink_pins=n,partitions=math.ceil(n/24),max_partition_sink_pins=math.ceil(n/math.ceil(n/24)),method="independent useful source predicate" if x["driver"]["role"]=="comb" else "same-edge state copies with identical update/clear and separate actual consumer groups",native_closure=False))
# Source has 16*63 payload write captures; native merges to 543.
old_wdata=sum(x["driver"]["role"]=="ff" and ".u_payload.wdata" in x["driver"]["pin"] for x in roots)
assert old_wdata==543
# Conservative complete capture bundle: head63+attr2+fresh1+ok1+pointer6+time32.
components={"event_read_context_plain_ff":16*(63+2+6+32),"event_context_valid_asr_ff":16*2,"retire_context_plain_ff":32+32+6,"retire_context_valid_asr_ff":2,"boot_alignment_plain_ff":50,"boot_alignment_valid_asr_ff":2,"same_edge_state_copy_asr_ff":sum(x["partitions"]-1 for x in fanout if x["role"]=="ff")}
plain=sum(v for k,v in components.items() if "plain" in k); asr=sum(v for k,v in components.items() if "asr" in k)
coeff={"DFFHQNx1":dict(area_um2=.2916,clock_cap_tt_ff=[.474736,.522010]),"DFFASRHQNx1":dict(area_um2=.37908,clock_cap_tt_ff=[.462899,.503152])}
base_area=9788.4; band_area=384.48*43.2
extra_area=plain*.2916+asr*.37908
out=dict(scope="MODEL ONLY: explicit new capture alternative; no retimed RTL proof; no admission",source_commit="1e057b7bf",source_hashes={f:sha(p/f) for f in ["dsdv_mu_hwin.sv","endpoint_roots.json.gz","overreach_pairs.json","endpoint_macros.json","ck.json"]},baseline=dict(native_roots=len(roots),macro_clocks=84,endpoint_pairs=93,macro_sink_pairs=sum(x["sink"]["role"]=="macro" for x in pairs),macro_to_comb_pairs=sum(x["driver"]["role"]=="macro" for x in pairs),max_endpoint_manhattan_um=max(x["manhattan_um"] for x in pairs),tt_setup_ps=[-371.040,-356.902,-354.383],macro_slew_tt_ff_ps=[503.3,525.8],macro_lateness_tt_ff_ps=[111.2,126.6],old_native_payload_write_ff=old_wdata),fanout_partition_model=fanout,regional_contact_model=regions,capture_components=components,capture_ff_total=plain+asr,capture_variant_incremental_area_um2=extra_area,capture_clock_cap_tt_ff_fF=[plain*.474736+asr*.462899,plain*.522010+asr*.503152],same_edge_write_unshare=dict(required_payload_write_ff=1008,old_native_ff=543,additional_plain_ff=465,additional_area_lower_bound_um2=465*.2916,additional_clock_cap_tt_ff_fF=[465*.474736,465*.522010],retention_proof="OPEN: keep real event-local memory hierarchy and all consumer ownership; native census must demonstrate actual distinct cells"),band=dict(area_um2=band_area,current_standard_area_um2=base_area,current_fraction=base_area/band_area,maximum_same_geometry_fraction=.6,remaining_area_at_60pct_um2=.6*band_area-base_area,capture_only_fraction_lower_bound=(base_area+extra_area)/band_area,verdict="FAIL unchanged band budget; needs new modeled legal rows/macro/halo layout and parent grant"),cost_coefficients=coeff,unpriced_required=["additional boot payload/control alignment and all five predicate cone replicas", "reset tree regional leaves/groups and asynchronous clear recovery", "clock-tree cells/wire/capacitance for all 84 macros and added FF", "new wire repeaters, pin landings, PG/contact/via escape and clock-root isolation", "source-mapped exact AO21 equation and upstream fanout propagation", "retire/boot count/record admissibility and whole parent calendar delta"],contract=dict(compare_capture_minimum_added_edges=1,complete_hwin_output_edge_delta=None,parent_C_delta=None,hwin_start_delta=None,pinpipe_delta=None,full_token_delta=None,unchanged_gold_required=True,early_prefetch_zero_delta_proved=False),implementation_authorized=False)
out["existing_macro_clock_load_tt_ff_fF"]=[84*9.3458,84*10.3732]
out["native_library_sha256"]={"tt":"57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3","ff":"d9b6e75c8720cdd450cff15178528502cc8df34c5ab6b0ffb53fc99d664b5302"}
classified=[]
for i,x in enumerate(pairs):
 d=x["driver"]["pin"]; t=x["sink"]["pin"]
 kind="head address before registered OLD-data read" if ".pb_r" in d else "registered payload write bank" if x["sink"]["role"]=="macro" else "registered SRAM output to compare cone"
 classified.append(dict(pair=i,driver=d,sink=t,producer_event=event(d),consumer_event=event(t),owner=kind,old_endpoint_manhattan_um=x["manhattan_um"],repair="event-local same-edge independently retained write/address capture" if x["sink"]["role"]=="macro" else "new read-context capture and aligned compare stage",schedule_proof="OPEN"))
(a.output.parent/"endpoint_pair_ownership.json").write_text(json.dumps(classified,indent=2)+"\n")
# Independently read/hash exact native Liberty coefficients; no synthesis.
libdir=Path("/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM")
for corner in ("tt","ff"):
 lib=libdir/("asap7sc7p5t_SEQ_RVT_"+corner.upper()+"_nldm_220123.lib")
 assert sha(lib)==out["native_library_sha256"][corner]
 text=lib.read_text()
 for master,area,cap in (("DFFHQNx1_ASAP7_75t_R",.2916,.474736 if corner=="tt" else .522010),("DFFASRHQNx1_ASAP7_75t_R",.37908,.462899 if corner=="tt" else .503152)):
  cell=text[text.index("cell ("+master+")"):]; cell=cell[:cell.find("\n  cell (",1)]
  assert float(re.search(r"area\s*:\s*([0-9.]+)",cell)[1])==area
  pin=cell[cell.index("pin (CLK)"):]; pin=pin[:pin.index("}")]
  assert float(re.search(r"capacitance\s*:\s*([0-9.]+)",pin)[1])==cap
out["native_library_coefficients_independently_verified"]=True
a.output.write_text(json.dumps(out,indent=2)+"\n")
