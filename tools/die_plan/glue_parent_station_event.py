#!/usr/bin/env python3
"""Build a disabled compact-GLUE/parent-FT architecture from the exact d90 lane graph.

This emits a source-event specification, NOT a runnable/released die plan. Clock,
reset, landing, source/latency binding and actual geometry must be derived together.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import schema


def build(plan_path, bank_path):
    raw = json.loads(plan_path.read_text())
    P = schema.Plan(raw, plan_path)
    parts = {p['name']: p for p in raw['partitions']}
    assert parts['glue']['origin_um'] == [0.0, 10022.4]
    assert raw['partition_types']['glue']['outline_um'] == [777.6, 1468.8]
    assert parts['native59']['origin_um'] == [0.0, 11491.2]
    width, compact_w, compact_h = 777.6, 432.0, 380.16
    y0 = 10022.4 + compact_h
    height = 11491.2 - y0
    assert abs(height - 1088.64) < 1e-7
    # Keep the native59 pin table exactly. Compact only the GLUE-facing pin map.
    scale = (compact_w - 2 * 4.32) / (width - 2 * 4.32)
    project = lambda x: 4.32 + (x - 4.32) * scale
    related = [p for p in raw['ports']
               if {p['src']['part'], p['dst']['part']} == {'glue', 'native59'}]
    # Pack complete crossing windows on real off-PG tracks. Six pins/um is
    # a PER-LAYER budget. Target five/layer (ten combined) including reserved
    # auxiliary contacts, leaving room around PG bands inside a 10um window.
    # Do not scale already quantized bit sites.
    windows = {}
    cursor = 4.32
    def old_window(port):
        side = 'src' if port['src']['part'] == 'glue' else 'dst'
        return P._type_geom('glue', port[side]['bus'])
    for port in sorted(related, key=lambda p: sum(old_window(p)[1])):
        geom = old_window(port)
        count = schema.port_pins_count(port)
        center = project(sum(geom[1]) / 2)
        lo = max(cursor, center - (count + 8) / 20)
        hi = schema.window_for(lo, count + 8, geom[2], P.layers,
                               per_um=10.0, track_max=.6)
        windows[port['id']] = [round(lo, 6), hi]
        cursor = hi + .32
    if cursor - .32 > compact_w - 4.32:
        raise ValueError(f'complete tracked GLUE interface exceeds compact N bay: {cursor - .32}')
    slots, witnesses, lane_rows = [], [], []
    incident_ids = {p['id'] for p in related}
    old_aux = {p['name']: p for p in raw['partition_types']['glue']['clock']['landing_contract']['pins']}
    for port in related:
        native_side = 'src' if port['src']['part'] == 'native59' else 'dst'
        glue_side = 'dst' if native_side == 'src' else 'src'
        ng = P._type_geom('native59', port[native_side]['bus'])
        gg = P._type_geom('glue', port[glue_side]['bus'])
        # Eight real native59 FT inputs inherit the shared crossing window from
        # their GLUE producer rather than declaring a second type-level window.
        inherited = ng is None
        if inherited:
            pr = P.ports[port['id']]
            assert native_side == 'dst' and pr['face'] == 'N'
            ng = ('S', pr['window_um'], pr['layers'], pr.get('order', 'lsb_low'))
        assert ng and gg and ng[0] == 'S' and gg[0] == 'N', port['id']
        assert ng[1:] == gg[1:], (port['id'], ng, gg)
        top_window, lays, order = ng[1:]
        bottom_window = windows[port['id']]
        name = 's_' + port['id'].rsplit('__', 1)[0]
        down = native_side == 'src'
        station_count = 5
        slot = dict(name=name, width=port['width'], stations=station_count,
                    in_face='N' if down else 'S', out_face='S' if down else 'N',
                    in_window_um=top_window if down else bottom_window,
                    out_window_um=bottom_window if down else top_window,
                    layers=lays, order=order)
        slot['native_geometry_origin'] = 'existing_shared_port' if inherited else 'existing_type_window'
        gio = 'out' if glue_side == 'src' else 'in'
        gb = port[glue_side]['bus']
        aux_names = ['fclk_' + gio + '_' + gb, 'cland_fstart_' + gio + '_' + gb]
        assert all(n in old_aux for n in aux_names)
        slot['existing_glue_aux_pins'] = [copy.deepcopy(old_aux[n]) for n in aux_names]
        # Physical pin count includes the source graph's real in-band epoch bit.
        points = schema.pin_positions(dict(port, face='N', window_um=top_window,
                                           layers=lays, order=order), P.layers)
        bottom_points = {b: (ln, x) for b, ln, x in schema.pin_positions(
            dict(port, face='S', window_um=bottom_window, layers=lays, order=order), P.layers)}
        sites = [[] for _ in range(station_count)]
        for bit, layer, x in points:
            # Regenerate from the window on real off-PG tracks. Scaling the old
            # bit coordinates themselves creates illegal 0.035um M7 spacing.
            blayer, xb = bottom_points[bit]
            assert blayer == layer
            endpoints = [(x, height - 4.32), (xb, 4.32)]
            if not down:
                endpoints.reverse()
            for i in range(station_count):
                f = i / (station_count - 1)
                xy = [(1 - f) * endpoints[0][a] + f * endpoints[1][a] for a in (0, 1)]
                sites[i].append([round(v, 6) for v in xy])
            hops = [sum(abs(sites[i + 1][-1][a] - sites[i][-1][a]) for a in (0, 1))
                    for i in range(station_count - 1)]
            witnesses.append(dict(port=port['id'], bit=bit, layer=layer,
                                  native_x=x, compact_x=xb, hops_um=hops))
        slot['bit_sites_um'] = sites
        slots.append(slot)
    # The original single physical crossing becomes two. Keep all old lanes;
    # rederive the landing network with ONE extra declared D4 crossing per lane.
    for lane in raw['lanes']:
        changed = [p for p in lane['ports'] if p in incident_ids]
        if not changed:
            continue
        assert len(changed) == 1
        old = raw['latency']['lanes'].get(lane['id'], {})
        lane_rows.append(dict(lane=lane['id'], split_port=changed[0],
                              old_record=old, added_stations=5,
                              added_physical_crossings=1, added_D4_landing_cycles=3,
                              added_cycles=8, added_ps=8 * raw['die']['period_ps']))
    banks = json.load(gzip.open(bank_path))
    bank_rows = []
    east = {'coll_flt_i', 'coll_fltv_i', 'sys_face__io_cmd_free', 'sys_face__io_fault'}
    for b in banks['buses']:
        face = 'E' if b['bus'] in east else 'N'
        bank_rows.append(dict(bus=b['bus'], face=face,
                              data_epoch_contacts=b['data_plus_epoch_width'],
                              actual_cell_area_um2=b['actual_assigned_total_area_um2'],
                              existing_role_membership_preserved=True))
    totals = {f: dict(buses=sum(b['face'] == f for b in bank_rows),
                     contacts=sum(b['data_epoch_contacts'] for b in bank_rows if b['face'] == f),
                     actual_cell_area_um2=sum(b['actual_cell_area_um2'] for b in bank_rows if b['face'] == f))
              for f in ('N', 'E')}
    return dict(status='DISABLED_ARCHITECTURE_NOT_RUNNABLE_NO_PHYSICAL_RELEASE',
                source_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                geometry=dict(glue_origin=parts['glue']['origin_um'],
                              glue_outline=[compact_w, compact_h],
                              ft_origin=[0, y0], ft_outline=[width, height],
                              preserved_parts=['native59', 'tt_ctlm', 'ucie_kv', 'coll_f3', 'coll_f4'],
                              sibling_ucie_zone_untouched=True),
                station_type=dict(module='ot_qc_glue_parent_ft', hard=False,
                                  outline_um=[width, height], ft_slots=slots),
                source_boundary_constraints=dict(native59_pins_unchanged=True,
                      glue_phy_S_pins_unchanged=True, glue_coll_f3_E_windows_unchanged=True,
                      coll_f3_to_glue_horizontal_span_um=345.6,
                      no_west_banks_at_die_edge=True,
                      maximum_nominal_station_hop_um=max(max(w['hops_um']) for w in witnesses),
                      site_error_allowance_per_end_um=20,
                      bounded_hop_um=max(max(w['hops_um']) for w in witnesses) + 40,
                      boundary_face_flops_nominal_setback_um=4.32),
                exact_bank_membership=bank_rows, face_totals=totals,
                latency=dict(lanes=lane_rows, changed_lane_count=len(lane_rows),
                      added_cycles_per_direction=8, added_roundtrip_cycles=16,
                      added_roundtrip_ps=16 * raw['die']['period_ps'],
                      model_status='Explicit unit price; programme/token incidence must be composed before adoption',
                      old_r8_pads_preserved=True, all_bundle_bits_delayed_together=True),
                transport_width=dict(payload_bits=sum(p['width'] for p in related),
                      physical_data_epoch_bits=len(witnesses),
                      station_data_epoch_flops=5 * len(witnesses)),
                cut_model=dict(layers=['M5', 'M7'], conservative_pitch_um=.064,
                      narrow_core_face_um=compact_w-8.64,
                      track_capacity_before_PG=int((compact_w-8.64) / .064) * 2,
                      data_epoch_demand=len(witnesses),
                      existing_named_FCLK_FSTART_contacts=2*len(related),
                      minimum_known_demand=len(witnesses)+2*len(related),
                      minimum_known_fraction_after40pct_reservation=(len(witnesses)+2*len(related)) / (int((compact_w-8.64) / .064) * 2 * .6),
                      qualification='Planning only; CA/control/clock/PG/access demand must be added before G0 release'),
                pin_allocation=dict(auxiliary_contact_reserve_per_crossing=8,
                      per_layer_pin_budget_per_um=6, per_layer_target_per_um=5,
                      track_allocation_fraction=.6,
                      packed_window_end_um=cursor-.32,
                      status='Data+epoch sites are real off-PG tracks; auxiliary names/clock/reset joins remain to be derived'),
                gates=dict(G0C='NOT RUN', strict_bind='NOT RUN',
                           actual_geometry='NOT RUN', exactness_mutant='NOT RUN'),
                required_completion=[
                    'Derive the compact GLUE macros, 27 N plus four E banks, output and clock/reset/START sites together',
                    'Add the real FT partition and split all 59 actual lanes; preserve both old leaf endpoints and each epoch',
                    'Derive ONE extra D4 landing per split lane and update the actual lane latency table/R8 schedules',
                    'Derive the new bridge output-clock provider as real hardware; old native59-to-GLUE physical clock receipts do not transfer',
                    'Derive the coupled clock and neighbour reset/START provider DAG including exact boot offsets; no new synchronizer',
                    'Run G0C delta=0new, strict bind=0, source LEC/lockstep plus mutant and model/token pricing',
                    'Render and look at the actual candidate before any P&R; clocks/PG/nominal TT/FF remain unqualified']) , witnesses


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('banks', type=Path)
    ap.add_argument('out', type=Path)
    args = ap.parse_args()
    event, sites = build(args.plan, args.banks)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'event.json').write_text(json.dumps(event, indent=1) + '\n')
    with gzip.open(args.out / 'bit_hops.json.gz', 'wt') as f:
        json.dump(sites, f)
    print(json.dumps(dict(lanes=event['latency']['changed_lane_count'],
                         width=event['transport_width'],
                         nominal_hop=event['source_boundary_constraints']['maximum_nominal_station_hop_um'],
                         bound=event['source_boundary_constraints']['bounded_hop_um'],
                         added_cycles=8)))

if __name__ == '__main__':
    main()
