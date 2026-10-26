from pathlib import Path
import json,sys,math,hashlib,collections
sys.path.insert(0,'/home/ubuntu/wt/codex-hbm-token-resume-1021/tools')
from hbm_layer_vehicle.layer_images import CpBus
from hbm_layer_vehicle import sm_images as SI, smb_unit as SB, att_images as A
from hbm_layer_vehicle.pv_probability_transport_1340 import compile_transport,source_windows
from hbm_layer_vehicle.pv_probability_rows_1340 import command,COMMAND_TO_WRITE,ROW_INTERVAL
from hbm_layer_vehicle.pv_kv_service_1340 import compile_service
from hbm_layer_vehicle.sm_slice_lower import refresh_reload
from hbm_layer_vehicle.check_slice_run import FAULT_OUTPUT_PORTS
r=Path('/home/ubuntu/scratch/tok-func2-hbm/pv_join_minimum_output_1600')
su=json.load(open('/home/ubuntu/scratch/tok-func2-hbm/pv_join_minimum_1545/su_emit/replay.json'))
bnd=json.load(open(r/'slice/boundary.json'));contract=json.load(open('/home/ubuntu/scratch/tok-func2-hbm/conn_idx/contract_func.json'))
pinput=json.load(open(r/'probability_input_plan.json')) if (r/'probability_input_plan.json').exists() else json.load(open('/home/ubuntu/scratch/tok-func2-hbm/pv_join_minimum_1545/../pv_join_minimum_output_1600/probability_input_plan.json'))
# Only authentic score M events; identical repeated score sectors are packed once.
pre={};cfg=[];oldstart=next(e['cyc'] for e in su['events'] if e['k']=='D' and e['port']=='su_prog__r_start' and int(e['val'],16))
for e in su['events']:
 if e['k']=='M':
  key=(e.get('quarter',0),e['sector'])
  if key in pre and pre[key]['val']!=e['val']:raise ValueError('conflicting pre-op input image')
  pre[key]=e
 elif e['k']=='D' and e['port']!='su_prog__r_start':cfg.append(e)
