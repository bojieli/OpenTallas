#!/usr/bin/env python3
"""Price packed KV on a maskless 32B service. No hardware timing qualification.

Loaded read/write assumptions are explicit. Existing U uses 500ns loaded read;
500ns write-visible is a separate conservative sizing assumption, not a source
measurement. Every read, merge, write, visible ACK and reverse CDC is charged.
"""
import math


def lock_calendar(read_ns=500,write_visible_ns=500):
    tick=0;events=[]
    phases=[('acquire_sector_lock',1,3),('read_request_fabric',53,3),('read_command_shared_stack',1,3),
            ('loaded_DRAM_read',math.ceil(read_ns*1.2),3),('read_return_fabric',53,3),
            ('return_CDC',8,3),('return_phase_margin',2,3),('import_old_sector_RF',2,4),
            ('merge_XOR_old_new',9,4),('merge_AND_byte_mask',9,4),('merge_XOR_old_masked_delta',9,4),
            ('store_issue',1,4),('write_request_fabric',53,3),('write_command_shared_stack',1,3),
            ('loaded_DRAM_write_visible',math.ceil(write_visible_ns*1.2),3),
            ('write_visible_ACK_fabric',53,3),('reverse_ACK_CDC',8,3),('reverse_phase_margin',2,3),
            ('release_lock_after_visible_ACK',1,3)]
    for name,cycles,q in phases:
        start=math.ceil(tick/q)*q;tick=start+cycles*q
        events.append(dict(phase=name,start_tick=start,end_tick=tick,cycle_ticks=q,cycles=cycles))
    return dict(candidate_only=True,common_tick_hz=3600000000,events=events,
                total_ticks=tick,elapsed_ns=tick/3.6,fast_cycle_equivalent=tick/3,
                read_loaded_ns_ASSUMED=read_ns,write_visible_loaded_ns_ASSUMED=write_visible_ns,
                INT_XOR_AND_binding='Nine serial cycles each is a sizing hypothesis from canonical INT class; bitwise exact implementation/area/timing remains unbound.',
                no_acceptance_as_completion=True,hardware_qualified=False)


def price(demands):
    rows=[]
    for d in demands:
        k=d['kinds']['K'];v=d['kinds']['V'];partial=[a+b for a,b in zip(k['partial_sector_writes_by_stack'],v['partial_sector_writes_by_stack'])]
        writes=[sum(x) for x in zip(k['partial_sector_writes_by_stack'],k['full_sector_writes_by_stack'],v['partial_sector_writes_by_stack'],v['full_sector_writes_by_stack'])]
        command=[r+w for r,w in zip(partial,writes)]
        rows.append(dict(graph_op=d['id'],layer=d['layer'],die=d['die'],position=d['position'],
                         produced_bytes=k['produced_payload_bytes']+v['produced_payload_bytes'],
                         locked_RMW_reads_by_stack=partial,full_sector_writes_by_stack=writes,
                         mixed_read_write_commands_by_stack=command,
                         port_payload_bytes=32*sum(command),
                         write_visible_ACKs=sum(writes),lock_release_after_ACKs=sum(partial),
                         minimum_shared_stack_command_cycles=max(command),
                         sector_merge_warp32_invocations=sum(partial),
                         merge_two_source_integer_warp_instructions=3*sum(partial),
                         merge_active_word_lanes_per_sector=8,
                         merge_RF_operand_bits=3*sum(partial)*8*2*32,
                         merge_RF_write_bits=3*sum(partial)*8*32,
                         masks=k['distinct_byte_masks'],
                         publication='All K/V addressed sector WRvisible ACKs and reverse CDC completed before publication. No accepted/queued-write completion credit.',
                         physical_admission=False))
    return dict(schema='opentallas.w13.packed-KV-locked-RMW.v1',rows=rows,
                mixed_command_policy='At most one shared read OR write command per stack per fast cycle; competing weights/KV/scales reduce available slots.',
                total_port_payload_bytes=sum(r['port_payload_bytes'] for r in rows),
                total_mixed_commands=sum(sum(r['mixed_read_write_commands_by_stack']) for r in rows),
                total_write_visible_ACKs=sum(r['write_visible_ACKs'] for r in rows),
                sector_lock_timing_template=lock_calendar(),
                candidate64_lock_contexts=dict(contexts_per_quad=16,quads=4,bits_per_context=675,
                    fields='old256/new256/mask32/address34/tag64/epoch16/lock1/state16',
                    conservative_added_DFF_footprint_mm2=64*675*.2916/.5/1e6,
                    allocation='Charge once outside RF if implemented there; RF reuse needs explicit liveness proof, not free subtraction.'),
                token_major_alternative='Not selected. Must price score gather/transpose, sharedbank conflicts, extra NoC traffic and exact context/address recipe before any model benefit.',
                physical_build_ready=False,hardware_adopted=False,token_cycles=None,speed_credit=0,
                missing=['actual physical controller timing/loaded queues/turnarounds/refill/refresh',
                         'sector lock ownership, epochs, conflicting readers/writers and safe release',
                         'canonical XOR/AND and FP8 producer implementation/area/contextualSSFF',
                         'SM/client/PC assignment plus wholeprogram mixed command calendar',
                         'actual WRvisible+reverseCDC and publication/reader generation gates'])
