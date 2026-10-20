#!/usr/bin/env python3
"""Extract real packed return lanes and emit conditional source epoch constraints.

No numeric return calendar, images, arrays, RTL or changed deadlines are emitted.
"""
import argparse,json,re,hashlib
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--placement',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 inv=json.loads(Path(a.inventory).read_text());place=json.loads(Path(a.placement).read_text())
 heads={h['head']:h for h in place['head_contracts']};ports=[]
 for s in inv['slices']:
  sid=int(re.fullmatch(r"4'd(\d+)",s['ports']['sid'])[1]);h=heads[sid]
  tokens=s['ports']['rt'].strip('{}').split(',');lane=0
  records=[]
  for token in reversed(tokens):
   token=token.strip();z=re.fullmatch(r"(\d+)'d0",token)
   if z:
    assert int(z[1])%70==0
    for _ in range(int(z[1])//70):records.append(dict(lane=lane,absent_literal_zero=True));lane+=1
   else:
    m=re.fullmatch(r'w_r_(f_\w+)_(src|lnd)\[69:0\]',token);assert m,token
    name='u_'+m[1];f=next(f for f in h['records'] if f['name']==name)
    records.append(dict(lane=lane,frame=name,return_net=token,endpoint=m[2],
      capture_tree='W' if lane<4 else 'E',capture_clock=s['ports']['clk'],
      frame_clock=f['actual_clock'],return_stations=f['actual_return_stations'],
      native_sample_phase=None,first_arr=None,last_arr=None,per_phase_emission_plan=None,
      semantic_dimension_range=[f['dimension_first'],f['dimension_last']],
      maximum_source_phases=f['six_row_phases']))
    lane+=1
  assert lane==8 and sum(not x.get('absent_literal_zero',False) for x in records)==h['frames']
  ports.append(dict(head=sid,slice=s['name'],epochs=h['selected_wqb_phase_count'],ports=records))
 rec=dict(schema='opentallas.s81.q_source_epoch_constraints.v1',
 selected_die_sha256=inv['sha256'],source_hashes={s:hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in [a.inventory,a.placement]},
 head_port_contracts=sorted(ports,key=lambda h:h['head']),physical_active_ports=122,
 constants=dict(capture_nodes=3,node_edges=13,pin_to_first_node=1,merge_reentry_edges=10,complete_to_cw_edges=4),
 equations={
 'arrival':'ARR(f,p,w)=sample_phase(frame_emit(f,p,w), actual_return_link(f), actual_capture_clock(f))',
 'tree':'F1 event DAG uses exact ordered sibling tags and three WIN2 node stages; do not add station halfcycles by rounding',
 'write':'CW(row)=F1_complete(row)+4; VP_commit(row)=CW(row)+actual_cw_route_and_SRAM_write_age(row)',
 'slot':'slot=(row+8*pos)&63; key=(pos,row16,nseg); retain key from first incomplete F1 through final complete reentry; different keys must not overlap',
 'cap_config':'new CFG only after pairing-store drain and all old-config D2 consumers; conservatively after every old CW/VP commit',
 'qr':'QR_start(head)>max(VP_commit(all64 tail inputs), VP_commit(all64 coefficients)) with measured command/read ages',
 'q_read':'Q_RDOUT_start(word)>max(VP_commit(32 actual input dimensions or QR output), source read-port release)',
 'source_epoch_end':'max(lastXS_tag_use, lastframe_return_and_capture_pipeline, lastCAP_write_commit, lastdependent_QR/read/gather_use)',
 'conservative_retire':'RETIRE>=source_epoch_end; earlier issuer-only retirement requires separate proof its reused tag/config state cannot affect in-flight source returns',
 'next_epoch':'epoch[p+1].CFG/slot/address reuse >= prior conflicting resource release, not prior heuristic end_iter',
 'deadline':'source_epoch_end + actual downstream gather/II4/consumer ages <= original fixed token deadline; otherwise FAIL'},
 conditional_nseg3_tail_bound='Only if arrivals/tree/F5-F11 legal and all3 segments present: last CW <= last ARR +40+2*10+4 = last ARR+64. This is an upper bound on CAP pipeline tail, not a chosen schedule or native return link estimate.',
 obligation_counts=dict(heads=16,rows=8192,physical_ports=122,selected_epoch_classes=[11,13,15]),
 schedule_generated=False,production_images_generated=False,new_ff=0,new_gates=0,new_macros=0,
 qualification='CONDITIONAL_SOURCE_OCCUPANCY_AND_REAL_PORT_MODEL; selected calendar HOLD')
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'source_epoch_contract.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('SOURCE_EPOCH_CONTRACT_PASS actualports122 packedlanes128 source_epochs11/13/15; native calendar HOLD')
if __name__=='__main__':main()
