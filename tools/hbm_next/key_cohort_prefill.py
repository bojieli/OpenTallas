#!/usr/bin/env python3
"""Size static two-cohort prefill of four distinct IDX quarter key buffers.

The native8SM source retains8 four-PC memory service groups and one32PCstack.
No South memory producers exist. Reuse these groups at different programme
slots/addresses, store both logical cohorts, then replay the four independent
quarter buffers on the existing numeric calendar. No arithmetic role is aliased.
The service must still meet its HBM deadline; byte lower bounds are not a
measured HBM completion guarantee. Physical source/destination names are logical.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def model(*, rows=171, slots=4, relay_cycles=0, service_bytes_per_edge=None,
          service_latency_edges=None, records=8, token_edges=629600):
    if rows < 1 or rows > 171 or slots not in (1, 4, 8) or relay_cycles < 0:
        raise ValueError('rows1..171, slots1/4/8, nonnegative physical relay cycles required')
    if (service_bytes_per_edge is None) != (service_latency_edges is None):
        raise ValueError('service throughput and latency must be supplied together')
    groups, pcs, cohorts, pair_bytes = 8, 32, 2, 136
    per_cohort = rows * groups * pair_bytes
    # Full parallel:8ports. Local4slot:2 independent hub pipes.8slot:1sharedpipe.
    pipes = 8 // slots
    payload_bits = 1099
    envelope_bits = payload_bits + 8 + 3 + 1 + 1 #row,physical lane,cohort,valid
    transport = cohorts * rows * slots
    # Source programme samples one cache row on each group's reserved slot.
    # Fixed programme stores are reused for each <=64row block and eachcohort.
    block_rows = [min(64, rows-b) for b in range(0,rows,64)]
    max_programme_words = (max(block_rows)-1)*slots + 2
    descriptors_per_group = cohorts * len(block_rows)
    ideal_fetch = math.ceil(cohorts * per_cohort / (pcs*32))
    reserved_fetch = None
    if service_bytes_per_edge is not None:
        if not 0 < service_bytes_per_edge <= pcs*32 or service_latency_edges < 0:
            raise ValueError('service bounds exceed32PC physical payload capacity')
        reserved_fetch = math.ceil(cohorts*per_cohort/service_bytes_per_edge)+service_latency_edges
    # Conservative additive reservation: no unproved overlap or inherited free slots.
    added = None if reserved_fetch is None else reserved_fetch+transport+relay_cycles+2
    keys = cohorts*rows*groups*2
    return dict(schema='opentallas.hbm_idx.static_key_cohort_prefill.v1',
      estimate_status='COMPONENT_CAPACITY_PASS; physical/HBM completion NOT_QUALIFIED',
      default_enabled=False,adopted=False,MACs_per_cycle=0,
      existing=dict(SMs=8,HBM_stacks=1,PCs=pcs,service_groups=groups,quarters=4,
                    quarter_keybuf_SRAMs=20,keybuf_depth=256,rows_used=rows),
      logical_cohorts=[dict(id=0,first_ord=0,consumers=['s_SW','s_SE']),
                       dict(id=1,first_ord=342,consumers=['s_NW','s_NE'])],
      exactness='distinct physical key addresses and role buffers; original1088payload,10btag,valid preserved; no arithmetic or reduction changes',
      service=dict(bytes_per_cohort=per_cohort,total_bytes=cohorts*per_cohort,
                   total_keys=keys,physical_peak_bytes_per_edge=pcs*32,
                   ideal_fetch_lower_bound_edges=ideal_fetch,
                   reserved_bytes_per_edge=service_bytes_per_edge,
                   reserved_initial_latency_edges=service_latency_edges,
                   reserved_fetch_edges=reserved_fetch,
                   HBM_deadline='must be measured on current controller/reservation programme; lowerbound is not a deadline'),
      schedule=dict(slots=slots,pipes=pipes,cohorts=cohorts,block_rows=block_rows,
                    descriptors_per_group=descriptors_per_group,descriptor_capacity=256,
                    max_programme_words=max_programme_words,
                    two_shape_unrolled_programme_words=sum((r-1)*slots+2 for r in set(block_rows)),
                    looped_programme_words=slots,
                    looped_programme='nativePREL lstep1, loops=blockrows; onebody reused across bothcohorts',
                    programme_capacity=2048,
                    existing_programme_occupancy='unknown; explicit nonoverlapping allocation required before install',
                    transport_edges=transport,relay_edges=relay_cycles,
                    final_capture_edges=2,
                    live_row_store='independent per-lane SRAM writes on(slot,row); all171rows of all4lanes resident before query',
                    replay='bothcohorts fullyresident before query row0; existing query/key/selector pitch unchanged'),
      boundary=dict(packet_bits=payload_bits,envelope_bits=envelope_bits,
                    total_forward_tracks=pipes*envelope_bits,
                    row_payload_bytes_per_transport_edge=groups*pair_bytes/slots,
                    assembly_FF_bits=0,
                    assembly_FF_area_floor_um2=0,
                    receive='per-lane write-enable demux to existing independent keybuf_slice SRAMs',
                    added_control_FF_bits_per_quarter=12,
                    source_TX_boundary_FF_bits_per_hub=4*envelope_bits,
                    source_transport='distributedfixedslotseed+merges; eachsourceonlyown1099packet, upstream1112rail',
                    source_registered_nodes=8,
                    source_path_capture_edges=list(range(1,slots+1)),
                    source_GO_alignment='per-source paths equalize final lane-slot arrival; no directwide4fanin assumed',
                    physical_extra_station_FF_bits='1112peradditional405um/CAstation, actualpathcensuspending',
                    physical='2localhub receive/assembly stations; exactroutes/CA/stationarea pending oneHBMplan event'),
      latency=dict(unoverlapped_reservation_edges=added,
                   added_edges_per_token=None if added is None else added*records,
                   records_per_token=records,baseline_token_edges=token_edges,
                   rate_loss_fraction=None if added is None else 1-token_edges/(token_edges+added*records),
                   qualification='conservative added reservation, no unknown overlap credit; actual source service and physical hops pending'),
      claims=dict(functional=False,physical=False,token=False))


def census(top):
    raw=Path(top).read_bytes(); text=raw.decode()
    # Native generated syntax has one instance header per line; avoid matching
    # across earlier instances when extracting parameterized headers.
    insts=[]
    for line in text.splitlines():
        m=re.match(r'  (\w+)(?: #\(.*\))? (\w+) \($',line)
        if m:insts.append((m.group(1),m.group(2)))
    return dict(top_sha256=hashlib.sha256(raw).hexdigest(),
      PC_controllers={q:sum(n.startswith('ctl_'+q+'_p') for _,n in insts) for q in ['SW','SE','NW','NE']},
      service_groups=[n for _,n in insts if re.fullmatch(r'svg_[A-Z]{2}\d',n)],
      unprovided_packets=re.findall(r'input wire \[1098:0\] (svg_\w+__sm_packet);',text),
      source_to_role=[dict(source_group=f'svg_NW{p}',packet_port='sm_packet',
        cohort0_consumer='hb_idx__s_SW' if p<4 else 'hb_idx__s_SE',
        cohort1_consumer='hb_idx__s_NW' if p<4 else 'hb_idx__s_NE',
        consumer_port='key_lines',lane=p,tag_base=128*p) for p in range(8)])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out',type=Path);ap.add_argument('--top',type=Path)
    ap.add_argument('--relay-cycles',type=int,default=0)
    ap.add_argument('--service-bytes-per-edge',type=float)
    ap.add_argument('--service-latency-edges',type=int)
    a=ap.parse_args()
    result=dict(cases={str(s):model(slots=s,relay_cycles=a.relay_cycles,
      service_bytes_per_edge=a.service_bytes_per_edge,service_latency_edges=a.service_latency_edges) for s in [1,4,8]})
    if a.top:result['native_source']=census(a.top)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    for k,m in result['cases'].items():
        print(k,'slots',m['schedule']['transport_edges'],'transportedges',m['boundary']['total_forward_tracks'],'tracks',m['latency'])

if __name__=='__main__':main()
