#!/usr/bin/env python3
"""Bounded source-rule and geometry screening. No RTL/native qualification."""
import argparse,collections,hashlib,json,math,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
p=a.packet
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
old=json.loads((Path(__file__).parent.parent/'s81_hwin_event_model_1019/model.json').read_text())
master=json.loads((p/'endpoint_master_contacts.json').read_text())['ot_sram_1r1w_64x16_m1']
macros=json.loads((p/'endpoint_macros.json').read_text());assert len(macros)==84
# 8 columns, 11 rows: five below and six above one full-width 200-row band.
ys=[43.2,86.4,129.6,172.8,216.0,345.6,388.8,432.0,475.2,518.4,561.6]
xs=[43.2*i for i in range(1,9)];band=[2.16,248.4,386.64,302.4];outline=[0,0,388.8,604.8];halo=10.8
free={(c,r) for c in range(8) for r in range(11)};groups=[]
for r in range(11):
 slots=[(c,r) for c in range(5)];groups.append(slots);free.difference_update(slots)
for r0,r1 in [(0,1),(2,3),(4,5),(6,7),(8,9)]:
 slots=[(c,r) for r in (r0,r1) for c in range(5,8)][:5];groups.append(slots);free.difference_update(slots)
assert len(groups)==16
remaining=sorted(free,key=lambda cr:(abs(ys[cr[1]]-275.4),cr))[:4]
assert len(remaining)==4
byevent=collections.defaultdict(list);aux=[]
for m in macros:
 match=re.search(r'g_event_mem\[(\d+)\]',m['name'].replace('\\',''))
 (byevent[int(match[1])] if match else aux).append(m)
placements=[]
for e,slots in enumerate(groups):
 assert len(byevent[e])==5
 for m,(c,r) in zip(sorted(byevent[e],key=lambda x:x['name']),slots):
  placements.append(dict(name=m['name'],event=e,xy=[xs[c],ys[r]],bbox=[xs[c],ys[r],xs[c]+18.36,ys[r]+20.79]))
for m,(c,r) in zip(sorted(aux,key=lambda x:x['name']),remaining):
 placements.append(dict(name=m['name'],event=None,xy=[xs[c],ys[r]],bbox=[xs[c],ys[r],xs[c]+18.36,ys[r]+20.79]))
def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-8 and min(a[3],b[3])-max(a[1],b[1])>1e-8
halos=[]
for m in placements:
 x,y,X,Y=m['bbox'];h=[x-halo,y-halo,X+halo,Y+halo];halos.append(h)
 assert all(abs(v/43.2-round(v/43.2))<1e-8 for v in m['xy'])
 assert h[0]>=0 and h[1]>=0 and h[2]<=outline[2] and h[3]<=outline[3]
 assert not overlap(h,band)
for i,h in enumerate(halos):
 assert all(not overlap(h,k) for k in halos[i+1:])
# Native abstract contacts, all signal+clock+PG rectangles retained exactly.
contacts=[];pg=[];signals=[]
for m in placements:
 x,y=m['xy']
 for pin in master['pins']:
  for r in pin['rectangles']:
   z=dict(macro=m['name'],event=m['event'],pin=pin['name'],signal=pin['signal'],layer=r['layer'],bbox=[r['bbox'][0]+x,r['bbox'][1]+y,r['bbox'][2]+x,r['bbox'][3]+y])
   contacts.append(z)
   (pg if pin['signal'] in ('POWER','GROUND') else signals).append(z)
assert len(pg)==84*53
# Pin-face density includes clock; power straps are explicitly separate physical shapes.
faces=collections.Counter('W' if r['bbox'][0]<.1 else 'E' for pin in master['pins'] if pin['signal'] in ('SIGNAL','CLOCK') for r in pin['rectangles'])
assert faces=={'W':32,'E':31};assert max(faces.values())/20.79<=6
# Event captures are bounded legal row *anchors*, not placed/sized cells.
regions=[]
for e in range(16):
 points=[((c['bbox'][0]+c['bbox'][2])/2,(c['bbox'][1]+c['bbox'][3])/2) for c in signals if c['event']==e]
 candidates=[(x,y) for x in [43.2*i for i in range(1,9)] for y in [249.48,275.4,301.32]]
 reach,x,y=min((max(abs(x-X)+abs(y-Y) for X,Y in points),x,y) for x,y in candidates)
 regions.append(dict(event=e,anchor=[x,y],max_contact_manhattan_um=reach,macro_count=5,signal_clock_contacts=len(points),native_stage_qualified=False))
