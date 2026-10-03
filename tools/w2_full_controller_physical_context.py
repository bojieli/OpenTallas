#!/usr/bin/env python3
"""Full selected W2 physical sizing and admission. No compiler/flow is launched."""
import argparse,ast,collections,hashlib,importlib.util,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_full_controller_physical_context_20261003'
SOURCES=[
 'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_protected_completion_reset_quarantine.sv',
 'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_coded_secondary_reset_quarantine.sv',
 'rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv',
 'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv']
PARAMS=dict(OPT_EXACT=1,OPT_RESET_QUARANTINE=1,NC=6,MAX_OUT=16,AW=34,CTAGW=32,GENW=4,SIDW=3,PTAGW=35,PC_ID=0)
BASE='f6df84e14c2bc5908bdbf85b2bd95cd56b1f5520'
PRICE='results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'
class Refusal(ValueError):pass
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def width_expr(expr,params):
 def ev(n):
  if isinstance(n,ast.Constant) and type(n.value)==int:return n.value
  if isinstance(n,ast.Name) and n.id in params:return params[n.id]
  if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult)):
   a,b=ev(n.left),ev(n.right)
   return a+b if isinstance(n.op,ast.Add) else a-b if isinstance(n.op,ast.Sub) else a*b
  raise Refusal('nonconstant width')
 return ev(ast.parse(expr,mode='eval').body)
def ports(text,params=PARAMS):
 head=text.split(')(',1)[1].split(');',1)[0];book={}
 for m in re.finditer(r'\b(input|output)\s+(?:wire|reg|logic)\s*(?:\[([^\]]+)\])?\s*([^;\n]+)',head):
  direction,rg,names=m.groups();w=1
  if rg:
   hi,lo=rg.split(':');w=width_expr(hi,params)-width_expr(lo,params)+1
  for n in names.strip().rstrip(',').split(','):
   n=n.strip()
   if not re.fullmatch(r'\w+',n):raise Refusal('port declaration')
   book[n]=dict(direction=direction,bits=w)
 return book

