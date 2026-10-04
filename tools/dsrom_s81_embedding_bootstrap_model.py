"""S81 charged embedding storage and finite cold-bootstrap implementation ABI.

Metadata only. No checkpoint payload, golden stimulus, RTL, or timing claim.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/uarch/dsrom_s81_embedding_bootstrap_20261004/'


def word_address(token, beat):
    if type(token) is not int or not 0 <= token < 129280:
        raise ValueError('released vocabulary bound')
    if type(beat) is not int or not 0 <= beat < 320:
        raise ValueError('embedding word bound')
    word = token * 320 + beat
    gp, slot = divmod(word, 16384)
    die, pair = divmod(gp, 632)
    mb, logical = divmod(slot, 8192)
    side, row = logical % 2, logical // 2
    return dict(global_word=word, global_pair=gp, storage_home=die,
                local_pair=pair, mb=mb, side=side, physical_row=row,
                local_macro=4*pair+2*mb+side, global_macro=4*gp+2*mb+side)


def vm_commit(beat, copy, raw_bf16):
    """Direct bit widening only; source arithmetic remains in the actual SU."""
    word_address(0, beat)
    if type(copy) is not int or not 0 <= copy < 4:
        raise ValueError('four actual H copies')
    if len(raw_bf16) != 16 or any(type(x) is not int or not 0 <= x < 65536 for x in raw_bf16):
        raise ValueError('one actual packed BF16 word required')
    return dict(addresses=[copy*5120+beat*16+i for i in range(16)],
                fp32_bits=[x << 16 for x in raw_bf16])


def serial_price(*, rom_response_edges, delivery_edges, vm_beat_edges,
                 release_edges, ssx_edges, period_ps):
    """One outstanding word, no guessed overlap. Inputs must be source-bound.

    Delivery is the slowest rank receipt; commit is the slowest rank's four
    copy writes. release includes actual all-rank visibility acknowledgement.
    SSX includes the existing squared/tree reduction and publication fence.
    """
    costs = (rom_response_edges, delivery_edges, vm_beat_edges, release_edges, ssx_edges)
    if any(type(x) is not int or x <= 0 for x in costs) or period_ps <= 0:
        raise ValueError('positive actual response/delivery/commit/fence/SU costs required')
    edges = 320*(rom_response_edges+delivery_edges+4*vm_beat_edges+release_edges)+ssx_edges
    return dict(bootstrap_edges=edges, bootstrap_us=edges*period_ps/1e6,
                measured=False, zero_overlap_assumed=True)


def build(root=ROOT):
    inputs = root/(BASE+'inputs')
    manifest = json.loads((inputs/'source_manifest.json').read_text())
    for name, pin in manifest.items():
        if hashlib.sha256((inputs/name).read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('embedding source changed: '+name)
    inv = json.loads((inputs/'S81_inventory.json').read_text())
    layout = inv['dedicated_storage']
    embed = next(x for x in layout['global_tensors'] if x['tensor']=='embed.weight')
    desc = json.loads((inputs/'embedding_descriptor.json').read_text())
    if (embed['shape'] != [129280,5120] or embed['pairs'] != 2525 or
        embed['words'] != 41369600 or embed['pair_start'] != 0 or
        embed['secded_bits'] != 0 or inv['ROM_ECC'] != 0 or
        layout['head_storage_pairs_per_die_ceiling'] != 632 or layout['head_dies'] != 8 or
        desc['dtype'] != 'BF16' or desc['shape'] != embed['shape'] or
        desc['source_storage_bytes'] != 1323827200):
        raise ValueError('selected released S81 embedding reservation changed')
    stream = (inputs/'native_stream.sv').read_text()
    boot = (inputs/'source_bootstrap.py').read_text()
    if ('parameter integer WR = 64' not in stream or
        'wrom_re <= f1_v' not in stream or
        'red_sq=1, red_tree=1, r_base=V_["SSX"]' not in boot):
        raise ValueError('actual SU bootstrap semantics changed')
    macro = next(x for x in json.loads((inputs/'macro_depth.json').read_text())['rows']
                 if x['macro']=='ot_rom_4096x274_m8')
    cells=json.loads((inputs/'cell_bodies.json').read_text())
    lef=json.loads((inputs/'cell_LEF.json').read_text())
    for name, expected in [('DFFASRHQNx1_ASAP7_75t_R',.37908),('NAND2x1_ASAP7_75t_R',.08748)]:
        for corner in ('SS','FF'):
            area=float(re.search(r'area\s*:\s*([0-9.]+)',cells[corner][name])[1])
            size=re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',lef[name])
            if abs(area-expected)>1e-12 or abs(float(size[1])*float(size[2])-area)>1e-12:
                raise ValueError('primitive area/LEF mismatch')
    homes = [632,632,632,629]
    muxes = sum(4*n-1 for n in homes)
    held_bits = 274+17+9+16+3  # payload/token/beat/4rank*4copy bitmap/busy,response,reservation
    return dict(schema='opentallas.S81.embedding.bootstrap.v1',
        status='SOURCE_BOUND_IMPLEMENTATION_MODEL_NOT_NATIVE_READER_QUALIFICATION',
        descriptor=desc, checkpoint_provenance=json.loads((inputs/'header_capture.json').read_text()), source_manifest=manifest,
        storage=dict(global_pool_dies=8, global_pool_pairs=5051, pairs_per_die_ceiling=632,
            embedding_pairs=2525, embedding_macro_count=10100, rows_per_macro=4096,
            raw_carrier_bits=274, useful_word_bits=256, embedding_home_pairs=homes,
            existing_charged_macro_body_mm2=2525*31525.4592/1e6,
            new_macro_charge_mm2=0, padding_removal_credit_mm2=0,
            head_and_norm_reservations_unchanged=True, ROM_ECC_required=False),
        address=dict(token_bits=17, beat_bits=9, global_word_bits=26, local_pair_bits=10,
            global_pair_bits=12, storage_home_bits=3, row_bits=12, macro_selector_bits=2,
            formula='word=token*320+beat; gp,slot=divmod(word,16384); home,pair=divmod(gp,632); mb,logical=divmod(slot,8192); side=logical%2; row=logical//2',
            codec='16 consecutive BF16 values, not field bf_slot interleaving',
            row_may_cross_two_pairs_and_two_homes=True, last_word=word_address(129279,319)),
        transfer=dict(words_per_token=320, raw_bytes_per_token=10240,
            reader_MACs_per_cycle=0, actual_SU_reused_for_arithmetic=True,
            H_base=0, H_copies=4, H_FP32_words_per_rank=20480, H_bytes_per_rank=81920,
            TP_ranks=4, TP4_H_bytes=327680, VM_AW=19,
            proposed_existing_VM_lanes=16, VM_lane_port_binding_qualified=False,
            accepted_VM_beats_per_rank=1280, VM_bytes_per_accepted_edge_per_rank=64,
            single_port_ROM_bytes_per_accepted_macro_edge=32,
            word_deliveries_all_ranks=1280, remote_word_deliveries_from_owner=960,
            warm_retention_policy_unchanged=True,
            mandatory_before_PC0='All actual H VM writes visible on every rank; existing exact SU red_sq=1 red_tree=1 SSX result visible; source bootstrap retired. No expected H/SSX restore.',
            SU_WROM_WR_BF16=64, nonstallable_SU_WROM_adapter_qualified=False,
            admission='Freeze other VM writers; retain bootstrap owner and source/revision identity; reject token out of range and stale/duplicate responses without releasing matching debt.'),
        finite_reader=dict(proposed_outstanding_words=1, accepted_response_hold_seats=1,
            all_rank_copy_commit_bitmap_bits=16, base_state_bits_excluding_owner=held_bits,
            owner_identity_bits=None, total_state_bits=None,
            base_state_FF50_mm2=held_bits*.37908/.5/1e6,
            credit_release='Actual 16 rank/copy VM visibility completions, not enqueue/read response; reset cannot erase accepted debt.',
            request_boundary_bits_excluding_owner=17+9+2,
            response_boundary_bits_excluding_owner=274+9+2,
            selected_local_macro_address_bits=10+2+12,
            owner_source_version_layout_reset_generation_contract_required=True),
        routing=dict(storage_reader_replicas=4, destination_VM_replicas=4,
            embedding_macro_leaves_per_home=[4*n for n in homes],
            prospective_binary_selection_muxes=muxes, mux_bit_equivalents=muxes*274,
            constructive_3NAND2_per_bit_area_floor_mm2=muxes*274*3*.08748/1e6,
            select_inverter_decoder_fanout_buffer_pipeline_area_mm2=None,
            new_capture_route_area_not_in_macro_charge=True,
            max_binary_mux_levels=12, pipeline_cuts=None, owner_packet_bits=None,
            track_capacity=None, contextual_SS60_FF25=False, slot_fit=False),
        latency=dict(VM_service_edges_lower_bound_per_rank=1280,
            VM_service_us_lower_bound_at_1p2GHz=1280/1200,
            cold_bootstrap_added_token_us=None, SSX_source_latency_edges=None,
            price_API='serial_price: positive actual ROM, delivery, VM, release and SSX costs; source calendar may replace serial model only with qualified finite overlap',
            macro_SS_clk_to_q_ps=macro['clk_to_q_ps_ss'], capture_setup_ps=25,
            setup_uncertainty_ps=60,
            one_cycle_1p2GHz_route_skew_budget_ps=1000/1.2-macro['clk_to_q_ps_ss']-25-60,
            native_capture_mux_delivery_fence_measurement_required=True),
        area_proxy_cells=dict(DFFASRHQN_um2=.37908, NAND2_um2=.08748,
            cell_source='Pinned cell_bodies/LEF/config snapshots; positive proxy only, not mapped area.'),
        executable_entry='word_address(token,beat); vm_commit(beat,copy,actual_BF16_word); serial_price(actual source edge costs)',
        actual_payload_read=False, actual_reader_RTL_PASS=False, measured=False, adopted=False)


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify',action='store_true')
    args=ap.parse_args()
    text=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    path=ROOT/(BASE+'model.json')
    if args.verify:
        if path.read_text()!=text: raise ValueError('embedding model drift')
    else: path.write_text(text)
    print('PASS S81 embedding metadata, addressing and finite bootstrap sizing')
