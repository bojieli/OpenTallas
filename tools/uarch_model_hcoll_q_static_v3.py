#!/usr/bin/env python3
"""Pre-build V3 pin-registered endpoint parent budget."""
from uarch_model_hcoll_q_static_v2 import model as v2_model
import json

def model(npt=3,solo=True):
 m=v2_model(npt,solo)
 m.update(source_version='hcoll.quadrant.v3',link_module='ot_hgi_coll_static_link_pinreg',
  link_read_to_pin_edges=5,link_receive_edges=1,sequence_metadata_lead_edges=1,
  link_controller_measured_FFs=3201,link_store_measured_FFs=[597,597,597,567],
  issuer_feedback_bits=9,
  production_status='candidate logical composition; physical qualification remains unproven')
 return m
if __name__=='__main__':print(json.dumps({'q3':model(3,True),'q2':model(2,False)},indent=2))
