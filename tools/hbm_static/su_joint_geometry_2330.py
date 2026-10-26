#!/usr/bin/env python3
"""Two source-bound whole-SU structural alternatives; deliberately unqualified planning.

No RTL master/view/contract is changed. Macro rectangles are actual LEF dimensions,
with local placement pitches from the measured six-SRAM gate. Soft-cell regions
are capacity envelopes, not fabricated physical views or mapped placements.
"""
import collections,hashlib,json,math,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import layout_png as LP
OUT=ROOT/'results/arch/hbm_su_f2_static_1014/joint_geometry_2330'
OUT.mkdir(parents=True,exist_ok=True)
SOURCES={}
def blob(ref,path):
 b=subprocess.check_output(['git','-C',str(ROOT),'show',f'{ref}:{path}']);SOURCES[f'{ref}:{path}']=hashlib.sha256(b).hexdigest();return b
area=json.loads(blob('d47fc58f7','results/arch/hbm_su_f2_static_1014/fit_map_2330/receipt.json'))['classes']
bank=json.loads(blob('d47fc58f7','results/arch/hbm_su_f2_static_1014/arithmetic/physical/bank_clock7/r10c_diagnostic/postroute_area.json'))
gate=json.loads(blob('82e10fb16','physical/ref_tile/hbm_su_static_kind0_l4_leaf1_1015/gate_result.json'))
# Actual gate synthesis area, not the older unregistered-lane map.
light=9502.0
assert any('9502' in str(i) and 'synthesized std area' in str(i) for i in gate['items'])
lef=blob('f86d487d1','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef').decode()
MW,MH=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups())
for p in ['rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pgslice.sv','rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_quarter.sv','rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore.sv']:
 blob('f86d487d1',p)
W,H=1250.,1780.;FTX=(605.,645.);FTY=(870.,910.)
quad_area=605*870;macro_area=48*MW*MH
# Reserve the entire macro-grid channels for routing first; allow only 35% of
# their area for logic as a stated sensitivity, not a physical qualification.
GRID_W=3*114.912+MW;GRID_H=11*62.64+MH
channel_area=GRID_W*GRID_H-macro_area
peripheral_area=quad_area-GRID_W*GRID_H
capacity=.60*peripheral_area+.35*channel_area
r={'schema':'opentallas.hbm.su.joint_geometry.v1','qualified':False,'complete_production_mapping':False,
 'source_binding':SOURCES,'macro':{'master':'ot_sram_1r1w_128x256_m1_r2c2','width_um':MW,'height_um':MH},
 'fixed_inventory':{'PG':16,'store_banks':512,'store_SRAM':3072,'LIGHT':384,'SFU':127,'FULL':1,'SIDE':1,'RF_banks':256,'reducers':4,'broadcast_declared_bits':891904,'broadcast_mapped_FF':'OPEN; identical replicas may merge'},
 'measured_std_um2':{'LIGHT_pinreg':light,'SFU':area['SFU']['area_um2'],'FULL':area['FULL']['area_um2'],'SIDE':area['SIDE']['area_um2'],'RF_bank':area['RF']['area_um2'],'bank_posthold_DRC2_diagnostic':bank['standard_area_um2']},
 'packing_budget':{'PG_outline_um':[W,H],'mandatory_feedthroughs_um':{'x':FTX,'y':FTY},'quad_um':[605,870],'SRAM_per_quad':48,'bank_macro_shape':'eight six-reader banks; each bank2cols x3rows; overall4cols x12rows','macro_pitch_um':[114.912,62.64],'intermacro_gap_um':[114.912-MW,62.64-MH],'macro_grid_um':[GRID_W,GRID_H],'soft_capacity_sensitivity_um2':capacity,'peripheral_logic_util':.60,'macro_channel_logic_util':.35,'arithmetic_CTS_hold_reserve_fraction':.30,'reserves_are_measured':False},
 'clock_obligations':{'bank_per_bank':'three related W/E/interior register roots plus six raw SRAM entries; actual source ABI must be forwarded through PG','LIGHT':'source-current gate largestroot4263','SFU':'10 mapped usedroots, largest10727','FULL':'12 mapped usedroots, largest10727','SIDE':'6 mapped usedroots, largest9997','RF_bank':'one577sinkroot','broadcast':'declared13936FF/root before merging; source-current wholePG CTS required','die_delivery':'actual phi-R per child/root; serial900/stream1200 related3:4; epoch/reset phase must match native fixed-cycle programme'},
 'alternatives':[]}
