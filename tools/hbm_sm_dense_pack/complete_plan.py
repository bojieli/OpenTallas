#!/usr/bin/env python3
"""Construct full16 tile +35 SM geometry; separate geometric and timing evidence."""
import pathlib,json,hashlib,copy,math
ROOT=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');OUT=pathlib.Path('results/hbm_sm_dense_pack')
prior=json.load(open(OUT/'plan.json')); blocks=[]
for lf,x in enumerate([10,356.72]):
 for kind,name,dx,y in [('xs','xs',0,160),('bdc','bdc',0,337.68),('tct','tct',132.32,337.68),('tcl','tcl0',132.32,428.96),('tcl','tcl1',238.72,428.96)]:
  m=prior['source_models'][kind];blocks.append(dict(name=f'{lf}_{name}',kind=kind,x=x+dx,y=y,w=m['w'],h=m['h'],orient='R0',status='ACTUAL_COMPUTE_LEF'))
for n,k,x,y,w,h in [('0_rowW','row_w',10,19,86.4,121),('beatW','beat_w',116.4,10,361,130),('1_rowW','row_w',497.4,19,86.4,121),('beatE','beat_e',603.8,19,77.76,121),('0_rowE','row_e',70,569.92,400,20),('1_rowE','row_e',530,569.92,140,30)]:
 path=ROOT/f'physical/ref_tile/smh_tr_group_{k}_ref/floorplan.json';d=json.load(open(path));oldw,oldh=d['die'][2:];m=4.32
 assert (w-m)*(h-m)>=(oldw-m)*(oldh-m)-1e-6
 blocks.append(dict(name=n,kind=k,x=x,y=y,w=w,h=h,orient='R0',status='NEW_HARDENING_REQUIRED',source=str(path.relative_to(ROOT)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),old_outline=[oldw,oldh],old_core_area=(oldw-m)*(oldh-m),new_core_area=(w-m)*(h-m)))
W,H=693.44,609.92
pairs=[]
for i,b in enumerate(blocks):
 assert b['x']>=0 and b['y']>=0 and b['x']+b['w']<=W+1e-6 and b['y']+b['h']<=H+1e-6
 for c in blocks[:i]:
  g=max(c['x']-b['x']-b['w'],b['x']-c['x']-c['w'],c['y']-b['y']-b['h'],b['y']-c['y']-c['h'])
  assert g>=20-1e-6,(b['name'],c['name'],g)
  pairs.append(g)
# ActualLEF target rl1/bk1 positions; plannedgroupPORTs are explicitly new contracts.
xs=prior['source_models']['xs']['pins'];landing=[];rowpairs=[]
for lf,srcx,destx in [(0,96.4,70),(1,583.8,544.528)]:
 source=[]
 for layer,pitch in [('M4',.096),('M6',.128)]:
  source += [(95.04+pitch*i,layer) for i in range(int((140-95.04)/pitch)+1)]
 source=sorted(source)[:818]
 target=sorted([(destx+.096*i,i) for i in range(818)],key=lambda v:abs(v[0]-srcx))
 rows=[dict(bit=bit,from_xy=[srcx,y],from_layer=layer,to_xy=[x,569.92],to_layer='M5',manhattan=569.92-y+abs(x-srcx)) for (y,layer),(x,bit) in zip(source,target)]
 assert max(r['manhattan']for r in rows)<=500
 rowpairs+= [dict(row=lf,kind='rowW.last_to_rowE.d',pairs=rows,max_um=max(r['manhattan']for r in rows))]
 # Full sourceLEF rl1 pins are818. Width86.4 firstN M5 supports900 two-track slots.
 xbase=[10,356.72][lf];firstbase=[10,497.4][lf]
 p=[(n,v)for n,v in xs.items()if n.startswith('rl1[')]
 reach=max(20+abs(xbase+v['x']-min(max(xbase+v['x'],firstbase),firstbase+86.4)) for n,v in p)
 landing.append(dict(row=lf,bits=len(p),kind='rowW.first_to_xs.rl1',geometric_projection_max_um=reach))
