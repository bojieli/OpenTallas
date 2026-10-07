#!/usr/bin/env python3
"""Per-port reservation protocol sized before RTL. Physical provider unqualified."""
import json

def model():
 return {
  'status':'MODEL_BEFORE_RTL_DEFAULT_OFF', 'window_flits':64,
  'invariant':'reserved_not_finally_retired = PHY forward flight + CDC including held head + WSTG + RX packet queue including held head <=64',
  'payload_bits':545,'message_data_bits':64,'message_encoded_bits':72,
  'message_layout':{'kind':8,'epoch':24,'sequence':24,'count':8},
  'per_port_state_encoded_bits':{'receiver':216,'sender':216},
  'all_8_ports_state_encoded_bits':3456,
  'boundary_bits_per_cycle':{'data_reservation':1,'final_retirement':1,'grant_transport_max':72,'ack_transport_max':72},
  'compute':'zero MACs; SECDED decoders, increment/decrement, comparison and 72-bit muxes; mapped area/routing/fanout unresolved',
  'ports':'3 protected64bit state words per endpoint, each read/decode and write/encode per cycle; 27 bytes read +27 bytes written per endpoint cycle',
  'replicas':8,'floorplan':'unplaced; eight per-port pairs, provider source may reside on another die; no slot-fit claim',
  'protocol':'stop-and-wait grant seq; ACK exact epoch/seq/count; repeated grant reACK without credit; stale ignored; sequence exhaustion fails closed; no timeout-generated regrant',
  'reset':'external coordinated cold reset flushes data and control transport and both endpoint states; start once with trusted fresh epoch only after quiescence, no context-arm/go coupling; epoch wrap forbidden by provider',
  'source':'starts zero; reserve valid/ready handshake is the admission point strictly before PHY launch; transport must retain reserved flit until final retirement or coordinated reset',
  'receiver':'initial64; only final queue retirement accrues returns; CDC pop never returns credit; debt bounds retirement accounting',
  'serialization':'two72bit messages per grant transaction, plus provider framing/FEC. If control link width B and overhead F, each direction costs ceil((72+F)/B) link cycles; B/F unknown, no free transport',
  'cdc':'grant/ACK adapters must transport valid-ready atomically with finite storage; synchronizer/CDC delays unknown and not implemented here',
  'latency':'initial source grant acceptance then >=1 cycle to first reservation; subsequent grants need one receiver scheduling cycle after ACK. stop/wait RTT bounds credit replenishment; formula min(1/3,64/(forward+CDC+14+visibility+downstreamstall+return)), additionally stop/wait batching cap',
  'physical_forward_cycles':None,'physical_return_cycles':None,'transport_framing_bits':None,
  'qualification':'functional minimal synchronous component pair only; actual PHY/source binding, external epoch/reset provider, native integration, SS/FF route absent'
 }
if __name__=='__main__': print(json.dumps(model(),indent=2))
