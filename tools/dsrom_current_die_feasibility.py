#!/usr/bin/env python3
"""Current S58/PAR2 hierarchical feasibility: source-identity cfg, PHW10, R49/c9, clock/reset.
Original diagnostic generator and live cases remain byte-identical. No engine RTL or flat synthesis.
"""
import argparse,gzip,hashlib,importlib.util,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_die_feasibility as D
from chip_assembly import floorplans
R49='results/uarch/dsrom_capture_home_r49_20261002/model.json'
C9='results/uarch/dsrom_c9_selected_clock_access_20261003/inputs/model.json'
CLOCK='results/uarch/dsrom_R49_raw_physical_union_20261002/shard0_clock_nets.jsonl.gz'
CFGLEF='physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef'
PHW=10; CTL=1+1+1+PHW+3; PERIOD=1000/1.2; UNC=60
ORIGINAL_GEOMETRY=D.geometry; ORIGINAL_GRAPH=D.build_grt

def load(p):
 b=(ROOT/p).read_bytes();return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
def box_inst(name,master,b,kind='svc'):
 x,y,X,Y=(v/1000 for v in b);return D.Inst(name,master,x,y,X-x,Y-y,kind)
def geometry(frame='D',shard=0):
 g=ORIGINAL_GEOMETRY(frame,True)
 r=load(R49);c=load(C9)
 g['blocks']=[i for i in g['blocks'] if i.name!='CAPTURE_HOME']
 raw=r['per_shard_raw_homes'][shard]
 g['blocks'] += [box_inst('CAPTURE_RAW','capture_raw',raw['bbox_DBU']),box_inst('CAPTURE_COMMON','capture_common',r['corrected_common_bbox_DBU']),box_inst('SELECTOR_CLOCK_BANK','selector_clock_bank',c['selected_selector_clock_construction']['named_bank_bbox_DBU'])]
 # Use v1 macro BODY. Origins are the source map; no v2 macro/frame adoption.
 for i,cfg in zip(g['cfgs'],load(f'{D.MAP}/cfg.json.gz')):
  match=re.fullmatch(r'candidate.shard0.cfg_pair(\d+).slice(\d+)',cfg['name'])
  if not match:raise ValueError('unknown cfg source identity')
  i.w,i.h=38.016,62.910;i.meta.update(pair=int(match[1]),slice=int(match[2]))
 # Blocks exclude the old containing CAPTURE_HOME; the R49 raw/common homes are disjoint.
 extra=g['blocks'][-3:]
 for a in extra:
  for b in g['elems']+g['cfgs']+g['blocks']:
   if a is not b and a.x<b.x+b.w and b.x<a.x+a.w and a.y<b.y+b.h and b.y<a.y+a.h:
    raise ValueError(f'current home overlap {a.name}/{b.name}')
 g['shard']=shard
 return g

