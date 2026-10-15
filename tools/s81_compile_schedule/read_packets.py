"""Compile immutable native-port return permutations for fixed VM read edges.

Packet positions follow the actual four-lane scatter wiring. Original client
ports and event identities survive the permutation. Bank conflicts are reported
without delaying reads or assuming a wider SRAM port.
"""
from collections import defaultdict
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
from static_vm_reservations import bank_of


def compile_packets(requests,bank_mapping='xor_row7_5_shift2',return_cycles=10):
    grouped=defaultdict(list)
    for event in requests['events']:
        if event['kind']=='read':grouped[event['issue_cycle']].append(event)
    packets=[];violations=[]
    for cycle,events in sorted(grouped.items()):
        used=set();rows=[];banks=defaultdict(list)
        for event in sorted(events,key=lambda e:(e['client'],e['slot'],e['id'])):
            client,port=event['client'],event['slot']
            if client=='su' and 0<=port<16:
                candidates=[lane for lane in range(16) if lane%4==event['row']%4]
                if port in candidates:candidates=[port]+[x for x in candidates if x!=port]
            elif client=='hc' and 0<=port<2:
                candidates=[16+event['row']%4,20+event['row']%4]
            else:
                violations.append(dict(kind='unbound_native_read_port',event=event['id']));continue
            free=[lane for lane in candidates if lane not in used]
            if not free:
                violations.append(dict(kind='insufficient_read_return_lane',event=event['id'],issue_cycle=cycle));continue
            lane=free[0];used.add(lane)
            packet_slot=8*(lane%4)+lane//4
            bank=bank_of(event['row'],dict(banks=32,bank_mapping=bank_mapping));banks[bank].append(event['id'])
            rows.append(dict(id=event['id'],row=event['row'],source_client=client,source_port=port,
                             job=event['job'],tag=event['tag'],logical_return_slot=lane,
                             scatter_packet_slot=packet_slot))
        for bank,ids in banks.items():
            if len(ids)>1:
                violations.append(dict(kind='fixed_read_bank_conflict',issue_cycle=cycle,bank=bank,events=ids))
        packets.append(dict(issue_cycle=cycle,release_cycle=cycle+return_cycles,release_group=cycle%8,
                            release_mask=sum(1<<lane for lane in used),rows=rows))
    expected=[e['id'] for e in requests['events'] if e['kind']=='read']
    actual=[r['id'] for p in packets for r in p['rows']]
    if len(actual)!=len(set(actual)) or sorted(expected)!=sorted(actual):
        violations.append(dict(kind='read_identity_coverage'))
    return dict(status='OBSERVED_DEMAND_PACKET_MAP_ONLY',packets=packets,violations=violations,
                reads=len(expected),issue_edges=len(packets),bank_mapping=bank_mapping,
                return_cycles=return_cycles,dispatch_eligible=False,qualified=False,
                note='No read is postponed. Production allocation, source-pinned native timeline and physical service must replace observed fixture demand.')
