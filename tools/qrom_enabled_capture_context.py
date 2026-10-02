#!/usr/bin/env python3
"""Current QROM enabled cones and actual LEF collars; no synthesis or routing.
A macro-collar construction is not a full tile or parent fit certificate.
"""
import gzip,hashlib,importlib.util,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/qrom_enabled_capture_context_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snap(v):return math.ceil(v/2160)*2160
def build():
 receipt=json.loads((BASE/'input_receipt.json').read_text())
 for n,p in receipt['inputs'].items():assert sha(BASE/'inputs'/n)==p['sha256']
 src=(BASE/'inputs/tile.sv').read_text();screen=json.loads((BASE/'inputs/screen.json').read_text());review=json.loads((BASE/'inputs/review.json').read_text())
 assert sha(BASE/'inputs/tile.sv')==screen['source_sha256']['rtl/hdc/ot_qwen_rom_tile_w12.sv']
 assert review['slacks_identical'] and review['source_pins_identical']
 for fragment in ['always @(posedge clk) if (code_sel_q[b] && code_rd_q) cap <= rd;','always @(posedge clk) if (kv_rd_q) cap <= kvs_rd;','assign rom_addr = wrom_addr[11:0];','.KV_NH(KV_NH)', '.KV_VB(KV_VB)']:assert fragment in src,fragment
 assert 'dffunmap' in (BASE/'inputs/mapper.py').read_text()
 s=importlib.util.spec_from_file_location('lef_helpers',BASE/'inputs/LEF_parser.py');helper=importlib.util.module_from_spec(s);s.loader.exec_module(helper);helper.BASE=BASE
 templates={n:helper.lef(n+'.lef') for n in ['ROM','SRAM']};halo=4320;placements=[];xslots=[];y=0
 rw,rh=templates['ROM']['size_DBU'];kw,kh=templates['SRAM']['size_DBU'];pw=snap(max(rw,kw)+2*halo);rom_h=snap(rh+2*halo);kv_h=snap(kh+2*halo)
 for bank in range(5):
  for pair in range(2):
   x=pair*pw+halo;z=bank*rom_h+halo;placements.append(dict(instance=f'g_col[{pair}].g_bank[{bank}].u_rom',master='ROM',origin_DBU=[x,z],body_DBU=[x,z,x+rw,z+rh],slot_DBU=[pair*pw,bank*rom_h,(pair+1)*pw,(bank+1)*rom_h],orientation='R0',capture_hierarchy=f'u_logic.g_pair[{pair}].g_bank[{bank}].g_cap.cap[255:0]',capture_bits=256,enabled_capture_source_line=next(i for i,l in enumerate(src.splitlines(),1) if 'if (code_sel_q[b] && code_rd_q) cap <= rd' in l)))
 for pair in range(2):
  x=pair*pw+halo;z=5*rom_h+halo;placements.append(dict(instance=f'g_kv[{pair}].u_kv',master='SRAM',origin_DBU=[x,z],body_DBU=[x,z,x+kw,z+kh],slot_DBU=[pair*pw,5*rom_h,(pair+1)*pw,5*rom_h+kv_h],orientation='R0',capture_bits=256,capture_hierarchy='u_logic.g_kv_local.g_kvcap.cap'))
 helper.disjoint([(p['instance'],p['slot_DBU']) for p in placements])
 shapes=[]
 for p in placements:
  t=templates[p['master']]
  for kind in ['pins','OBS']:
   for a in t[kind]:shapes.append(dict(a,instance=p['instance'],kind=kind,bbox_DBU=helper.translate(a['bbox_DBU'],*p['origin_DBU'],t['size_DBU'],'R0')))
 ss=gzip.decompress((BASE/'inputs/seq_ss.lib.gz').read_bytes()).decode();cell=ss[ss.index('cell (DFFHQNx1_ASAP7_75t_R)'):];area=float(re.search(r'area\s*:\s*([\d.]+)',cell).group(1));rom=next(r for r in screen['rows'] if r['macro']=='ot_rom_4096x266_m8' and r['corner']=='ss' and not r['negative_control'])
 cone=dict(source_sha256=sha(BASE/'inputs/tile.sv'),ROM=dict(capture_bits=2560,feedback_mux_bit_equations=2560,next_value='cap_next = (code_sel_q[b] && code_rd_q) ? rd : cap',bank_enable_count=5,bank_enable_capture_loads=512,code_rd_capture_loads=2560,source_control='code_sel_q <= rom_ce only on wrom_re; code_rd_q <= wrom_re; code_sel_q2 <= code_sel_q only on old code_rd_q',source_accepted_read_to_capture_cycles=1,capture_to_bank_select='2560 bank mask ANDs and2048 nontrivial OR bits; actual mapper balancing not assumed',capture_strobe_and_select_arrival_cone_required=True),KV=dict(capture_bits=512,feedback_mux_bit_equations=512,enable_capture_loads=512,next_value='cap_next = kv_rd_q ? kvs_rd : cap',source_read_to_capture_cycles=1),capture_FF3072_area_lower_bound_um2=3072*area,area_scope='RVT capture flop area only; feedback/control buffers, bank mask/OR, arithmetic, other registers, CTS/PG and routing extra.',added_MEM_EXTRA_cycle=1,existing_engine_parameter_already_prices_MEM_EXTRA=True,new_extra_cycles_not_assumed_free=True)
 result=dict(schema='opentallas.qrom.enabled-capture-context.v1',source_main_pin=receipt['current_main_pin'],source_receipt_sha256=sha(BASE/'input_receipt.json'),generator_sha256=sha(Path(__file__)),target_configuration=review['current_target_configuration'],unreviewed7294_uarch_model_not_consumed=True,source_tile_hash_matches_ideal_screen=True,enabled_cones=cone,
  macro_context=dict(ROM_instances=10,KV_SRAM_instances=2,DBU_per_um=1000,construction_collar_DBU=halo,collar_basis='Explicit proposed4.32um clear collar; neither source-owned hardened slot nor proven pin escape/PG minimum.',macro_collar_envelope_DBU=[2*pw,5*rom_h+kv_h],macro_body_sum_mm2=(10*rw*rh+2*kw*kh)/1e12,macro_collar_sum_mm2=2*pw*(5*rom_h+kv_h)/1e12,pin_shapes=sum(r['kind']=='pins' for r in shapes),PG_pin_shapes=sum(r['kind']=='pins' and r.get('use') in ['POWER','GROUND'] for r in shapes),OBS_shapes=sum(r['kind']=='OBS' for r in shapes),full_tile_logic_not_contained=True,actual_full_tile_outline_provider_missing=True,actual_PG_stripe_via_connections_missing=True,clock_skew_and_enabled_cell_mapping_missing=True,source_native_metal_pin_OBS_artifact='translated_pin_OBS.json.gz'),
  timing_budget=dict(SS_setup_budget_after_direct_capture_ps=rom['slack_ps'],SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,period_ps=screen['period_ps'],direct_capture_added_load_fF=rom['added_load_fF'],direct_capture_clock_slew_ps=rom['clock_transition_ps'],physical_enabled_cone_budget='mapped feedback/data select incremental delay + extra wire/load effect + adverse relative clock insertion must <=7.895628ps against the pinned direct screen, or re-evaluate actual full path including changed capture cell/setup/load. No subtracting uncertainty.',negative_screen_retained_ps=next(r['slack_ps'] for r in screen['rows'] if r['negative_control']),no_enabled_or_wire_or_skew_pass_inferred=True),
  numeric_rejection_criteria=[{'quantity':'SS full enabled capture setup WNS ps','reject_if':'<0 under833.333333ps period and60ps uncertainty; use actual macro SS arc, mux/control arrival, load, wire and clock insertion.'},{'quantity':'FF hold WNS ps','reject_if':'<0 under25ps uncertainty including feedback/control min paths and actual CTS skew.'},{'quantity':'macro pin access and PG connectivity','reject_if':'Any signal pin lost or unconnected VDD/VSS shape; OBS/halo intersection or unbound layer-resolved vias/escape.'},{'quantity':'full tile occupancy','reject_if':'Full arithmetic/control/capture/CTS/PG cannot be assigned disjoint legal instances inside source-owned tile outline; macro-collar envelope alone gives no pass.'},{'quantity':'bounded context launch','reject_if':'Current source params/unchanged rounding tree, model latency, exact full-scope source manifest, measured CPU/RAM/disk reservation or Euclid/parent intake absent.'}],
  next_bounded_context=dict(kind='Enabled macro capture source slice + source bank control, independently reviewed mapped SS/FF cone before full tile P&R.',source_excerpt_only='No new engine RTL created. Exact lines/expressions and instance cones in this record.',required_review='Euclid capture-cone and physical owner source/slot review; Maxwell current model re-pin separate.',model_latency_price='Existing MEM_EXTRA1 capture retained; any added pipeline stage requires composed token/calendar price.',fleet='Local or coordinatedPVE1/128VM only; no PVE2/PVE3 admission.'),scope='Geometry/source review only; macro ideal screen retained, no current fulltile or parent closure.',new_builds=0)
 return result,placements,shapes,templates

def main():
 result,placements,shapes,templates=build()
 for n,obj in [('model.json',result),('macro_collar_placement.json',placements),('translated_pin_OBS.json.gz',shapes),('macro_templates.json',templates)]:
  b=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();b=gzip.compress(b,mtime=0) if n.endswith('.gz') else b;p=BASE/n
  if p.exists() and p.read_bytes()!=b:raise ValueError('immutable record changed '+n)
  p.write_bytes(b)
 print(json.dumps({'SS_direct_budget_ps':result['timing_budget']['SS_setup_budget_after_direct_capture_ps'],'macro_context':result['macro_context'],'new_builds':0}))
if __name__=='__main__':main()
