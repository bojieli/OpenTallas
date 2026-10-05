"""Bounded TP96 collective-round sizing using the unified HBM model.

No generator or product rate is changed. Testbench credit admission is explicit,
not a new dispatch/router implementation or physical qualification.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import uarch_model as M

ROOT = Path(__file__).resolve().parents[1]

def preflight():
    economics = json.loads((ROOT / 'results/uarch/economics.json').read_text())
    rows = json.loads((ROOT / 'results/uarch/economics_levers.json').read_text())['gated_alike']
    if isinstance(rows, dict):
        rows = rows['rows']
    hbm = M.v41_hbm_n(96, 4, economics, rows, clock_hz=1.2e9)
    ranks, packages, lanes, depth = 96, 48, 16, 128
    word_bytes, record_bits = lanes * 4, lanes * 32 + 34
    serial_ns, streaming_ns = 1e9 / 9e8, .833
    levels = math.ceil(math.log2(packages))
    # One word is admitted only with space reserved for every multicast copy.
    # Credit is returned after the last of 96 endpoint consumers accepts it.
    # A gather word generates 96 output records; an AR word generates one.
    switch_pipeline = 200
    wire = 16
    link_upper_ns = 2 * (wire * serial_ns + 2 * streaming_ns + 250 + 32 * serial_ns)
    package_ns = 2 * (wire * serial_ns + 16 * serial_ns + 4)
    round_ns = link_upper_ns + package_ns + (2 + 3 * levels + switch_pipeline) * serial_ns
    cases = []
    for name, mode, words, payload in [('w19_oreduce', 0, 512, 32768),
                                      ('expert_intermediate', 1, 5, 288),
                                      ('index_candidates', 1, 64, 4096)]:
        outputs = ranks if mode else 1
        cycles = math.ceil(words * (round_ns / serial_ns + outputs + 64))
        cases.append(dict(name=name, mode=mode, words_per_rank=words, payload_bytes_per_rank=payload,
                          physical_bytes_per_rank=words * word_bytes, records_per_endpoint=words * outputs,
                          endpoint_credit_reservation=outputs, composed_serial_cycles_upper_bound=cycles,
                          composed_ns_upper_bound=cycles * serial_ns,
                          basis='serial word admission, two external+two package hops, LAT3 package/tree, 200-stage switch, 64-cycle consumer stall allowance; measured cycles replace this bound only at this scope'))
    tracks = record_bits * 2
    capacity = 4 * int(64 / .08)
    source_paths = ['tools/uarch_model.py','tools/w15_collectives.py','tools/w19_hbm_tp96_isa.py',
                    'tools/hdc_golden.py','results/floorplan/hbm_gpu/v41_hbm_die.json',
                    'results/uarch/economics.json','results/uarch/economics_levers.json']
    return dict(schema='w15_tp96_collective_preflight_v1', admission='functional_RTL_round_only',
                model_call='v41_hbm_n(96, 4, economics, gated_alike, clock_hz=1.2e9)',
                model_shape={k:hbm.get(k) for k in ['dies','stacks_per_die','sm_per_die','capacity_users_1m']},
                ranks=ranks, packages=packages, lanes=lanes, macs_per_cycle=0,
                fp32_adds_per_serial_cycle=(packages + packages - 1) * lanes,
                arithmetic='LAT3 binary32 RNE; package adjacent-pair, fixed pairwise package tree; W19 8-rank aligned subtrees, zero on inactive ranks; BF16 boundary checked separately by golden',
                clocks=dict(serial_ns=serial_ns, streaming_ns=streaming_ns, setup_uncertainty_ps=60, hold_uncertainty_ps=25),
                ports_Bpc=dict(endpoint_read=word_bytes, endpoint_write=word_bytes, switch_per_port=word_bytes),
                boundaries_bits_pc=dict(endpoint=record_bits, multicast_aggregate=packages * record_bits),
                replicas=dict(endpoints=ranks, package_adders=packages * lanes, switch_adders=(packages-1)*lanes,
                              actual_link_tx=4*packages, actual_link_rx=4*packages),
                finite_buffers=dict(endpoint_records=depth, switch_records_per_port=512, tx_entries=8,
                                    rx_entries=64, package_queue_records=64, multicast_landing_records=128, forwarding_records=128,
                                    endpoint_storage_bits=ranks * depth * record_bits),
                mux_demux_fanout=dict(multicast_fanout=packages, endpoint_fanout=2, gather_mux_inputs=packages,
                                     gather_mux_bit_equivalents=(packages-1)*record_bits),
                routing=dict(tracks_per_local_duplex_boundary=tracks, capacity_tracks=capacity,
                             analytical_fit=tracks<=capacity, basis='ASSUMED 64um /80nm pitch, four layers; actual hub routing-layer acceptance pending'),
                area=dict(endpoint_fifo_dff_mm2=ranks*depth*record_bits*M.DFF_UM2/1e6,
                          basis='pessimistic DFF accounting for bounded testbench landing FIFOs; hardware macro/slot fit pending; no new engine implementation'),
                cases=cases, defaults_unchanged=True,
                scope='All 96 RTL endpoints, actual bytes; endpoint credit reservation is harness admission, not implemented rank runtime. No switch bandwidth slot compression.',
                excluded_claims=['full-token RTL','product rate','hardware adoption','SS/FF contextual closure'],
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths})

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=preflight();args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.out.exists():raise SystemExit('refuse to overwrite preflight')
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('TP96_PREFLIGHT_PASS',result['ranks'],result['routing']['analytical_fit'])
