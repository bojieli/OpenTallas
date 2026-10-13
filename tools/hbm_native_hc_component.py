#!/usr/bin/env python3
"""Expand the B2 HC logical pair ot_hgi_hc_quarter into its two die-placed SYS bank tiles.

Every bit range is parsed from the pinned ot_hgi_hc_quarter source, and every child
port width is checked against the pinned ot_hgi_hc_tile header. ot_hgi_hc_quarter is
a logical group only: no hard parent is created, and the legacy hfd_hc / hfd_hc_tile_xl
4x88 envelope is not coverage. The tile route is still running, so no view is bound
and nothing here is a closure claim.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PAIR_RTL = 'rtl/hbm_accel/generic/peers/ot_hgi_hc_quarter.sv'
TILE_RTL = 'rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv'
MAP = 'results/rtl/ref_tile/hc_tile_xl/b2_functional_map.json'
KIT = 'physical/ref_tile/hc_tile_xl/floorplan.json'
TILE_JOB = 'hc_tile_xl-c4-550082537-hs'
GRID = (0.432, 2.16)       # tools/hbm_native_integration_1013.py GRID
QUARTERS = [('SW', 21.6, 21.6), ('SE', 16513.632, 21.6), ('NW', 21.6, 13003.2), ('NE', 16513.632, 13003.2)]
HC_ORIGIN = (43.2, 10800.0)  # UNRESOLVED_HC_<quarter> reservation offset in the same tool
CHAIN_IN = ['d_v', 'd_ss', 'd_nv', 'd_wa', 'd_xa', 'sum_in', 'f_in']
CHAIN_OUT = ['o_v', 'o_ss', 'o_nv', 'o_wa', 'o_xa', 'sum_out', 'f_out']


def pinned(root, commit, path):
    return subprocess.run(['git', '-C', str(root), 'show', f'{commit}:{path}'], check=True,
                          capture_output=True).stdout


def clog2(n):
    return (int(n) - 1).bit_length()


def header(text, module):
    """Return (params, ports) of a module header; widths are evaluated, never assumed."""
    m = re.search(r'\bmodule\s+' + module + r'\s*#\s*\((.*?)\)\s*\(\s*\n(.*?)\n\s*\);', text, re.S)
    if not m:
        raise ValueError('no header for ' + module)
    ptext = re.sub(r'//[^\n]*', '', m[1])
    env = {'clog2': clog2}
    for name, expr in re.findall(r'(\w+)\s*=\s*([^,]+?)\s*(?:,|$)', re.sub(r'\bparameter\b|\binteger\b', '', ptext).strip(), re.S):
        env[name] = int(eval(expr.replace('$clog2', 'clog2').replace('/', '//'), {}, env))
    ports = {}
    for line in re.sub(r'//[^\n]*', '', m[2]).splitlines():
        d = re.match(r'\s*(input|output)\s+(?:wire|reg)?\s*(?:\[(.+?):0\])?\s*([\w\s,]+?)\s*,?\s*$', line)
        if not d:
            if line.strip():
                raise ValueError(f'{module}: unparsed port line {line!r}')
            continue
        width = 1 if d[2] is None else int(eval(d[2].replace('$clog2', 'clog2').replace('/', '//'), {}, env)) + 1
        for name in re.split(r'\s*,\s*', d[3].strip()):
            ports[name] = dict(direction=d[1], width=width)
    env.pop('clog2')
    return env, ports


def main(a):
    root = a.root
    pair_src = pinned(root, a.source_commit, PAIR_RTL)
    tile_src = pinned(root, a.tile_commit, TILE_RTL)
    params, pair_ports = header(pair_src.decode(), 'ot_hgi_hc_quarter')
    tile_params, tile_ports = header(tile_src.decode(), 'ot_hgi_hc_tile')
    for k, v in params.items():
        if k in tile_params and tile_params[k] != v:
            raise ValueError(f'parameter {k}: pair {v} != tile {tile_params[k]}')
    fmap = json.loads((root / MAP).read_text())
    q = fmap['quarter_candidate']
    kit = json.loads((root / KIT).read_text())
    text = pair_src.decode()
    mids = dict(re.findall(r'assign\s+(\w+_mid)\s*=\s*(\w+)\[0\];', text))      # x_mid <- chain_x[0]
    outs = {c: p for p, c in re.findall(r'assign\s+(\w+)\s*=\s*(\w+)\[1\];', text)}  # chain_x[1] -> boundary
    inst = re.search(r'ot_hgi_hc_tile\s*#\(.*?\)\s*u_tile\s*\((.*?)\n\s*\);', text, re.S)[1]
    conns = re.findall(r'\.(\w+)\((.*?)\)\s*,?\s*\n', inst + '\n')
    if {p for p, _ in conns} != set(tile_ports):
        raise ValueError('pair instance does not bind exactly the tile port list')
    env = dict(params)
    tw, th = q['child_outline_um']
    if [tw, th] != [kit['die'][2], kit['die'][3]]:
        raise ValueError('map child outline differs from the hc_tile_xl kit die')
    face = {p: f for f, names in kit['pins'].items() for p in names}
    tiles = ['g_tile[0].u_tile', 'g_tile[1].u_tile']
    children = [dict(instance=t, logical_module=q_cell, view_lef=None, view_lib={}, xy_um=list(xy), orientation='R0',
                     w_um=tw, h_um=th, pg_top=None, closure_status='OPEN_ROUTE_RUNNING_NO_VIEW_NO_TT_FF_DRC_VERDICT',
                     physical_kit='hc_tile_xl', source_job=TILE_JOB, source_commit=a.tile_commit, bank_stage=i,
                     kit_layer_contract=kit['layer_contract'], kit_pin_layers=dict(horizontal=['M4', 'M6'], vertical=['M5']))
                for i, (t, xy) in enumerate(zip(tiles, q['placement_um'])) for q_cell in ['ot_hgi_hc_tile']]
    boundary = {n: dict(direction=p['direction'], width=p['width'],
                        role='clock' if n == 'clk' else 'reset' if n == 'rst_n' else 'data') for n, p in pair_ports.items()}
    connections, binding, constants, used = [], [], [], {n: 0 for n in pair_ports}

    def ep(i, p, lsb, w):
        return dict(instance=i, port=p, lsb=lsb, width=w)

    def bind(t, port, parent, lsb):
        w = tile_ports[port]['width']
        if tile_ports[port]['direction'] != pair_ports[parent]['direction'] or lsb + w > pair_ports[parent]['width']:
            raise ValueError(f'bad boundary binding {parent}[{lsb}+:{w}] -> {port}')
        used[parent] += w
        kind = boundary[parent]['role'] if boundary[parent]['role'] != 'data' else 'boundary'
        connections.append(dict(net=f'ext_{parent}_{lsb}', endpoints=[ep('$boundary', parent, lsb, w), ep(tiles[t], port, 0, w)], kind=kind))
        binding.append(dict(parent_port=parent, parent_lsb=lsb, width=w, child_instance=tiles[t], child_port=port, child_lsb=0))

    for port, expr in conns:
        expr = expr.strip()
        for t in (0, 1):
            m = re.fullmatch(r't==0 \? (\w+) : (\w+)', expr)
            if m:                                   # chain input: boundary into bank 0, bank 0 output into bank 1
                if t == 0:
                    bind(0, port, m[1], 0)
                else:
                    src = next(p for p, e in conns if e.strip() == mids[m[2]] + '[t]')
                    w = tile_ports[port]['width']
                    if tile_ports[src]['width'] != w:
                        raise ValueError('chain width mismatch ' + port)
                    connections.append(dict(net='chain_' + src, endpoints=[ep(tiles[0], src, 0, w), ep(tiles[1], port, 0, w)], kind='chain_seam'))
            elif re.fullmatch(r'chain_\w+\[t\]', expr):   # chain output: only bank 1 reaches the boundary
                if t == 1:
                    bind(1, port, outs[expr[:-3]], 0)
            elif expr == 'first && t==0':
                if t == 0:
                    bind(0, port, 'first', 0)
                else:
                    constants.append(dict(instance=tiles[1], port=port, width=1, value=0))
            elif re.fullmatch(r'\w+', expr):
                bind(t, port, expr, 0)
            elif re.fullmatch(r'(\w+)\[t\]', expr):
                bind(t, port, expr[:-3], t)
            else:
                m = re.fullmatch(r'(\w+)\[t\*\((.+?)\) \+: \((.+?)\)\]', expr)
                if not m or m[2] != m[3]:
                    raise ValueError(f'unparsed connection .{port}({expr})')
                k = int(eval(m[2], {}, env))
                if k != tile_ports[port]['width']:
                    raise ValueError(f'slice width {k} != tile port {port}')
                bind(t, port, m[1], t * k)
    for n, p in pair_ports.items():       # clk/rst_n fan to both tiles; every other parent bit is bound exactly once
        if used[n] != p['width'] * (2 if n in ('clk', 'rst_n') else 1):
            raise ValueError(f'parent port {n}: {used[n]} bits bound of {p["width"]}')

    bits = lambda names, d: sum(pair_ports[n]['width'] for n in names if pair_ports[n]['direction'] == d)
    seam_bits = sum(c['endpoints'][0]['width'] for c in connections if c['kind'] == 'chain_seam')
    nxl = pair_ports['xl_cr']['width']
    interface = dict(chain_in_bits=bits(CHAIN_IN, 'input'), chain_out_bits=bits(CHAIN_OUT, 'output'), chain_mid_seam_bits=seam_bits,
                     x_lanes=nxl, x_lane_bits=pair_ports['xl_q']['width'] // nxl, x_forward_bits=pair_ports['xl_q']['width'],
                     x_return_bits=pair_ports['xl_cr']['width'] + pair_ports['xl_done']['width'],
                     hbm_lanes=pair_ports['hq_v']['width'],
                     hbm_request_bits=sum(pair_ports[n]['width'] for n in ('hq_v', 'hq_addr', 'hq_len', 'hq_tag')),
                     hbm_request_ready_bits=pair_ports['hq_rdy']['width'],
                     hbm_response_bits=sum(pair_ports[n]['width'] for n in ('hr_v', 'hr_tag', 'hr_beat', 'hr_data')),
                     control_in_bits=sum(p['width'] for n, p in pair_ports.items() if n.startswith('c_')) + 1,
                     status_out_bits=pair_ports['t_rdy']['width'] + pair_ports['t_flt']['width'],
                     tile_pin_faces={f: sorted(n) for f, n in kit['pins'].items()},
                     chain_direction='W face of bank 0 in, E face of bank 1 out; bank 0 E face abuts bank 1 W face across the seam gap',
                     added_pipeline_cycles=q['added_pipeline_cycles'], arithmetic_order=q['arithmetic_order'])
    for k in ('chain_in_bits', 'chain_out_bits', 'x_lanes', 'x_forward_bits', 'x_return_bits', 'hbm_lanes'):
        if interface[k] != q[k]:
            raise ValueError(f'{k}: source {interface[k]} != map {q[k]}')
    if face['sum_in'] != 'W' or face['sum_out'] != 'E':
        raise ValueError('chain faces are not W in / E out')

    ow, oh = q['outline_um']
    (x0, y0), (x1, y1) = q['placement_um']
    gap = round(x1 - (x0 + tw), 6)
    nm = lambda v: round(v * 1000)
    geometry = dict(width_identity_um=f'2*{tw} + {gap} + 2*{x0} = {round(2*tw+gap+2*x0, 6)}',
                    height_identity_um=f'{th} + 2*{y0} = {round(th+2*y0, 6)}',
                    seam_gap_um=gap, margin_um=[x0, y0], placement_grid_um=list(GRID),
                    on_grid=all(nm(v) % nm(g) == 0 for xy in q['placement_um'] + [HC_ORIGIN] for v, g in zip(xy, GRID)),
                    tile_outline_on_grid=nm(tw) % nm(GRID[0]) == 0 and nm(th) % nm(GRID[1]) == 0,
                    pin_track_pitch_um=q['track_pitch_um'],
                    on_pin_track_pitch=all(nm(v) % nm(q['track_pitch_um']) == 0 for v in [x0, y0, x1, y1, tw, th, ow, oh]),
                    child_area_um2=round(2 * tw * th, 4), bbox_area_um2=round(ow * oh, 4))
    errors = []
    if nm(2 * tw + gap + 2 * x0) != nm(ow) or nm(th + 2 * y0) != nm(oh): errors.append('bbox identity')
    if gap != q['seam_gap_um'] or y0 != y1: errors.append('seam gap / row alignment')
    if not (geometry['on_grid'] and geometry['tile_outline_on_grid'] and geometry['on_pin_track_pitch']): errors.append('grid')
    if errors:
        raise ValueError('geometry: ' + ', '.join(errors))
    seam_tracks = int(nm(th) // nm(q['track_pitch_um']))
    cut = dict(axis='x', pos_um=round(x0 + tw + gap / 2, 6), demand_bits=seam_bits, usable_tracks=seam_tracks,
               ratio=seam_bits / seam_tracks, bits_per_track_limit=[0.55, 0.60],
               capacity_grade='one horizontal layer at the 0.048 um pin pitch over the full tile height, as b2_functional_map.json; '
                              'no PG/OBS subtraction is possible before the c4 tile LEF exists',
               terms=[dict(net=c['net'], bits=c['endpoints'][0]['width']) for c in connections if c['kind'] == 'chain_seam'])
    if seam_tracks != q['one_horizontal_layer_seam_tracks'] or abs(cut['ratio'] - q['seam_min_layer_demand_fraction']) > 1e-12:
        raise ValueError('seam cut differs from the functional map')
    die = [dict(instance=f'hb_hc_{n}', quarter=n, orientation='R0', xy_um=[round(qx + HC_ORIGIN[0], 6), round(qy + HC_ORIGIN[1], 6)],
                tile_xy_um=[[round(qx + HC_ORIGIN[0] + x, 6), round(qy + HC_ORIGIN[1] + y, 6)] for x, y in q['placement_um']],
                replaces_reservation=f'UNRESOLVED_HC_{n}') for n, qx, qy in QUARTERS]
    rec = dict(schema='opentallas.hbm.native_component.v1', component='hc', logical_module='ot_hgi_hc_quarter',
               source_commit=a.source_commit,
               source_sha256={PAIR_RTL: hashlib.sha256(pair_src).hexdigest(), TILE_RTL: hashlib.sha256(tile_src).hexdigest()},
               source_commits={PAIR_RTL: a.source_commit, TILE_RTL: a.tile_commit},
               parameters=params, outline_um=q['outline_um'], boundary_ports=boundary, children=children,
               connections=connections, boundary_binding=binding, constants=constants, unused_outputs=[],
               replicated_instances=[d['instance'] for d in die], cut_ledger=[cut], long_seams=[],
               status='CANDIDATE_NOT_QUALIFIED', functional_map=dict(path=MAP, sha256=hashlib.sha256((root / MAP).read_bytes()).hexdigest(),
                                                                     status=fmap['status'], contract_version=fmap['contract_version']),
               hierarchy=dict(levels=['die', 'ot_hgi_hc_tile'], logical_group_only='ot_hgi_hc_quarter', third_hard_level=False,
                              outline_um_is=q['outline_um_is'], tiles_per_quarter=2, quarters=4, tiles_die=8,
                              lanes_tile=params['W'], lanes_die=8 * params['W']),
               die_quarter_placement=dict(rule='translation only, R0 in all four quarters, at the UNRESOLVED_HC_<quarter> origin of '
                                               'tools/hbm_native_integration_1013.py; the die compiler owns the final origin',
                                          instances=die),
               interface_summary=interface, geometry_check=geometry,
               layer_cap=dict(default='M5', status='requested default for the native die child; NOT what the committed kit carries',
                              committed_kit=dict(path=KIT, pg_layer=kit['layer_contract']['pg_layer'], rlayers=kit['layer_contract']['rlayers'],
                                                 strap_layer=kit['layer_contract']['strap_layer']),
                              open='the c4 view decides pg_top; an M5-capped export is not built'),
               legacy_envelope=dict(cells=[fmap['historical_physical_envelope']['quarter_cell'], fmap['historical_physical_envelope']['child_cell']],
                                    children_per_quarter=fmap['historical_physical_envelope']['children_per_quarter'],
                                    functional_coverage=False, note='physical envelope only; never presented as HC coverage'),
               qualification=dict(tile_route='RUNNING', tile_tt=None, tile_ff=None, tile_drc=None, child_lint=None,
                                  pair_functional_gate=dict(path='results/rtl/ref_tile/hc_tile_xl/qpair_5ed73de79/receipt.json',
                                                            scope='QPAIR functional assembly exactness and three mutants only; no physical timing'),
                                  missing_gates=fmap['missing_gates']),
               unresolved=['Tile hc_tile_xl-c4-550082537-hs is still routing: no LEF, no TT/FF/SS libs, no DRC verdict, no child lint; children carry no view.',
                           'Per-pin seam distances, PG/OBS-aware cut capacity and long_seams cannot be measured before the tile LEF exists.',
                           'HC_MIX_POST scalar shell (ot_hgi_hc_unit SYS control, sigmoid/exponential/Sinkhorn) and the FUSED.HC_POST / HC_PRE_NORM residual LL path have no native physical map; this helper covers the eight HCP bank tiles only.',
                           'Chain head/tail between quarters, c_* control, x lanes to the local VM slice and the eight HBM lanes are boundary ports here; the die consumer must bind them from source.',
                           'Production exact + mutants + throughput at the pair-integrated SYS unit are not run.'],
               closed=False, hard_parent_created=False, final_signoff_eligible=False)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'component.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(dict(children=len(children), connections=len(connections), boundary_bindings=len(binding),
                          constants=len(constants), boundary_bits=sum(p['width'] for p in boundary.values()),
                          interface={k: interface[k] for k in ('chain_in_bits', 'chain_out_bits', 'chain_mid_seam_bits', 'x_lanes', 'x_forward_bits', 'x_return_bits', 'hbm_lanes')},
                          geometry=[geometry['width_identity_um'], geometry['height_identity_um']], cut_ratio=round(cut['ratio'], 6),
                          closed=False)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--source-commit', default='5ed73de79')
    p.add_argument('--tile-commit', default='550082537')
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'results/arch/hbm_native_1013/hc')
    main(p.parse_args())
