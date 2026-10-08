#!/usr/bin/env python3
"""Finite mutable-control protection inventory for the proposed NC1 HBROM tile.

This prices a new fail-stop dual-control wrapper, not existing unprotected RTL.
No ROM payload protection is introduced. Array SRAM payload ECC is priced by
hbrom_protection_model. All widths/counts here are explicit design obligations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def checked_equal(a: int, b: int, width: int) -> bool:
    """Both replicas must be in range and equal; no truncation before comparison."""
    if width < 1:
        raise ValueError('width must be positive')
    return 0 <= a < (1 << width) and 0 <= b < (1 << width) and a == b


def commit_allowed(state_a, state_b, command_a, command_b, *, width, poisoned=False):
    """Reference fail-stop decision; a prior fault cannot clear on equality."""
    return (not poisoned and checked_equal(state_a, state_b, width)
            and checked_equal(command_a, command_b, width))


def build(*, ring_depth=1024, max_out=512, network_latency=17, rows=4096,
          descriptor_depth=8, activation_words=128, activation_beats=2):
    for name, value in locals().copy().items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f'{name} must be positive integer')
    if ring_depth & (ring_depth-1) or descriptor_depth & (descriptor_depth-1):
        raise ValueError('ring and descriptor depths must be powers of two')
    if max_out > ring_depth:
        raise ValueError('max_out exceeds ring capacity')
    tw = (ring_depth-1).bit_length()
    dw = (descriptor_depth-1).bit_length()
    rw = max(1, (rows-1).bit_length())
    nc = 1
    # Every independently protected entry has its own compare. Large bitmaps
    # use bit-local comparison, never a global combinational bitmap reduction.
    inv = []
    def add(name, count, width, purpose):
        inv.append(dict(name=name, entries=count, bits_per_entry=width,
                        raw_bits=count*width, purpose=purpose))
    add('operation_descriptor_queue', descriptor_depth, 512, 'Complete descriptor, including identity, extents, formats, dependency mask')
    add('active_and_lookahead_descriptor', 2, 512, 'One active and one prepared descriptor; immutable while outstanding')
    add('descriptor_pointers_and_count', 2, max(1,dw), 'Read and write pointers')
    add('descriptor_count', 1, dw+1, 'Full/empty discrimination')
    add('transaction_epoch_and_operation_sequence', 2, 32, 'No reuse or wrap until quiescence')
    add('ring_allocated_bits', ring_depth, 1, 'Additional allocation authorization; native full bitmap belongs to inner_control_plan')
    add('ring_slot_identity', ring_depth, 64, 'Epoch32 and operation sequence32 bound at allocation')
    add('active_line_address_and_remaining', 1, 56, '32-bit address plus 24-bit remaining lines')
    add('activation_write_valid_bits', activation_words*activation_beats, 1, 'One existing NC1 context; every independently written 2048-bit beat has valid state')
    add('activation_slot_owner', 1, 3+64+16+16, 'State, identity, extent, accepted-beat count')
    add('scale_slot_owner', 2, 3+64+16+16, 'Separate ownership for non-inline scale material; inline scales remain weight data')
    add('output_valid_and_reserved_bits', rows, 2, 'Reserve all rows before unbackpressured sm_v launch')
    add('output_slot_identity', 1, 64, 'Entire row array leased to one operation; no next owner until full retirement')
    add('output_write_read_count', 3, rw+1, 'Writes, consumer cursor and count; row range checked')
    add('completion_records', descriptor_depth, 128, 'Epoch, operation, status, output count and retirement metadata')
    add('completion_reserved_valid_bits', descriptor_depth, 2, 'Completion capacity reserved at admission')
    add('completion_pointers', 2, max(1,dw), 'Read and write pointers')
    add('completion_occupancy_reservations', 2, dw+1, 'Queued plus reserved completions')
    # Carried beside real payload, not inferred from current active descriptor.
    tag_width = 64+tw+2  # operation identity, slot and valid/poison
    add('rom_feed_request_response_identity', network_latency+2, tag_width, 'All irreversible-read pipeline stages plus two seal stages')
    add('codec_weight_identity', 4, tag_width, 'Two SRAM encode and two decode stages')
    add('result_identity_pipeline', 2, 64+rw+2, 'Two output boundary stages; row and validity remain protected')
    add('owner_control_flags', 32, 1, 'Admission, active, draining, cancel, fault and sticky publication controls')
    add('rom_address_walk_counters', 4, 32, 'Four bank stripes, independent address progression')
    add('rom_feed_config_image', 1, 16+13+8+2+1+32+32+32, 'Feed epoch16, rows13, groups8, fmt2, gs1 and physicalbase/region/virtualbase32')
    add('rom_feed_slot_bases', 8, 32, 'Eight IL slot base addresses checked before read')
    add('rom_feed_live_tag_bitmap', ring_depth, 1, 'Reject unallocated or duplicate incoming tag')
    add('sm_operation_image', 2, (rw+1)+16+8+1+2, 'Duplicate checked launch envelopes before two PIO stages')
    for r in inv:
        # DMR protects stored state. A separate command envelope is checked
        # against both independently generated commands before commit.
        r['protected_storage_bits'] = 2*r['raw_bits']
        r['compare_xor2_count'] = r['raw_bits']
        r['compare_or2_count'] = r['entries']*max(0,r['bits_per_entry']-1)
    raw = sum(r['raw_bits'] for r in inv)
    xors = sum(r['compare_xor2_count'] for r in inv)
    ors = sum(r['compare_or2_count'] for r in inv)
    seals = sum(r['entries']*math.ceil(r['bits_per_entry']/64) for r in inv)
    # Duplicated local seal bits; equality of seals is checked at destination.
    storage = 2*raw + 2*seals
    dff = .2916
    gate = .3
    flop_area = storage*dff/1e6
    logic_area = (xors+ors+2*seals)*gate/1e6
    paths=['rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
           'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv',
           'rtl/abi3/ot_a3_operand_bank_owner.sv',
           'results/floorplan/qwen_o4_unit_areas.json']
    return dict(schema='opentallas.hbrom.control-plan.v1',
        status='PRICED_PROPOSAL_NOT_IMPLEMENTED_OR_TIMING_QUALIFIED',
        shape=dict(NC=nc,ring_depth=ring_depth,max_out=max_out,network_latency=network_latency,
                   rows=rows,descriptor_depth=descriptor_depth,activation_words=activation_words,
                   activation_beats=activation_beats, activation_contexts=1),
        inventory=inv,
        protection=dict(scheme='Dual modular redundant mutable control, independent next-state cones and fail-stop command comparison',
          correction='None. A mismatch poisons the operation; no output may be published, retire outstanding reads then require software recovery/reset.',
          covered_fault_model='Any single stored control bit flip in either replica; single divergence of one independently generated command. Common-mode or equal changes in both replicas are outside DMR guarantee.',
          compare='Every state entry read is compared locally; commands, including enable/address/slot/epoch, are independently generated and checked before irreversible side effect. Large maps compare addressed bits, not full-map reduction.',
          seal='512-bit descriptor comparison split into eight64-bit groups, registered local partial seals then registered final decision. No state mutation of sealed descriptor until release. Mutable fast command checks run at every side effect and cannot rely on an old descriptor seal.',
          sticky_fault='Duplicated fail-stop latch; disagreement itself denies permission. Reset clears fault only at externally established quiescence.',
          no_rom_ecc=True,
          payload='SRAM payload ECC and result data ECC are separate protection_plan costs; this file protects metadata only.'),
        cycles=dict(descriptor_admission_extra=2,rom_issue_extra=1,
                    response_commit_extra=1,activation_publish_extra=1,
                    output_publish_extra=1,completion_extra=1,
                    peak_lines_per_cycle=1,
                    protected_credit_depth_min=2*(network_latency+2)+2,
                    note='Pipeline latency allowance, not measured timing. Counter reservation occurs before command-check stage; pipeline slots count against credits. Guard checks must accept one per cycle. Existing timing must add these stages explicitly.'),
        area=dict(raw_state_bits=raw,duplicated_raw_bits=2*raw,seal_bits=2*seals,
                  protected_state_bits=storage,xor2_count=xors,or2_count=ors,
                  dff_um2=dff,gate_allowance_um2=gate,
                  storage_cell_mm2=flop_area,compare_logic_allowance_mm2=logic_area,
                  packed_total_allowance_mm2=2*(flop_area+logic_area),
                  packed_increment_over_unprotected_mm2=2*(flop_area+logic_area-raw*dff/1e6),
                  basis='DFF area existing floorplan coefficient; logic .3um2/gate explicit allowance. 50% utilization. Independent NEXT-STATE arithmetic cones, CTS, hold fixing and compare distribution require synthesis; not a bound or signoff claim.'),
        scope=dict(included='New descriptor-owner, ROM feed, ring metadata, activation validity, result and completion wrapper state at full NC1 shape.',
                   native_bulk_accounting='Native full1024 + alloc/cons/used33 + outstanding10 =1067 overlapping bits excluded here. Complete1949bit native control inventory and DMR accounted in inner_control_plan; slot generation and separate allocated bits remain outer-only.',
                   additional_required='Existing sm_v internal arithmetic pipeline tags, issuer/stack counters and bulk-copy retiming duplicates need independent control-cone inventory and protection integration before claiming full-tile protection. Existing duplicate fanout registers are NOT DMR without independent next-state cones and compare.',
                   template='Immutable descriptor templates are ROM: no ECC required. Mutable fetched copies appear in inventory. Template address/bounds controlled by protected descriptor state.'),
        mandatory_checks=['Exhaustive single-bit mutation of protected descriptors, epochs, pointers and validity bits denies unauthorized commits.',
                          'Late response carries allocated slot generation and cannot publish into next operation.',
                          'Fault during request-check pipeline cannot issue unchecked read.',
                          'No result leak on control mismatch; irrevocable old reads drain without freeing active lease.',
                          'Full contextual SS60ps/FF25ps measurement of added guard stages and duplicated fanout.'],
        sources_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='results/uarch/hbrom/control_plan.json')
    p.add_argument('--network-latency',type=int,default=17)
    a=p.parse_args()
    out=ROOT/a.output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(build(network_latency=a.network_latency),indent=2)+'\n')

if __name__=='__main__':
    main()
