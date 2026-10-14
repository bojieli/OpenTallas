#!/usr/bin/env python3
"""Extract retained SM tile logic without dropping a state bit or a hard seam.

The extracted leaf is a sizing candidate. Its ports are actual cut nets, not
fabricated pin counts. A separate clock port for each hard child is exposed in
the parent candidate; physical phase, reach and slot assignment remain gates.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARD = {'ot_hbm_accel_smh_' + s for s in ('pt_w', 'pt_e', 'xs', 'bdc', 'tcl', 'tct')}


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def extract(design, variant):
    top = 'ot_hbm_accel_smh_tile_' + variant
    original = design['modules'][top]
    hard = {n: c for n, c in original['cells'].items() if c['type'] in HARD}
    own = {n: c for n, c in original['cells'].items() if c['type'] not in HARD}
    assert len(hard) == 12
    inside, outside, drivers = set(), set(), set()
    for cell in own.values():
        for port, bits in cell['connections'].items():
            ints = {b for b in bits if isinstance(b, int)}
            inside |= ints
            if cell['port_directions'][port] == 'output':
                drivers |= ints
    for cell in hard.values():
        for bits in cell['connections'].values():
            outside |= {b for b in bits if isinstance(b, int)}
    for port in original['ports'].values():
        outside |= {b for b in port['bits'] if isinstance(b, int)}
    icg = next(c for c in own.values() if 'ICG' in c['type'])
    gate_enable_bit = icg['connections']['ENA'][0]
    # Registered ENA is exported for same-semantics ICG copies on every child
    # root. The original ICG stays in the own leaf and clocks its own state.
    cut = sorted((inside & outside) | {gate_enable_bit})
    ports = {f'cut_{b}': {'direction': 'output' if b in drivers else 'input', 'bits': [b]} for b in cut}
    # Keep source wire attributes, especially explicit kept register copies.
    # Dropping them leaves the Boolean graph intact but loses physical state
    # retention when synthesis removes individually unused vector bits.
    netnames = {}
    for name, net in original['netnames'].items():
        bits = [b for b in net['bits'] if not isinstance(b, int) or b in inside]
        if not any(isinstance(b, int) for b in bits):
            continue
        row = copy.deepcopy(net)
        row['bits'] = bits
        netnames[name] = row
    leaf = {'attributes': {'keep_hierarchy': '1'}, 'ports': ports, 'cells': copy.deepcopy(own),
            'netnames': netnames}
    leaf_name = 'ot_smh_own_' + variant
    parent = copy.deepcopy(original)
    parent['cells'] = copy.deepcopy(hard)
    parent['cells']['u_own'] = {'hide_name': 0, 'type': leaf_name, 'parameters': {}, 'attributes': {},
                              'port_directions': {p: d['direction'] for p, d in ports.items()},
                              'connections': {p: d['bits'] for p, d in ports.items()}}
    # A second candidate exposes the real twelve roots. Common-clock expansion
    # is still retained separately for the exact decomposition gate.
    roots = copy.deepcopy(parent)
    maxbit = max(inside | outside)
    clocks = []
    for index, (name, cell) in enumerate(sorted(hard.items())):
        assert len(cell['connections']['clk']) == 1
        bit = maxbit + index + 1
        pin = 'clk_child_' + str(index)
        roots['ports'][pin] = {'direction': 'input', 'bits': [bit]}
        roots['netnames'][pin] = {'hide_name': 0, 'bits': [bit], 'attributes': {}}
        gated_bit = maxbit + len(hard) + index + 1
        child_icg = copy.deepcopy(icg)
        child_icg['connections'] = {'CLK': [bit], 'ENA': [gate_enable_bit],
                                    'GCLK': [gated_bit], 'SE': ['0']}
        roots['cells']['u_child_icg_' + str(index)] = child_icg
        roots['cells'][name]['connections']['clk'] = [gated_bit]
        clocks.append({'instance': name, 'master': cell['type'], 'parent_clock_port': pin,
                       'original_clock_bit': cell['connections']['clk'][0],
                       'ICG_instance': 'u_child_icg_' + str(index),
                       'enable_bit': gate_enable_bit, 'enable_own_port': 'cut_' + str(gate_enable_bit),
                       'enable_owner': 'retained raw-clock ENA register; same negative-level ICG at each child root',
                       'physical_phase': 'phi - measured child boundary insertion', 'physical_phase_measured': False})
    qbits = sum(len(c['connections'].get('Q', [])) for c in own.values()
                if any(s in c['type'].lower() for s in ('dff', 'latch')))
    assert qbits == 995, qbits
    assert sum('ICG' in c['type'] for c in own.values()) == 1
    return original, leaf, parent, roots, {
        'variant': variant, 'source_top': top, 'own_master': leaf_name,
        'hard_children': len(hard), 'own_cells': len(own), 'own_sequential_Q_bits': qbits,
        'per_SM_16_tile_sequential_Q_bits': 16 * qbits, 'own_ICGs': 1,
        'cut_ports': len(ports), 'cut_input_bits': sum(p['direction'] == 'input' for p in ports.values()),
        'cut_output_bits': sum(p['direction'] == 'output' for p in ports.values()),
        'child_clocks': clocks, 'physical_status': 'OWN_LEAF_UNHARDENED_SLOT_UNASSIGNED',
        'exactness_scope': 'All original cell parameters/connections retained; hard interiors not arithmetic-qualified here.'}


def verify(original, leaf, parent):
    """Expand the actual extracted leaf and compare the complete circuit graph."""
    got = copy.deepcopy(parent['cells'])
    instance = got.pop('u_own')
    translation = {p['bits'][0]: instance['connections'][n][0] for n, p in leaf['ports'].items()}
    for name, cell in leaf['cells'].items():
        row = copy.deepcopy(cell)
        row['connections'] = {p: [translation.get(b, b) for b in bits] for p, bits in row['connections'].items()}
        assert name not in got
        got[name] = row
    assert original['ports'] == parent['ports']
    assert original['cells'] == got, 'expanded extracted circuit differs from pinned original'
    return len(got)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='results/arch/hbm_native_1013/sm_compaction')
    p.add_argument('--out', default='results/arch/hbm_native_1013/sm_own_logic')
    a = p.parse_args()
    src, out = ROOT / a.input, ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for variant in ('eg', 'wg'):
        input_path = src / (variant + '.json')
        design = json.loads(input_path.read_text())
        original, leaf, parent, roots, row = extract(design, variant)
        count = verify(original, leaf, parent)
        mutant = copy.deepcopy(parent)
        port = next(n for n, v in leaf['ports'].items() if v['direction'] == 'output')
        mutant['cells']['u_own']['connections'][port] = ['0']
        try:
            verify(original, leaf, mutant)
        except AssertionError:
            killed = True
        else:
            killed = False
        assert killed, 'own-leaf output cut mutant survived'
        leaf_design = {'creator': design['creator'], 'modules': {row['own_master']: leaf}}
        # Retain the ICG blackbox declaration for synthesis and library mapping.
        for name, module in design['modules'].items():
            if 'ICG' in name:
                leaf_design['modules'][name] = module
        write(out / (variant + '_own.json'), leaf_design)
        split = copy.deepcopy(design)
        split['modules'][row['source_top']] = parent
        split['modules'][row['own_master']] = leaf
        write(out / (variant + '_split_common_clock.json'), split)
        split['modules'][row['source_top']] = roots
        write(out / (variant + '_split_child_clocks.json'), split)
        row.update(input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
                   source_commit=json.loads((src / 'sources.json').read_text())['source_commit'],
                   exact_expansion_cells=count, cut_mutant_observed_rejected=killed,
                   mutant='tie first own-leaf output cut to zero',
                   behavioural_bench=False, timing_closed=False, throughput_measured=False)
        rows.append(row)
        # Produces real synthesizable RTL from the extracted cells, not a stub.
        (out / (variant + '_write.ys')).write_text(
            f'read_json {out.relative_to(ROOT)}/{variant}_own.json\n'
            f'hierarchy -check -top {row["own_master"]}\n'
            f'write_verilog {out.relative_to(ROOT)}/{variant}_own.sv\n'
            'synth -top ' + row['own_master'] + '\nstat\n')
    write(out / 'extraction.json', {'schema': 'opentallas.smh.own_logic_cut.v1', 'rows': rows,
          'status': 'EXACT_CIRCUIT_EXTRACTION_PHYSICAL_AND_BEHAVIOURAL_GATES_OPEN'})
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
