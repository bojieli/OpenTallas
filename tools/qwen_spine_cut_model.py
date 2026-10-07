#!/usr/bin/env python3
"""Source-pinned Qwen tree boundary contract, before any physical replacement.

The spatial proposal preserves all held positions, including inactive positions;
transport serialization is an alternative requiring its own finite-flow RTL.
Neither is an adopted route or a headline performance measurement.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def model():
    gt, tcut, smin, lanes, ta = 6144, 7, 7, 16, 3
    lg = (gt - 1).bit_length()
    words = gt >> tcut
    positions = gt >> smin
    levels = []
    for lv in range(tcut + 1, lg):
        pairs = gt >> lv
        levels.append(dict(level=lv, pairs=pairs, preserved_positions=positions,
            sum_pairs=[[2*p, 2*p+1] for p in range(pairs)],
            sum_destination=list(range(pairs)),
            held_destination=list(range(positions)),
            select_rule='sel[level] ? pair_sum : held[position]; positions >= pairs always hold',
            cycles=ta+1))
    sources = ['rtl/hdc/ot_qwen_me_spine_h_w12.sv',
               'tools/qwen_rom_fulldie.py', 'tools/qwen_rom_fulldie_b3r2.py',
               'results/floorplan/qwen_o4_unit_areas.json']
    hashes = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    adds = sum(x['pairs'] for x in levels)
    # TA-cycle hold plus each level's destination register and initial capture.
    ff_bits = positions*32*(len(levels)*(ta+1)+1)
    units = json.loads((ROOT/sources[-1]).read_text())
    fadd = next(u['area_um2'] for u in units['units'] if u['module']=='ot_hdc_fadd')
    proxy = adds*fadd + ff_bits*units['dff_bit_um2']
    # This is an area proxy, not a claim that a LAT3 add closes at 1.2 GHz.
    pitch = 0.064
    lane_width = 600
    channel_width = 160
    tracks = int(channel_width/pitch)*2
    return dict(schema='opentallas.qwen-spine-cut-contract.v1', source_sha256=hashes,
        adoption=False, physical_closed=False,
        contract=dict(GT=gt, TCUT=tcut, SMIN=smin, W=lanes, TREE_LAT=ta,
            input_words_per_lane=words, output_words_per_lane=positions,
            data_bits_per_side=words*lanes*32, levels=levels,
            output_active_positions_by_split={str(s):gt >> s for s in range(smin,lg+1)},
            golden='Adjacent pairs in original position order, original RNE primitive; never mix lanes'),
        existing_die_cut=dict(band_inputs=6, bits_per_band=512, output_bits=512,
            input_bits_per_cycle=6*512, output_bits_per_cycle=512,
            input_width_matches=False, output_width_matches=False,
            serialization_min_input_beats=words//6,
            serialization_output_beats_by_split={str(s):gt >> s for s in range(smin,lg+1)},
            preserves_all_output_positions_beats=positions,
            rejection='No packing, transaction identity, finite buffering or schedule proves these narrower ports equivalent'),
        spatial_candidate=dict(master='ot_qwen_me_sptree_w12', replicas=lanes,
            MACs_per_cycle=0, FP32_adds_per_cycle_per_replica=adds,
            communication_bytes_per_cycle_per_replica=dict(input=words*4,output=positions*4),
            boundary_bits_per_cycle_per_replica=dict(input=words*32,output=positions*32,select=lg+1,valid=lg+1,fault=1),
            intensity=dict(FP32_adds_per_input_byte=adds/(words*4),MACs_per_input_byte=0),
            memory_ports={},
            mux_demux=dict(select_mux_bits_per_replica=adds*32,hold_mux_inputs=2,output_demux='Static lane-to-group transpose; no arithmetic'),
            fanout=dict(max_select_loads=levels[0]['pairs']*32,
                requirement='Kept local copies per <=4 positions; original single select register is not closure ready'),
            area=dict(proxy_cell_um2_per_replica=round(proxy,3),hold_and_output_FF_bits_per_replica=ff_bits,
                proxy_method='Historical TT fadd area plus exact hold/output flops; excludes adder pipeline and CTS/repair',
                width_um=lane_width,height_um=lane_width,utilization_proxy=round(proxy/lane_width**2,4),
                total_reserved_mm2=lanes*(lane_width/1000)**2,
                fits_1mm_rule=True,parent_slot_fit=False,
                parent_slot_reason='16 independently placed lane masters and full-width group/lane transpose need regenerated die geometry'),
            routing=dict(tracks_per_lane_boundary=words*32,channel_width_um=channel_width,
                assumed_two_layer_pitch_um=pitch,track_capacity=tracks,
                reserved_signal_fraction=0.6,fits_channel=words*32 <= tracks*0.6,
                die_routing_layer_check='PENDING; local capacity arithmetic is not a hub routing-layer pass'),
            latency=dict(existing_tree_cycles=1+len(levels)*(ta+1),
                proposed_extra_capture_cycles_per_level=1,
                conservative_extra_cycles_per_tree_transaction=len(levels),
                extra_ns_per_tree_transaction_at_1p2GHz=len(levels)/1.2,
                token_added_cycles_formula='5 * number_of_exposed_tree_transactions_per_token',
                token_transaction_count=None,
                composed_single_user_token_status='BLOCKED: calendar needs exact transaction count and transport mapping',
                clock_status='LAT3 arithmetic at streaming clock unproven; serial-domain or deeper pipeline must be separately priced')),
        deferred_composites=dict(
            vector_memory='Need actual protected SRAM port/shape inventory and registered slice crossings; no generic register-memory substitution',
            su64_sfu='Preserve lane-local fusion and serial feedback within each hardened lane group; price split transport',
            constants_sequencer='Keep closed core as reused view; price ROM bank/descriptor and VP sequencer cuts independently'),
        next_build_gate=['Exact geometry maps every group/lane word',
            'Unified calendar composes added latency before RTL construction',
            'RTL lint launches calibrated closure immediately; exact and negative benches gate adoption',
            'True SS/FF +15/+15 ps with input150ps, output80fF, DRC0 and die-context validation'])


def check_contract(record):
    c = record['contract']
    assert c['input_words_per_lane'] == 48 and c['output_words_per_lane'] == 48
    assert [x['pairs'] for x in c['levels']] == [24,12,6,3,1]
    assert c['data_bits_per_side'] == 24576
    for level in c['levels']:
        assert level['sum_pairs'] == [[2*p,2*p+1] for p in range(level['pairs'])]
        assert level['held_destination'] == list(range(48))
    assert not record['existing_die_cut']['input_width_matches']
    assert not record['existing_die_cut']['output_width_matches']
    assert not record['adoption']


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path)
    p.add_argument('--negative-control', action='store_true')
    a = p.parse_args()
    result = model()
    if a.negative_control:
        result['contract']['levels'][0]['sum_pairs'][0] = [0,2]
    check_contract(result)
    payload = json.dumps(result, indent=2)+'\n'
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(payload)
    else:
        print(payload,end='')
