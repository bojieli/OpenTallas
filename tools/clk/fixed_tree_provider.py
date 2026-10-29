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


def provider_join(layer_at, at, pin_layer, pxy, entering, original, actual_xy=None):
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
    pts.extend((f'M{i}',px,py) for i in range(6,2,-1))
    ax,ay=actual_xy or pxy
    if ax!=px and ay!=py:raise ValueError('CLK M3 escape jog is not straight')
    if (ax,ay)!=(px,py):pts.append(('M3',ax,ay))
    pts.extend((f'M{i}',ax,ay) for i in (2,1))
    return pts



def native_access(endpoints, landings, stub_doc, via_half=(.016,.027)):
    """Keep actual pin metal separate from explicit, reviewed parent M7 stubs."""
    if landings is None and stub_doc is None:return {},{}
    if landings is None or stub_doc is None:raise ValueError('native landings and explicit PHY stubs are a pair')
    if stub_doc.get('status')!='PASS_GEOMETRY' or stub_doc.get('failures'):
        raise ValueError('PHY stub geometry is not qualified')
    normal={r['port']:r for r in landings['records']};stubs={r['port']:r for r in stub_doc['stubs']}
    if len(normal)!=len(landings['records']) or len(stubs)!=len(stub_doc['stubs']) or set(normal)&set(stubs):
        raise ValueError('duplicate native pin landing/stub')
    if set(normal)|set(stubs)!=set(endpoints):raise ValueError('native landing/stub coverage is incomplete')
    hx,hy=via_half
    for port,r in {**normal,**stubs}.items():
        ep=endpoints[port]
        if any(ep[k]!=r[k] for k in ('inst','pin','net')) or ep['layer']!='M7':
            raise ValueError('native landing endpoint identity changed: '+port)
        if any(abs(a-b)>1e-6 for a,b in zip(ep['rect_um'],r['rect_um'])):
            raise ValueError('native M7 pin geometry changed: '+port)
        x,y=r['entry_xy_um'];rect=r['m7_stub_um'] if port in stubs else ep['rect_um']
        if not (rect[0]<=x-hx+1e-8 and x+hx<=rect[2]+1e-8 and rect[1]<=y-hy+1e-8 and y+hy<=rect[3]+1e-8):
            raise ValueError('VIA78 is outside declared actual pin/stub metal: '+port)
        if port in stubs:
            nr=ep['rect_um']
            if abs(rect[0]-nr[0])>1e-6 or abs(rect[2]-nr[2])>1e-6 or rect[1]>nr[1] or rect[3]<nr[3]:
                raise ValueError('PHY stub must be a continuous same-column extension of actual pin: '+port)
    return {**normal,**stubs},stubs


def patch_once(source, old, new):
    if source.count(old)!=1:raise ValueError('fixed_tree integration anchor changed: '+old[:80])
    return source.replace(old,new,1)


def adapted_source(source):
    source=patch_once(source,"REPO = Path(__file__).resolve().parents[2]","REPO = Path(_provider_repo)")
    source=patch_once(source,"    ports['root'] = dict(layer='M9',xy=M['meta']['root_um'])", """    ports['root'] = dict(layer='M9',xy=M['meta']['root_um'])
    native_plan, native_stubs = _provider_native_access(endpoints,_native_landing_doc,_native_stub_doc)
    _provider_stub_xy.update({tuple(r['entry_xy_um']):tuple(endpoints[k]['xy']) for k,r in native_stubs.items()})
    nets, ports, endpoints, provider_report = _provider_loads.extend(nets, ports, endpoints,
        _provider_inventory, _provider_bindings, _provider_via12)
    provider_only = {r['port']: endpoints[r['port']] for r in provider_report['rows']}
    M['taps'] = taps + [dict(port=k, layer=v['layer'], xy=ports[k]['xy']) for k,v in provider_only.items()]
    _provider_m1_xy.update({tuple(ports[k]['xy']):tuple(v['xy']) for k,v in provider_only.items()})
    (out/'provider_endpoints.json').write_text(json.dumps(provider_report)+'\\n')
    _provider_xy.update(tuple(round(v,6) for v in r['xy']) for r in provider_report['rows'])
""")
    source=patch_once(source,"        if not entering and pin_layer == 'M7':", """        if not entering and pin_layer == 'M1':
            pts = _provider_join(layer_at,at,pin_layer,pxy,entering,original_join,_provider_m1_xy.get(tuple(pxy)))
        elif not entering and pin_layer == 'M7':""")
    source=patch_once(source,"        out = [pts[0]]", """        if not entering and pin_layer == 'M7' and tuple(pxy) in _provider_stub_xy:
            native_xy=_provider_stub_xy[tuple(pxy)]
            if pts[-1][1:] != native_xy:pts.append(('M7',*native_xy))
        out = [pts[0]]""")
    source=patch_once(source,"        ep=endpoints[tap['port']];x,refy=ep['xy'];x0,y0,x1,y1=ep['rect_um']", """        ep=endpoints[tap['port']];x,refy=ep['xy']
        access_rect=native_stubs[tap['port']]['m7_stub_um'] if tap['port'] in native_stubs else ep['rect_um']
        x0,y0,x1,y1=access_rect""")
    source=patch_once(source,"        selected=None\n        for y in candidates:", """        if tap['port'] in native_plan:
            candidates=[native_plan[tap['port']]['entry_xy_um'][1]]
        selected=None
        for y in candidates:""")
    source=patch_once(source,"    (out/'endpoint_access.json').write_text", """        if tap['port'] in native_stubs:
            endpoint_access[tap['port']].update(m7_enclosure_inside=False,
                access_kind='explicit reviewed parent M7 stub + VIA78; actual pin unchanged',
                m7_stub_um=native_stubs[tap['port']]['m7_stub_um'],native_pin_rect_um=ep['rect_um'])
    (out/'endpoint_access.json').write_text""")
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
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    ap.add_argument('--native-clock-landings',type=Path)
    ap.add_argument('--phy-clock-stubs',type=Path)
    a,base_args=ap.parse_known_args(argv)
    facts=json.loads(a.provider_via_facts.read_text())
    m1=[r[1:] for r in facts['tech_vias_dbu']['VIA12'] if r[0]=='M1']
    if len(m1)!=1:raise ValueError('ambiguous actual VIA12 M1 enclosure')
    x0,y0,x1,y1=m1[0]
    ns=dict(__file__=str(a.base_adapter),__name__='provider_fixed_tree',_provider_loads=P,_provider_repo=str(a.repo),
        _provider_inventory=json.loads(a.provider_clock_loads.read_text()),
        _provider_bindings=json.loads(a.provider_bindings.read_text()),
        _provider_via12=(max(abs(x0),abs(x1)),max(abs(y0),abs(y1))),
        _provider_join=provider_join,_provider_xy=set(),_provider_stub_xy={},_provider_m1_xy={},
        _provider_native_access=native_access,
        _native_landing_doc=json.loads(a.native_clock_landings.read_text()) if a.native_clock_landings else None,
        _native_stub_doc=json.loads(a.phy_clock_stubs.read_text()) if a.phy_clock_stubs else None)
    src=adapted_source(a.base_adapter.read_text())
    exec(compile(src,str(a.base_adapter),'exec'),ns)
    old=sys.argv;sys.argv=[str(a.base_adapter)]+base_args
    try:ns['main']()
    finally:sys.argv=old

if __name__=='__main__':main()
