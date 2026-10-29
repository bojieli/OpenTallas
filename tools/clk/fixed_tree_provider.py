#!/usr/bin/env python3
"""Run an existing fixed_tree prebuild with actual provider flop endpoints.

The base adapter is explicit, not silently imported from an arbitrary worktree.
The original M7 partition endpoints and clock cells are retained. New provider
endpoints terminate on their actual M1 CLK metal through an M7 riser and a real
adjacent-layer via chain. No M7 pin is invented. The existing all-net/power
short, spacing and routed-Tcl census remains authoritative and fail-closed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import provider_clock_loads as P


def provider_join(layer_at, at, pin_layer, pxy, entering, original):
    if entering or pin_layer != 'M1':
        return original([],layer_at,at,pin_layer,pxy,entering)
    x,y=at;px,py=pxy
    pts=[(layer_at,x,y)]
    # Only top metal moves horizontally. M7 is a vertical riser on the actual
    # CLK bar column; the lower chain stays at that bar's actual coordinate.
    if layer_at=='M9':pts.append(('M8',x,y))
    elif layer_at!='M8':raise ValueError('provider branch must arrive on M8/M9')
    if x!=px:pts.append(('M8',px,y))
    pts.append(('M7',px,y))
    if y!=py:pts.append(('M7',px,py))
    pts.extend((f'M{i}',px,py) for i in range(6,0,-1))
    return pts


def patch_once(source, old, new):
    if source.count(old)!=1:raise ValueError('fixed_tree integration anchor changed: '+old[:80])
    return source.replace(old,new,1)


def adapted_source(source):
    source=patch_once(source,"    ports['root'] = dict(layer='M9',xy=M['meta']['root_um'])", """    ports['root'] = dict(layer='M9',xy=M['meta']['root_um'])
    nets, ports, endpoints, provider_report = _provider_loads.extend(nets, ports, endpoints,
        _provider_inventory, _provider_bindings, _provider_via12)
    provider_only = {r['port']: endpoints[r['port']] for r in provider_report['rows']}
    M['taps'] = taps + [dict(port=k, layer=v['layer'], xy=v['xy']) for k,v in provider_only.items()]
    (out/'provider_endpoints.json').write_text(json.dumps(provider_report)+'\\n')
    _provider_xy.update(tuple(round(v,6) for v in r['xy']) for r in provider_report['rows'])
""")
    source=patch_once(source,"        if not entering and pin_layer == 'M7':", """        if not entering and pin_layer == 'M1':
            pts = _provider_join(layer_at,at,pin_layer,pxy,entering,original_join)
        elif not entering and pin_layer == 'M7':""")
    source=patch_once(source,"        tmp=[];original_steps(tmp,pts,**kwargs)", """        tmp=[];original_steps(tmp,pts,**kwargs)
        provider = bool(pts and pts[-1][0]=='M1' and tuple(round(v,6) for v in pts[-1][1:]) in _provider_xy)
        pads = {'M2':(19,9),'M3':(9,20),'M4':(43,12),'M5':(12,43),'M6':(36,16),'M7':(16,36)}
""")
    source=patch_once(source,"                lines.append(line)\n                if (a,b)==('M7','M8'):lines.append('$e addRect -96 -40 96 40')", """                if provider and a in pads:
                    hx,hy=pads[a];lines.append(f'$e addRect {-hx} {-hy} {hx} {hy}')
                lines.append(line)
                if provider and b in pads:
                    hx,hy=pads[b];lines.append(f'$e addRect {-hx} {-hy} {hx} {hy}')
                if (a,b)==('M7','M8'):lines.append('$e addRect -96 -40 96 40')""")
    source=patch_once(source,"        shapes += port_access_shapes(wires,cells,ports,next(iter(masters)))", """        shapes += port_access_shapes(wires,cells,ports,next(iter(masters)))
        shapes += [tuple(r) for r in _provider_loads.lower_escape_shapes(provider_report,
            via_facts['tech_vias_dbu'], dbu)]""")
    source=patch_once(source,"        return '$e addITerm [IT '+ep['inst']+' '+ep['pin']+']'", """        return '$e addITerm [IT '+_provider_loads.tcl_word(ep['inst'])+' '+_provider_loads.tcl_word(ep['pin'])+']'""")
    return source


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,add_help=False)
    for name in ('base-adapter','provider-clock-loads','provider-bindings','provider-via-facts'):
        ap.add_argument('--'+name,type=Path,required=True)
    a,base_args=ap.parse_known_args(argv)
    facts=json.loads(a.provider_via_facts.read_text())
    m1=[r[1:] for r in facts['tech_vias_dbu']['VIA12'] if r[0]=='M1']
    if len(m1)!=1:raise ValueError('ambiguous actual VIA12 M1 enclosure')
    x0,y0,x1,y1=m1[0]
    ns=dict(__file__=str(a.base_adapter),__name__='provider_fixed_tree',_provider_loads=P,
        _provider_inventory=json.loads(a.provider_clock_loads.read_text()),
        _provider_bindings=json.loads(a.provider_bindings.read_text()),
        _provider_via12=(max(abs(x0),abs(x1)),max(abs(y0),abs(y1))),
        _provider_join=provider_join,_provider_xy=set())
    src=adapted_source(a.base_adapter.read_text())
    exec(compile(src,str(a.base_adapter),'exec'),ns)
    old=sys.argv;sys.argv=[str(a.base_adapter)]+base_args
    try:ns['main']()
    finally:sys.argv=old

if __name__=='__main__':main()