def model():
 text=(ROOT/SOURCES[0]).read_text();sec=(ROOT/SOURCES[1]).read_text()
 pb={int(i):int(w) for i,w in re.findall(r'(\d+):payload_bits=(\d+);',text)}
 kinds={int(i):int(k) for i,k in re.findall(r'(\d+):kind=(\d+);',text)}
 primary=[int(v) for _,v in re.findall(r'(\d+):\s*global_index=(\d+);',text)]
 secondary=[int(v) for _,v in re.findall(r'(\d+):\s*global_index=(\d+);',sec)]
 assert len(primary)==182 and len(secondary)==37 and set(primary).isdisjoint(secondary)
 assert sorted(primary+secondary)==list(range(219)) and set(pb)==set(range(219))
 canonical=json.loads((ROOT/'results/uarch/w2_nc6_correction_control_20261003/inputs/canonical_map.json').read_text())['rows']
 assert all(pb[r['index']]==r['payload_bits'] and kinds[r['index']]==r['kind'] for r in canonical)
 spec=importlib.util.spec_from_file_location('codec',ROOT/'tools/w2_nc6_mutable_protection_model.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
 facts=json.loads((ROOT/PRICE).read_text())['facts'];A=lambda n:facts[n]['SS']['area_um2']
 F='DFFASRHQNx1_ASAP7_75t_R';I='INVx1_ASAP7_75t_R';N='NAND2x1_ASAP7_75t_R';B='BUFx4_ASAP7_75t_R'
 old=json.loads((ROOT/'results/uarch/w2_nc6_mutable_protection_20261003/model.json').read_text());bits=219*72
 def xor_count(rows):
  enc=0
  for n in rows:
   ns=[sum(bool(p&(1<<i)) for p in c.POSITIONS[:n]) for i in range(7)]
   enc+=sum(max(0,v-1) for v in ns)+max(0,n+sum(v>0 for v in ns)-1)
  return enc,len(rows)*(sum(m.bit_count()-1 for m in c.MASKS)+71)
 e,k=xor_count(list(pb.values()));oe,ok=xor_count([r['payload_bits'] for r in c.layout()])
 tree=lambda n:sum(math.ceil(n/8**i) for i in range(1,1+math.ceil(math.log(max(2,n),8))))
 # Exact retained count-utility constructive budget, with full219 word selectors exposed separately.
 mux=lambda n:2*n+3*(n-1)
 write_mux=96*72*(mux(8)-3)+123*72*(mux(6)-3)
 en_decode=(3*96+6*16+6*16+2*219)*10*4
 guard=6*5*9+6*(72*4+10*4+4*4+32)+219*16+8*96+6*64
 buf=math.ceil((2*219*72+6*16*72)/8)
 holdbit=A(F)+2*A(I)+3*A(N)+2*A(B)+.04374
 retained219=old['cell_price']['gross_body_mm2_perPC_ASSUMED']+((bits-13608)*holdbit+(4*(e+k-oe-ok)+write_mux+en_decode+guard)*A(N)+2*(tree(bits)-tree(13608))*A(B)+buf*A(B))/1e6
 # Address ranges are semantically qualified, but do not assume synthesis narrows dynamic selectors.
 raw_fixed_mux=8*2*(219-1)*72
 peer_payload_mux=8*2*3*(219-1)*44
 selector_nands=3*(raw_fixed_mux+peer_payload_mux)
 # Replace the old opaque fullcorrection/rescue budgets, not add them twice.
 replaced=old['cell_price']['fullcorrection_NAND2_budget']+(219*16+8*96+6*64)
 guard_lut=8*(7*4+72*4+10*4+96*4+7*219*4) # explicit conservative separate checks/priority sizing reserve
 priced=retained219+(selector_nands+guard_lut-replaced)*A(N)/1e6
 portbook=ports(text);inputs=sum(v['bits'] for v in portbook.values() if v['direction']=='input');outputs=sum(v['bits'] for v in portbook.values() if v['direction']=='output')
 polarity={}
 for pc in range(128):
  ones=sum(c.seal(int(i==132),pc,i,kinds[i]).bit_count() for i in range(219))
  polarity[str(pc)]={'SETN_bits':ones,'RESETN_bits':bits-ones,'reset_SS_fF':ones*facts[F]['SS']['pins']['SETN']['cap_fF']+(bits-ones)*facts[F]['SS']['pins']['RESETN']['cap_fF']}
 byrec=collections.Counter(r['record'] for r in canonical)
 return dict(schema='w2.full-controller.physical-context.v1',source_commit=BASE,
  source_sha256={p:sha(ROOT/p) for p in SOURCES},model_sha256={p:sha(ROOT/p) for p in ['tools/uarch_model.py','tools/w2_nc6_count_utility_closure.py','tools/w2_nc6_mutable_protection_model.py',PRICE]},
  selected_top='ot_w2_nc6_protected_completion_reset_quarantine',parameters=PARAMS,
  storage=dict(words=219,primary_words=182,secondary_words=37,physical_bits=bits,payload_bits=sum(pb.values()),static_seal_padding_bits=bits-sum(pb.values()),record_CW_census=dict(byrec),no_reduced_proxy=True,netlist_required='219*72 live physically-preserved sequential bits INCLUDING seal/padding; keep attributes alone are not proof; reject constant-pruned mapped census'),
  ports=dict(book=portbook,input_bits=inputs,output_bits=outputs,boundary_signal_bits=inputs+outputs-2,client_lanes=6,client_payload_bits_per_lane=256,backend_payload_bits=256,client_offered_payload_bytes_per_edge=6*32,backend_accepted_payload_bytes_per_edge_upper=32,new_ports=0,service_unit='controller does no MACs; data32B per accepted beat, physical HBM64B sector distinct'),
  logic_inventory=dict(MACs=0,parallel_current_decoders=219,independent_write_encoders=219,encoder_variable_XOR2=e,current_check_XOR2=k,codec_constructive_NAND2=4*(e+k),table_rows=96,table_read_lookup_ports=3,journal_seats=9,journal_payload_bits_each=87,count_workers=6,count_worker_payload_bits=98,corrector_engines=8,corrector_payload_bits=96,full_word_write_router_NAND2=write_mux,write_enable_decode_NAND2=en_decode,write_router_BUFx4=buf,normal_primary_writers=9,secondary_count_writers=6,raw_fixed_dynamic_bitmux_upper=raw_fixed_mux,peer_payload_dynamic_bitmux_upper=peer_payload_mux,selector_NAND2_upper=selector_nands,proxy_repair_rescue_NAND2_replaced=replaced,extra_guard_priority_NAND2_reserve=guard_lut),
  area=dict(retained_219_constructive_budget_mm2_per_PC=retained219,full_source_selector_exposed_budget_mm2_per_PC=priced,clock_reset_SS_CLK_fF=bits*facts[F]['SS']['pins']['CLK']['cap_fF'],reset_by_PC=polarity,method='Retained189 baseline plus exact30CW/count/write-router delta; expose full219 dynamic raw/fixed/peer payload selectors conservatively instead of assumed narrow banks; replace opaque old repair/rescue budgets once. Analytical sizing reserve, NOT exact mapped gates/SSFF fit.',net_F0_replacement=None,actual_mapped_area=None,assigned_slot=None,actual_mux_simplification_credit=0,PG_CTS_routing_hold_repair='existing analytical floor only; actual loaded construction not included as qualified fit'),
  replication=dict(requested_controllers=1280,bits_total=bits*1280,body_mm2_total=priced*1280,at50pct_placement_mm2_before_actual_PG_routes=priced*1280/0.5,per_die_existing_PC_geometry=128,requested_die_equivalents=10,scope='User requested1280 composition. Per-controller PC_ID7 remains die-local0..127; no 1280-wide tag truncation or unsupported whole-system family assignment. Existing qwen r11 has128PC/die, not a controller-specific slot.',net_replacement_credit=0),
  latency=dict(clock_target_hz=1200000000,period_ps=2500/3,setup_uncertainty_ps=60,hold_uncertainty_ps=25,same_client_request_II_edges=19,different_client_prospective_II_edges=10,corrector_recurring_II=9,CAP=4,FIX=4,rearm_edges=1,positive_clock_bound_is_not_admitted=True,conditional_backend_payload_B_per_edge=32/10,conditional_1280_backend_payload_Bps=1280*32/10*1200000000,measurement='30case gate functional, no continuous service benchmark.19/10 source calendar retained; no arbitrary timeout, fault repair retirement may stall.',whole_token_delta=None,whole_token_composition_required='Bind this source-calendar controller to actual per-PC accepted request/dependency counts/parallelism in unified HBM model; do not add independent latency estimates or inherit generic500ns loaded-HBM figure.'),
  context_requirements=['Authoritative fullcontroller slot ID/bbox/PG/OBS/neighbor/clockreset allocation from Claude HBM, disjoint Goodall RF','Named port-driver cells and min/max slew/input arrival/capture arcs/output loads for EVERY real port; no ideal unloaded IO','Exact legal M2-M5/escape widths/tracks/pitches/sourcefamily capacities and onceonly1280 replica assignments','Locked SS+FF Liberty/LEF/RC scale coherence, real CTS/reset insertion/skew/loads and clock period833.333ps/60setup25hold','Mapped sequential census must preserve full15768 CW bits and complete6client/9journal/8engine/219codec cones; reject pruned proxy','Unified composed token latency/area netF0 debit and actual selected1280 scope binding; no rate credit'],
  decision='BLOCKED_CONTEXT_ALLOCATION_AND_LOADED_PORT_MODEL',actions=dict(compiler=False,PnR=False,runtime=False,main_edit=False),resource_policy='EPYC measured headroom and peer lease required; no wall/CPU/AS/perfile caps; preserve incremental outputs')

def admit(context):
 m=model()
 if context.get('source_sha256')!=m['source_sha256']:raise Refusal('source enrollment')
 if context.get('parameters')!=PARAMS or any(type(v)!=int for v in context.get('parameters',{}).values()):raise Refusal('full selected parameters')
 slot=context.get('slot',{});box=slot.get('bbox_um',[])
 if not slot.get('id') or len(box)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in box) or box[2]<=0 or box[3]<=0:raise Refusal('actual allocated slot')
 util=slot.get('placement_utilization');excluded=slot.get('PG_OBS_excluded_um2')
 if type(util) not in (int,float) or not math.isfinite(util) or not 0<util<=0.5:raise Refusal('placement density not priced')
 if type(excluded) not in (int,float) or not math.isfinite(excluded) or excluded<0:raise Refusal('PG/OBS exclusion unknown')
 if (box[2]*box[3]-excluded)*util < m['area']['full_source_selector_exposed_budget_mm2_per_PC']*1e6:raise Refusal('full source slot area deficit')
 if not slot.get('owner_receipt_sha256') or not slot.get('PG_clock_reset_OBS_bound') or not slot.get('neighbor_context'):raise Refusal('loaded physical slot ownership')
 if not context.get('replica1280_source_map') or not context.get('unified_token_composition_sha256'):raise Refusal('composed replicas/token')
 for name in m['ports']['book']:
  if name in ('clk','rst_n'):continue
  p=context.get('ports',{}).get(name,{})
  if not p.get('source_owner') or not p.get('path_sha256'):raise Refusal('unbound port '+name)
  numeric=['slew_min_ps','slew_max_ps','arrival_min_ps','arrival_max_ps'] if m['ports']['book'][name]['direction']=='input' else ['load_fF']
  if any(type(p.get(k)) not in (int,float) or not math.isfinite(p[k]) for k in numeric):raise Refusal('finite port timing '+name)
  if m['ports']['book'][name]['direction']=='input':
   if not p.get('driver_cell') or not (p.get('slew_min_ps',0)>0 and p.get('slew_max_ps',0)>=p['slew_min_ps']):raise Refusal('input slew '+name)
   if 'arrival_min_ps' not in p or 'arrival_max_ps' not in p or p['arrival_max_ps']<p['arrival_min_ps']:raise Refusal('input arrival '+name)
  elif not p.get('load_fF',0)>0 or not p.get('capture_cell'):raise Refusal('output load '+name)
 if context.get('period_ps')!=2500/3 or context.get('setup_uncertainty_ps')!=60 or context.get('hold_uncertainty_ps')!=25:raise Refusal('clock/uncertainty')
 if not context.get('SS_FF_PDK_lock_sha256') or not context.get('CTS_reset_source_arcs') or not context.get('legal_signal_track_map'):raise Refusal('physical locks/routes')
 return dict(metadata_schema_valid=True,full_source=True,no_caps=True,actual_launch_requires_cold_context_artifact_review=True,compiler_launched=False,source_sha256=m['source_sha256'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',type=Path);p.add_argument('--context',type=Path);a=p.parse_args()
 d=admit(json.loads(a.context.read_text())) if a.context else model()
 if a.model:a.model.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
 else:print(json.dumps(d,sort_keys=True,indent=2))
