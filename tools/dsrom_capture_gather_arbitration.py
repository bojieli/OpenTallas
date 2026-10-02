#!/usr/bin/env python3
"""One proposed ordered shard0 gather; no capacities/stations/providers selected."""
import argparse,json
from pathlib import Path
import dsrom_capture_home_r49 as H
import dsrom_capture_physical_shard_paths as P

def runs():
    result=[]
    for row in range(576):
        s=P.owner(row)['physical_shard']
        if not result or result[-1]['shard']!=s:result.append(dict(shard=s,first_row=row,last_row=row))
        else:result[-1]['last_row']=row
    return result

class Arbiter:
    def __init__(self,context):self.context=context;self.next_row=0
    def accept(self,row,shard,context,token_valid,raw_valid,sink_reserved,ready):
        if not token_valid or not ready:return False
        if context!=self.context or row!=self.next_row or shard!=P.owner(row)['physical_shard'] or not raw_valid or not sink_reserved:raise ValueError('wrong owner/order/valid/reservation')
        self.next_row+=1;return True

def build():
    h=H.build();d,_=H.H.inputs();facts=d['capture.json']['source_cell_facts']
    # Conservative gross fourflags+16bit source row+169bit lease. This is not
    # certified incremental state relative to old1483 control census.
    counts={'DFFASRHQNx1_ASAP7_75t_R':189,'INVx1_ASAP7_75t_R':378,'NAND2x1_ASAP7_75t_R':567,'TIEHIx1_ASAP7_75t_R':189,'BUFx4_ASAP7_75t_R':434}
    # 378 typed-feedback BUFs plus two FO8 trees of 24+3+1 each.
    tie_area=d['capture.json']['SETN_TIEHI_LEF_area_um2']/1483
    body=sum(n*(tie_area if m.startswith('TIEHI') else facts[m]['SS']['area_um2']) for m,n in counts.items())
    return dict(schema='DS_CAPTURE_ORDERED_GATHER_PROPOSAL_1',candidate=h['candidate'],geometry_commit='4cc368a46ca8894b102bb34ccd674168571cd282',
      local_controller_homes=[dict(shard=s,bbox_DBU=h['corrected_common_bbox_DBU'],banks=64,seats=n,instance_ports=None) for s,n in enumerate((320,256))],
      global_ordered_gather_home=dict(shard=0,retained_service_region='HUB_GATHER',bbox_DBU=[10974880,19618000,11605600,21819040],actual_instance_pins=None),
      arbitration='next source row only; source-static row bit7 selects shard after row0..575 bounds; no arrival-order retirement or epoch alias',
      ordered_owner_runs=runs(),single169bit_logical_phase_lease=True,route_shard_separate=True,request_bits=187,reply_bits=240,
      reserve='reserve gather sinkseat and positive request/reply/credit-route capacity BEFORE local read; no field-ready',
      refused_sink='hold ordered expectedrow and sink debt; no release or sourcecredit from sameedge consumption',
      positive_source_credit_return_required=True,credit_return_latency=None,credit_capacity_C=None,
      remote_provider_candidate='fff6dc9c0b609955b2db2ac8565eb6ab0baadaf2',provider_successful_envelope_requires_repriced240reply_or_sourceexact_packet_identity_adapter=True,
      formatter='unchanged row+pos*ops+obase and fmt/pw62/pw63/rsplit; use supplied BF16; reject sourceerror/VM19alias',
      VM='exclusive addressed VM512 fullblock lease; assembly/masks/commit/visibility provider unbound; never deliveryACK alias',
      release='all576 ordered healthy rows causally visible AND source fenced AND fresh accepted packetdelivery ACK AND route debts empty; CDC/SU acceptance separate',
      gross_arbiter_minimum_state=dict(lease169=169,nextrow16=16,active_fault_delivery_visible_flags=4,total=189,cells=counts,cell_body_um2=body,reserve50pct_mm2=2*body/1e6,
      conditional_extra_charge_if_all_new=True,containment_or_replacement_in_prior1483_control_bits=None,compare_counter_mux_fanout_routes_extra=None),
      local_controller_replacement_or_added_state=None,reply_gather_sink_state_bits='240*C plus occupancy/address state (C unselected)',
      registered_pipeline_state=None,implemented_CDC=None,consumer_enrolled_endpoint=None,consumer_required_first_last_edges=None,
      complete_source_cell_inventory=False,geometry_fit=False,contextual_PR_admitted=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