assert max(x['max_contact_manhattan_um'] for x in regions)<405
# Added plain/ASR bits preserve prior additive budget; no existing state removed.
plain=1768+465;asr=48+5 # five additional reset group/local FF reservation, same third release
area=plain*.2916+asr*.37908;std=9788.4+area;ba=(band[2]-band[0])*(band[3]-band[1]);oa=388.8*561.6;na=388.8*604.8
# Small exact recurrence of SOURCE RULES only: idle walker, record invalidation,
# registered SRAM Q, registered compare, current-fresh-qualified fire.
def first_head(n,extra,phase,omit_hold=False):
 pointer=phase;fresh=False;raw=None;captured=None;eq=False;okq=False;valid=False;first=None;rows=[]
 for t in range(-1,n+7):
  q=raw;ok=valid and pointer==0
  fire=okq and fresh and eq
  if fire:first=t;break
  # Source st protects the slot one edge before its staged record; record
  # protects it again on the edge which sets vld. Omitting either is unsafe.
  hold=not omit_hold and pointer==0 and t in (-1,0)
  adv=fire or (not ok and not hold)
  selected=captured if extra else (q,fresh)
  next_eq=bool(selected and selected[1] and selected[0]==0)
  rows.append(dict(edge=t,pointer=pointer,valid=valid,fresh=fresh,hold=hold,q_slot=q,compare_ready=next_eq))
  # Model only a readiness predicate, not actual timestamp arithmetic. At
  # t=1 slot0 is either SRAM coherent or qualified by previous-write forwarding.
  raw=pointer if t>=1 else None
  captured=(q,fresh)
  fresh=not adv and not (t==0 and pointer==0)
  pointer=(pointer+1)%n if adv else pointer
  valid=valid or t==0
  eq=next_eq;okq=ok
 return first,rows
witness=[]
for n in range(2,48):
 rows=[]
 for phase in range(n):
  b,_=first_head(n,False,phase);c,_=first_head(n,True,phase)
  rows.append(dict(pointer_at_start=phase,baseline_first_ready_from_rec_slot=b,extra_capture_first_ready_from_rec_slot=c))
 witness.append(dict(n=n,phases=rows,baseline_worst_ready_from_rec_slot=max(r['baseline_first_ready_from_rec_slot'] for r in rows),capture_worst_ready_from_rec_slot=max(r['extra_capture_first_ready_from_rec_slot'] for r in rows),original_min_D=n+2))
assert witness[-1]['baseline_worst_ready_from_rec_slot']==47
assert witness[-1]['capture_worst_ready_from_rec_slot']==48
# Counterexample to the *model mutation* which drops source hold: its apparent
# 49->50 obstruction is spurious. Preserve it so it cannot become release lore.
omitted_hold=[first_head(47,False,46,True)[0],first_head(47,True,46,True)[0]]
assert omitted_hold==[49,50]
# Same-edge logical write collision: registered OLD raw is wrong, forwarding required.
forward=dict(edge=1,read_address=7,previous_write_address=7,old_raw=0x11,new_write_payload=0x93,qualified_q=0x93,raw_only_cache=0x11)
# Counterexample for simple retire delay: baseline slot already clear, delayed image busy.
retire_alias=dict(baseline_retire_edge=100,original_start_edge=101,baseline_preedge_vld_at101=0,delayed_preedge_vld_at101=1,result='baseline accepts; delayed retirement rejects if other predicates legal')
# No invented parent dimensions: exact formula and bounded packing sensitivity.
sens=[]
for N in [1,2,4,8,16,32,64]:
 sens.append(dict(old_array_rows=N,parent_height_um=N*561.6,new_rows_same_parent=math.floor(N*561.6/604.8),old_rows=N))
