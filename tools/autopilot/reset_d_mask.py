#!/usr/bin/env python3
"""Source-specific reset-D-mask canary. Produces candidates, never changes geometry gates.

Only the frozen native BFQG source/reset implementation is supported. The typed
mapped cone is checked against the real placement graph; EQ/KEEP/reset evidence
and both source digests are mandatory. No name-only reset or generic comb waiver.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

SOURCE_SHA = {
    'ot_hgi_sm_xload_bfqg.sv': '5317524cf8e6d9644e2fb9a04d6aff16fd338f95beb692bf13c67014dca315b5',
    'ot_rst_relay.sv': '0071a3d067e72da7a450dd265aa8390b968f0228491ed2245fe8947b499264c5',
}
PIN_CAPTURES = {'wce': 'wce_q$_SDFF_PN0_', **{
    f'r_ce[{i}]': f'g_t[{i}].rp_ce$_SDFF_PN0_' for i in range(8)}}
OUTPUTS = {'Y', 'Q', 'QN', 'H', 'L'}


def norm(s):
    return s.strip().lstrip('\\').replace('\\[', '[').replace('\\]', ']')


def mapped_cells(text):
    cells = {}
    for master, name, body in re.findall(r'^  (\S+) (\S+)\s+\(\n(.*?)^  \);', text, re.M | re.S):
        name = norm(name)
        if name in cells:
            raise ValueError('duplicate mapped cell ' + name)
        cells[name] = {'master': master, 'ports': {
            p: norm(n) for p, n in re.findall(r'\.(\w+)\((.*?)\)', body)}}
    return cells


class Graph:
    def __init__(self, cells):
        self.cells = cells
        self.drivers = defaultdict(list)
        self.loads = defaultdict(list)
        for name, cell in cells.items():
            for port, net in cell['ports'].items():
                (self.drivers if port in OUTPUTS else self.loads)[net].append((name, port))

    def driver(self, net):
        ds = self.drivers.get(net, [])
        if len(ds) != 1:
            raise ValueError('not exactly one driver: ' + net)
        return ds[0]

    def through_buffers(self, net):
        seen = set()
        parity = 0
        while self.drivers.get(net):
            if net in seen:
                raise ValueError('buffer loop')
            seen.add(net)
            name, port = self.driver(net)
            cell = self.cells[name]
            if not re.fullmatch(r'(?:BUF|INV)\w*_ASAP7_75t_R', cell['master']):
                break
            if set(cell['ports']) != {'A', 'Y'} or port != 'Y':
                raise ValueError('unsupported buffer ports')
            parity ^= int(cell['master'].startswith('INV'))
            net = cell['ports']['A']
        return net, parity

    def high(self, net):
        net, parity = self.through_buffers(net)
        name, port = self.driver(net)
        return parity == 0 and self.cells[name]['master'] == 'TIEHIx1_ASAP7_75t_R' and port == 'H'


def reset_chain(g):
    """Exact frozen source's async2sync+relay chain, no functional enable/data."""
    names = ['u_rst.rst_n$_DFF_PN0_', 'u_rst.sync_q[1]$_DFF_PN0_',
             'u_rst.sync_q[0]$_DFF_PN0_']
    net = 'u_rst.relay_q[0][0]'
    chain = []
    for index, expected in enumerate(names):
        net, parity = g.through_buffers(net)
        name, output = g.driver(net)
        if name != expected or output != 'QN' or parity != 1:
            raise ValueError('reset operand is not the qualified relay chain')
        c = g.cells[name]
        p = c['ports']
        if c['master'] != 'DFFASRHQNx1_ASAP7_75t_R' or set(p) != {'CLK', 'D', 'QN', 'RESETN', 'SETN'}:
            raise ValueError('reset relay cell class changed')
        if p['CLK'] != 'clk_ctrl' or p['RESETN'] != 'rst_n' or not g.high(p['SETN']):
            raise ValueError('reset relay clock/assertion/preset changed')
        chain.append(name)
        net = p['D']
    if not g.high(net):
        raise ValueError('reset release chain has functional data/enable')
    return chain


