#!/usr/bin/env python3
"""Minimum protected committed-payload -> phase-event bridge, before RTL."""
import argparse,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def build():
 sources=['rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_phase.sv','rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_egress_payload.sv']
 fields=dict(active=1,failed=1,context_epoch_tag_short=49,captured_E=6,captured_packed_BF=5,
              received_E=6,received_packed_BF=5,emitted_CAP_E=6,emitted_DRAIN_E=6,emitted_CAP_O=6,emitted_DRAIN_O=6)
 bits=2*sum(fields.values())
 return dict(schema='opentallas.softmax_egress_events.v1',adopted=False,route_admitted=False,
  source_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in sources},
  MAC_per_cycle=0,payload_bytes_per_cycle=0,payload_storage_bits=0,
  identity=dict(context_bits=49,receipt_bits=56,capture_metadata_bits=55,event_metadata_bits=59,
   epoch_admission='Parent owns fresh epoch and same begin context; bridge verifies every source and destination identity'),
  storage=dict(fields=fields,complemented_FF_bits=bits,FF_floor_mm2=bits*.2916/1e6,
   representation='Typed monotonic counters retain finite committed-event debt; no repeated per-event epoch/tag storage',
   pending_capacity_events_T640=144,pending_capacity_events_T128=80),
  ports=dict(capture='one actual SRAM packedrow commit per stream edge; E II1, BF II2',
   receipt='one protected destination-visible packedrow receipt per stream edge',
   phase_event='at most one committed event per stream edge; emitted only when actual phase ready/kind/row agree',
   event_kind=dict(CAP_E=2,DRAIN_E=3,CAP_O=6,DRAIN_O=7)),
  ordering=dict(E_regions=[72,111],E_short_region=[72,79],BF_regions=[112,127],
   E='Each source commit and destination receipt yields one event, in row order',
   BF='Each actual packedrow commit or receipt yields lower-half event then upper-half event',
   reject=['wrong epoch/tag','wrong row order','duplicate/excess commit/receipt','receipt before source commit',
     'BF capture before all E destination receipts','event consumption against wrong phase row','premature release','control complement upset']),
  latency=dict(commit_to_first_event_edges=1,packed_commit_to_second_event_edges=2,
   BF_first_vector_to_packed_commit_edges=2,BF_first_vector_to_first_event_edges=3,
   BF_second_vector_to_second_event_edges=3,
   BF32_first_input_to_last_CAP_O_event_edges=34,
   BF_packed_write_initiation_interval=2,BF_expanded_phase_initiation_interval=1,
   phase_post_capture_barrier_edges=2,
   bound='Clock edges with phase continuously ready at matching row; arbitrary phase backpressure adds measured waiting, never discarded events'),
  clock=dict(stream_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,physical_budget=None),
  area=dict(mapped_combinational_area=None,routing_track_capacity=None,physical_fit=False),
  scope=['No payload recomputation; actual source/destination commits from qualified payload component',
   'No b_valid-based visibility shortcut','No full-system simulation','No production placement/SS/FF claim'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(build(),indent=2)+'\n'
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(s)
 else:print(s,end='')