tile={'verdict':'ALL16_CHILD_OUTLINES_AND_20UM_CLEARANCES_PASS_NEW_TRANSPORT_HARDENING_REQUIRED','width_um':W,'height_um':H,'area_um2':W*H,'minimum_macro_gap_um':min(pairs),'children':blocks,'logical_transport_slices':96,'row_bits':1636,'beat_bits':2069,'transit_cycles':4,'landing_cycles':1,'new_group_roots':6,'clock_masking':False,'sourceLEF':{'prior_compute_pin_manifest':'plan.json','sha256':hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest()},'row_pin_pairing':rowpairs,'landing':landing,'cut':{'ew_demand':3705,'M8_gross_tracks':H/.08,'M8_at60percent':H/.08*.6,'M6_capacity_counted':0,'M8_free_basis':'Actual compute LEFs zeroM8OBS; transport newhardening maxM5 withM6PGstraps, noM8OBS contract.','boundary_two_pitch_M8_slots':int(H/.16),'boundary_additional_M6_slots_needed':3705-int(H/.16)},'limits':['Re-cutgroup dimensions preserve actual oldgroup core area, not just outline sum. New q1keep synthesis/CTS may require morearea.','Proposed rowWlast E/M4M6 and rowEinput S/M5 pin pairing is a NEW PORT contract, not measured macro pins.','RowE0 outputN x391.5..469.932, rowE1outputN x591.5..669.932, M5 viaM7escape; all3705Eboundary slots explicitly allocated onM8 0.16pitch.','Everyhardgroup first/last flop placement must honor these PORTcontracts; actualQ/D timing andinternalreach remainunmeasured.','Actualsource xs operand pinfaces remain inplan.json. ExistingXB/XF relayregisters must be legallyplaced andchecked againstthis newgeometry.','M8PG/clock/blockage reservations andfullcut topology stillrequire measurement.','Realclockroots andTTsetup FFhold DRC0 unqualified.']}
# Existing XREL operand registers, one station within each20um compute gap.
operand=[]
for lf,xbase in [(0,10),(1,356.72)]:
 for bus in ['w','x']:
  for bit in range(788):
   sp=xs[f'o_i{bus}[{bit}]'];sx=xbase+sp['x'];sy=160+sp['y']
   if bit<532:
    dp=prior['source_models']['bdc']['pins'][f'i_{bus}[{bit}]'];tx=xbase+dp['x'];ty=337.68+dp['y'];kind='xb'
   else:
    h=(bit-532)//128;b=(bit-532)%128
    dp=prior['source_models']['tcl']['pins'][f'i_{bus}[{b}]'];tx=xbase+[132.32,238.72][h]+dp['x'];ty=428.96+dp['y'];kind='xf'
   rx=(sx+tx)/2;ry=327.68
   first=abs(rx-sx)+abs(ry-sy);second=abs(tx-rx)+abs(ty-ry)
   assert max(first,second)<500
   operand.append(dict(row=lf,bus=bus,bit=bit,kind=kind,source=[sx,sy],existing_relay=[rx,ry],destination=[tx,ty],first_um=first,second_um=second))
tile['source_based_operand_relay_pairs']=operand
tile['max_operand_first_um']=max(r['first_um']for r in operand);tile['max_operand_second_um']=max(r['second_um']for r in operand)
tile['limits'].append('ExistingXREL stations at y327.68 are sourcepin Manhattan proofs; exactDFF packing, M7/M9 verticalovermacro routes andcontrol/reset nets stillrequire placement/routing.')
# Complete canonical boundary allocation, allsourcebits retained once.
boundary=[]
for bit in range(2069):
 sy=19+(121-.1)*bit/2068
 ty=10+.16*bit
 boundary.append(dict(bus='bout',bit=bit,source=[681.56,sy],destination=[W,ty],layer='M8',manhattan=W-681.56+abs(ty-sy)))
for row,sx,sy,off in [(1,591.5,599.92,2069),(0,391.5,589.92,2887)]:
 for bit in range(818):
  x=sx+.096*bit;y=10+.16*(off+bit)
  boundary.append(dict(bus='rout',row=row,bit=bit,source=[x,sy],destination=[W,y],layer='M8',manhattan=W-x+abs(y-sy)))
assert len(boundary)==3705 and max(r['manhattan']for r in boundary)<500
inputpairs=[]
for row,lo,dx in [(0,80,10),(1,19,497.4)]:
 slots=sorted([(lo+.128*i,'M6')for i in range(500)]+[(lo+.16*i,'M8')for i in range(500)])[:818]
 for bit,(y,layer)in enumerate(slots):
  inputpairs.append(dict(bus='rin',row=row,bit=bit,source_registered_Q=[5,y],destination_PORT=[dx,y],PORT_layer=layer,manhattan=dx-5))