def qualify_cones(cells):
    g = Graph(cells)
    chain = reset_chain(g)
    rows = []
    seen_captures = set()
    for pin, expected in PIN_CAPTURES.items():
        loads = g.loads.get(pin, [])
        if len(loads) != 1:
            raise ValueError('input does not own exactly one reset mask: ' + pin)
        gate_name, pin_port = loads[0]
        gate = cells[gate_name]
        gp = gate['ports']
        if not re.fullmatch(r'AND2x\w*_ASAP7_75t_R', gate['master']) or set(gp) != {'A', 'B', 'Y'} or pin_port not in {'A', 'B'}:
            raise ValueError('input is not one AND2 D-mask: ' + pin)
        other = gp['B' if pin_port == 'A' else 'A']
        if other != 'u_rst.relay_q[0][0]':
            raise ValueError('mask operand is functional or unqualified: ' + pin)
        sinks = g.loads.get(gp['Y'], [])
        if sinks != [(expected, 'D')]:
            raise ValueError('mask output is shared, enabled or not the own capture D: ' + pin)
        capture = cells[expected]
        cp = capture['ports']
        if capture['master'] != 'DFFHQNx1_ASAP7_75t_R' or set(cp) != {'CLK', 'D', 'QN'} or cp['CLK'] != 'clk_ctrl':
            raise ValueError('capture clock/cell class changed: ' + pin)
        if expected in seen_captures:
            raise ValueError('shared capture')
        seen_captures.add(expected)
        rows.append({'pin': pin, 'mask': gate_name, 'capture': expected, 'clock': 'clk_ctrl'})
    return {'reset_chain': chain, 'candidates': rows}


def physical_join(cells, dump, rows, typed_dump=None):
    """Independently require actual placed net edges, not a mapped-name-only receipt."""
    from reset_d_mask_typed import verify_typed
    typed, critical = verify_typed(typed_dump or {}, rows)
    ids, drivers, loads, clocks, pin_ids = {}, {}, defaultdict(set), defaultdict(set), {}
    kinds, masters, cell_inputs = {}, {}, defaultdict(set)
    for line in dump.splitlines():
        f = line.split('\t')
        if f[0] == 'C':
            ids[int(f[1])] = norm(f[8])
            kinds[int(f[1])] = f[2]
            masters[int(f[1])] = f[3]
        elif f[0] == 'P':
            pin_ids[f[2]] = int(f[1])
        elif f[0] == 'N':
            index = len(drivers)
            drivers[index] = f[2]
            for sink in f[3:]:
                loads[f[2]].add(sink)
                if sink.startswith('i') and not sink.endswith('c'):
                    cell_inputs[int(sink[1:])].add(f[2])
                if sink.startswith('i') and sink.endswith('c'):
                    clocks[int(sink[1:-1])].add(f[2])
        elif f[0] == 'ND':
            raise ValueError('parallel-driver dump unsupported for this canary')
    def terminals(root):
        pending, visited, ends = [root], set(), set()
        while pending:
            driver = pending.pop()
            if driver in visited:
                continue
            visited.add(driver)
            for sink in loads.get(driver, set()):
                if sink.startswith('i') and not sink.endswith('c') and kinds.get(int(sink[1:])) == 'B':
                    pending.append(sink)
                else:
                    ends.add(sink)
        return ends

    def origin(driver):
        seen, parity = set(), 0
        while driver.startswith('i') and kinds.get(int(driver[1:])) == 'B':
            if driver in seen:
                raise ValueError('actual buffer loop')
            seen.add(driver)
            cid = int(driver[1:])
            ins = cell_inputs[cid]
            if len(ins) != 1 or not re.fullmatch(r'(?:BUF|INV)\w*_ASAP7_75t_R', masters[cid]):
                raise ValueError('actual non-pure buffer path')
            parity ^= int(masters[cid].startswith('INV'))
            driver = next(iter(ins))
        return driver, parity

    inverse = {name: cid for cid, name in ids.items()}
    def typed_ref(driver):
        if driver[0] == 'port':
            if driver[1] not in pin_ids:
                raise ValueError('untyped receipt omitted actual root port')
            return 'p' + str(pin_ids[driver[1]])
        if driver[1] not in inverse:
            raise ValueError('untyped receipt omitted actual driver cell')
        return 'i' + str(inverse[driver[1]])

    for name in critical:
        cid = inverse.get(name)
        if cid is None or masters[cid] != typed.cells[name]['master']:
            raise ValueError('typed/untyped critical cell mismatch')
        expected = set()
        expected_clocks = set()
        for pin, p in typed.cells[name]['ports'].items():
            if p['direction'] != 'INPUT':
                continue
            ref = typed_ref(typed.driver(p['net']))
            (expected_clocks if pin == 'CLK' else expected).add(ref)
        if cell_inputs[cid] != expected or clocks[cid] != expected_clocks:
            raise ValueError('typed/untyped critical pin-edge mismatch: ' + name)

    for name in ['u_rst.rst_n$_DFF_PN0_', 'u_rst.sync_q[1]$_DFF_PN0_', 'u_rst.sync_q[0]$_DFF_PN0_']:
        cid = inverse.get(name)
        if cid is None or masters[cid] != 'DFFASRHQNx1_ASAP7_75t_R':
            raise ValueError('actual reset relay cell class changed')
        if len(clocks[cid]) != 1 or origin(next(iter(clocks[cid]))) != ('p' + str(pin_ids.get('clk_ctrl')), 0):
            raise ValueError('actual reset relay clock changed')
    for row in rows:
        mask, capture = inverse.get(row['mask']), inverse.get(row['capture'])
        if mask is None or capture is None or terminals('i' + str(mask)) != {'i' + str(capture)}:
            raise ValueError('actual placement lacks mask-to-own-capture edge: ' + row['pin'])
        if not re.fullmatch(r'AND2x\w*_ASAP7_75t_R', masters[mask]) or masters[capture] != 'DFFHQNx1_ASAP7_75t_R':
            raise ValueError('actual mask/capture cell truth class changed')
        expected_reset = 'i' + str(inverse.get('u_rst.rst_n$_DFF_PN0_'))
        origins = {origin(n) for n in cell_inputs[mask]}
        if origins != {('p' + str(pin_ids.get(row['pin'])), 0), (expected_reset, 1)}:
            raise ValueError('actual mask has functional/reset-polarity operand')
        if terminals('p' + str(pin_ids.get(row['pin']))) != {'i' + str(mask)}:
            raise ValueError('actual input does not feed its own mask')
        if len(clocks[capture]) != 1 or origin(next(iter(clocks[capture]))) != ('p' + str(pin_ids.get('clk_ctrl')), 0):
            raise ValueError('actual capture clock is not the declared source clock')
    return {'actual_capture_edges': len(rows), 'note': 'No geometry verdict or source-release effect'}


