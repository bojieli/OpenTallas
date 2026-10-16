#!/usr/bin/env python3
"""S81 VM A2-F: wire-reach relay stages per hop of the write / read / commit paths in a route-plan floorplan, and their
token-path price (tools/throughput/accepted_cost.py rom_loss, the a2_programme_cost.py method).

Every bit connection of the floorplan (a2_route_plan.connections: Prim tree over the actual pins, top-down VM port
pins) is a register-to-register hop of the RTL (every VM leaf registers its pins).  A hop longer than the per-cycle
reach R needs ceil(L / R) - 1 relay registers; all bits of a hop class move together, so the class pays its longest
connection.  R = 900 um at TT: measured ASAP7 0.76 ps/um repeated upper-metal wire (1,118 um at 833 ps raw, memory
ss-wire-reach-504um) minus clk-q + setup + 80-ps spread (signoff TT setup / FF hold; SS is sensitivity only).
Path sums: WRITE = ingress (VM face pin or CDC/landing leaf -> W0 payload) + payload -> front + front -> scatter +
scatter -> b8 -> b4 -> bank; READ = request (port -> rsched -> FSR -> b8 -> b4 -> bank) + response (bank -> b4 -> b8 ->
return -> read leaf -> port); COMMIT = b8 -> seq tile.  Price: +W on every VM-landing node and +R on every VM-reading
node is bounded above by +(W + R) on every node (the 'upper' rom_loss model, as a2_programme_cost.py).
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'tools/throughput'))
import a2_route_plan as R  # noqa: E402
import a2f_route_plan as F  # noqa: E402

ROOT = HERE.parents[1]
VM_CLASSES = {'su', 'field', 'coll', 'select', 'hbm'}     # a2_programme_cost.py 'landing' set


def cls(m):
    if m.startswith('PORT'):
        return 'port'
    for k, v in (('w0_payload', 'payload'), ('w0_header', 'header'), ('field16', 'front'), ('meta26', 'front'),
                 ('control4', 'front'), ('stripe_', 'front'), ('controller', 'front'), ('fault_join', 'fault'),
                 ('scatter', 'scatter'), ('relay128_b8', 'b8'), ('relay128_b4', 'b4'), ('bank128', 'bank'),
                 ('return_bank8', 'return'), ('read_q', 'read'), ('read_v', 'read'), ('fsr', 'fsr'),
                 ('rsched', 'rsched'), ('seq_tile', 'seq'), ('x34_t', 'cdc_t'), ('x43', 'cdc'), ('x34_s', 'cdc'),
                 ('landing', 'landing'), ('cap_leaf', 'cap'), ('cap_ctl', 'cap')):
        if k in m:
            return v
    return 'other'


PATHS = {
    'write': [('ingress', {('port', 'payload'), ('cdc_t', 'payload'), ('landing', 'payload')}),
              ('payload_front', {('payload', 'front'), ('header', 'front'), ('port', 'front')}),
              ('front_scatter', {('front', 'scatter')}), ('scatter_b8', {('b8', 'scatter')}),
              ('b8_b4', {('b4', 'b8')}), ('b4_bank', {('b4', 'bank')})],
    'read': [('port_rsched', {('port', 'rsched')}), ('rsched_fsr', {('fsr', 'rsched')}), ('fsr_b8', {('b8', 'fsr')}),
             ('b8_b4', {('b4', 'b8')}), ('b4_bank', {('b4', 'bank')}), ('b8_return', {('b8', 'return')}),
             ('return_read', {('read', 'return')}), ('read_port', {('port', 'read')})],
    'commit': [('b8_seq', {('b8', 'seq')})],
}


def measure(P, nets, W, H, reach):
    conns, _ = R.connections(P, nets, W, H)
    mx = collections.defaultdict(float)
    for (a, b, ta, tb) in conns:
        k = tuple(sorted((cls(ta), cls(tb))))
        mx[k] = max(mx[k], abs(a[0] - b[0]) + abs(a[1] - b[1]))
    out = {}
    for path, hops in PATHS.items():
        rows, tot = [], 0
        for name, keys in hops:
            L = max((mx.get(tuple(sorted(k)), 0.0) for k in keys), default=0.0)
            st = max(0, math.ceil(L / reach) - 1)
            tot += st
            rows.append(dict(hop=name, max_um=round(L, 1), relay_stages=st))
        out[path] = dict(hops=rows, added_edges=tot)
    return out


def price(write_add, read_add):
    import accepted_cost as ac
    res = {}
    for wl, f in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')):
        doc = json.load(open(ROOT / f'results/arch/token_path_20261009/{f}.json'))
        ids = [n['id'] for n in doc['nodes'] if n.get('op') != 'wave.busy']
        rx = '^(' + '|'.join(map(re.escape, ids)) + ')$'
        d = write_add + read_add
        r = ac.rom_loss(doc, rx, 0, 0, node_delta=float(d)) if d else dict(e2e_loss_pct=0.0, added_cycles=0.0)
        vm = [n['id'] for n in doc['nodes'] if n.get('op') != 'wave.busy' and n.get('cls') in VM_CLASSES]
        rv = ac.rom_loss(doc, '^(' + '|'.join(map(re.escape, vm)) + ')$', 0, 0, node_delta=float(d)) if d else r
        res[wl] = dict(node_delta=d, upper_every_node=dict(added_cycles=r['added_cycles'], e2e_loss_pct=r['e2e_loss_pct']),
                       vm_class_nodes=dict(added_cycles=rv['added_cycles'], e2e_loss_pct=rv['e2e_loss_pct']))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--variant', default='midcapd')
    ap.add_argument('--faces', default='band')
    ap.add_argument('--reach', type=float, nargs='+', default=[900.0, 1118.0])
    ap.add_argument('--baseline', action='store_true', help='A2 v4 floorplan of a2_route_plan.py instead')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    if a.baseline:
        leaves, nets = R.load()
        P, W, H, _ = R.build_v4(leaves, nets, 3369.6)
        tag = 'a2_v4'
    else:
        F.install_pin_models()
        if a.faces in ('band', 'bandw'):
            base = R.port_face
            cdc = ('aSW', 't_wfc', 'f_wfc', 'sel', 'col', 'qSW', 't_gather')
            side = 'E' if a.faces == 'band' else 'W'
            R.port_face = lambda p: side if p.startswith(cdc) else base(p)
        vo = F.VARIANTS[a.variant]
        leaves, nets = R.load()
        ol = dict(F.OUTLINES)
        ol.update(vo.get('outlines', {}))
        leaves, nets = F.transform(leaves, nets, ol)
        P, W, H, _ = (F.build_mid if vo.get('family') == 'mid' else F.build)(leaves, nets, 3369.6, vo)
        tag = 'a2f_' + a.variant
    res = dict(schema='opentallas.s81.vm-reach-price.v1', floorplan=tag, faces=None if a.baseline else a.faces,
               rectangle_um=[round(W, 1), round(H, 1)], model=__doc__.split('\n')[2].strip(), by_reach={})
    for rr in a.reach:
        m = measure(P, nets, W, H, rr)
        m['price'] = price(m['write']['added_edges'], m['read']['added_edges'])
        res['by_reach'][str(rr)] = m
        print(rr, {k: (v['added_edges'], [(h['hop'], h['max_um'], h['relay_stages']) for h in v['hops']])
                   for k, v in m.items() if k != 'price'})
        print('   price', m['price'])
    out = Path(a.out or ROOT / f'results/arch/s81_vm_a2f_1015/reach_price_{tag}.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
