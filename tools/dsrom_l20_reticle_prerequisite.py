#!/usr/bin/env python3
"""Bind a frozen owner reservation to repository manufacturing policy.

Capacity sensitivities are necessary conditions, not a legal layout or timing
certificate. No source generator is executed or edited by this review.
"""
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_l20_reticle_prerequisite_20261002'
BASE = 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
FLOOR = '4e38326d6f361bc85e660f48c59c355e2bb95274'


def fits(w, h, envelope=(26., 33.)):
    return min(w, h) <= min(envelope) and max(w, h) <= max(envelope)


def build():
    pins = []
    def source(path, revision=BASE):
        b = subprocess.check_output(['git', 'show', revision + ':' + path], cwd=ROOT)
        pins.append(dict(path=path, revision=revision, sha256=hashlib.sha256(b).hexdigest()))
        return b
    def snapshot(name):
        b = (OUT / 'inputs' / name).read_bytes()
        pins.append(dict(path='inputs/' + name, sha256=hashlib.sha256(b).hexdigest()))
        return json.loads(b)
    model = snapshot('model.json')
    outline = snapshot('reservation_outline.json')
    receipt = snapshot('snapshot_receipt.json')
    for r in receipt:
        b = (OUT / r['snapshot']).read_bytes()
        if hashlib.sha256(b).hexdigest() != r['sha256']:
            raise ValueError('owner draft snapshot identity mismatch')
    text = source('tools/uarch_model.py').decode()
    atlas = source('docs/ARCHITECTURE_ATLAS.html').decode()
    tree = ast.parse(text)
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'HBM_SHORE' for t in n.targets))
    keyword = next(k for k in assignment.value.keywords if k.arg == 'reticle_mm')
    envelope = ast.literal_eval(keyword.value)
    if envelope != (26., 33.):
        raise ValueError('reticle policy changed; review orientation and package join')
    fp = json.loads(source('results/floorplan/v41_pack_refit_w18_e8p5.json', FLOOR))
    hbm_failures = json.loads(source('results/uarch/hbm_tc_parent_capacity_20261002/model.json',
                                    'bcb3d59cd1415995ae0da0fd1f50dd6b7d626064'))['failed_unchanged']
    debit = outline['fixed815_field_debit_mm2']
    if debit != model['refit']['fixed_die_field_loss_mm2_including_declared_extra_corridors']:
        raise ValueError('incoherent owner model/outline')
    w, h = [v / 1000 for v in outline['grow_rectangular_die_bbox_um']]
    # Quantize INWARD to the retained 2.16um floorplan grid, never enlarge
    # the reticle limit by rounding. Rotation remains explicitly allowed.
    constrained = [math.floor(v * 1000 / 2.16) * 2.16 / 1000 for v in (33., 26.)]
    constrained_area = math.prod(constrained)
    retained_area = fp['geometry']['die_mm2']
    extra = constrained_area - retained_area
    # Keep the declared 12.5% clock/reset/PG/hold/DFT reserve at the
    # expanded outline too. Crediting every added mm2 to field is optimistic.
    overhead_fraction = model['co_resident_reservations_mm2']['all_clock_reset_PG_hold_DFT_unallocated_die_overhead'] / retained_area
    added_overhead = extra * overhead_fraction
    residual = max(0., debit - extra + added_overhead)
    capacity = model['current_product_capacity_sensitivity']
    rows = capacity['rows']
    baseline = rows[0]['baseline_usable_mm2']
    usable = baseline - .9 * residual
    required_stage = min(r['stages'] for r in rows if r['need_mm2'] <= usable)
    old_stage = capacity['baseline_min_stages']
    current_need = next(r['need_mm2'] for r in rows if r['stages'] == old_stage)
    recovery = max(0., current_need - usable) / .9
    inventory = Counter(r[-1] for r in fp['instances'])
    # Preserve each declared instance identity, master, orientation and old
    # endpoint. This list exposes displaced geometry instead of silently
    # freeing field area. Master sizes come from pinned LEFs, never guesses.
    dims = {}
    for r in fp['instances']:
        master = r[1]
        if master.startswith('ASSUMED_') or master in dims:
            continue
        import re
        b = source('physical/asap7_memory_macros/' + master + '/' + master + '.lef', FLOOR).decode()
        m = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', b)
        dims[master] = [float(m[1]), float(m[2])]
    x, y = outline['origin_um']
    hw, hh = outline['bbox_um']
    co = outline['other_hub_regions_preserved_and_explicitly_shifted']
    footprint = [x - 43.2, y - 43.2,
                 max([x + hw] + [r['origin_um'][0] + r['bbox_um'][0] for r in co]) + 43.2,
                 y + hh + 43.2]
    displaced = []
    for r in fp['instances']:
        if r[-1] not in ('ROM_MAC.expert', 'ROM_MAC.dense_QE', 'ROM_MAC.ME', 'VM.CONSTANT_HE', 'ENGRAM.spill'):
            continue
        a, b = r[2:4]; mw, mh = dims[r[1]]
        if r[4] in ('R90', 'R270', 'MXR90', 'MYR90'):
            mw, mh = mh, mw
        if a < footprint[2] and a + mw > footprint[0] and b < footprint[3] and b + mh > footprint[1]:
            displaced.append(dict(name=r[0], master=r[1], origin_um=r[2:4], orientation=r[4], group=r[-1]))
    stage_delta = required_stage - old_stage
    cited = [34.712928, 29.23992]
    return dict(schema='dsrom-l20-reticle-package-prerequisite-v1', pins=pins,
        verdict='BLOCKED_RETICLE_GROWTH_AND_UNBOUND_CONSTRAINED_PLACEMENT',
        envelope=dict(reticle_mm=list(envelope), max_width_mm=33., max_height_mm=26., rotation_allowed=True,
            alternative_orientation_mm=[26., 33.], maximum_area_mm2=858.,
            source_lines=[keyword.lineno, 4222], limits_are_repository_policy_not_foundry_approval=True),
        cited_earlier_proposal=dict(outline_mm=cited, area_mm2=math.prod(cited), fits_reticle=fits(*cited),
            field_debit_mm2=52.97520248063999, provenance='user citation and parent review; owner draft subsequently changed'),
        frozen_owner_proposal=dict(outline_mm=[w,h], area_mm2=w*h, fits_reticle=fits(w,h),
            longest_dimension_excess_mm=max(w,h)-33., shortest_dimension_excess_mm=min(w,h)-26.,
            area_excess_over_envelope_mm2=w*h-858., field_debit_mm2=debit,
            component_area_PASS_does_not_admit_die=True),
        constrained_alternative=dict(outline_mm=constrained, area_mm2=constrained_area, fits_reticle=fits(*constrained),
            retained_outline_mm=[fp['geometry']['die_w_um']/1000,fp['geometry']['die_h_um']/1000],
            maximum_gross_expansion_mm2=extra, residual_field_debit_mm2=residual,
            die_overhead_fraction=overhead_fraction, added_die_overhead_reservation_mm2=added_overhead,
            usable_field_mm2=usable, required_field_at_unchanged_stages_mm2=current_need,
            gross_packing_recovery_needed_to_keep_all_current_stages_mm2=recovery,
            spare_source_pair_rows=fp['capacity']['spare_pair_rows'],
            spare_source_pair_row_area_mm2=fp['area']['unused_rom_pair_slots_mm2'],
            unused_slots_are_not_free_PDN_or_placement_credit=True,
            capacity_sufficient_stages=required_stage, baseline_stages=old_stage, additional_stage_events=stage_delta,
            additional_layer_dies=4*stage_delta,
            capacity_sufficient_total_dies=4*required_stage+capacity['unchanged_head_dies']+capacity['unchanged_table_dies'],
            added_packages_if_paired_layer_dies=2*stage_delta,
            added_event_latency_expression=f'{stage_delta} additional stage events: sum(fabric.hop(stage,payload,stage_index)) plus recompiled substage events; endpoint transport must be rebound',
            added_latency_measured=False, token_rate_certified=False,
            alternative_status='CAPACITY_SENSITIVITY_ONLY_BLOCKED_PENDING_COMPLETE_PLACEMENT_PROVIDER',
            all_source_instances_preserved_in_obligation_ledger=True, legal_relocation_complete=False,
            source_instance_count=len(fp['instances']),
            source_instance_counts_by_group=dict(inventory), source_soft_region_count=len(fp['soft_regions']),
            all_ports_and_replica_counts=outline['per_user_parallelism'],
            source_field_collisions_with_proposed_hub_envelope=len(displaced),
            displaced_instances_requiring_legal_relocation=displaced,
            original_instances=fp['instances'], original_soft_regions=fp['soft_regions'], original_channels=fp['channel_rects'],
            new_components=outline['components'],new_route_bands=outline['clear_route_bands'],
            source_hub_envelope_um=footprint,
            source_8192row_inventory_is_not_current_4096row_product_fit=True,
            no_field_drop_no_new_spatial_redistribution=True),
        package=dict(repository_baseline='two reticle dies plus eight HBM stacks; CoWoS-L class',
            atlas_two_die_package_statement_present='94 two-die packages' in atlas,
            numeric_package_max_width_mm=None,numeric_package_max_height_mm=None,
            exact_missing_provider='Package/foundry owner: approved per-die 33x26 orientation and usable seal-ring/core envelope; exact two-die/eight-HBM interposer/substrate outline, keepouts, die gaps, UCIe beach and stack/PHY placement at constrained dimensions',
            die_reticle_PASS_is_not_package_feasibility=True, package_admission=False),
        remaining_gate='Complete current4096-row element inventory/placements at constrained outline, including every displaced field pair and strip, halo/OBS/PDN/clock/hold exclusions and all source ports. Recompile unchanged golden work into priced stage/event/provider graph; source-load endpoint SS/FF timing before admission.',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        retained_FAILUREs=model['retained_FAILUREs'], retained_HBM_FAIL_unchanged=hbm_failures,
        mandatory_bmul_repair_owner='Epicurus; no gate or hardware fit transfer',
        no_admission=True, no_RTL_PnR=True, no_original_edits=True,
        clock_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25)


def artifact():
    return (json.dumps(build(),sort_keys=True,indent=2)+'\n').encode()


if __name__ == '__main__':
    path=OUT/'model.json'
    if path.exists():
        raise SystemExit('refuse evidence overwrite')
    path.write_bytes(artifact())
