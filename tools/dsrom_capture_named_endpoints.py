#!/usr/bin/env python3
"""Literal proposed R49 raw-cell read/write/clock endpoints, not routed pins."""
import argparse,gzip,json,hashlib
from pathlib import Path
import dsrom_capture_home_r49 as H
ROOT=Path(__file__).resolve().parents[1]

def endpoints():
    home=H.build();d,_=H.H.inputs();lef=d['cell_LEF.json']
    roles={r['role']:r for r in home['actual_raw_bit_cell_roles']}
    for bank in home['root_banks']:
        x,y=bank['bbox_DBU'][:2]
        for seat in range(bank['seats']):
            row=256*(seat//2)+2*bank['global_root']+seat%2
            if row>=576:raise ValueError('Seat to source-row mapping')
            for bit in range(69):
                pins={}
                for role,pin in [('storage','D'),('storage','QN'),('storage','CLK'),('restore','Y')]:
                    r=roles[role];pt,rect=H.pinpoint(lef[r['master']],pin)
                    dx=x+bit*home['raw_bit_pitch_DBU']+r['x_offset_DBU'];dy=y+seat*540
                    pins[role+'.'+pin]=dict(layer='M1',point_DBU=[dx+pt[0],dy+pt[1]],access_rect_DBU=[rect[0]+dx,rect[1]+dy,rect[2]+dx,rect[3]+dy],master=r['master'])
                yield dict(proposed_endpoint_identity=f"capture.shard{bank['shard']}.root{bank['local_root']}.seat{seat}.bit{bit}",
                    physical_shard=bank['shard'],global_root=bank['global_root'],local_root=bank['local_root'],seat=seat,source_row=row,opaque_raw_bit=bit,pins=pins,
                    read_source_pin='restore.Y',clock_pin='storage.CLK',orientation='R0',actual_placed_instance_name=None,legal_signal_escape=None)

def contract():
    h=H.build()
    return dict(schema='DS_CAPTURE_LITERAL_NAMED_ENDPOINTS_1',geometry_commit='4cc368a46ca8894b102bb34ccd674168571cd282',candidate=h['candidate'],
      proposed_endpoint_count=39744,physical_shard_seats=[320,256],separate_physical_dies=True,
      raw_read_source='QN-restoring INV/Y per proposed raw bit, also drives feedback branch; load changes need SS/FF checks',
      row_to_seat='seat=2*(row//256)+(row%2); root=(row%256)//2; shard=root//64',
      local_controller_reserved_bbox_DBU=h['corrected_common_bbox_DBU'],actual_local_controller_instance_ports=None,
      global_context_bits=169,route_shard_bits=1,request_bits=187,response_bits=240,
      gather_region_candidate=dict(shard=0,name='HUB_GATHER',bbox_DBU=[10974880,19618000,11605600,21819040],actual_provider_ports=None),
      VM_region_candidate=dict(shard=0,name='HUB_VM',bbox_DBU=[10974880,18203200,11605600,19618000],exclusive_512b_fullblock_lease=True,actual_provider_ports=None),
      CDC_endpoint=dict(source_domain_policy_GHz=1.2,consumer_domain_policy_GHz=.9,native_source_singleclk=True,selected_implementation=None,phase=None,actual_provider_ports=None),
      source_formatter_and_supplied_BF16_unchanged=True,no_crossdie_combinational576_mux=True,
      source_root_write_ports64_per_shard_not187b_read_request=True,typed_feedback_margins_not_forward_path_closure=True,
      legal_vias_OBS_PG_clock_reset_routes=False,finite_credit_return_path_and_deadline_bound=False,contextual_PR_admitted=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=True)
    raw=b''.join((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode() for r in endpoints())
    blob=gzip.compress(raw,mtime=0);(a.outdir/'raw_endpoints.jsonl.gz').write_bytes(blob)
    m=contract();m['raw_endpoints_sha256']=hashlib.sha256(blob).hexdigest();m['raw_endpoint_content_sha256']=hashlib.sha256(raw).hexdigest()
    (a.outdir/'contract.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
