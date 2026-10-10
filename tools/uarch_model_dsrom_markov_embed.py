#!/usr/bin/env python3
"""MD6 released embedding port, sized before RTL; additive unified-model term."""
import ast,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    t=ast.parse((ROOT/'tools/uarch_model.py').read_text())
    ff=next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='DFF_UM2' for x in n.targets))
    pairs=math.ceil(129280*256*2/262144)
    return dict(schema='opentallas.md6.embed.v1',scope='component model; no full-head or physical qualification',
      shape=[129280,256],dtype='BF16',payload_bytes=66191360,macs_per_cycle=0,
      compute_intensity_MAC_per_byte=0,communication_intensity_bytes_per_lookup=512,
      ports=dict(request_bits=17+32,response_bytes_per_cycle=32,macro_bytes_per_cycle=32),
      boundary_bits_per_cycle=dict(request=49,macro_pair_local=256,group_to_final=16*256,response=256+32+4+1),
      macro=dict(rows=4096,width=274,payload_width=256,pairs=pairs,count=2*pairs,clkq_ss_ps=744.0,capture_cycles=2),
      hierarchy=dict(groups=16,banks_per_group=16,group_select_mux=16,final_select_mux=16,address_fanout_max=32,replicas=1),
      routing=dict(group_boundary_tracks_needed=4096,response_tracks_needed=293,channel_capacity_tracks=None,fit='unproven; requires dedicated slot'),
      area=dict(macro_area_mm2=2*pairs*7881.4/1e6,at_60pct_mm2=2*pairs*7881.4/1e6/.60,
                queue_FF_lower_bound_mm2=8*293*ff/1e6,
                capture_and_select_FF_lower_bound_mm2=(253*256+16*256+256+253+16*13)*ff/1e6,includes_logic=False,slot_fit=False),
      latency=dict(request_cycles=2,macro_and_capture_cycles=2,group_select_cycles=1,final_select_cycles=1,
                   response_queue_cycles=1,first_beat_cycles=7,last_beat_cycles=22,ns_last=22/1.2,
                   issue_beats=16,queue_depth=8,max_reserved=8,backpressure='issue only when issued-minus-consumed < 8'),
      enabled_default=False,ROM_ECC=False,qualification='pending exactness and SS/FF contextual timing')
if __name__=='__main__':print(json.dumps(model(),indent=2))
