#!/usr/bin/env python3
"""Pin the selected collective hierarchy and preserve unqualified PARK requirements."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('rtl/hbm_accel/generic/collective/p2p')
PARENTS = ['ot_hfd_coll_q_static.sv'] + [f'ot_hfd_coll_q_static_v{v}.sv' for v in (2, 3, 4)]
REQUIRED = ['ot_hgi_coll_static_issuer', 'ot_hgi_coll_qslots', 'ot_hgi_coll_pring_static',
            'ot_hgi_coll_static_vmwrite', 'ot_hgi_coll_tkm_static']
SUCCESSORS = [
    dict(function='Input landing and fixed inter-die forwarding retention',
         actual_modules=['ot_hgi_coll_static_link_capture', 'ot_hgi_coll_static_pinreg_store'],
         capacity='64 replay slots per rail; four actual 64x512 SRAM macros per rail',
         owner='/root/h_collective/static_link_sequence',
         evidence='results/arch/hcoll_fec_endpoint_1015/receipt.json',
         next_gate='Actual core/FEC/PHY512 clock crossings and native selected transport; physical controller/store child views and pin reach',
         qualified=False),
    dict(function='Scheduled landing and fanout between local clients',
         actual_modules=['ot_hgi_coll_qslots'],
         capacity='One captured flit per source and registered sink; no implicit 512-flit elastic queue',
         owner='/root/h_collective',
         evidence='results/arch/hbm_p2p_1014/q_static_v2_1015/receipt.json',
         next_gate='Actual selected producer/consumer joins, per-child physical views, production throughput',
         qualified=False),
    dict(function='Partial-vector retention for exact group reductions',
         actual_modules=['ot_hgi_coll_reduce_static'],
         capacity='16 tags across 16 FP32 lanes, with explicit load/read/add/publication reservations',
         owner='/root/h_collective/static_ring',
         evidence='results/arch/hcoll_g96_calendar_1015/bridge/local_retime/independent_audit.json',
         next_gate='Real control-program storage, final transport/relay calendar and actual native operation',
         qualified=False),
    dict(function='TOPK candidate and output retention',
         actual_modules=['ot_hgi_coll_tkm_static'],
         capacity='32 native PT64 tiles plus two actual staging SRAM buffers; full shape depends on n/k/group',
         owner='/root/publisher',
         evidence='results/arch/hbm_p2p_1014/idx_tkm_join_1015/receipt.json',
         next_gate='Reuse preserved KMAX2048 build to execute actual INDEX producer through native TKM and output commits',
         qualified=False),
    dict(function='Final addressed vector retention',
         actual_modules=['ot_hgi_coll_static_vmwrite'],
         capacity='Eight actual VM sector banks; 24 native SRAM macros in the proved selected VM composition',
         owner='/root/h_vm',
         evidence='results/arch/hbm_p2p_1014/native_vm_1015',
         next_gate='Actual distributed placement/calendar and final consumer visibility',
         qualified=False),
    dict(function='SU-delivered output storage and later operand production',
         actual_modules=[], capacity='Actual native SU store/producer ABI remains a separate required join',
         owner='/root/h_elements_b', evidence=None,
         next_gate='Connect actual native SU result storage and source generation; declared INJLAT12 stimulus is insufficient',
         qualified=False),
]

def audit():
    parents = {}
    for name in PARENTS:
        path = BASE / name
        source = (ROOT / path).read_text()
        # A lexical absence is stronger than choosing a particular generate arm:
        # none of the selected versioned files can instantiate a PARK master.
        assert 'ot_hgi_coll_park' not in source, f'Historical PARK reference in {path}'
        for module in REQUIRED:
            assert module in source, f'Missing actual selected child {module} in {path}'
        parents[str(path)] = dict(sha256=hashlib.sha256(source.encode()).hexdigest(),
                                 historical_PARK_reference_count=0)
    v4 = (ROOT / BASE / PARENTS[-1]).read_text()
    for module in ('ot_hgi_coll_static_link_capture', 'ot_hgi_coll_reduce_static'):
        assert module in v4, f'Missing V4 successor {module}'
    return dict(schema='opentallas.hcoll.selected-storage-successors.v1',
                status='Selected hierarchy source proof only; logical PARK storage requirement remains OPEN',
                parent_sources=parents,
                historical=dict(module='ot_hgi_coll_park_q1', closed_record='f6b4ec71b',
                                native_pop_capture_ps=192.1, capture_limit_ps=190,
                                action='Preserve CLOSED history and failed native audit; do not reroute unused selected-hierarchy master'),
                successors=SUCCESSORS,
                qualification='No logical requirement is retired until the connected production successor passes exactness, physical and throughput gates')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('STORAGE_SUCCESSOR_SOURCE PASS parents4 historical_PARK_refs0 logical_requirement_OPEN')

if __name__ == '__main__':
    main()
