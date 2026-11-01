#!/usr/bin/env python3
"""Disabled sampled-protocol +1-edge profile: land every input and register exact next-state outputs.

Clock stays direct. Timed resets are landed too (+1 boot/reset edge). Native state
and arithmetic remain intact. Outputs use native next-state plus OLD landed
inputs, so the profile implements the previous edge's complete native output.
No canonical recipe consumes this experiment.
"""
import argparse
import copy
import json
from pathlib import Path

ONE = format(1, '032b')


def materialize(original, top, clock):
    doc = copy.deepcopy(original)
    m = doc['modules'][top]
    cells, ports, nets = m['cells'], m['ports'], m['netnames']
    if ports[clock]['direction'] != 'input' or len(ports[clock]['bits']) != 1:
        raise ValueError('exact scalar input clock required')
    clk = ports[clock]['bits'][0]
    native_cells = list(cells)
    nid = max(b for n in nets.values() for b in n['bits'] if isinstance(b, int))

    def fresh():
        nonlocal nid
        nid += 1
        return nid

    def bitcell(name, typ, conn, params=None):
        cells[name] = dict(hide_name=0, type=typ, parameters=params or {},
                           attributes=dict(keep=ONE), connections=conn,
                           port_directions={p: 'output' if p in ('Q', 'Y') else 'input' for p in conn})

    landed = {}
    for pn, port in ports.items():
        if port['direction'] != 'input' or pn == clock:
            continue
        for i, b in enumerate(port['bits']):
            if not isinstance(b, int) or b in landed:
                raise ValueError('input aliases/constants require an explicit contract')
            q = landed[b] = fresh()
            bitcell(f'peer_land_in_{q}', '$dff', dict(CLK=[clk], D=[b], Q=[q]),
                    dict(WIDTH=ONE, CLK_POLARITY=ONE))
    for cn in native_cells:
        c = cells[cn]
        for pn, bits in c['connections'].items():
            if c['port_directions'][pn] == 'input':
                c['connections'][pn] = [landed.get(b, b) for b in bits]
    for nn, net in nets.items():
        if nn not in ports:
            net['bits'] = [landed.get(b, b) for b in net['bits']]
    drivers = {b: (cn, pn, i) for cn in native_cells for pn, bs in cells[cn]['connections'].items()
               if cells[cn]['port_directions'][pn] == 'output' for i, b in enumerate(bs) if isinstance(b, int)}
    landed_q = set(landed.values())
    cache = {}
    active = set()
    native_ff = set()

    def nextbit(b):
        if not isinstance(b, int) or b in landed_q:
            return b
        if b in cache:
            return cache[b]
        if b in active:
            raise ValueError('combinational cycle')
        if b == clk or b not in drivers:
            raise ValueError(f'unmodelled native cone leaf {b}')
        cn, pn, index = drivers[b]
        c = cells[cn]
        typ = c['type']
        if typ in ('$dff', '$adff'):
            if pn != 'Q' or c['connections']['CLK'] != [clk] or int(c['parameters']['CLK_POLARITY'], 2) != 1:
                raise ValueError('only one positive-edge clock supported')
            native_ff.add(cn)
            d = c['connections']['D'][index]
            if typ == '$adff':
                width = len(c['connections']['Q'])
                reset = c['parameters']['ARST_VALUE'].zfill(width)[::-1][index]
                pol = int(c['parameters']['ARST_POLARITY'], 2)
                q = fresh()
                a, z = ([d], [reset]) if pol else ([reset], [d])
                bitcell(f'peer_next_reset_{q}', '$mux',
                        dict(A=a, B=z, S=c['connections']['ARST'], Y=[q]), dict(WIDTH=ONE))
                d = q
            cache[b] = d
            return d
        if not typ.startswith('$') or typ.startswith('$mem'):
            raise ValueError(f'opaque/memory output needs a source contract: {cn} {typ}')
        active.add(b)
        cc = copy.deepcopy(c)
        for p, bs in c['connections'].items():
            if c['port_directions'][p] == 'output':
                cc['connections'][p] = [fresh() for _ in bs]
                cache.update(zip(bs, cc['connections'][p]))
        for p, bs in c['connections'].items():
            if c['port_directions'][p] == 'input':
                cc['connections'][p] = [nextbit(x) for x in bs]
        cc['attributes'] = {}
        cells[f'peer_next_logic_{len(cells)}'] = cc
        active.remove(b)
        return cache[b]

    outputs = 0
    for pn, port in ports.items():
        if port['direction'] != 'output':
            continue
        for i, b in enumerate(port['bits']):
            d = nextbit(landed.get(b, b))
            q = fresh()
            bitcell(f'peer_land_out_{q}', '$dff', dict(CLK=[clk], D=[d], Q=[q]),
                    dict(WIDTH=ONE, CLK_POLARITY=ONE))
            port['bits'][i] = q
            nets[pn]['bits'][i] = q
            outputs += 1
    return doc, dict(schema='opentallas.peer_landing_prep.v1', top=top, clock=clock,
                     enabled=False, added_mission_edges=1, added_boot_reset_edges=1,
                     input_ff_bits=len(landed), output_ff_bits=outputs,
                     native_ff_cones=len(native_ff), canonical_adoption='HELD',
                     conditions=['clock running during reset', 'sampled synchronous protocol',
                                 'compiler and feedback round trips each include landing',
                                 'keepdc required for physical constant-output FFs',
                                 'full protocol miter/mutant and physical gates required'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pre', type=Path)
    p.add_argument('post', type=Path)
    p.add_argument('ledger', type=Path)
    p.add_argument('--top', required=True)
    p.add_argument('--clock', required=True)
    a = p.parse_args()
    out, ledger = materialize(json.loads(a.pre.read_text()), a.top, a.clock)
    a.post.write_text(json.dumps(out))
    a.ledger.write_text(json.dumps(ledger, indent=2) + '\n')
    print(json.dumps(ledger))


if __name__ == '__main__':
    main()
