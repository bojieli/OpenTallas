"""Approved DR5 token-read cut, priced before RTL and physical launch."""
def model():
 return dict(schema='opentallas.dsrom.wfc-prompt-pipe.v1',adopted=False,default_enabled=False,
  MACs_per_cycle=0,memory_bytes_per_cycle=dict(token_entry=5.375),
  boundary_bits_per_cycle=dict(request=36,response=22),routing_tracks=dict(request=144,response=88),
  replicas=dict(S0_token_store=1,source_return_tag=1),
  mechanism='Capture selected table entry and request tag, compare one cycle later; SOURCE return metadata delayed identically',
  area=dict(measured_r2_cell_um2=7145,added_register_bits_upper=100,added_cell_um2_allowance=200,
            outline_um=[120,120],core_um=[119.04,119.04],cell_fill_upper=(7145+200)/(119.04**2),slot_fits_under_60_percent=True),
  latency=dict(prompt_response_added_cycles=1,S0_issue_added_cycles_upper=1,per_token_latency_added_ns_upper=1/1.2),
  historical_failure='r1 TT=-478.67ps; r2 token outline utilisation61.9%; failures preserved',
  qualification='Exact SOURCE+token-store binding and new TT/FF routes required; old views do not qualify successor')
if __name__=='__main__':
 import json;print(json.dumps(model(),indent=2))