assert len(pre)==16 and all(e['rec'] in (20,21) for e in pre.values())
# Verify packed source inputs against genuine score128 words, never exp/P.
score=json.load(open('/home/ubuntu/scratch/tok-func-hbm/rsrc/L00/records.json'))['records']['0'][21]
import numpy as np
with np.load('/home/ubuntu/scratch/tok-func-hbm/rsrc/L00/operands.npz') as z:scorebits=z[score['inputs']['A']['array']].view(np.uint32).reshape(-1)
packed=np.array([int(e['val'],16)>>(32*i)&0xffffffff for e in sorted(pre.values(),key=lambda e:e['sector']) for i in range(8)],np.uint32)
assert np.array_equal(packed,scorebits)
assert hashlib.sha256(packed.tobytes()).hexdigest()==score['inputs']['A']['sha256']
maxcfg=max(e['cyc'] for e in cfg);bus=CpBus(t=(4*maxcfg+2)//3+64,src='image:PV_JOIN_CP')
ev=list(pre.values())+cfg;phases=[]
def calendar(owner,write,loops,local=False):
 for q,tgt in enumerate(range(96,100)):
  payload=SI.cal_word(rslot_v=255,wslot_v=255,rslot=sum(owner<<(3*b) for b in range(8)),wslot=sum(write<<(3*b) for b in range(8)),lg_local_read=255 if local and q==0 else 0,lg_local_write=255 if local and q==0 else 0)
  bus.install(tgt,[SI.prog_row(0,payload,SI.CAL_W)],0);bus.desc(tgt,0,1,loops)
def stage(name,loops,owner,write,local=False):
 calendar(owner,write,loops,local);c=bus.launch();phases.append(dict(name=name,host_launch=c,calendar_publish=c+10,calendar_end=c+10+loops,read_owner=owner,write_owner=write,loops=loops));return c
L1=stage('SU_score_max_exp_BF16',1400,0,0,True)
start=(3*(L1+48)+3)//4;delta=start-oldstart
for e in su['events']:
 if e['k']=='D' and e['port']=='su_prog__r_start' or e['k']=='C':
  q=dict(e);q['cyc']+=delta;ev.append(q)
Pready=(4*(3721+delta)+2)//3
assert Pready<L1+1400
bus.t=L1+10+1400+32
windows=source_windows(pinput);dest=[[256+16*j]*4 for j in range(len(windows))]
gq=compile_transport(pinput,destinations=dest,contract=contract,gq_source_path='/home/ubuntu/wt/codex-hbm-idx-transport-1352/rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv',first_fire=40)
for q in range(4):bus.install(176+q,gq['rows'][q],0);bus.desc(176+q,0,len(windows),1)
L2=stage('fourquarter_GQ_actual_P_copy',800,3,2)
Pcopy=L2+3+gq['transactions'][-1]['last_bank_write']
# Real copied probabilities checked at each of4 actual destinations. No collateral images.
with np.load('/home/ubuntu/scratch/tok-func2-hbm/pv_actual_kv_1538/L00/att_kv.npz') as z:Pgold=z['r0.ATT.PV.0.A'].view(np.uint32).reshape(-1)
remap={x['logical_word']:x['destination_physical_words'] for x in gq['probability_word_remaps']}
checks={}
for i in range(128):
 for q,word in enumerate(remap[55360+i]):
  sec,lane=divmod(word,8);v,m=checks.get(sec,(0,0));checks[sec]=(v|(int(Pgold[i])<<(32*lane)),m|(0xffffffff<<(32*lane)))
for sec,(v,m) in sorted(checks.items()):ev.append(dict(k='C',dom='stream',cyc=Pcopy+32,port=f'vm:{sec:x}',val=f'{v:064x}',mask=f'{m:064x}',rec=24,src='comparison:actual_fourquarter_copy_of_expected_SU_P'))
bus.t=L2+10+800+32
# Phase3: real runtime N1 xload pages and true HBM KV/PV service; all programmes fixed before launch.
xl=[(64+i*ROW_INTERVAL,command(remap[55360+i][0],i)) for i in range(128)]
rows=SI.cmd_table_rows(xl,SI.XL_CW);bus.install(100,[w for _,w in rows],SI.CMD_WIN_TABLE);bus.desc(100,0,128,1)
record,_=A.load_ds(Path('/home/ubuntu/scratch/tok-func2-hbm/pv_actual_kv_1538'),0)
class NoP(dict):
 def __getitem__(self,k):
  if k=='p':raise AssertionError('captured P stimulus')
  return super().__getitem__(k)
op=next(o[:5] for o in A.plan_d4g(record)[0] if o[0]=='pv_sm_SW0')
svc=compile_service(record=NoP(record),op=op,probability_rows={i:i for i in range(8)},latencies=A.E.DEFAULT_LAT,go_at=40000)
bus.install(126,[sum(refresh_reload(p)<<(8*p) for p in range(16))],0x800)
bus.install(64,svc['svg_programme'],0);bus.install(64,svc['svg_descriptors'],0x400);bus.desc(64,0,1,1)
bus.install(192,svc['xc_programme'],0);bus.install(192,svc['xc_descriptors'],0x400);bus.desc(192,0,2,1)
L3=stage('real_XQL_pstore_and_one_SM_PV',40600,2,0)
lastwrite=L3+3+8+xl[-1][0]+COMMAND_TO_WRITE
SMbody=L3+3+40000+SB.LAT_GO
assert lastwrite<SMbody and Pcopy<L3
for sector,value in svc['hbm_image'].items():ev.append(dict(k='M',mem='hbm',inst='phy_SW',sector=int(sector),val=f'{int(value):064x}',dom='hbm',cyc=0,src='input:authentic_KV_canonical_packed136'))
end=L3+40600+32
faults=[]
for o in bnd['outputs']:
 if o['driver'].rsplit('.',1)[-1] in FAULT_OUTPUT_PORTS:
  faults.append(o['name']);ev.append(dict(k='C',dom='stream',cyc=end,port=o['name'],val='0',mask=f'{(1<<o["width"])-1:x}',src='assert:actual_selected_fault_zero',rec=24))
ev+=bus.ev
x=dict(schema='opentallas.hbm_slice_replay.v1',scope='component_probe',qualifies_native_layer=False,qualifies_native_chain=False,state_seed_provenance=['authentic_native_score_and_KV_inputs_only'],events=sorted(ev,key=lambda e:(e['dom'],e['cyc'],e['k'])),assumptions=['TB_IMAGE_LOAD_ONLY SU programmeinput boundary; sparse host install unqualified','only genuine scores and K/V preloaded; all exp/P generated by real SU path','historical160/40 PV latency explicit candidate; exact current-source execution pending','oneSM unnormalized8-row PV node at real output interface; no denominator/SO/globalmerge/VMdrain/page-reuse claim'])
(r/'replay_candidate.json').write_text(json.dumps(x,indent=1)+'\n')
spec=json.load(open(r/'sm_node_scoreboard_candidate.json'));spec.update(begin_edge=SMbody,end_edge=L3+40500,status='EXACT_EXPECTED_VALUES_FIXED_CANDIDATE_WINDOW_NO_EXECUTION')
(r/'sm_node_scoreboard.json').write_text(json.dumps(spec,indent=1)+'\n')
meta=dict(status='PRE_ADMISSION_SOURCE_PROGRAMME_CANDIDATE',hardware_executed=False,source_score_sha256=score['inputs']['A']['sha256'],preloads=dict(score_sectors=len(pre),probability=0,exp=0,collateral=0,HBMsectors=len(svc['hbm_image'])),phases=phases,Pready=Pready,Pcopy=Pcopy,pstore_last_write=lastwrite,SM_body_word0=SMbody,fixed_end=end,raw_events=len(ev),non_M_events=sum(e['k']!='M' for e in ev),NEV_required=1+sum(e['k']!='M' for e in ev),fault_faces=len(faults),fault_names=faults,defines=['OT_COLL_GQ_SINGLE_SENDER'],SU_record_indices=[20,21,23],SU_component_image_grade='TB_IMAGE_LOAD_ONLY',output='64unique real SM rows ×8 FP32 values; unnormalized8-row csum8 node; no VMwriter or page reuse',historical_latency_inherited_PASS=False,programme_capacities=dict(SVG_words=len(svc['svg_programme']),XC_words=len(svc['xc_programme']),XL_rows=len(rows),GQ_rows=len(windows)),source_plan='cut396/48masters; source readset pending finalized publication')
(r/'preflight.json').write_text(json.dumps(meta,indent=1)+'\n');print(json.dumps({k:meta[k] for k in ['status','preloads','Pready','Pcopy','pstore_last_write','SM_body_word0','fixed_end','raw_events','non_M_events','NEV_required','fault_faces','programme_capacities']}))
