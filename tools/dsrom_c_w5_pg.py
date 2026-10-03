#!/usr/bin/env python3
"""W5 successor: priced wake/debt and Liberty leakage, never inferred off-rail power.

Composes the source-pinned Scenario C unified-uarch output without modifying it.
All calendar and analog inputs must carry their own evidence; a fixture is not
a production calendar. Missing values propagate as null, not free costs.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


def pin(path):
    path = Path(path)
    try:
        label = str(path.resolve().relative_to(ROOT))
    except ValueError:
        label = str(path)
    return {'path': label, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def blocks(text, pattern):
    # Liberty braces in quoted strings and comments must not change depth.
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    for match in re.finditer(pattern, text):
        start = text.index('{', match.end())
        depth, quoted, escape = 1, False, False
        for end in range(start + 1, len(text)):
            char = text[end]
            if escape:
                escape = False
            elif char == '\\' and quoted:
                escape = True
            elif char == '"':
                quoted = not quoted
            elif not quoted:
                depth += (char == '{') - (char == '}')
                if depth == 0:
                    yield match, text[start + 1:end]
                    break
        else:
            raise ValueError('unclosed Liberty group')


def liberty_palette(paths):
    cells, sources = {}, []
    for path in paths:
        raw = Path(path).read_bytes()
        text = (gzip.decompress(raw) if str(path).endswith('.gz') else raw).decode()
        unit = re.search(r'leakage_power_unit\s*:\s*"(' + NUMBER + r')\s*(pW|nW|uW|mW|W)"', text)
        if not unit:
            raise ValueError('explicit leakage_power_unit required: ' + str(path))
        scale = float(unit[1]) * {'pW': 1e-12, 'nW': 1e-9, 'uW': 1e-6, 'mW': 1e-3, 'W': 1}[unit[2]]
        corner = re.search(r'_(SS|TT|FF)(?:_|\.)', Path(path).name)
        if not corner:
            raise ValueError('corner must be named in Liberty filename')
        for match, body in blocks(text, r'\bcell\s*\(\s*"?([^\)"\s]+)"?\s*\)\s*'):
            primary = re.search(r'\bcell_leakage_power\s*:\s*(' + NUMBER + ')', body)
            states = [float(v[1]) for _, b in blocks(body, r'\bleakage_power\s*\([^)]*\)\s*')
                      if (v := re.search(r'\bvalue\s*:\s*(' + NUMBER + ')', b))]
            values = ([float(primary[1])] if primary else []) + states
            if not values or any(not math.isfinite(v) or v < 0 for v in values):
                raise ValueError('missing/invalid leakage: ' + match[1])
            area = re.search(r'\barea\s*:\s*(' + NUMBER + ')', body)
            entry = {'on_rail_max_state_W': max(values) * scale,
                     'area_library_units': float(area[1]) if area else None,
                     'off_rail_W': None,
                     'off_rail_status': 'NOT_CHARACTERIZED_BY_ON_RAIL_LOGIC_STATES'}
            key = match[1] + '/' + corner[1]
            if key in cells:
                raise ValueError('duplicate cell/corner ' + key)
            cells[key] = entry
        sources.append(pin(path))
    return {'schema': 'dsrom_c_w5_liberty_v1', 'sources': sources, 'cells': cells,
            'scope': 'Liberty screen, not measured silicon power; off-rail and SerDes standby unknown'}


def wake_price(contract):
    keys = ('prewake_route_cycles', 'inrush_wait_cycles', 'powergood_cycles',
            'relock_cycles', 'guard_cycles', 'release_cycles')
    vals = [contract.get(k) for k in keys]
    for value in vals + [contract.get('lead_cycles')]:
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError('cycle costs must be nonnegative integers or null')
    total = sum(vals) if all(v is not None for v in vals) else None
    lead = contract.get('lead_cycles')
    return {'terms': dict(zip(keys, vals)), 'wake_cycles_serial_upper': total,
            'lead_cycles': lead,
            'added_cycles': max(0, total - lead) if total is not None and lead is not None else None,
            'overlap': 'no overlap credit without a measured event calendar'}


def occupancy(stage_map, calendar):
    """Explicit W2 successors; union busy/prewake/live-debt, not (batch+1)/S."""
    ids = [d['id'] for d in stage_map['domains']]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate domain')
    successors = stage_map['successors']
    for domain in stage_map['domains']:
        if domain['kind'] not in ('stage', 'link', 'engram'):
            raise ValueError('unknown domain kind')
        if domain['kind'] == 'link' and (len(domain.get('endpoints', [])) != 2 or
                                        any(e not in ids for e in domain['endpoints'])):
            raise ValueError('link requires two known endpoint domains')
    if any(a not in ids or b not in ids for a, b in successors.items()):
        raise ValueError('unknown successor')
    if not calendar:
        raise ValueError('empty calendar')
    counts = dict.fromkeys(ids, 0)
    for tick in calendar:
        sets = {k: set(tick.get(k, [])) for k in ('busy', 'live_debt', 'explicit_wake')}
        if any(s - set(ids) for s in sets.values()):
            raise ValueError('unknown calendar domain')
        awake = set().union(*sets.values())
        awake.update(successors[d] for d in sets['busy'] if d in successors)
        # Links remain awake when either endpoint has busy, prewake or debt.
        for domain in stage_map['domains']:
            if domain['kind'] == 'link' and any(e in awake for e in domain['endpoints']):
                awake.add(domain['id'])
        for domain in stage_map['domains']:
            if domain['kind'] == 'engram' or domain.get('always_on', False):
                awake.add(domain['id'])
        for domain in awake:
            counts[domain] += 1
    return {d: {'awake_cycles': n, 'observed_cycles': len(calendar), 'awake_fraction': n / len(calendar)}
            for d, n in counts.items()}


def control_allocation(netlist, palette):
    """Constructive NAND/INV allocation for the generic synthesized controller.

    Each two-input generic combinational cell gets up to 5 NAND2 + 3 INV;
    each FF gets the characterized dual-reset FF plus the same enable/reset
    allocation. This is a conservative model construction, not a mapped route.
    """
    cells = netlist['modules']['ot_dsrom_c_w5_pg']['cells']
    types = [c['type'] for c in cells.values()]
    allowed = {'$_ANDNOT_', '$_AND_', '$_MUX_', '$_NAND_', '$_NOR_', '$_NOT_',
               '$_ORNOT_', '$_OR_', '$_XNOR_', '$_XOR_'}
    if any(t not in allowed and not t.startswith('$_DFF') for t in types):
        raise ValueError('unpriced synthesized cell type')
    ffs = sum(t.startswith('$_DFF') for t in types)
    inventory = {'DFFASRHQNx1_ASAP7_75t_R': ffs,
                 'NAND2x1_ASAP7_75t_R': 5 * len(types), 'INVx1_ASAP7_75t_R': 3 * len(types)}
    rows = {}
    for corner in ('SS', 'TT', 'FF'):
        coeffs = {n: palette['cells'][n + '/' + corner] for n in inventory}
        rows[corner] = {'area_um2_predictive_model': math.fsum(inventory[n] * coeffs[n]['area_library_units'] for n in inventory),
                        'on_rail_leakage_W_upper_model': math.fsum(inventory[n] * coeffs[n]['on_rail_max_state_W'] for n in inventory)}
    return {'generic_cell_count_measured': len(types), 'FF_bits_measured': ffs,
            'constructive_inventory_model': inventory, 'by_corner': rows,
            'exclusions': ['isolation clamp', 'power switch', 'retained external debt', 'CDC', 'CTS', 'fanout buffering', 'PDN', 'SerDes'],
            'area_units': 'ASAP7 source cell area in um2; area is a model allocation, not physical closure'}


def compose(base, contract, palette=None, stage_map=None, calendar=None):
    selected = next(r for r in base['scenarios'] if r['scenario'] == 'C: A + B')
    price = wake_price(contract)
    domains = occupancy(stage_map, calendar) if stage_map is not None and calendar is not None else None
    rows = {}
    for ctx, row in selected['ctx'].items():
        extra = price['added_cycles']
        # One wake per traversed stage is conservative until actual W2 calendar joins.
        extra_us = extra * selected['stages'] / 1200 if extra is not None else None
        rate = 1e6 / (1e6 / row['ar'] + extra_us) if extra_us is not None else None
        rows[ctx] = {'baseline_AR_tok_s_model': row['ar'], 'added_token_us_model': extra_us,
                     'AR_tok_s_conditional': rate, 'delta_AR_tok_s_conditional': rate - row['ar'] if rate else None}
    # Always-on debt FFs can be priced only against an actual cell-count inventory.
    inventory = contract.get('retained_cell_inventory', {})
    retained = {}
    if palette is not None:
        for corner in ('SS', 'TT', 'FF'):
            known = all(cell + '/' + corner in palette['cells'] for cell in inventory)
            retained[corner] = math.fsum(count * palette['cells'][cell + '/' + corner]['on_rail_max_state_W']
                                   for cell, count in inventory.items()) if known and inventory else None
    return {'schema': 'dsrom_c_w5_pg_model_v1', 'status': 'DEFAULT_OFF_COMPONENT_PREPARATION',
            'unified_model_binding': {'raw_uarch_model_sha256': base['raw_uarch_model_sha256'],
                                     'composition': 'Scenario C output, with additive priced wake cycles'},
            'wake': price, 'occupancy': domains, 'per_context': rows,
            'leakage': {'retained_inventory': inventory, 'retained_on_rail_W_by_corner': retained,
                        'logic_off_rail_W': None, 'SerDes_standby_W': None,
                        'qualified_static_kw': None, 'legacy_10pct_adopted': False,
                        'historical_assumed_static_kw_b1': base['scenario_c']['power_gating']['1048576']['by_batch']['1']['static_kw']['pg_logic_links'],
                        'conservative_no_savings_static_kw_model': selected['static_w_icg'] / 1000,
                        'Engram_always_on_W_model': 3324.4},
            'sizing_before_RTL': {'MACs_per_cycle': 0, 'memory_ports_B_per_cycle': {},
                'control_input_bits_per_domain_per_cycle': 16,
                'control_output_bits_per_domain_per_cycle': 6,
                'clock_reset_bits_per_domain': 2, 'debug_state_bits_optional': 3,
                'retained_state': 'FSM 3 bits, guard counter 8 bits, wake pending 1 bit, parity 1 bit, sticky fault 1 bit; external live debt retained',
                'replicas_model': {'stage_die': selected['layer_dies'], 'links': None},
                'mux_demux': 'local FSM; prewake static adjacency OR, one edge per successor',
                'fanout': 'actual W2 adjacency and MaxwellPDN distribution required',
                'routing_tracks_required_per_domain': 24, 'routing_channel_capacity': None,
                'area_mm2': None, 'floorplan_fit': None, 'wake_switch_isolation_retention_area': None,
                'latency_contribution': price},
            'gates': {'RTL_fixture': 'NOT_RUN', 'production_zero_added_cycles': 'PENDING_W2_ACTUAL_CALENDAR',
                      'Liberty_PG_residual': 'BLOCKED_OFF_RAIL_SWITCH_AND_SERDES_CHARACTERIZATION',
                      'wake_droop_inrush': 'PENDING_MAXWELLPDN', 'SS_setup_FF_hold': 'NOT_RUN',
                      'hub_routing_layers': 'PENDING_CONTEXT', 'adopted': False},
            'delta_against_C': {'dies': 0, 'qualified_mm2': None, 'qualified_kW': None,
                               'qualified_tok_s': None},
            'qualification': 'Independent model/RTL fixture only. Analog costs and physical slots are not zero.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'results/uarch/dsrom_return_storage_hbm_20261003/model.json')
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--liberty', type=Path, nargs='*', default=[])
    parser.add_argument('--stage-map', type=Path)
    parser.add_argument('--calendar', type=Path)
    parser.add_argument('--netlist', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.stage_map is None and args.calendar is not None or args.stage_map is not None and args.calendar is None:
        parser.error('stage-map and calendar must be supplied together')
    palette = liberty_palette(args.liberty) if args.liberty else None
    model = compose(json.loads(args.baseline.read_text()), json.loads(args.contract.read_text()), palette,
                    json.loads(args.stage_map.read_text()) if args.stage_map else None,
                    json.loads(args.calendar.read_text()) if args.calendar else None)
    if args.netlist:
        if palette is None:
            parser.error('netlist pricing requires Liberty')
        model['controller_allocation'] = control_allocation(json.loads(args.netlist.read_text()), palette)
    inputs = [args.baseline, args.contract, Path(__file__), ROOT / 'tools/uarch_model.py']
    if args.stage_map:
        inputs += [args.stage_map, args.calendar]
    if args.netlist:
        inputs += [args.netlist]
    model['inputs'] = [pin(p) for p in inputs]
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in [('model.json', model), ('liberty.json', palette)]:
        (args.out / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
