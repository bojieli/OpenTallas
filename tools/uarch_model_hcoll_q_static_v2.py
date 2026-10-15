#!/usr/bin/env python3
"""Pre-build V2 actual-parent budget; no physical qualification claim."""
import json

def model(npt=3,solo=True):
 ns,nd=npt+8,npt+13
 return {'status':'UNQUALIFIED_PREBUILD_ANALYTIC','physical_frame_bits':612,
  'sources':ns,'sinks':nd,'logical_clock_roots':(108 if solo else 68),
  'new_operator_clock_roots':{'reduce':33,'argmax':1 if solo else 0},
  'qslots_capture_root_registers':ns*546+1,
  'qslots_output_root_registers':ns*545+nd*545+ns+2*nd+nd*4+2,
  'protocol_leaf_declared_bound':7208+59*npt,
  'measured_qslots_output_root_registers':14824 if solo else 13727,
  'sequence_word_to_reservation_edges':1,
  'source_faces':'separate registered reduction and ARGMAX outputs; no producer mux',
  'link_sequence':'16 protected bits, extended overflow fault at65536, actual64slot SRAM reuse',
  'area_estimate':'sum measured native leaf/macro areas; currently unknown',
  'unverified':['actual synthesis clock-root count','physical slot area/pins','die timing',
                'normative program compiler join','full native V2 operation programs']}
if __name__=='__main__': print(json.dumps({'q3':model(3,True),'q2':model(2,False)},indent=2))
