"""Prepare only: materialize exact DATA edits from retained structural exports."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('extraction',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=a.extraction
rows=[l.split('\t') for l in (r/'cones.tsv').read_text().splitlines()]
def conns(inst):
 out={}
 for owner,pin,net,other,master,op,direction in rows:
  if owner==inst:out.setdefault(pin,{'net':net,'terms':[]})['terms'].append({'inst':other,'master':master,'pin':op,'direction':direction})
 for v in out.values():v['terms']=sorted(v['terms'],key=lambda t:(t['inst'],t['pin']))
 return out
swaps=[]
for inst,old,new in [('fanout24569','BUFx2_ASAP7_75t_R','BUFx4_ASAP7_75t_R'),('fanout35140','BUFx4f_ASAP7_75t_R','BUFx6f_ASAP7_75t_R')]:
 c=conns(inst);assert set(c)>={'A','Y'},(inst,c)
 me=[t for t in c['Y']['terms'] if t['inst']==inst];assert me==[{'inst':inst,'master':old,'pin':'Y','direction':'OUTPUT'}],me
 swaps.append({'inst':inst,'old_master':old,'new_master':new,'exact_old_connections':c,'equivalence':'A input;Y output;function A in exact selected TT and FF Libs'})
sink=r'u_u_lrly1.c_va\[29\]$_DFF_P_';hc=conns('_145581_')['Y'];assert hc['net']==r'u_u_lrly1.pa_q\[157\]'
assert {(x['inst'],x['pin']) for x in hc['terms']}=={('_145581_','Y'),(sink,'D')},hc
holds={'inst':'codex_l1_hold_cva29_buf','master':'BUFx2_ASAP7_75t_R','input_pin':'A','output_pin':'Y','source_inst':'_145581_','source_pin':'Y','old_net':hc['net'],'sink_inst':sink,'sink_pin':'D','new_net':'codex_l1_hold_cva29','exact_old_net_terms':hc['terms'],'placement':'initial location/orientation at exact sink; native DPL must legalize; all original clock-connected instances fixed'}
files={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ('cell_baseline.tsv','clock_baseline.tsv','bterm_baseline.tsv','cones.tsv','master_pins.tsv','odb_before.sha256')}
m={'schema':'opentallas.qc.l1.data_candidate.v1','status':'PREPARED_UNEXECUTED_REVIEW_REQUIRED','source_odb_sha256':'f2ea233f4efaf564046b47fd1beb15b16363f52e4a5455e645564a94fce10d66','structural_exports_sha256':files,'swaps':swaps,'insert_buffer':holds,'allowed_logical_edits':3,'allowed_new_instances':1,'allowed_new_nets':1,'sequential_stages_added':0,'protected':'all original instance names/master counts except two listed swaps; all original FFs, clock-connected instance master/location/orientation/net-pin identities and flags, BTerms/source clock and SDC bytes; no clock padding or added cycles','rollback':{'method':'discard candidate output; restore exact immutable original5_1ODB/SDC; never mutate original','source_sha256':'f2ea233f4efaf564046b47fd1beb15b16363f52e4a5455e645564a94fce10d66','inverse_edits':['restore fanout24569 old master','restore fanout35140 old master','reconnect exact hold sink D to old_net; destroy inserted BUF and new_net']},'acceptance':'actual TT/FF final policy via current legacy_gate.py grt complete helper context; unchanged clock identity; native late write_guides/all CLOCK+SIGNAL guide coverage; actual changed geometry LOOK; later source/postroute EQ independent; no DRT authorization','retime_scope':'all predecessor drivers and output fanout terms in exact_old_connections; hold upstream INV/launch FF and single sink; full joint timing for all interactions'}
a.out.write_text(json.dumps(m,indent=2)+'\n')
