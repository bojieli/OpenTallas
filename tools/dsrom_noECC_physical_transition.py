#!/usr/bin/env python3
"""Source-bound no-ECC macro geometry and complete-selector reservation join.

Extracts raw pin/OBS/PG rectangles. Does not generate RTL or qualify placement.
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_noECC_physical_transition_20261002'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def intersection(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))

def union_area(rects):
    xs = sorted({x for r in rects for x in (r[0], r[2])})
    area = 0
    for x0, x1 in zip(xs, xs[1:]):
        spans = sorted((r[1], r[3]) for r in rects if r[0] < x1 and r[2] > x0)
        end = None
        length = 0
        for lo, hi in spans:
            length += max(0, hi-max(lo, end if end is not None else lo))
            end = max(hi, end if end is not None else hi)
        area += (x1-x0)*length
    return area

def geometry(lef):
    width, height = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', lef).groups())
    pins = []
    for match in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$', lef, re.M | re.S):
        name, body = match.groups()
        use = re.search(r'USE (\w+)', body)[1]
        layer = None
        rectangles = []
        for line in body.splitlines():
            if 'LAYER ' in line:
                layer = re.search(r'LAYER (\w+)', line)[1]
            if 'RECT ' in line:
                rect = list(map(float, re.search(r'RECT (.*?) ;', line)[1].split()))
                rectangles.append(dict(layer=layer, rect_um=rect))
        pins.append(dict(name=name, use=use, rectangles=rectangles))
    obs = []
    layer = None
    for line in lef.split('  OBS\n', 1)[1].split('  END', 1)[0].splitlines():
        if 'LAYER ' in line:
            layer = re.search(r'LAYER (\w+)', line)[1]
        if 'RECT ' in line:
            obs.append(dict(layer=layer, rect_um=list(map(float, re.search(r'RECT (.*?) ;', line)[1].split()))))
    return dict(width_um=width, height_um=height, body_um2=width*height, pins=pins, OBS=obs)

def rectangles(value):
    if isinstance(value, dict):
        if 'bbox_DBU' in value:
            yield {k:value[k] for k in ('name', 'bbox_DBU', 'area_mm2')}
        for v in value.values():
            yield from rectangles(v)
    elif isinstance(value, list):
        for v in value:
            yield from rectangles(v)

def build():
    receipts = json.loads((BASE/'inputs/receipt.json').read_text())
    for r in receipts:
        if sha(BASE/'inputs'/r['copy']) != r['sha256']:
            raise ValueError('changed pinned input: '+r['copy'])
    source = (BASE/'inputs/element.sv').read_text()
    for clause in ('if (i2x_v && !i2x_bk) cap0 <= rd0;', 'assign i2_v = i3_v;', "wire cg_en = !rst_n || go || go_e || walk_busy || drain != 8'd0;"):
        if clause not in source:
            raise ValueError('capture/control source mismatch')
    g = geometry((BASE/'inputs/macro.lef').read_text())
    layers = sorted({r['layer'] for r in g['OBS']} | {r['layer'] for p in g['pins'] for r in p['rectangles']})
    exclusions = {}
    for layer in layers:
        obs = [r['rect_um'] for r in g['OBS'] if r['layer']==layer]
        pg = [r['rect_um'] for p in g['pins'] if p['use'] in ('POWER','GROUND') for r in p['rectangles'] if r['layer']==layer]
        exclusions[layer] = dict(OBS_union_um2=union_area(obs), PG_union_um2=union_area(pg), OBS_PG_union_um2=union_area(obs+pg),
            remaining_planar_area_um2=g['body_um2']-union_area(obs+pg),
            usable_tracks_proven=False, reason='Area is not track capacity; pin escape, vias, halo, clock routes and translated neighbours still require actual placement.')
    clocks = json.loads((BASE/'inputs/clock_pin_extract.json').read_text())['actual_clock_pin_loads']
    topk = json.loads((BASE/'inputs/topk.json').read_text())
    oldrects = list(rectangles(json.loads((BASE/'inputs/reticle.json').read_text())))
    slot = topk['slot_binding']['reservation']
    bounds = []
    for c in topk['slot_binding']['comparisons']:
        if c['runtime_n'] != 2048:
            continue
        box = slot['bbox_DBU']
        width_um = (box[2]-box[0])/1000
        required = c['retained_state_required_core_mm2_at_source_50pct']
        expanded = [box[0],box[1],box[2],box[1]+math.ceil(required*1e6/width_um*1000)]
        overlaps = [dict(name=r['name'], intersect_mm2=intersection(expanded,r['bbox_DBU'])/1e12) for r in oldrects if r['name']!=slot['name'] and intersection(expanded,r['bbox_DBU'])]
        shape = next(s for s in topk['shapes'] if s['kind']==c['kind'] and s['runtime']['n']==2048 and s['compiled']['N']==4)
        construction = shape['area']['accounted_construction_cell_um2']/1e6/.5
        fullbox = [box[0],box[1],box[2],box[1]+math.ceil(construction*1e6/width_um*1000)]
        bounds.append(dict(kind=c['kind'], state_only_mm2=required, missing_state_only_mm2=required-slot['area_mm2'],
            historical_same_width_expansion_bbox_DBU=expanded, displaced_rectangles=overlaps,
            named_source_construction=shape['area'],
            source_construction_core_proxy_mm2_at50pct=construction,
            construction_replacement_delta_mm2=construction-slot['area_mm2'],
            construction_bbox_DBU=fullbox,
            construction_displaced_rectangles=[dict(name=r['name'],intersect_mm2=intersection(fullbox,r['bbox_DBU'])/1e12) for r in oldrects if r['name']!=slot['name'] and intersection(fullbox,r['bbox_DBU'])],
            construction_is_unoptimized_proxy_not_minimum_or_fit=True,
            unallocated_extension_is_not_free_area=True,
            ports=shape['ports'], tracks=shape['tracks'], clock=shape['clock'],
            source_select_cycle_upper_envelope=shape['source_select_cycle_upper_envelope'],
            reservation_is_replacement_not_addition=True, selected=False,
            complete_logic_clock_route_area_not_in_state_bound=True))
    return dict(schema='opentallas.dsrom.noECC.physical-transition.v1', candidate='DS4096-TP4-S58-PAR2-NP2048',
        candidate_ownership_count_not_changed=True, generator_sha256=sha(Path(__file__)), inputs=receipts,
        policy=dict(ROM_ECC_required=False, no_replacement_mandatory_parity_CRC=True, SRAM_HBM_link_control_protection_unchanged=True,
            fault_free_golden_exact_required=True, clock_GHz=1.2, SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25),
        macro=g, local_macro_layer_exclusions=exclusions,
        complete_NB2_PP1_pair=dict(physical_macros=4, logical_slots=2, depth=4096, gross_bits=4*4096*274,
            physical_read_ports=4, bits_per_macro_read=274, bytes_per_macro_read=34.25,
            bank_alternation='Source chooses bank via a_ctr[0]; no four simultaneous enabled reads or perfect service assumed.',
            macro_body_um2=4*g['body_um2'], existing_capture_bits=1096,
            existing_capture_and4macro_clock_pins=clocks, adjacent_compute_control_and_whole_frame_still_required=True),
        capture_contract=dict(accepted_issue_edge=0, PP_capture_postNBA_edge=2, lane_consume_preedge=3,
            ECC_added_cycles=0, preserve_source_multicycle_capture=True,
            measured_macro_CQ_wire_setup_skew_hold_in_context_required=True,
            issue_hazard_PP_BP_credit_guards_retained=True,
            original_clock_DRAIN_is_not_universal_backend_completion=True),
        removal_ledger=dict(checker_corrector_and_ECC_exception_pipeline='omit in coordinated successor',
            parity_sidecar_and_local_mirror='omit ECC-only roles; Nash must bind repurposed/removed physical instances before area credit',
            no_reclaim_of_payload_inline_positions_without_exact_image_schema=True,
            numeric_area_credit_applied_mm2=0, no_ECC_II2_or_checked_terminal_dependency=True,
            shared_valid_owner_backpressure_delivery_ACK_state_not_removed=True),
        selector_join=dict(source_commit='1d8304647ceb7a1b64d96217c6dfa075b5704f0a', compiled={'N':4,'NMAX':2048,'LDW':4},
            old_candidate_store_slot=slot, state_only_replacement_bounds=bounds,
            filter_serial_quota_still_mandatory=True, full_reservation_owner='Epicurus with Maxwell/physical owner',
            historical_coordinates_not_current_placement=True, no_double_candidate_store_charge=True,
            required='ONE complete selector instance/state/logic/clock/route union and translated replacement rectangle in coordinated noECC map; displaced controller and corridors reallocated before admission.'),
        next_gate=dict(scope='Complete current q/BF NB2PP1FAST1 element and source-matched noECC macro/data-capture/clock/PG/OBS context',
            prerequisites=['Nash noECC executable payload/macro ownership map without lost weights',
                'Maxwell single successor ledger including complete selector replacement and all service instances',
                'Translated full element pins/OBS/halos/PG/vias/clock union, source loads and channel capacity',
                'SS macro-to-capture plus capture-to-lane and FF hold constraints with exact enables and valid/activation/tag alignment'],
            RTL_PR_admitted=False),
        retired_preparation=dict(archive='/tmp/dsrom-retired-ECC-context-2b23bbb9a-20261002.tar.gz', sha256='a299ea48aaad78ae54a4a879ca58ce30f6ef19e6f1688180ef7960f9f43f4a6c', generator_exit=0,
            owned_live_ECC_jobs=0, committed_ECC_failures_and_measurements_unchanged=True),
        applicability={'DS_ROM':'this source-bound context', 'Qwen_ROM':'noECC policy applies; own source/context qualification required', 'DS_HBM':'protection unchanged; no cost transfer', 'Qwen_HBM':'protection unchanged; no cost transfer'})

if __name__ == '__main__':
    data=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
    out=BASE/'model.json'
    if out.exists() and out.read_bytes()!=data:
        raise ValueError('preserve prior record; successor required')
    out.write_bytes(data)
    print(sha(out))
