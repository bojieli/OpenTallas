"""Pin-typed actual connectivity checks for the source-specific reset canary.
No geometry gate or release decision is made here.
"""
from collections import defaultdict
import re


class TypedGraph:
    def __init__(self, data):
        if data.get('schema') != 'opentallas.typed_physical_connectivity.v1':
            raise ValueError('actual pin-typed connectivity is mandatory')
        self.cells, self.ports = data['cells'], data['ports']
        self.drivers, self.loads = defaultdict(list), defaultdict(list)
        for name, c in self.cells.items():
            for pin, p in c['ports'].items():
                net = p.get('net')
                if net is None:
                    continue
                if p['direction'] not in {'INPUT', 'OUTPUT'}:
                    continue
                (self.drivers if p['direction'] == 'OUTPUT' else self.loads)[net].append(('cell', name, pin))
        for name, p in self.ports.items():
            net = p.get('net')
            if net is not None:
                (self.drivers if p['direction'] == 'INPUT' else self.loads)[net].append(('port', name, None))

    def driver(self, net):
        if net is None or len(self.drivers.get(net, [])) != 1:
            raise ValueError('typed net does not have exactly one driver: ' + str(net))
        return self.drivers[net][0]

    def buffer(self, name):
        c = self.cells[name]
        if not re.fullmatch(r'(?:BUF|INV)\w*_ASAP7_75t_R', c['master']):
            return False
        p = c['ports']
        if set(p) != {'A', 'Y'} or p['A']['direction'] != 'INPUT' or p['Y']['direction'] != 'OUTPUT':
            raise ValueError('typed buffer pin class changed')
        return True

    def origin(self, net):
        parity, seen = 0, set()
        while True:
            if net in seen:
                raise ValueError('typed buffer loop')
            seen.add(net)
            d = self.driver(net)
            if d[0] != 'cell' or not self.buffer(d[1]):
                return d, parity
            if d[2] != 'Y':
                raise ValueError('typed buffer output changed')
            c = self.cells[d[1]]
            parity ^= int(c['master'].startswith('INV'))
            net = c['ports']['A']['net']

    def high(self, net):
        d, parity = self.origin(net)
        return d[0] == 'cell' and d[2] == 'H' and parity == 0 and self.cells[d[1]]['master'] == 'TIEHIx1_ASAP7_75t_R'

    def terminals(self, net):
        pending, seen, ends = [(net, 0)], set(), set()
        while pending:
            net, parity = pending.pop()
            if (net, parity) in seen:
                raise ValueError('typed buffer fanout cycle or reconvergence')
            seen.add((net, parity))
            for sink in self.loads.get(net, []):
                if sink[0] == 'cell' and self.buffer(sink[1]):
                    if sink[2] != 'A':
                        raise ValueError('typed buffer input changed')
                    c = self.cells[sink[1]]
                    pending.append((c['ports']['Y']['net'], parity ^ int(c['master'].startswith('INV'))))
                else:
                    ends.add((*sink, parity))
        return ends

    def exact_cell(self, name, master, inputs, outputs):
        c = self.cells.get(name)
        if c is None or c['master'] != master or set(c['ports']) != set(inputs) | set(outputs):
            raise ValueError('typed cell/pin class changed: ' + name)
        if any(c['ports'][pin]['direction'] != 'INPUT' for pin in inputs) or any(c['ports'][pin]['direction'] != 'OUTPUT' for pin in outputs):
            raise ValueError('typed pin direction changed: ' + name)
        return c['ports']


def verify_typed(data, rows):
    g = TypedGraph(data)
    reset_names = ['u_rst.rst_n$_DFF_PN0_', 'u_rst.sync_q[1]$_DFF_PN0_', 'u_rst.sync_q[0]$_DFF_PN0_']
    critical = set(reset_names)
    for index, name in enumerate(reset_names):
        p = g.exact_cell(name, 'DFFASRHQNx1_ASAP7_75t_R', ['CLK', 'D', 'RESETN', 'SETN'], ['QN'])
        if g.origin(p['CLK']['net']) != (('port', 'clk_ctrl', None), 0):
            raise ValueError('typed reset CLK is not the actual qualified clock')
        if g.origin(p['RESETN']['net']) != (('port', 'rst_n', None), 0):
            raise ValueError('typed RESETN is functional or wrong-polarity')
        if not g.high(p['SETN']['net']):
            raise ValueError('typed SETN is not genuinely tied high')
        if index + 1 < len(reset_names):
            if g.origin(p['D']['net']) != (('cell', reset_names[index + 1], 'QN'), 1):
                raise ValueError('typed reset D has functional data/enable or wrong polarity')
        elif not g.high(p['D']['net']):
            raise ValueError('typed reset release seed is not genuinely tied high')
    for row in rows:
        pin, mask, capture = row['pin'], row['mask'], row['capture']
        if pin not in g.ports or g.ports[pin]['direction'] != 'INPUT':
            raise ValueError('typed native pin missing')
        c = g.cells.get(mask)
        if c is None or not re.fullmatch(r'AND2x\w*_ASAP7_75t_R', c['master']):
            raise ValueError('typed mask is not AND2')
        p = c['ports']
        if set(p) != {'A', 'B', 'Y'} or p['A']['direction'] != 'INPUT' or p['B']['direction'] != 'INPUT' or p['Y']['direction'] != 'OUTPUT':
            raise ValueError('typed AND pins changed')
        expected = {(('port', pin, None), 0), (('cell', reset_names[0], 'QN'), 1)}
        if {g.origin(p[k]['net']) for k in ['A', 'B']} != expected:
            raise ValueError('typed AND has a functional/wrong-polarity mask operand')
        if g.terminals(g.ports[pin]['net']) not in [{('cell', mask, 'A', 0)}, {('cell', mask, 'B', 0)}]:
            raise ValueError('typed input is shared or has extra functional logic')
        if g.terminals(p['Y']['net']) != {('cell', capture, 'D', 0)}:
            raise ValueError('typed mask output has extra/shared capture or logic')
        cp = g.exact_cell(capture, 'DFFHQNx1_ASAP7_75t_R', ['CLK', 'D'], ['QN'])
        if g.origin(cp['CLK']['net']) != (('port', 'clk_ctrl', None), 0):
            raise ValueError('typed capture clock changed')
        if g.origin(cp['D']['net']) != (('cell', mask, 'Y'), 0):
            raise ValueError('typed capture D changed')
        critical.update([mask, capture])
    return g, critical