def proof_gate(lec, provenance, source_dir):
    if lec.get('verdict') != 'EQUIVALENT' or lec.get('top') != 'ot_hgi_sm_xload_cl2_bfqg':
        raise ValueError('native positive EQ missing')
    if lec.get('counts') != dict(compare_points=8650, proved=8650, differs=0, undecided=0):
        raise ValueError('compare obligations changed')
    rc = lec.get('reset_contract', {})
    if any(rc.get(k) != 4 for k in ['default', 'requested', 'used']) or rc.get('debug_overrides'):
        raise ValueError('genuine native reset4 required')
    keep = lec.get('kept_registers', {})
    if keep.get('declared') != 1064 or keep.get('in_netlist') != 1064 or any(keep.get(k, {}).get('n') != 0 for k in ['constant_proved', 'missing', 'unobservable_removed']):
        raise ValueError('full native KEEP required')
    if provenance.get('provenance', {}).get('dirty') is not False or lec.get('provenance', {}).get('commit') != provenance.get('provenance', {}).get('commit'):
        raise ValueError('native source/proof commit join failed')
    for name, sha in SOURCE_SHA.items():
        if provenance.get('files', {}).get('rtl/' + name) != sha or hashlib.sha256((source_dir / name).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen source/reset qualifier changed: ' + name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['mapped', 'dump', 'typed-dump', 'lec', 'provenance', 'source-dir', 'out']:
        p.add_argument('--' + key, required=True, type=Path)
    a = p.parse_args()
    proof_gate(json.loads(a.lec.read_text()), json.loads(a.provenance.read_text()), a.source_dir)
    cells = mapped_cells(a.mapped.read_text())
    result = qualify_cones(cells)
    result['physical_join'] = physical_join(cells, a.dump.read_text(), result['candidates'], json.loads(a.typed_dump.read_text()))
    result['input_sha256'] = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in [('mapped', a.mapped), ('actual_dump', a.dump), ('typed_dump', a.typed_dump), ('lec', a.lec), ('provenance', a.provenance)]}
    result.update(schema='opentallas.reset_d_mask.canary.v1', scope='SOURCE_SPECIFIC_CANDIDATE_ONLY',
                  gating_changed=False, generic_comb_waiver=False, registration_release=False)
    a.out.write_text(json.dumps(result, indent=1) + '\n')
    print('RESET_D_MASK_CANDIDATES', len(result['candidates']), 'NO_GATE_CHANGE')


if __name__ == '__main__':
    main()
