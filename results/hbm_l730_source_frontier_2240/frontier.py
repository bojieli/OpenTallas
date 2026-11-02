import json,sys,math,hashlib
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import schema as S,gen_phys as G
r=Path(__file__).resolve().parent
paths={'old':r/'original_plan_s11_d44r.json','new':Path('/home/ubuntu/coord/tmp/codex-hbm-d44r-2039/entryO_union_clock.json')}
groups=[('u_sfucore_Q_ctl','u_core_u_engine_u_arithmetic_procdff_71639__Q',0,1021,0),('u_sfucore_Q_opstore_a','cmd0_Q',1022,1341,576),('u_sfucore_Q_opstore_b','cmd0_Q',1342,1661,576)]
report={'status':'FAIL_UNSITED_SOURCE_TO_FACE_AND_NATIVE_VIEW_JOIN','source13_bout':'u_bout_L730_o: direct raw producer wires into one ot_dp_st W1662; no source relay chain','data_bits':1662,'epoch_bits':1,'type_results':[],'actual_port_pin_join':'HOLD: legacy pin files expose no exact selected source port names; no alias inferred','extra_source_cycles_adopted':0,'scope':'Bounding-box lower bounds only prove failure; they do not qualify actual selected port locations or constitute a repair.'}
for label,path in paths.items():
 raw=json.load(open(path));P=S.Plan(raw)
 for tn in ('q_b113','q_b113__physical_v1'):
  t=raw['partition_types'][tn];pins={b:(x-1,y)for bus,b,l,x,y,face in G.type_pins(P,tn)if bus=='L730_o'};records=[]
  for inst,port,lo,hi,src in groups:
   core=next(c for c in t['hard_cores']if c['inst']==inst);a,b=core['origin_um'];w,h=core['outline_um'];bounds=[]
   for bit in range(lo,hi+1):
    x,y=pins[bit];lower=max(a-x,0,x-a-w)+max(b-y,0,y-b-h);bounds.append(lower)
   pinfile=r/core['pins_file'];stored=json.load(open(pinfile));names={q['name']for q in stored}
   missing=[f'{port}[{src+i}]'for i in range(hi-lo+1)if f'{port}[{src+i}]'not in names]
   records.append(dict(core=inst,source_port=port,lane_data_bits=[lo,hi],source_bits=[src,src+hi-lo],core_bbox_um=[a,b,a+w,b+h],min_possible_source_to_face_um=[round(min(bounds),3),round(max(bounds),3)],guaranteed_over405=sum(x>405 for x in bounds),minimum_extra_relay_banks_per_bit=[math.ceil(min(bounds)/405)-1,math.ceil(max(bounds)/405)-1],exact_selected_source_ports_missing_from_pinfile=len(missing)))
  report['type_results'].append(dict(variant=label,type=tn,window=next(b['window_um']for b in t['buses']if b['name']=='L730_o'),groups=records,internal_stations_claiming_L730=[x for x in t['internal_stations']if'L730'in str(x)]))
report['new_lower_bound_repair_price_per_type']=dict(ctl_extra_banks=3,opstore_a_extra_banks=1,opstore_b_extra_banks=1,unaligned_data_FF_min=1022*3+320+320,aligned_three_cycle_data_FF_min=1662*3,aligned_three_cycle_epoch_FF_min=3,aligned_latency_added_cycles_at_least=3,clock_ps=833,aligned_latency_added_ps_at_least=2499,note='This is a lower bound, not legal bank placement. Exact source pins/current physical views, body/clock/reset/source/miter/model joins required. Existing old placement already needed at least2 added ctl banks; move increases this minimum by1.')
(r/'frontier.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
