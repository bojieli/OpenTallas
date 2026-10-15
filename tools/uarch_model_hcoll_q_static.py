#!/usr/bin/env python3
"""Before-build hierarchy budget for actual H-COLL q3/q2 scheduled parents."""
import json

def model(npt=3,solo=True):
    if npt not in (2,3): raise ValueError('production quadrants have2 or3 rails')
    ns,nd=2+npt+4+1,npt+12+1
    sw=(ns-1).bit_length()
    output_root=ns*545+nd*545+ns+2*nd+nd*sw+2
    return {
      'status':'UNQUALIFIED_COMPOSITION_PLAN',
      'rails':npt,'tkm_instantiated':solo,
      'clock_roots':{'issuer':4,'qslots':2,'ring':17,'vmwrite':1,'protocol':1,'links':5*npt,'tkm':34 if solo else 0,
                     'total':25+5*npt+(34 if solo else 0)},
      'qslots':{'sources':ns,'sinks':nd,'capture_root_register_estimate':ns*546+1,
                 'output_root_register_estimate':output_root},
      'writer_declared_register_bound':7944,
      'protocol_declared_register_bound':7207+8*npt,
      'registered_address_word_to_consumer_edges':1,
      'native_link_macros_64x512':4*npt,
      'ring_state_roots':8,'ring_arithmetic_roots':8,
      'timing_edges':{'su_inject_fixed_response':12,'qslots_source_to_output':2,
                      'writer_low_launch':1,'writer_high_launch':2,'link_tx':3,'link_rx':1,
                      'vm_bank_sample_to_registered_response':6,'vm_request_launch_to_qslots_capture':10},
      'area_estimate':'sum actual child macro and mapped leaf areas; current aggregate unknown',
      'unverified':['issuerprogram fullshape traces','production native composition behavior',
                    'all physical slots and pin cuts','mapped area','die timing',
                    'shared VM read ownership allocation','mirror replication calendar'],
    }
if __name__=='__main__': print(json.dumps({'q3':model(3,True),'q2':model(2,False)},indent=2))