for mode in ['A_preserve_mapping','B_balance_mapping']:
 quads=[];blocks=[];banks=[]
 for q in range(4):
  ox=0 if q%2==0 else 645.;oy=0 if q<2 else 910.
  xbase=math.ceil((ox+20)/.432)*.432;ybase=math.ceil((oy+20)/2.16)*2.16
  qkinds=[]
  for k in range(8):
   n=q*8+k
   lid=(n if n<16 else 64+n-16) if mode.startswith('A') else(2*q+k if k<2 else 32+6*q+k-2)
   kind='FULL' if lid==0 else('SFU' if lid<32 else'LIGHT')
   qkinds.append(kind);rects=[]
   for rd in range(6):
    col=2*(k%2)+(rd%2);row=3*(k//2)+rd//2
    x=round(xbase+col*114.912,6);y=round(ybase+row*62.64,6)
    assert x>=ox+20-1e-6 and x+MW<=ox+605 and y>=oy+20-1e-6 and y+MH<=oy+870
    assert abs(x/.432-round(x/.432))<1e-6 and abs(y/2.16-round(y/2.16))<1e-6
    b=[f'b{n}r{rd}',x,y,x+MW,y+MH];blocks.append(b);rects.append(b[1:])
   banks.append({'physical_bank':n,'logical_lane_Q0G0':lid,'kind_Q0G0':kind,'SRAMs':rects,'raw_bank_boundary_bits':{'input_data':102,'output_data':198,'clock_entries_proposed':9}})
  cnt=collections.Counter(qkinds)
  logic=sum(light if k=='LIGHT' else area[k]['area_um2'] for k in qkinds)
  req=logic*1.30+8*bank['standard_area_um2']+891904*.30/16/4
  quads.append({'quad':q,'counts_Q0G0':dict(cnt),'arithmetic_raw_std_um2':logic,'estimated_std_with_30pct_arith_reserve_actualbank_and_declaredBCASTupper_um2':req,'soft_capacity_sensitivity_um2':capacity,'margin_before_unpriced_VM_control_um2':capacity-req,'controller_bridge_area_known':False})
 # Exact geometry assertions before any drawing.
 for i,a in enumerate(blocks):
  for b in blocks[i+1:]:assert min(a[3],b[3])<=max(a[1],b[1])+1e-6 or min(a[4],b[4])<=max(a[2],b[2])+1e-6
 alt={'name':mode,'status':'UNQUALIFIED_PLANNING','PG_example':'Q0G0; allotherPGcounts in mapping table below','macro_rectangles':blocks,'banks':banks,'quadrants':quads,
      'geometric_macro_checks':{'storeSRAMs':len(blocks),'overlap':0,'outside':0,'FTintersection':0,'internal_local_macro_grid':True,'global_die_track_origin':'OPEN'},
      'logic_cells_placed':False,'actual_pin_assignment':'OPEN; currentPGslot baselines are not new grants','cut_utilization':'OPEN; require actualallincident buses and GRT, not scalar area','native_phase_setup_hold_DRC':'OPEN','normal_cycles_added':'OPEN; no zero-cycle or end-to-end performance claim',
      'boundary_plan':'LG registers/3:4 bridges at real VM-facing windows; control/RF capture at E pin then local broadcast. Any new capture/output/relay edges must be compiled. Wires-only parent forwards every real child clock entry.',
      'mapping_change':('Keep logicalLID and VMstore-group assignment; moving heavy arithmetic out of overloadedquadrants requires fixed request/data relays and added latency.' if mode.startswith('A') else 'Preserve all logical IDs and operation counts, repartition eachPG into8heavy+24LIGHT. RTL lid()/store-fill/drain group decoding/red_sel ownership AND compiler VMaddress/home maps/producers must change atomically; no runtime routing/credits.'),
      'needed_proof':['all512 native lockstep and six mutants on exact compiled timeline','allcanonical required operations instantiated (17 gaps remain explicit until fixed)','actual native pin routes and fullconnectedPG cut/GRT/CTS','parentserial/stream3:4 phase and every fixedboundary/relay cycle']}
 if mode.startswith('B'):
  mapping={}
  for g in range(4):
   ids=[g*8+2*(n//8)+n%8 if n%8<2 else 32+g*24+6*(n//8)+n%8-2 for n in range(32)]
   mapping[str(g)]=ids
  assert sorted(sum(mapping.values(),[]))==list(range(128))
  alt['quarter_logical_lane_permutation']=mapping;alt['recommendation']='Preferred structural prototype: balances the measured heavy area while retainingVM-facing locality; not an adopted source or physical view.'
 else:alt['recommendation']='Comparison only: measured heavyquadrants exceed this explicitsoftcapacity budget; added relays/rehome or largerconnected regions required.'
 r['alternatives'].append(alt)
 # Raster is source-driven geometry, not an AI illustration.
 v=LP.View([0,0,W,H],max_px=1400,top=116);c=LP.Canvas(v.cw,v.ch)
 c.text(8,6,mode+' ACTUAL MACROS / UNQUALIFIED SOFT PLAN',scale=2)
 c.text(8,29,'192 SRAMs:94.824x41.040; exact20.088/21.6 gaps. Grey = real macro, white = OPEN logic.')
 c.text(8,43,'Orange = mandatory40um relay cross. No cell placement, pins, clock route or native closure claimed.')
 c.text(8,57,'Budget:60% peripheral+35% macro-channel logic; arithmetic30% CTS/hold sensitivity, NOT measured.')
 for qq in quads:
  q=qq['quad'];ox=0 if q%2==0 else 645.;oy=0 if q<2 else 910.
  col=(210,235,215) if qq['margin_before_unpriced_VM_control_um2']>=0 else(250,220,215)
  c.fill(*v.rect([ox,oy,ox+605,oy+870]),col)
 for rr in [[605,0,645,H],[0,870,W,910]]:c.fill(*v.rect(rr),(250,180,80))
 for b in blocks:
  rr=v.rect(b[1:]);c.fill(*rr,(145,150,165));c.box(*rr,(35,35,50),1);c.text(rr[0]+2,rr[1]+2,b[0])
 c.box(*v.rect([0,0,W,H]),(0,0,0),2)
 for qq in quads:
  q=qq['quad'];ox=0 if q%2==0 else 645.;oy=0 if q<2 else 910.
  x=v.x(ox+10);y=v.y(oy+835)
  c.text(x,y,'Q'+str(q)+' '+str(qq['counts_Q0G0']),scale=1)
  c.text(x,y+12,'Rawstd %.0fum2; budget margin%+.0f'%(qq['arithmetic_raw_std_um2'],qq['margin_before_unpriced_VM_control_um2']))
 c.save(OUT/(mode+'.png'))
(OUT/'alternatives.json').write_text(json.dumps(r,indent=1)+'\n')
print(json.dumps({'capacity_per_quad':capacity,'alternative_margins':{a['name']:[round(q['margin_before_unpriced_VM_control_um2']) for q in a['quadrants']] for a in r['alternatives']}},indent=1))