def graph(g,ret='local'):
 insts,nets=ORIGINAL_GRAPH(g,ret)
 wm={n.id[:-4]:n.src[0] for n in nets if n.cls=='cfg_word_to_element'}
 nets=[n for n in nets if n.cls not in ('cfg_macro_to_wordmux','cfg_word_to_element')]
 for c in g['cfgs']:
  w=wm[f'e{c.meta["pair"]}'];sl=c.meta['slice']
  nets += [D.Net(c.name+'_d',72,(c.name,'rd_out'),[(w,f'd{sl}')],'cfg_macro_to_wordmux'),D.Net(c.name+'_a',13,(w,f'a{sl}'),[(c.name,'addr_in')],'cfg_macro_to_wordmux')]
 for e in g['elems']:
  nets.append(D.Net(e.name+'_cfg',54,(wm[e.name],'o'),[(e.name,'cfg')],'cfg_word_to_element'))
 for n in nets:
  if n.cls=='return_to_vm':n.dsts=[('CAPTURE_RAW',n.id[:-3])]
 nets += [D.Net('capture_read_request',187,('CAPTURE_COMMON','request'),[('CAPTURE_RAW','request')],'capture_request'),D.Net('capture_registered_reply',240,('CAPTURE_RAW','reply'),[('CAPTURE_COMMON','reply')],'capture_reply'),D.Net('capture_scalar_publish',63,('CAPTURE_COMMON','publish'),[('HUB_VM','rom_slot0_ingress')],'VM_publication')]
 # Explicit clock/reset fanout graph, including every cfg macro. Regional relays remain
 # inherited priced black boxes; this is clock TRUNK feasibility, not leaf CTS/skew proof.
 relay=[i for i in insts if i.kind=='relay']
 nets += [D.Net('clock_trunk',1,('CAPTURE_COMMON','clk_root_s0_clock_upper_L5_0'),[(i.name,'clk_in') for i in relay],'clock_trunk'),D.Net('reset_trunk',1,('CAPTURE_COMMON','reset_source'),[(i.name,'reset_in') for i in relay],'reset_trunk')]
 for r in relay:
  root=r.meta['root'];targets=[i for i in insts if (i.kind in ('q','bf') and i.meta['root']==root) or (i.kind=='cfg' and i.meta['pair']//32==root)]
  nets += [D.Net(f'clk_region{root}',1,(r.name,'clk_out'),[(i.name,'clk') for i in targets],'clock_region'),D.Net(f'rst_region{root}',1,(r.name,'reset_out'),[(i.name,'rst_n') for i in targets if i.kind!='cfg'],'reset_region')]
 other=[i for i in insts if i.kind not in ('q','bf','cfg','relay','phy') and i.name!='CAPTURE_COMMON']
 nets += [D.Net('clock_services',1,('CAPTURE_COMMON','clk_services'),[(i.name,'clk') for i in other],'clock_service'),D.Net('reset_services',1,('CAPTURE_COMMON','reset_services'),[(i.name,'rst_n') for i in other],'reset_service')]
 return insts,nets

def model(frame='D',shard=0):
 D.CTL=CTL
 g=geometry(frame,shard);insts,nets=graph(g)
 w=floorplans.wire_delay_model(); lookup={i.name:i for i in insts};edge_price={}
 for n in nets:
  src=lookup[n.src[0]]
  lengths=[abs(src.cx-lookup[i].cx)+abs(src.cy-lookup[i].cy) for i,_ in n.dsts]
  far=max(lengths,default=0)
  edge_price[n.id]={'bits':n.bits,'fanout':len(n.dsts),'rectangle_centre_L1_um':far,'wire_pipeline_lower_screen_cycles':max(1,math.ceil(far*w['ps_per_um']/(PERIOD-UNC-w['overhead_ps']))) if n.cls not in ('clock_trunk','clock_region','clock_service','reset_trunk','reset_region','reset_service') else None,'not_routed_pin_length':True,'class':n.cls}
 clocks=[(i,p) for n in nets if n.cls.startswith('clock') for i,p in n.dsts]
 if sum(i.startswith('cfg') for i,p in clocks)!=14336:raise ValueError('cfg clock census')
 inputs=[R49,C9,CLOCK,CFGLEF,f'{D.MAP}/field.json.gz',f'{D.MAP}/cfg.json.gz',f'{D.MAP}/services.json.gz',f'{D.MAP}/bands.json.gz','tools/dsrom_die_feasibility.py','tools/chip_assembly/floorplans.py']
 return {'candidate':'DS4096-TP4-S58-PAR2-NP2048','frame':frame,'shard':shard,'PHW':PHW,'control_bits':CTL,'instances':len(insts),'field_elements':2048,'compiled_weight_macros':8192,'cfg_macros':14336,'clock_cfg_endpoints':14336,'clock_element_endpoints':2048,'R49_raw':load(R49)['per_shard_raw_homes'][shard],'R49_common':load(R49)['corrected_common_bbox_DBU'],'selected_c9_bank':load(C9)['selected_selector_clock_construction'],'v1_cfg_abstract':CFGLEF,'cfg_grouping':'source cfg_pairN.sliceM, never geometric sort','cfg_ECC_required':False,'native_root_source':next(json.loads(x)['source'] for x in gzip.decompress((ROOT/CLOCK).read_bytes()).decode().splitlines() if json.loads(x)['name']=='s0_clock_upper_L5_0_Y'),'edges':edge_price,'wire_model':w,'stream_period_ps':PERIOD,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'clock_skew_or_slew_qualified':False,'full_die_admitted':False,'hierarchical_diagnostic_build_ready':True,'capture_credit_ACK_provider_unbound':True,'single_user_latency_admitted':False,'actual_full_token_added_cycles':None,'model_wire_costs_not_zero':True,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs}}

def prepare_grt(out,frame,shard):
 out.mkdir(parents=True,exist_ok=False)
 D.CTL=CTL
 D.geometry=lambda f,s:geometry(f,shard)
 D.build_grt=graph
 result=D.write_grt_case(out,frame,'local',16,2*8/90,.25,True)
 # The inherited renderer predates explicit element clock/reset ports. Add the
 # requested pins in two reserved bottom-edge bundled tracks outside the data span.
 text=(out/'blocks.lef').read_text();pk=.048*16
 for name,span in [(f'dsq_elem_{frame}_b',D.Q_PIN_SPAN[0]),('dsbf_elem_b',.05*D.BF_FRAME[0])]:
  start=text.index('MACRO '+name+'\n');end=text.index('END '+name+'\n',start)
  chunk=text[start:end];pins=''
  for j,pin in enumerate(('clk','rst_n')):
   x=(math.floor(span/pk)-4+j+.25)*pk
   pins+=f'  PIN {pin}[0]\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n'+D.rect(x-pk/4,0,x+pk/4,pk)+f'\n    END\n  END {pin}[0]\n'
  chunk=chunk.replace('  OBS\n',pins+'  OBS\n');text=text[:start]+chunk+text[end:]
 (out/'blocks.lef').write_text(text)
 result.update(PHW=10,control_bits=CTL,R49_c9_bound=True,clock_and_reset_explicit=True,model_only=False)
 (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
 # Initial floorplan limits: source instance census and native pins are checked separately.
 (out/'model.json').write_text(json.dumps(model(frame,shard),indent=2,sort_keys=True)+'\n')
 return result

# Native pin-access: actual ASAP7 tech and v1 cfg LEF, source-site residues preserved.
# One interface master at a time prevents a full-die native GCell allocation; same source
# master/position phase census covers all instances. Per-instance obstacle context is separate.
def prepare_pin(out,frame,shard):
 out.mkdir(parents=True,exist_ok=False);D.CTL=CTL
 g=geometry(frame,shard)
 for kind in ('q','bf'):
  i=next(e for e in g['elems'] if e.kind==kind)
  (out/f'{kind}.lef').write_text(D.element_real_lef('ds_'+kind,kind,i.w,i.h))
 (out/'cfg.lef').write_bytes((ROOT/CFGLEF).read_bytes())
 import check_macro_track_alignment as track
 masters={}
 for kind in ('q','bf','cfg'):
  mm=track.parse_lef((out/f'{kind}.lef').read_text())
  if len(mm)!=1:raise ValueError('missing/duplicate requested native master')
  masters[kind]=mm[0]
 gate=[]
 for inst in g['elems']+g['cfgs']:
  kind=inst.kind
  checked=track.check_placement(masters[kind],'R0',round(inst.x*1000),round(inst.y*1000))
  bad=sum(layer['offtrack'] for layer in checked['layers'].values())
  if bad:raise ValueError(f'native instance offtrack {inst.name}: {bad}')
  gate.append({'instance':inst.name,'master':masters[kind]['name'],'origin_nm':[round(inst.x*1000),round(inst.y*1000)],'offtrack':bad})
 (out/'macro_track_gate.json').write_text(json.dumps({'requested_masters':[m['name'] for m in masters.values()],'actual_instance_census':len(gate),'instances':gate,'verdict':'PASS','hook':'ot_mts phase-equivalent R0 joint432nm source origins; no reframe'},sort_keys=True)+'\n')
 cases=[]
 for name,w,h in [('q',D.FRAMES[frame][0],D.FRAMES[frame][1]),('bf',*D.BF_FRAME),('cfg',38.016,62.910)]:
  master='ot_rom_4096x72_m8' if name=='cfg' else 'ds_'+name
  header=f'read_lef {D.PLAT}/lef/asap7_tech_1x_201209.lef\nread_lef {D.PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef\nread_lef /work/{name}.lef\n'
  # A local DEF preserves native origin track phases and names every signal net.
  lef=(out/f'{name}.lef').read_text();pins=re.findall(r'^  PIN (\S+)',lef,re.M)
  signal=[p for p in pins if p not in ('VDD','VSS')]
  definition=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;',f'DESIGN pin_{name} ;','UNITS DISTANCE MICRONS 1000 ;',f'DIEAREA ( 0 0 ) ( {round((w+8.64)*1000)} {round((h+8.64)*1000)} ) ;','COMPONENTS 1 ;',f'- one {master} + FIXED ( 4320 4320 ) N ;','END COMPONENTS',f'NETS {len(signal)} ;']+[f'- n{k} ( one {p} ) ;' for k,p in enumerate(signal)]+['END NETS','END DESIGN']
  (out/f'{name}.def').write_text('\n'.join(definition)+'\n')
  (out/f'{name}.tcl').write_text(header+f'read_def /work/{name}.def\nsource {D.PLAT}/openRoad/make_tracks.tcl\nset_routing_layers -signal M1-M9\npin_access -verbose 1\nwrite_db /work/{name}_pin.odb\nputs "CURRENT_NATIVE_PIN_ACCESS_DONE {name} {len(signal)}"\nexit\n')
  cases.append({'kind':name,'master':master,'signal_pins':len(signal),'abstract_scope':'actual v1 macro' if name=='cfg' else 'source-port model interface, not hardened element abstract'})
 (out/'manifest.json').write_text(json.dumps({'cases':cases,'all_instances':len(g['elems'])+len(g['cfgs']),'full_die_context_pin_access_qualified':False,'selected_clock_leaves_not_replaced':True},indent=2)+'\n')
 return cases

# Full 204 W CURRENT-MAP IR job: actual native metal rules, source-shaped load tiles.
# It does not invent measured activity: area-proportional allocation is explicit and conserved.
def prepare_pdn(out,frame,shard):
 import w18.die_pdn as P
 out.mkdir(parents=True,exist_ok=False)
 g=geometry(frame,shard);blocks=g['elems']+g['cfgs']+g['blocks']
 # Containing return/cfg bands and enclosed macro bodies are not both current loads.
 # Only the source instance union has current; complement/overlap remains geometry diagnostics.
 total=sum(i.w*i.h for i in blocks)
 comps=[];power={};lefs={};sources=[]
 for block in blocks:
  tiles=P.tiles(block.x,block.y,block.w,block.h,500 if block.kind not in ('q','bf') else 130)
  watts=204*block.w*block.h/total
  for k,(x,y,w,h) in enumerate(tiles):
   nm=f'{block.name}_t{k}';master=f'load_{round(w*1000)}_{round(h*1000)}'
   if master not in lefs:lefs[master]=P.load_lef(master,w,h,'current source-shaped load tile; explicitly area-proportional204W allocation')
   comps.append((nm,master,x,y,'R0'));power[nm]=watts/len(tiles)
 for n,s in lefs.items():(out/(n+'.lef')).write_text(s)
 (out/'top.def').write_text(P.def_file('dsrom_current_pdn',33000,26000,comps))
 (out/'power_map.json').write_text(json.dumps(power,sort_keys=True)+'\n')
 t=f'''read_lef {D.PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {D.PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
'''+''.join(f'read_lef /work/{n}.lef\n' for n in lefs)+'''read_def /work/top.def
initialize_floorplan -die_area {0 0 33000 26000} -core_area {0 0 33000 26000} -site asap7sc7p5t
source '''+D.PLAT+'''/openRoad/make_tracks.tcl
set block [ord::get_db_block]
foreach r [$block getRows] {odb::dbRow_destroy $r}
add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name die -voltage_domains CORE -pins M9
add_pdn_stripe -grid die -layer M8 -width 2 -spacing 9.28 -pitch 22.56 -offset 2
add_pdn_stripe -grid die -layer M9 -width 2 -spacing 9.28 -pitch 22.56 -offset 2
add_pdn_connect -grid die -layers {M8 M9}
pdngen
read_liberty '''+D.PLAT+'''/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source '''+D.PLAT+'''/setRC.tcl
set_pdnsim_source_settings -bump_dx 90 -bump_dy 90 -bump_size 10
'''+''.join(f'set_pdnsim_inst_power -inst {n} -power {p:.12f}\n' for n,p in power.items())+'''set_pdnsim_net_voltage -net VDD -voltage 0.7
set_pdnsim_net_voltage -net VSS -voltage 0
analyze_power_grid -net VDD -source_type BUMPS -voltage_file /work/VDD.rpt
analyze_power_grid -net VSS -source_type BUMPS -voltage_file /work/VSS.rpt
write_db /work/pdn.odb
puts "CURRENT_PDN204_DONE"
exit
'''
 (out/'run.tcl').write_text(t)
 m={'total_W':sum(power.values()),'loads':len(comps),'masters':len(lefs),'current_A':204/.7,'allocation':'area-proportional source-shape capacity screen; not measured switching map','M8_M9_each_PG_fraction':16/90,'actual_mesh_fraction':4/22.56,'mesh_width_um':2,'mesh_pitch_um':22.56,'native_max_width_um':2,'original_reserved_metal_fraction_not_reduced':True,'bumps_pitch_um':90,'load_pin_to_internal_M7_upfeed_qualified':False,'global_source_mesh_case':True,'full_die_PG_admitted':False,'actual_macro_local_grid_not_replaced':True}
 if abs(m['total_W']-204)>1e-7:raise ValueError('power conservation')
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m

def main():
 a=argparse.ArgumentParser();a.add_argument('--job',choices=['model','grt','pin','pdn'],required=True);a.add_argument('--frame',choices=['C','D'],default='D');a.add_argument('--shard',type=int,choices=[0,1],default=0);a.add_argument('--out',type=Path,required=True);v=a.parse_args()
 if v.job=='model':
  v.out.parent.mkdir(parents=True,exist_ok=True);v.out.write_text(json.dumps(model(v.frame,v.shard),indent=2,sort_keys=True)+'\n')
 else:print(json.dumps({'grt':prepare_grt,'pin':prepare_pin,'pdn':prepare_pdn}[v.job](v.out,v.frame,v.shard))[:1500])
if __name__=='__main__':main()
