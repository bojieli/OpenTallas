import gzip,json,hashlib,collections,math
from pathlib import Path
p=Path('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz');j=json.load(gzip.open(p,'rt'));inst=j['insts'];cs=[i for i in inst if i['master']=='dsfd_cfifo']; cn={i['name'] for i in cs};out=[]
W=384.48;H=159.84
for a in cs:
 x=a['x'];y=a['y']+a['h']-H
 for b in inst:
  if a['name']==b['name']:continue
  if b['x']>=x+W or b['x']+b['w']<=x or b['y']>=y+H or b['y']+b['h']<=y:continue
  out.append(dict(cfifo=a['name'],other=b['name'],master=b['master'],overlap_um=[min(x+W,b['x']+b['w'])-max(x,b['x']),min(y+H,b['y']+b['h'])-max(y,b['y'])]))
buses=[b for b in j['buses'] if any(e[0] in cn for e in b[3])];ports=collections.Counter()
for b in buses:
 for n,p0 in b[3]:
  if n in cn:ports[p0]+=1
model=dict(schema='opentallas.s81.cfifo.partition_sizing.v1',scope='UNQUALIFIED_STRUCTURAL_SIZING_AND_FIRST_PASS_DIAGNOSTIC',source_commit=j['source_commit'],plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),final_pins=False,final_hops=False,final_clocks=False,parents=len(cs),incident_buses=len(buses),ports=dict(ports),proposal=dict(outline_um=[W,H],origin_delta_um=[0,95.016-H],cycles_added=0,ingress_widths=[[113]*5,[108,108,107,107,107]],ingress_leaf_um=[47.52,47.52],formatter_widths=[128]*8+[76],formatter_leaf_um=[21.6,17.28],return_leaf_um=[25.92,17.28],clock_roots=dict(source=10,read=10,formatter=9,return_control=1),max_root_sinks=9*113+37,control_duplicated_flops=480,old_flops_model=12313,new_flops_model=12793,relative_ff_cost=12793/12313-1,minimum_parallel_128bit_channel_um=128/(.6*31.51),reserved_channel_um=20,macro_area_um2=10*47.52**2+9*21.6*17.28+25.92*17.28,parent_area_um2=W*H,parent_area_delta_vs_old_slot_mm2=128*(W*H-431.976*95.016)/1e6),overlaps=out,overlap_count=len(out),open=['Actual leaf synthesis/hold allowance/PG/pins/clock tree','Actual parent signal routes for every incident bit','Marker fanout and samephase root delivery','Current final GEN per-instance overlap/pins/hops/cuts','Native launch220 capture190 spread80','TT setup FF hold DRC0'])
model['proposal']['postcts_density_estimate']=dict(method='Use measured flat9940.2um2/12313 modeledflops as conservative initial area/flop; not physical proof',ingress_max_flops=1190,ingress_core_area_um2=43.2**2,ingress_core_fill_estimate=1190*(9940.2/12313)/(43.2**2),formatter_core_area_um2=17.28*12.96,formatter_core_fill_estimate=128*(9940.2/12313)/(17.28*12.96))
model['proposal']['channel_parallel_two_ingress_groups_bits']=226
model['proposal']['parallel_group_cut_ratio_at_21_6um']=226/(21.6*31.51)
model['proposal']['channel_caveat']='This bound covers one pair of113-bit groups only. Actual parent bit routes/cumulative cuts not proven.'
model['proposal']['reserved_channel_um']=21.6
Path('results/rtl/s81_cfifo_partition_1016/sizing.json').write_text(json.dumps(model,indent=2)+'\n');print({k:model[k] for k in ['parents','incident_buses','ports','overlap_count']});print(out[:5])
