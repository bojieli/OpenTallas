#!/usr/bin/env python3
"""Model-before-RTL for checked published-span SU scalar read endpoint."""
import json

def model():
    # Conservative primitive gate bound: each SECDED encoder <320 XOR2;
    # decoder <320 XOR2+64*(7 XNOR2+6 AND2+1 XOR2)+32 small gates.
    rows=8;ff=rows*72
    ecc_gates=rows*(320+320+64*14+32)
    extra_gates=4096 # protected-state/address/owner equality and port gates envelope
    cell_bound=ff*.37908+(ecc_gates+extra_gates)*.2
    return dict(schema='opentallas.hbm.su.installed_span.prebuild.v1',selected=False,adopted=False,
      MACs_per_cycle=0,descriptor=dict(owner_bits=73,record_bits=16,source_bits=5,logical_word_base_bits=24,rows_bits=13,byte_base_bits=37,byte_limit_bits=37),
      replicas=1,outstanding_reads=1,protected_rows=rows,protected_ff_bits=ff,
      storage='8 SECDED72 control/descriptor/request/result rows; one returned32bit word, no new result memory',
      boundary_bits=dict(request=148,response=371,consumer_request=38,consumer_result=46),
      memory_bytes_per_request=32,consumer_bytes_per_result=4,MACs_per_byte=0,
      clock_ghz=1.2,latency=dict(bind_to_wait_publication=1,publication_to_read_ready=1,
        read_accept_to_service_request=1,checked_response_to_consumer_result=1,
        result_accept_to_next_read_ready=1,minimum_initiation_interval_cycles=4,
        total_read_cycles='1 requeststage + serviceacceptance/response latency +1 resultstage +consumerstall',
        per_token_cost='numberofSUreadtransactions*(measuredproviderlatency+2+stall); fullschedulerjoin required before tokenrate claim'),
      area=dict(ff_um2=.37908,conservative_logic_gate_um2=.2,ecc_gate_bound=ecc_gates,
        other_gate_bound=extra_gates,cell_area_bound_um2=cell_bound,slot_um=[128,128],
        slot_utilization_bound=cell_bound/(128*128),target_utilization=.55,
        slot_fit_analytical=cell_bound/(128*128)<=.55),
      routing=dict(proposed_channel_width_um=48,track_pitch_um=.072,capacity_tracks=666,
        aggregate_service_tracks=519,analytical_fit=True,physical_fit=False,
        source_fanout='encoded rows decode locally; largestownerbit comparisons request/publication/response, retainedbuffer tree required at synth'),
      reset='coldPOR only resets protection; warmreset withboundspan or outstandingservice quarantines instead of dropping ownership',
      adoption_gates=['actual descriptorinstallation/ownerbinding','bitexact read/identity andnegativegates','SS/FF context and protectedendpointplacement','actual SUcontroller virtualedge scheduling join'],
      open='one-outstanding adapter only; no full SUprogram/scheduler integration or final timing')
if __name__=='__main__':print(json.dumps(model(),indent=2))
