#!/usr/bin/env python3
"""Assign the actual SVC FP32 probability frame ingress before its closed job.
Two direct seams use measured CLOSED job/IOq pins. Other SVC seams must be
rechecked after the IOq orientation changes; no old slab qualification is reused.
"""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_svc_native';out.mkdir(exist_ok=True)
 _,job=V.lef_bits('physical/s81_ph_views/closed/dsfd_svcio_job/dsfd_svcio_job.lef')
 _,ioq=V.lef_bits('physical/s81_ph_views/closed/dsfd_svcio_q/dsfd_svcio_q.lef')
 jxy=(7999.104,1369.44);pxy=(8066.496,1269.216);ixy=(8121.168,1447.176)
 qo=[];proof=[]
 for bit,p in sorted(job['q'].items()):
  x=jxy[0]+p[2]-pxy[0];qo.append(['N','M5',round(x,3),.084])
  proof.append({'bus':'pack.q_o->job.q','bit':bit,'length_um':round(abs(pxy[0]+x-jxy[0]-p[2])+abs(pxy[1]+86.4-.042-(jxy[1]+64.8-p[3])),3)})
 for bit,p in sorted(job['q_o'].items()):
  t=ioq['q'][bit];length=abs(jxy[0]+p[2]-ixy[0]-t[2])+abs(jxy[1]+64.8-p[3]-(ixy[1]+129.6-t[3]))
  proof.append({'bus':'job.q_o->IOq.q','bit':bit,'length_um':round(length,3)})
 pp={'q_o':qo,'q':[['S','M5',42.924+.096*i,.084] for i in range(515)],'clk':[['W','M4',4.032,.084]],'rst_n':[['W','M4',4.992,.084]],'fault':[['E','M4',43.2,.084]]}
 V.write(out,'ot_s81_svc_probability_frame',[129.6,86.4],pp,'clk','Native raw q S; transformed q_o N exactly opposite CLOSED MX job.q; W stream root/reset','v20_svc_native_ingress',{'adoption':'new native top composition and all changed IOq seams/clock/reset must pass','source':'tools/s81/svc_native_ingress_pins.py'})
 d={'schema':'opentallas.s81.subslots.v1','parent':'dsfd_svc_c','parent_outline':[8500.032,1576.776],'source_prior':'physical/s81_ph_views/svc/composition.json (prior dsfd_svc, not full native top)','children':[{'instance':'g_native_pv.u_pv_pack','master':'ot_s81_svc_probability_frame','at':list(pxy),'outline':[129.6,86.4],'orient':'R0'},{'instance':'u_job','master':'dsfd_svcio_job','at':list(jxy),'outline':[270.,64.8],'orient':'MX'},{'instance':'u_io.u_q','master':'dsfd_svcio_q','at':list(ixy),'outline':[270.,129.6],'orient':'MX'}],'direct_pair_geometry':proof,'max_um':max(p['length_um'] for p in proof),'qualification':'OPEN native parent: unchanged legacy children need actual current RTL binding; changed IOq other seams/phi-R/root reset and raw external q flight unverified'}
 (out/'ingress_layout.json').write_text(json.dumps(d,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';c=json.loads(p.read_text());c['sub_layouts']['dsfd_svc_c_native_ingress']={'source':'physical/s81_die_pins/v20_svc_native/ingress_layout.json','qualification':'OPEN native full parent, slots reserved for actual masters'};p.write_text(json.dumps(c,indent=1)+'\n')
 print('SVC_NATIVE_INGRESS',len(proof),'actual bit joins max_um',d['max_um'])
if __name__=='__main__':main()