out=dict(schema='s81.hwin.region.calendar.model.v1',scope='MODEL ONLY; no RTL/gate/adoption',source_commit='1e057b7bf',kit_commit='281ec8898',source_hashes={f:sha(p/f) for f in ['dsdv_mu_hwin.sv','endpoint_macros.json','endpoint_master_contacts.json','endpoint_summary.json','overreach_pairs.json','ck.json']},baseline_failure_preserved=dict(overreach_pairs=93,unsafe_native_roots=9,pre_first_FF_predicate_bits=5,TT_setup_ps=[-371.040,-356.902,-354.383],macro_slew_TT_FF_ps=[503.3,525.8]),geometry=dict(outline=outline,old_outline=[0,0,388.8,561.6],band=band,legal_row_pitch_um=.27,band_rows=200,placement_grid_um=43.2,halo_um=halo,macro_count=84,macro_bits=86016,macro_area_um2=84*18.36*20.79,macro_macro_halo_overlap=0,macro_band_halo_overlap=0,origins_on_lattice=True,placements=placements,regional_anchors=regions,whole_routed_stage_qualified=False),contacts=dict(total_rectangles=len(contacts),signal_clock_rectangles=len(signals),PG_rectangles=len(pg),PG_terminal_objects=168,all_native_macro_contacts_retained=True,face_counts=dict(faces),face_per_um={k:v/20.79 for k,v in faces.items()},legal_access_vias_OBS_PG_connected=False),cost=dict(baseline_measured_std_um2=9788.4,added_plain_FF=plain,added_ASR_FF=asr,added_FF=plain+asr,added_FF_area_um2=area,band_area_um2=ba,priced_FF_inclusive_std_um2=std,priced_FF_inclusive_band_fraction=std/ba,remaining_std_before60pct_um2=.6*ba-std,macro_clock_count=84,macro_clock_cap_TT_FF_fF=[84*9.3458,84*10.3732],added_FF_clock_cap_TT_FF_fF=[plain*.474736+asr*.462899,plain*.522010+asr*.503152],extra_comparator_reset_clock_PG_area_um2=None),parent=dict(old_area_um2=oa,new_area_um2=na,area_delta_um2=na-oa,area_multiplier=na/oa,pooled_ideal_capacity_multiplier=oa/na,same_width_parent_integer_sensitivity=sens,actual_parent_width_um=None,actual_parent_height_um=None,actual_dies_per_wafer=None,actual_die_count_delta=None,extra_landing_edges=None),calendar=dict(original_contract='D>=nw+2, gap>=nw+2, D<=RL-2',first_head_walk_witness=witness,worst_case_trace=first_head(47,True,1)[1],omitted_hold_model_mutant=omitted_hold,omitted_hold_verdict='REJECTED model: contradicts source st/rec_slot protection',timestamp_mapping='accepted start tm at k; staged rec_slot sets vld at k+1; readiness+1 maps to D. n47 capture48 mapsD49. n2 baseline3 mapsD4, capture4 mapsD5; source-rule model, not RTL proof',two_slot_boundary=dict(original_D=4,baseline_ready_D=4,naive_capture_ready_D=5,scope='bounded source-rule readiness witness; full RTL counterexample still required'),proposed_early_write_bypass='capture coherent registered wdata at preceding write edge only when wv/address/record-generation prove selected head; no raw SRAM cache; control/timing/lifetime OPEN',early_capture_zero_date_qualified=False,sufficient_candidate_contract_NOT_PROVEN='Original D>=nw+2 may suffice for first-head readiness with BOTH source holds; pointer/generation/fresh/fault/retire/boot proof still OPEN',full_added_edge_local_compare_delta=1,complete_output_delta=None,retire_delta=None,RX_delta=None,boot_delta=None,parent_C_delta=None,SU_token_delta=None,MU_rate_delta=None,original_gold_changed=False,forwarding_witness=forward,retirement_delay_collision_witness=retire_alias),clock_root_plan=dict(regional_roots=18,event_roots=16,gap_retire_roots=2,event_macro_clock_cap_TT_FF_fF=[5*9.3458,5*10.3732],each_aux_macro_clock_cap_TT_FF_fF=[2*9.3458,2*10.3732],root_locations='beside each modeled event capture, separate gap/retire capture roots; exact CTS cells unpriced',macro_FF_slew_spread_neighbour_qualified=False,full_native_PG_census_required='all inst PG ITerms including protected clock cells and physical-only/ties, plus every macro PG geometry; PSM connected shape report alone insufficient'),implementation_authorized=False)
(a.out/'model.json').write_text(json.dumps(out,indent=2)+'\n');(a.out/'contacts.jsonl').write_text(''.join(json.dumps(c,separators=(',',':'))+'\n' for c in contacts))
# Small standalone SVG makes model footprint reviewable without claiming P&R.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="520" height="700" viewBox="-15 -35 430 670">','<rect x="0" y="0" width="388.8" height="604.8" fill="white" stroke="black"/>','<rect x="2.16" y="248.4" width="384.48" height="54" fill="#dae8fc" stroke="#4a78aa"/>','<text x="0" y="-12" font-size="12">HWIN MODEL: 388.8 x604.8; no physical approval</text>']
for m in placements:
 x,y=m['xy'];e=m['event'];svg.append(f'<rect x="{x}" y="{y}" width="18.36" height="20.79" fill="'+('#cde9ca' if e is not None else '#f3d8b5')+'" stroke="black" stroke-width=".4"/>');svg.append(f'<text x="{x+1}" y="{y+12}" font-size="6">{e if e is not None else "aux"}</text>')
for r in regions:
 x,y=r['anchor'];svg.append(f'<circle cx="{x}" cy="{y}" r="2" fill="#c0392b"/>')
svg+=['<text x="4" y="624" font-size="9">84 real macros; 43.2 origin grid; 10.8 halo; one 54um band</text>','<text x="4" y="638" font-size="9">Red: candidate anchors only. PG/OBS/routed stage/clock OPEN.</text>','</svg>'];(a.out/'floorplan_model.svg').write_text('\n'.join(svg)+'\n')
print(json.dumps(dict(geometry='SCREEN PASS',macro_count=84,PG_rectangles=len(pg),max_event_contact_lower_bound_um=max(r['max_contact_manhattan_um'] for r in regions),FF_inclusive_fill=std/ba,footprint_growth_pct=(na/oa-1)*100,calendar='HOLD: correct holds give47/48 after record; omitted-hold mutant49/50 rejected; full ABI proof OPEN')))
