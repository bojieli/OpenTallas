"""Native operation backend candidate sized from real storage and pinned die geometry."""
import argparse,json
from pathlib import Path
SLOT=dict(name='hb_native_operation_backend',master='ot_hbm_native_mtp_operation_backend_mx1',x=14295.456,y=9791.28,w=120.096,h=120.96,orient='R0',domain='stream')
def model(context):
    s=dict(SLOT);collisions=[]
    for i in context['instances']:
        if min(s['x']+s['w'],i['x']+i['w'])>max(s['x'],i['x']) and min(s['y']+s['h'],i['y']+i['h'])>max(s['y'],i['y']):collisions.append(i['name'])
    return dict(schema='opentallas.native_backend_slot.v1',adopted=False,candidate=s,
      context_source=context['source_commit'],variant=context['variant'],collisions=collisions,
      historical_protected_storage_bits=2355,current_MX1_storage_bits=2134,MX1_FF_area_floor_um2=2134*.2916,inventory_source="bf972bc00/f7498a6b1",
      core_density=.55,slot_cell_capacity_um2=s['w']*s['h']*.55,
      replicas=dict(backend=1,real_CP16SM=2,SM_response_fanout=32),MACs_per_cycle=0,
      memory='Historical inventory2355 included twoCP NCMD2 mutable SECDED command memories; current MX1 own1168bits+two actualCP483bits each=2134bits; SM arithmetic excluded',
      boundary_bits=dict(launch_valid=32,launch_PC=64,launch_token=34,launch_position=40,launch_owner=146,SM_status=96,SM_results=1024,descriptor_PC=64,descriptor_kind=4,descriptor_noise=17,native_command=269,completion=69,AM=18),
      routing='Every functional pin requires fresh literal collar; long32SM fanout transport and output result mux must be priced against actual station geometry',
      latency='Actual11kernel typed operation order and CP launch/result latency priced by operation backend source model; placement adds no assumed zero-latency die wires',
      clock=dict(period_ns=5/6,setup_uncertainty_ns=.060,hold_uncertainty_ns=.025,chosen_source='actual production PLL clk_stream root',arrival_ns=None,reset='destination DATA/reset boundary pending characterization',qualification='No measured root-to-backend CTS arrival or actual final pin segment; not ready for physical intake'),
      physical='Geometry reservation only if collisions empty; actual cell area/pin capacity/clock arrival remain unqualified')
def main():
    a=argparse.ArgumentParser();a.add_argument('--context',required=True);a.add_argument('--out',required=True);v=a.parse_args();d=model(json.loads(Path(v.context).read_text()));Path(v.out).write_text(json.dumps(d,indent=2)+'\n');print('collisions',d['collisions'])
if __name__=='__main__':main()
