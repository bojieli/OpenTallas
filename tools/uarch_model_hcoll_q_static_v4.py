#!/usr/bin/env python3
"""Pre-build all-input-capture V4 quadrant/host budget; physical qualification separate."""
from uarch_model_hcoll_q_static_v3 import model as v3_model
import json

def model(npt=3,solo=True):
 m=v3_model(npt,solo)
 m['unverified']=[v.replace('V2','V4') for v in m['unverified']]
 m.update(source_version='hcoll.quadrant.v4',link_module='ot_hgi_coll_static_link_capture',
  link_read_to_pin_edges=6,link_receive_edges=2,link_write_to_native_SRAM_edges=4,sequence_metadata_lead_edges=1,
  link_controller_measured_FFs=4421,link_store_measured_FFs=[597,597,597,567],
  host_clock_entries=109 if solo else 69,
  endpoint_clock_entries=5,
  compiler_contract='Endpoint reservation input E: TX publication E+6. RX pins sampled E: publication E+2; qslots captures E+3. Every external endpoint input is captured before guard forks. Sequence arithmetic prepared one edge before reservation.',
  production_status='candidate actual logical composition; no inherited V3 link calendar or physical qualification')
 return m
if __name__=='__main__':print(json.dumps({'q3':model(3,True),'q2':model(2,False)},indent=2))
