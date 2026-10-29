#!/usr/bin/env python3
"""Actual provider CLK endpoints for the existing fixed-clock graph.

This adapter adds loads to existing nets only. It never adds a clock buffer,
changes a tap, substitutes a clock source, or fabricates an M7 pin for an M1
flop terminal. Geometry and timing remain obligations of the fixed-tree build.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys


def tcl_word(value):
    """Preserve mapped names containing literal dollar signs/backslashes."""
    if any(c in value for c in '{}\n\r'):
        raise ValueError('unsupported brace/newline in physical terminal name')
    return '{' + value + '}'


def pin_entry(load, dbu, via12):
    """Select a VIA12 enclosure wholly inside actual M1 CLK pin metal."""
    candidates = []
    hx, hy = via12
    for shape in load['shapes_dbu']:
        layer, x0, y0, x1, y1 = shape
        if layer != 'M1' or x1-x0 < 2*hx-1e-7 or y1-y0 < 2*hy-1e-7:
            continue
        x, y = (x0+x1)/2, (y0+y1)/2
        candidates.append((-(y1-y0), -(x1-x0), x, y, shape))
    if not candidates:
        raise ValueError(f"actual M1 CLK metal cannot enclose VIA12: {load['inst']}")
    _, _, x, y, shape = min(candidates)
    return dict(layer='M1', xy=[x/dbu,y/dbu], rect_um=[v/dbu for v in shape[1:]],
                inst=load['inst'], pin='CLK', net=load['net'],
                via12_enclosure_um=[hx/dbu,hy/dbu], actual_m1=True)


def extend(nets, ports, endpoints, inventory, bindings, via12=(9,11)):
    """Return new graph objects, leaving every existing cell/net/endpoint intact.

    `nets` uses the tree's raw net names; provider facts use the actual ODB
    ck_ prefix. The exact binding table controls that translation, including
    stages that take the inverter's A net instead of Y.
    """
    nets, ports, endpoints = copy.deepcopy(nets), copy.deepcopy(ports), copy.deepcopy(endpoints)
    bynet = {n['name']: n for n in nets}
    if len(bynet) != len(nets):
        raise ValueError('duplicate original clock net')
    clock_bind = {k:v for k,v in bindings['ports'].items() if v['role']=='clock'}
    known = {v['net'] for v in clock_bind.values()}
    seen = set(); rows = []; net_count = {}
    dbu = inventory['dbu']
    if not isinstance(dbu,(int,float)) or dbu <= 0:
        raise ValueError('invalid actual database units')
    for index, load in enumerate(inventory['loads']):
        name, actual = load['inst'], load['net']
        if name in seen:
            raise ValueError(f'duplicate provider CLK terminal: {name}')
        seen.add(name)
        if actual not in known:
            raise ValueError(f'provider clock has no selected tap binding: {actual}')
        raw = actual if actual in bynet else actual[3:] if actual.startswith('ck_') else actual
        if raw not in bynet:
            raise ValueError(f'provider clock is absent from the unchanged tree: {actual}')
        if not load['master'].startswith(('DFF','SDFF')):
            raise ValueError(f'provider clock load is not a sequential cell: {name}')
        port = f'provider_clk_{index:05d}'
        if port in ports or port in endpoints:
            raise ValueError(f'duplicate physical endpoint key: {port}')
        ep = pin_entry(load, dbu, via12)
        ports[port] = dict(layer=ep['layer'],xy=ep['xy'])
        endpoints[port] = ep
        bynet[raw]['loads'].append('port:'+port)
        rows.append(dict(port=port,stage=load['stage'],raw_net=raw,**ep))
        net_count[actual] = net_count.get(actual,0)+1
    return nets, ports, endpoints, dict(schema='opentallas.provider_clock_loads.v1',
        status='ACTUAL_M1_ENDPOINTS_UNROUTED', physical_route=False, timing_qualified=False,
        loads=len(rows), nets=len(net_count), max_added_fanout=max(net_count.values(),default=0),
        added_cells=0, cycles_added=0, rows=rows)



def lower_escape_shapes(report, tech_vias_dbu, dbu):
    """Actual M1->M7 access stacks, including real via enclosures and AREA pads.

    M7->M8 risers/landings are deliberately absent: they require the joint
    clock/PG track allocation. These shapes reserve the fixed lower escape
    before a power planner consumes the same cell-local columns.
    """
    pads={'M2':(.019,.009),'M3':(.009,.020),'M4':(.043,.012),
          'M5':(.012,.043),'M6':(.036,.016),'M7':(.016,.036)}
    out=[]
    for row in report['rows']:
        x,y=row['xy'];net=row['net']
        for via in ('VIA12','VIA23','VIA34','VIA45','VIA56','VIA67'):
            for layer,x0,y0,x1,y1 in tech_vias_dbu[via]:
                if not layer.startswith('M'):continue
                out.append([net,layer,x+x0/dbu,y+y0/dbu,x+x1/dbu,y+y1/dbu])
        for layer,(hx,hy) in pads.items():
            out.append([net,layer,x-hx,y-hy,x+hx,y+hy])
    return out


def rewrite_endpoint_tcl(text, endpoints):
    """Replace only synthetic encoder BTerms with actual ITerms."""
    import re
    counts = {}
    def replace(match):
        name=match.group(1)
        if name not in endpoints:return match.group(0)
        counts[name]=counts.get(name,0)+1
        ep=endpoints[name]
        return '$e addITerm [IT '+tcl_word(ep['inst'])+' '+tcl_word(ep['pin'])+']'
    result=re.sub(r'\$e addBTerm \[BT ([^\]\s]+)\]',replace,text)
    wrong={name:counts.get(name,0) for name in endpoints if counts.get(name,0)!=1}
    if wrong:raise ValueError(f'actual endpoint encoder count is not one: {wrong}')
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('graph','loads','bindings','out'):ap.add_argument('--'+key,required=True,type=Path)
    a=ap.parse_args(argv)
    graph=json.loads(a.graph.read_text())
    nets,ports,endpoints,report=extend(graph['nets'],graph['ports'],graph['endpoints'],
        json.loads(a.loads.read_text()),json.loads(a.bindings.read_text()))
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'graph.json').write_text(json.dumps(dict(graph,nets=nets,ports=ports,endpoints=endpoints))+'\n')
    report['inputs']={key:dict(path=str(getattr(a,key)),sha256=hashlib.sha256(getattr(a,key).read_bytes()).hexdigest()) for key in ('graph','loads','bindings')}
    (a.out/'provider_endpoints.json').write_text(json.dumps(report)+'\n')
    print(f"PROVIDER_CLOCK_ENDPOINTS {report['loads']} actual M1 CLK terminals on {report['nets']} unchanged nets; UNROUTED")

if __name__=='__main__':main()