for bit in range(2069):
 sy=140+.16*bit;dy=10+129.9*bit/2068
 inputpairs.append(dict(bus='bin',bit=bit,source_registered_Q=[5,sy],destination_PORT=[116.4,dy],PORT_layer='M4/M6',manhattan=111.4+abs(sy-dy)))
assert len(inputpairs)==3705 and max(r['manhattan']for r in inputpairs)<500
assert len(set((r['destination'][1],r['layer'])for r in boundary))==3705
tile['output_boundary_pairs']=boundary;tile['input_receiver_pairs']=inputpairs
tile['max_output_external_um']=max(r['manhattan']for r in boundary);tile['max_input_receiver_external_um']=max(r['manhattan']for r in inputpairs)
tile['limits'].append('All3705 inputsource Q positions are proposed actualtilePINREG placement atx5; realclock roots and placement of this retained parentlogic requiretilehardening.')
(OUT/'complete16.json').write_text(json.dumps(tile,indent=2)+'\n')
source=ROOT/'results/arch/hier_contract_1011/handoff/r25gq_sm_child_origins.json';old=json.load(open(source))['sm_component'];children=[]
# Keep all11 frontchild pairwise offsets; rigid shift moves them out ofleft4newtilecolumns.
left=[i*(W+20) for i in range(4)];frontshift=left[-1]+W+20-2561.76
frontmax=max(c['x']+c['outline_um'][0] for c in old['children'] if c['name'].startswith('g_fd'))+frontshift
right=[frontmax+20+i*(W+20)for i in range(4)];col=left+right
for c in old['children']:
 c=copy.deepcopy(c);n=c['name']
 if n.startswith('g_fd'):c['x']+=frontshift
 elif '.u_be' in n:c['x']=col[int(n.split('[')[1].split(']')[0])]
 else:
  i=int(n.split('[')[1].split(']')[0]);p=int(n.split('g_p[')[1].split(']')[0]);c['x']=col[i];c['y']=97.76+(1-p)*(H+20);c['outline_um']=[W,H];c['status']='NEW16CHILD_TILE_UNQUALIFIED'
 children.append(c)
assert len(children)==35
viol=[]
for i,b in enumerate(children):
 for c in children[:i]:
  bw,bh=b['outline_um'];cw,ch=c['outline_um'];g=max(c['x']-b['x']-bw,b['x']-c['x']-cw,c['y']-b['y']-bh,b['y']-c['y']-ch)
  if g<-.0001:viol.append([b['name'],c['name'],g])
assert not viol
sw=max(c['x']+c['outline_um'][0]for c in children)+10;sh=max(c['y']+c['outline_um'][1]for c in children)+10
sm={'verdict':'COMPLETE35_GEOMETRY_NO_OVERLAP_NEWSEAMS_UNQUALIFIED','source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'children':children,'frame_outline_um':[sw,sh],'frame_area_mm2':sw*sh/1e6,'sm_count':32,'all32_sm_frame_area_mm2':sw*sh*32/1e6,'baseline_sm_budget_mm2':9.412,'delta32_vs_budget_mm2':(sw*sh/1e6-9.412)*32,'front_rigid_shift_x_um':frontshift,'retained_front_children':11,'retained_backends':8,'retained_tiles':16,'clearance':'New tile-to-tile/front/BE20um; sourcefront internal offsets andgaps preserved, not promotedto20um.','limits':['Newtileinput/output pinface ordering must mapactualSMchain.','Rigidfrontshift changes front-to-tile wiring andneeds actualregisteredreach pluscut price.','No newrelays orlatency assumed. This is completegeometry andhonestbudgetprice, notnativefitproof.']}
(OUT/'complete35.json').write_text(json.dumps(sm,indent=2)+'\n')
print(json.dumps({'tile_area':tile['area_um2'],'min_gap':tile['minimum_macro_gap_um'],'row_external_max':[r['max_um']for r in rowpairs],'sm_frame':sm['frame_outline_um'],'sm_area_mm2':sm['frame_area_mm2'],'all32_mm2':sm['all32_sm_frame_area_mm2'],'delta32_vs_9_412':sm['delta32_vs_budget_mm2']},indent=2))
