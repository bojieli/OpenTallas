#!/usr/bin/env python3
"""Materialize an existing clock topology using PG-aware fixed-wire planning.

No GRT guide is consumed. Inputs are the existing clock netlist, exact cell sites,
real LEF pin metal, die PG grid and the prepared source's endpoint ITerm map.
This is a die-local adapter around existing fixed-wire geometry/encoder APIs.
"""
import argparse
from collections import Counter, defaultdict
import contextlib
import hashlib
import json
import math
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools/die_plan'))
import clock_routed as CR
import die_clock_128 as C128
import die_clock_mesh as DCM
import die_infra as DI


def lef_access(text, master):
    match = re.search(r'(?ms)^MACRO\s+'+re.escape(master)+r'\s*\n(.*?)^END\s+'+re.escape(master)+r'\s*$', text)
    if not match:
        raise ValueError(f'LEF macro absent: {master}')
    body = match[1]
    size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body)
    access = {}
    for pin in ('A', 'Y'):
        pm = re.search(r'(?ms)^\s*PIN\s+'+pin+r'\s*\n(.*?)^\s*END\s+'+pin+r'\s*$', body)
        if not pm:
            raise ValueError(f'{master}/{pin} absent')
        layers = re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\Z)', pm[1], re.S)
        rects = [tuple(map(float, r)) for layer, contents in layers if layer == 'M1'
                 for r in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', contents)]
        # Choose an actual vertical M1 bar, keeping A/Y on distinct escape rows.
        bars = [r for r in rects if r[3]-r[1] > r[2]-r[0] and r[2]-r[0] >= .0179]
        target_y = .09 if pin == 'A' else .18
        bars = [r for r in bars if r[1]+.008 <= target_y <= r[3]-.008]
        if not bars:
            raise ValueError(f'no legal M1 access bar for {master}/{pin}')
        chosen = min(bars, key=lambda r:r[0]) if pin == 'A' else max(bars, key=lambda r:r[2])
        access[pin] = ((chosen[0]+chosen[2])/2, target_y)
    return tuple(map(float, size.groups())), access


def clock_graph(text, tree):
    cells, driven, loads = {}, {}, defaultdict(list)
    pattern = r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\w+)\s*\(([^;]+)\);'
    for master, name, pins in re.findall(pattern, text):
        pp = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', pins))
        if set(pp) != {'A', 'Y'}:
            raise ValueError(f'clock cell is not an A/Y primitive: {name}')
        key = name[3:] if name.startswith('ck_') else name
        xy = tree['sites'].get(key)
        if xy is None:
            raise ValueError(f'no exact physical site: {name}')
        cells[name] = dict(x=xy[0], y=xy[1], lib=master, orient='R0')
        if pp['Y'] in driven:
            raise ValueError(f'multiple clock drivers: {pp["Y"]}')
        driven[pp['Y']] = name
        loads[pp['A']].append(name)
    if not cells:
        raise ValueError('no clock primitives parsed')
    aliases = dict(re.findall(r'(?m)^\s*assign\s+(\w+)\s*=\s*(\w+)\s*;', text))
    tap_ports = {t['port'] for t in tree['taps']}
    if set(aliases) != tap_ports:
        raise ValueError('clock output aliases do not match the exact tree taps')
    for port, net in aliases.items():
        loads[net].append('port:'+port)
    driven['root'] = 'port:root'
    if set(loads) != set(driven):
        raise ValueError(f'undriven/dead nets: {sorted(set(loads)^set(driven))}')
    nets = [dict(name=name, drv=drv, loads=loads[name]) for name, drv in driven.items()]
    return cells, nets


@contextlib.contextmanager
def real_pin_access(access,window_um=8.64,access_patches=False):
    old = dict(CR.PIN_ACCESS)
    old_bars = dict(C128.PIN_BAR_X)
    old_riser = C128.STACK_RISER_MAX_UM
    original_join = CR._port_join
    original_steps=CR._emit_steps;original_pad_layers=CR.stack_pad_layers
    def area_steps(lines,pts,**kwargs):
        tmp=[];original_steps(tmp,pts,**kwargs)
        transitions=iter([(a[0],b[0]) for a,b in zip(pts,pts[1:]) if a[0]!=b[0]])
        for line in tmp:
            if 'addTechVia' in line:
                a,b=next(transitions)
                if (a,b)==('M8','M7'):lines.append('$e addRect -96 -40 96 40')
                lines.append(line)
                if (a,b)==('M7','M8'):lines.append('$e addRect -96 -40 96 40')
            else:lines.append(line)
    def pad_layers(stack):
        pads=original_pad_layers(stack)
        # The explicit VIA78 patch above supplies the M8 area exactly once.
        for lays in pads.values():lays.discard('M8')
        return pads

    def adjacent_join(lines, layer_at, at, pin_layer, pxy, entering):
        if not entering and pin_layer == 'M7':
            x, y = at; px, py = pxy
            pts = [(layer_at,x,y)]
            # Stay above the macro until the final VIA78 at actual pin metal.
            if layer_at == 'M9':
                if y != py: pts.append(('M9',x,py))
                pts.append(('M8',x,py))
                if x != px: pts.append(('M8',px,py))
            else:
                xj = _jog_x7(px, y, py, x, _ENDPOINT_NET[(round(px,6),round(py,6))]) if (y != py and _JOGX > 0) else px
                if x != xj: pts.append(('M8',xj,y))
                if y != py:
                    pts += [('M9',xj,y),('M9',xj,py),('M8',xj,py)]
                    if xj != px: pts.append(('M8',px,py))
            pts.append(('M7',px,py))
        else:
            pts = original_join(lines,layer_at,at,pin_layer,pxy,entering)
        out = [pts[0]]
        for point in pts[1:]:
            prev = out[-1]
            if point[0] != prev[0]:
                assert point[1:] == prev[1:]
                a, b = int(prev[0][1:]), int(point[0][1:])
                step = 1 if b > a else -1
                out.extend((f'M{i}', *point[1:]) for i in range(a+step, b, step))
            out.append(point)
        return out
    try:
        CR.PIN_ACCESS.update(access)
        C128.PIN_BAR_X.update({master:{pin:point[0] for pin,point in pins.items()} for master,pins in access.items()})
        # This adapter uses the current body-bay neighborhood, then clips it
        # against the actual host and hard-core halo below. The old 2.5 um
        # constant describes a different mesh's window, not these plan bays.
        C128.STACK_RISER_MAX_UM=window_um
        CR._port_join = adjacent_join
        if access_patches:
            CR._emit_steps=area_steps;CR.stack_pad_layers=pad_layers
        yield
    finally:
        CR.PIN_ACCESS.clear()
        CR.PIN_ACCESS.update(old)
        C128.PIN_BAR_X.clear()
        C128.PIN_BAR_X.update(old_bars)
        C128.STACK_RISER_MAX_UM=old_riser
        CR._port_join = original_join
        CR._emit_steps=original_steps;CR.stack_pad_layers=original_pad_layers


_PROV_OLD = """                if ld.startswith("port:"):           # port loads: as the default comb (drop one track pair off)
                    if abs(p[1] - ty) > 1e-6:"""
_PROV_NEW = """                if ld.startswith("port:provider_clk_") and _PROV_MODE in ("A", "B"):
                    # DIE-QC-38 provider M1 CLK landing selection (no M8 landing on the pin row):
                    # near load -> on-trunk VIA78 + M7 riser to the pin row (as a clock-cell pin stack);
                    # far load  -> A: M9 drop to the nearest PG-clear M8 row, B: router-legal M8 jog + M9 drop (cell L-drop rule)
                    near = _PROV_NEAR_A if _PROV_MODE == "A" else STACK_RISER_MAX_UM
                    if abs(p[1] - ty) <= near:
                        branches.append((ld, p[0], ty)); xs_.append(p[0]); _PROV_STATS["near"] += 1
                        continue
                    if _PROV_MODE == "A":
                        yl = _prov_pg_clear_ix(p[1], p[0] + off, router, nm) if _PROV_F1 else _prov_pg_clear(p[1])
                        bx, bm = track("M9", p[0] + off, ty, yl, nm, f"drop {ld}")
                        add(("M9", bx, min(ty, yl), bx, max(ty, yl)), bm)
                        if _PROV_F1 and router is not None:
                            _pad = ("M8", nm, "access", yl - .04, yl + .04, bx - .096, bx + .096)
                            _PROV_STATS["f1_pad_hit" if router.ix.hits(_pad, first=True) else "f1_pad_clear"] += 1
                            if _PROV_F1RES == 1 or (_PROV_F1RES == 2 and abs(yl - _prov_pg_clear(p[1])) > 1e-6): router.ix.add(_pad)
                        branches.append((ld, bx, yl)); xs_.append(bx); _PROV_STATS["far_pgclear"] += 1
                        continue
                    sg = 1.0 if ty >= p[1] else -1.0
                    by, jm = track("M8", p[1] + sg * off, p[0] - mm, p[0] + mm, nm, f"jog {ld}")
                    bx, bm = track("M9", p[0], ty, by, nm, f"drop {ld}")
                    add(("M9", bx, min(ty, by), bx, max(ty, by)), bm)
                    if abs(bx - p[0]) > 1e-6:
                        add(("M8", min(bx, p[0]), by, max(bx, p[0]), by), jm)
                    branches.append((ld, bx, by)); xs_.append(bx); _PROV_STATS["far_jog"] += 1
                    continue
                if ld.startswith("port:"):           # port loads: as the default comb (drop one track pair off)
                    if abs(p[1] - ty) > 1e-6:"""
import os as _os, inspect as _inspect, bisect as _bisect
_PROV_MODE = _os.environ.get("OT_DQC38_PROV", "")
_PROV_NEAR_A = float(_os.environ.get("OT_DQC38_NEAR_A", "2.5"))
_PROV_STATS = Counter()
_NAT_MODE = _os.environ.get("OT_DQC38_NAT", "") == "1"
_PROV_STRAPS = []
_PROV_STRAPS9 = []
# DIE-QC-39 QC-001: reserve the native M7 port M8 landing row trunk column -> pin x BEFORE any tree track (vertical-trunk
# nets), so the native drop stays on its landing row and no M9 jog is drawn at a pin x inside an M9 PG strap band.
#   band = only ports whose pin x lies in an M9 strap +- (0.32 + 0.04) band (the measured 1,678); all = every native port
_LAND_RES = _os.environ.get("OT_DQC39_LANDRES", "")
# DIE-QC-39 L4/L5: a native drop that could not keep its landing row (shielded landing track blocked) jogs on M9 at the
# nearest M9-track column OUTSIDE the M9 PG strap band (<= _JOGX um from pin x), then a short M8 stub on the landing row
_JOGX = float(_os.environ.get("OT_DQC39_JOGX", "0"))
_JOG_STATS = Counter()
_ROUTER = []
_JIX = []
_JOG_CACHE = {}
_ENDPOINT_NET = {}
_NATIVE_M7 = []
def _jog_x7(px, y, py, bx, nm, pitch=.08, phase=.04, h=.04):
    """Choose a complete port join against other-net conductors, including via end pads.

    Same-net joints are accepted by MetalIndex identity, never by clipping endpoints.
    Both horizontal stubs and the full VIA89 enclosures participate in selection.
    """
    key=(nm,round(px,6),round(y,6),round(py,6),round(bx,6))
    if key in _JOG_CACHE:return _JOG_CACHE[key]
    R=_ROUTER[0]
    if not _JIX:_JIX.append(C128.MetalIndex(R.ix.space))
    J=_JIX[0];k0=round((px-phase)/pitch);lo,hi=sorted((y,py));xj=None
    via=CR.via_rects()['VIA89']
    def shape(lay,x0,y0,x1,y1):
        return (lay,nm,'access',y0,y1,x0,x1) if lay=='M8' else (lay,nm,'access',x0,x1,y0,y1)
    for d in range(int(_JOGX/pitch)+1):
        for k in ((k0,) if d==0 else (k0-d,k0+d)):
            x=round(phase+k*pitch,4)
            if abs(x-px)>_JOGX+1e-9:continue
            qs=[shape('M9',x-h,lo-h,x+h,hi+h),
                shape('M8',min(x,px)-h,py-h,max(x,px)+h,py+h),
                shape('M8',min(x,bx)-h,y-h,max(x,bx)+h,y+h)]
            for yy in (y,py):
                for lay,(hx,hy) in via.items():qs.append(shape(lay,x-hx,yy-hy,x+hx,yy+hy))
            if any(R.ix.hits(q,first=True) or J.hits(q,first=True) for q in qs):continue
            xj=x
            for q in qs:J.add(q)
            break
        if xj is not None:break
    _JOG_STATS['netaware_clear' if xj is not None else 'netaware_none']+=1
    if xj is None:xj=px # preserve failed geometry for census, never accept an unqualified join
    _JOG_CACHE[key]=xj
    return xj
def _jog_x(px, pitch=.08, phase=.04):
    k0 = round((px - phase) / pitch)
    for d in range(int(_JOGX / pitch) + 1):
        for k in ((k0,) if d == 0 else (k0 - d, k0 + d)):
            x = round(phase + k * pitch, 4)
            if abs(x - px) <= _JOGX + 1e-9 and not _x_in_m9_band(x):
                _JOG_STATS["jog_moved" if abs(x - px) > 1e-9 else "jog_at_pin"] += 1
                return x
    _JOG_STATS["jog_no_clear_column"] += 1
    return px
def _x_in_m9_band(x, sp=.32, h=.04):
    lo = [a for a, b in _PROV_STRAPS9]
    j = _bisect.bisect_right(lo, x + sp + h) - 1
    return any(x + h > a - sp and x - h < b + sp for a, b in _PROV_STRAPS9[max(0, j - 1):j + 2])
# DIE-QC-40 F1 (QC-001 shield class): a far provider M9 drop lands its M8 pad on the nearest PG-clear row whose pad
# (+-0.3 um x around the ideal drop column) is also clear of every reserved tree/shield shape of another net (the own net's
# drawn VSS shield included); the chosen pad is then reserved so later tracks + shields keep clear of it.
_PROV_F1 = _os.environ.get("OT_DQC40_F1", "") == "1"
_PROV_F1RES = int(_os.environ.get("OT_DQC40_F1RES", "1"))   # 0 none, 1 every far provider pad, 2 only pads F1 moved off the PG-clear row
def _prov_pg_clear_ix(y, x, router, nm, sp=.32, h=.04, step=.005, lim=8.64):
    if router is None: return _prov_pg_clear(y, sp, h, step, lim)
    lo = [a for a, b in _PROV_STRAPS]
    def bad(v):
        j = _bisect.bisect_right(lo, v + sp + h) - 1
        if any(v + h > a - sp and v - h < b + sp for a, b in _PROV_STRAPS[max(0, j - 1):j + 2]): return True
        return bool(router.ix.hits(("M8", nm, "access", v - h, v + h, x - .3, x + .3), first=True))
    k = 0
    while k * step <= lim:
        for v in (y - k * step, y + k * step):
            if not bad(v):
                if k: _PROV_STATS["f1_moved"] += 1
                return round(v, 4)
        k += 1
    _PROV_STATS["f1_none"] += 1
    return _prov_pg_clear(y, sp, h, step, lim)
def _prov_pg_clear(y, sp=.32, h=.04, step=.005, lim=8.64):
    lo = [a for a, b in _PROV_STRAPS]
    def bad(v):
        j = _bisect.bisect_right(lo, v + sp + h) - 1
        return any(v + h > a - sp and v - h < b + sp for a, b in _PROV_STRAPS[max(0, j - 1):j + 2])
    k = 0
    while k * step <= lim:
        for v in (y - k * step, y + k * step):
            if not bad(v): return round(v, 4)
        k += 1
    return y
_LAND_PRE = '    if _LAND_RES and router is not None:\n        for n in nets:\n            nm = n["name"]\n            dcell = not n["drv"].startswith("port:")\n            D = pin_xy(cells, n["drv"], "Y", row_y) if dcell else port_xy(n["drv"])\n            Ls = [(ld, port_xy(ld) if ld.startswith("port:") else pin_xy(cells, ld, "A", row_y)) for ld in n["loads"]]\n            if max(abs(p[0] - D[0]) for _, p in Ls) >= max(abs(p[1] - D[1]) for _, p in Ls):\n                continue\n            for ld, p in Ls:\n                if not ld.startswith("port:") or ld.startswith("port:provider_clk_") or ld == "port:root":\n                    continue\n                if abs(p[0] - (D[0] + off)) <= 1e-6:\n                    continue\n                if _LAND_RES == "band" and not _x_in_m9_band(p[0]):\n                    continue\n                a0, a1 = min(D[0] + off, p[0]), max(D[0] + off, p[0])\n                c, _m, _e = router.place("M8", p[1], a0, a1, nm, keep=(p[1] - 1e-6, p[1] + 1e-6))\n                _PROV_STATS["land_reserved" if c is not None else "land_reserve_blocked"] += 1\n'
def _prov_install():
    src = _inspect.getsource(C128._fixed_wires_stack)
    if src.count(_PROV_OLD) != 1: raise ValueError("C128 provider anchor changed")
    src = src.replace(_PROV_OLD, _PROV_NEW)
    if _NAT_MODE:
        o2 = """                    by, bm = track("M8", p[1] + sg * off, tx, p[0], nm, f"drop {ld}")"""
        n2 = """                    nat = port and _NAT_MODE and not ld.startswith("port:provider_clk_")
                    by, bm = track("M8", p[1] + (0.0 if nat else sg * off), tx, p[0], nm, f"drop {ld}")
                    if nat: _PROV_STATS["nat_drop_on_landing" if abs(by - p[1]) < 1e-6 else "nat_drop_moved"] += 1"""
        if src.count(o2) != 1: raise ValueError("C128 native drop anchor changed")
        src = src.replace(o2, n2)
    if _LAND_RES:
        o3 = "    for n in nets:\n        nm = n[\"name\"]\n        dcell"
        if src.count(o3) != 1: raise ValueError("C128 net loop anchor changed")
        src = src.replace(o3, _LAND_PRE + o3)
    # Provider A pin exactly on a vertical trunk still needs a legal M8 landing track.
    src=src.replace('if port and abs(p[0] - tx) <= 1e-6:',
        'if port and not ld.startswith("port:provider_clk_") and abs(p[0] - tx) <= 1e-6:')
    g = C128.__dict__
    g.update(_LAND_RES=_LAND_RES, _x_in_m9_band=_x_in_m9_band, _NAT_MODE=_NAT_MODE, _PROV_MODE=_PROV_MODE, _PROV_NEAR_A=_PROV_NEAR_A, _PROV_STATS=_PROV_STATS, _prov_pg_clear=_prov_pg_clear, _prov_pg_clear_ix=_prov_pg_clear_ix, _PROV_F1=_PROV_F1, _PROV_F1RES=_PROV_F1RES)
    exec(compile(src, C128.__file__, "exec"), g)


def access_census(shapes):
    """Same rectangle short/spacing check as CR, with bounded local buckets."""
    bins = defaultdict(list); shorts=spacing=0; details=[]; tile=2.16
    for number,a in enumerate(shapes):
        net,layer,x0,y0,x1,y1 = a
        sp = CR.SPACE[layer]; seen=set()
        for bx in range(math.floor((x0-sp)/tile),math.floor((x1+sp)/tile)+1):
            for by in range(math.floor((y0-sp)/tile),math.floor((y1+sp)/tile)+1):
                for k in bins[(layer,bx,by)]:
                    if k in seen: continue
                    seen.add(k); b=shapes[k]
                    if net == b[0]: continue
                    dx=max(0.,max(x0,b[2])-min(x1,b[4]));dy=max(0.,max(y0,b[3])-min(y1,b[5]))
                    kind=None
                    if dx == dy == 0: shorts+=1;kind='short'
                    elif math.hypot(dx,dy)<sp-1e-9:spacing+=1;kind='spacing'
                    if kind:details.append([kind,layer,net,b[0],x0,y0,x1,y1,list(b[2:]),number,k])
        for bx in range(math.floor(x0/tile),math.floor(x1/tile)+1):
            for by in range(math.floor(y0/tile),math.floor(y1/tile)+1):bins[(layer,bx,by)].append(number)
    return dict(shapes=len(shapes),shorts=shorts,spacing=spacing,examples=details)



def clock_cell_via_shapes(wires):
    # Min-area M2-M6 patches are already in CR.stair_shapes. Include actual
    # outer-layer enclosures too: a bare M7 riser endcap is smaller than VIA78.
    out=[];vr=CR.via_rects()
    for wire in wires:
        for stack in wire.get('stacks',[]):
            x,basey=stack['xy'];topy=stack['riser_from'][1]
            for layer,via,y in [('M1','VIA12',basey),('M7','VIA67',basey),
                                ('M7','VIA78',topy),('M8','VIA78',topy)]:
                hx,hy=vr[via][layer]
                if layer=='M8':hx,hy=.096,.040
                atx=stack.get('m6_entry_xy',stack['xy'])[0] if layer=='M1' else x
                out.append((wire['name'],layer,atx-hx,y-hy,atx+hx,y+hy))
    return out


def port_access_shapes(wires,cells,ports,buf):
    shapes=[]; vias=CR.via_rects()
    for wire in wires:
        if wire.get('pin_stack'):
            tl,bl=('M8','M9') if wire['horiz'] else ('M9','M8')
            endpoints=[];t0=wire['trunk_tap']
            if wire['drv'].startswith('port:'):
                pn=wire['drv'][5:];p=ports[pn]
                endpoints.append((('port',pn,p['layer'],p['xy'],t0,tl),True))
            for ld,bx,by in wire['branches']:
                if ld.startswith('port:'):
                    pn=ld[5:];p=ports[pn]
                    on_trunk=abs(by-t0[1])<1e-6 if wire['horiz'] else abs(bx-t0[0])<1e-6
                    endpoints.append((('port',pn,p['layer'],p['xy'],(bx,by),tl if on_trunk else bl),False))
        else:
            net=CR.net_plan(wire,cells,ports,buf)
            endpoints=[(net['drv'],True)]+[(p,False) for p in net['loads']]
        for endpoint,entering in endpoints:
            if endpoint[0] != 'port':continue
            _,name,layer,xy,at,top=endpoint[:6]
            pts=CR._port_join([],top,at,layer,xy,entering)
            for a,b in zip(pts,pts[1:]):
                if a[0] != b[0]:
                    for lay,(hx,hy) in vias[CR.via(a[0],b[0])].items():
                        if lay=='M8' and CR.via(a[0],b[0])=='VIA78':hx,hy=.096,.040
                        shapes.append((wire['name'],lay,a[1]-hx,a[2]-hy,a[1]+hx,a[2]+hy))
                elif a[1:] != b[1:]:
                    half=.04 if a[0] in ('M8','M9') else CR.WIDTH[a[0]]/2
                    shapes.append((wire['name'],a[0],min(a[1],b[1])-half,min(a[2],b[2])-half,max(a[1],b[1])+half,max(a[2],b[2])+half))
    return shapes


def review_render(P,wires,cells,pg,region,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    r=P.rect(region)
    fig,ax=plt.subplots(figsize=(8,12))
    def hits(x0,y0,x1,y1):return x0<=r[2] and x1>=r[0] and y0<=r[3] and y1>=r[1]
    for x0,y0,x1,y1,tag in DCM.DC.keepouts(P):
        if hits(x0,y0,x1,y1):
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#ddd',ec='#aaa'))
    for net,layer,x0,y0,x1,y1 in pg:
        if layer in ('M8','M9') and hits(x0,y0,x1,y1):
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#aaa',alpha=.3,lw=0))
    selected=0
    for wire in wires:
        for layer,x0,y0,x1,y1 in wire['segs']:
            if hits(min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)):
                ax.plot([x0,x1],[y0,y1],color='#1565c0' if layer=='M8' else '#2e7d32',lw=.65)
                selected+=1
    for cell in cells.values():
        if r[0]<=cell['x']<=r[2] and r[1]<=cell['y']<=r[3]:ax.plot(cell['x'],cell['y'],'k.',ms=2)
    ax.set(xlim=(r[0],r[2]),ylim=(r[1],r[3]),xlabel='die x (um)',ylabel='die y (um)',
           title=f'{region}: planned FIXED clock metal, {selected} visible segments\nM8 blue / M9 green / real PG grey / hard keep-outs shaded; NOT ROUTED')
    ax.set_aspect('equal');fig.tight_layout();fig.savefig(out,dpi=150);plt.close(fig)


def pg_grid_tcl(pg):
    pg_lines = []
    for net in sorted({r[0] for r in pg if r[1] in ('M8','M9')}):
        kind = 'GROUND' if net.upper().startswith('VSS') else 'POWER'
        pg_lines += [f'set pn [$blk findNet {net}]',
                     f'if {{$pn == "NULL"}} {{set pn [odb::dbNet_create $blk {net}]}}',
                     f'$pn setSigType {kind}', '$pn setSpecial',
                     'set psw [odb::dbSWire_create $pn FIXED]']
        pg_lines += C128.grid_tcl(pg,'$psw',net=net)
        horizontal = [r for r in pg if r[0] == net and r[1] == 'M8']
        vertical = [r for r in pg if r[0] == net and r[1] == 'M9']
        pg_lines += ['set pg_h {'+' '.join('{'+ ' '.join(map(str,r[2:])) +'}' for r in horizontal)+'}',
                     'set pg_v {'+' '.join('{'+ ' '.join(map(str,r[2:])) +'}' for r in vertical)+'}',
                     'set v89 [$tech findVia VIA89]',
                     'foreach h $pg_h {lassign $h hx0 hy0 hx1 hy1; set y [expr {($hy0+$hy1)/2}]; foreach v $pg_v {lassign $v vx0 vy0 vx1 vy1; set x [expr {($vx0+$vx1)/2}]; if {$hx0 <= $x && $x <= $hx1 && $vy0 <= $y && $y <= $vy1} {'
                     +f'set key "{net}@[um $x],[um $y]"; '
                     +'if {![info exists pg_vias($key)]} {odb::dbSBox_create $psw $v89 [um $x] [um $y] STRIPE; set pg_vias($key) 1}}}}']
    return pg_lines


def access_windows(P,cells,nets,access,radius):
    """Actual free M7 bar-column intervals inside the existing clock host."""
    bucket=500.;hosts=defaultdict(list);rects={n:P.rect(n) for n in P.parts}
    margin=max([CR.WIDTH['M7']/2]+[boxes['M7'][1] for boxes in CR.via_rects().values() if 'M7' in boxes])
    for name,r in rects.items():
        for bx in range(math.floor(r[0]/bucket),math.floor(r[2]/bucket)+1):
            for by in range(math.floor(r[1]/bucket),math.floor(r[3]/bucket)+1):hosts[(bx,by)].append(name)
    ko=DCM.DC.keepouts(P);byhost=defaultdict(list);io=[]
    for row in ko:
        (io if row[4].startswith('io/') else byhost[row[4].split('/')[0]]).append(row)
    windows={};clipped=0
    for name,c in cells.items():
        cx,cy=c['x']+c['w']/2,c['y']+.135
        matches=[n for n in hosts[(math.floor(cx/bucket),math.floor(cy/bucket))]
                 if rects[n][0]<=cx<=rects[n][2] and rects[n][1]<=cy<=rects[n][3]]
        if len(matches)!=1:raise ValueError(f'clock cell host is not unique: {name} {matches}')
        host=matches[0];r=rects[host]
        for pin in ('A','Y'):
            x=c['x']+access[c['lib']][pin][0];y=cy
            lo=max(y-radius,r[1]+margin);hi=min(y+radius,r[3]-margin)
            for x0,y0,x1,y1,tag in byhost[host]+io:
                halo=2.16
                if x0-halo-margin < x < x1+halo+margin:
                    a,b=y0-halo-margin,y1+halo+margin
                    if a <= y <= b:raise ValueError(f'existing clock pin enters hard-core halo: {name}/{pin} {tag}')
                    if b<y:lo=max(lo,b)
                    if a>y:hi=min(hi,a)
            if lo>hi:raise ValueError(f'no physical M7 access window: {name}/{pin}')
            if lo>y-radius+1e-6 or hi<y+radius-1e-6:clipped+=1
            windows[(name,pin)]=(x,y,lo,hi)
    net_windows={}
    for net in nets:
        ends=[]
        if not net['drv'].startswith('port:'):ends.append(windows[(net['drv'],'Y')])
        ends.extend(windows[(ld,'A')] for ld in net['loads'] if not ld.startswith('port:'))
        net_windows[net['name']]=ends
    return windows,net_windows,dict(radius_um=radius,host_and_macro_clipped=clipped,pins=len(windows),macro_halo_um=2.16)



def clock_column_windows(windows,nets):
    """Disjoint physical M7 access windows for unlike-net stacked bars.

    Bisect the free gap between fixed future M7 stack bases. A local M7
    riser may not cross another clock pin, even before that net is routed.
    Keep .048 um on each side of the bisector for VIA78 enclosure+spacing.
    """
    pin_net={}
    for n in nets:
        if not n['drv'].startswith('port:'):pin_net[(n['drv'],'Y')]=n['name']
        pin_net.update({(ld,'A'):n['name'] for ld in n['loads'] if not ld.startswith('port:')})
    bins=defaultdict(list);B=.1;reach=.064;count=0
    for key,(x,y,lo,hi) in windows.items():bins[math.floor(x/B)].append((key,x,y))
    for key,(x,y,lo,hi) in list(windows.items()):
        old=(lo,hi)
        for b in range(math.floor((x-reach)/B),math.floor((x+reach)/B)+1):
            for other,ox,oy in bins[b]:
                if other==key or pin_net[other]==pin_net[key] or abs(ox-x)>reach+1e-8:continue
                if abs(oy-y)<1e-8:raise ValueError(f'fixed M7 stack bases conflict: {key}, {other}')
                mid=(oy+y)/2
                if oy>y:hi=min(hi,mid-.048)
                else:lo=max(lo,mid+.048)
        if lo>y+1e-6 or hi<y-1e-6:raise ValueError(f'fixed clock column lacks access interval: {key}')
        if (lo,hi)!=old:count+=1
        windows[key]=(x,y,lo,hi)
    return dict(pins_clipped=count,pins=len(windows),bisector_margin_um=.048,
                note='conservative disjoint M7 windows; no extra M7 conductor or cell move')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('tree', 'netlist', 'lef', 'plan', 'endpoints', 'out'):
        ap.add_argument('--'+key, required=True)
    ap.add_argument('--backbone-plan', help='physically checked M6-entry-jog plan with records keyed cell/pin')
    ap.add_argument('--tech-vias', required=True, help='actual source ODB census JSON: dbu and tech_vias_dbu')
    ap.add_argument('--max-move', type=float, default=8.64)
    ap.add_argument('--review-region', default='c_E2_bf_10')
    ap.add_argument('--reserved-access', help='actual power-access conductor/via enclosure rectangles: [net,layer,x0,y0,x1,y1]')
    args = ap.parse_args()
    via_facts=json.loads(Path(args.tech_vias).read_text());dbu=via_facts['dbu']
    actual_vias={}
    for name,boxes in via_facts['tech_vias_dbu'].items():
        actual_vias[name]={layer:(max(abs(x0),abs(x1))/dbu,max(abs(y0),abs(y1))/dbu)
                          for layer,x0,y0,x1,y1 in boxes if layer in CR.LAYERS}
    if set(actual_vias)!=set(CR.via_rects()):raise ValueError('actual tech-via facts incomplete')
    CR.via_rects=lambda:actual_vias
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tree = json.loads(Path(args.tree).read_text())
    raw_endpoints = json.loads(Path(args.endpoints).read_text())
    endpoints = raw_endpoints.get('endpoints', raw_endpoints)
    endpoints = {k:dict(v,xy=v.get('xy_um',v.get('xy'))) for k,v in endpoints.items()}
    cells, nets = clock_graph(Path(args.netlist).read_text(), tree)
    if set(endpoints) != {t['port'] for t in tree['taps']}:
        raise ValueError('endpoint map does not cover every tree tap exactly')
    lef = Path(args.lef).read_text()
    masters = {c['lib'] for c in cells.values()}
    sizes, access = {}, {}
    for master in masters:
        sizes[master], access[master] = lef_access(lef, master)
    for c in cells.values():
        c['w'] = sizes[c['lib']][0]
        if abs(c['x']/.054-round(c['x']/.054)) > 1e-5 or abs(c['y']/.27-round(c['y']/.27)) > 1e-5:
            raise ValueError(f'off-grid existing cell: {c}')
    P = DI.load_plan(args.plan)
    root = tree['nodes']['0']
    taps = []
    for tap in tree['taps']:
        ep = endpoints[tap['port']]
        if ep['inst'] != tap['part'] or ep['pin'] != tap['tap'] or ep['layer'] != 'M7':
            raise ValueError(f'endpoint identity/layer mismatch: {tap["port"]}')
        planned=ep.get('planned_xy_um',tap['xy'])
        if max(abs(a-b) for a,b in zip(planned,tap['xy'])) > .001:
            raise ValueError(f'endpoint source coordinate mismatch: {tap["port"]}')
        rect=ep['rect_um'];x,y=ep['xy']
        if not (rect[0]<=x<=rect[2] and rect[1]<=y<=rect[3]):
            raise ValueError(f'endpoint outside actual M7 metal: {tap["port"]}')
        taps.append(dict(tap,xy=ep['xy'],layer=ep['layer']))
    M = dict(meta=dict(root_um=[root['x'],root['y']]), taps=taps)
    ports = {t['port']:dict(layer=t['layer'],xy=t['xy']) for t in taps}
    ports['root'] = dict(layer='M9',xy=M['meta']['root_um'])
    nd = dict(width=.08, space=.32, rf=.5, cf=1.15)
    pg = DI.pg_rects(P, C128.pg_grid(P))
    (out/'pg_rects.json').write_text(json.dumps(pg)+'\n')
    _PROV_STRAPS[:] = sorted((r[3], r[5]) for r in pg if r[1] == 'M8')
    _PROV_STRAPS9[:] = sorted((r[2], r[4]) for r in pg if r[1] == 'M9')
    if _PROV_MODE: _prov_install()
    power_access=[]
    if args.reserved_access:
        power_access=json.loads(Path(args.reserved_access).read_text())
        if isinstance(power_access,dict):power_access=power_access['shapes']
        for row in power_access:
            if len(row)!=6 or row[0] not in ('VDD','VSS') or row[1] not in CR.LAYERS:
                raise ValueError(f'invalid physical power-access rectangle: {row}')
            if not (row[2]<row[4] and row[3]<row[5]):raise ValueError(f'empty physical power access: {row}')
    router = C128.TrackRouter(nd,'VSS',DCM.DEFAULT_TRACKS,args.max_move)
    _ROUTER[:] = [router]
    # Reserve the full VIA78 minarea patch along each M8 segment end.
    # Actual wire and encoder geometries remain unchanged; only track selection gains the missing .056 um cap.
    _old_place=router.place
    def patch_aware_place(layer,ideal,a0,a1,name,**kwargs):
        if layer=='M8':a0-=.056;a1+=.056
        return _old_place(layer,ideal,a0,a1,name,**kwargs)
    router.place=patch_aware_place
    router.reserve(C128.pg_shapes(pg))
    router.reserve(C128.pg_shapes(power_access))
    # Native M7 conductor is authoritative; the graft-map centroid is a
    # reference, not a legal M8 track. Enter at a real track with the entire
    # VIA78 M7 enclosure inside actual pin metal, never a fabricated M7 jog.
    endpoint_access = {}; endpoint_failures=[]
    # This index checks zero-length VIA78 landing enclosures only, using
    # the LEF access minimum; shielded tree planning retains its .32 spacing.
    landing_ix=C128.MetalIndex(CR.SPACE['M8'])
    for shape in C128.pg_shapes(pg)+C128.pg_shapes(power_access):landing_ix.add(shape)
    hx,hy = CR.via_rects()['VIA78']['M7']
    mx,my = .096,.040  # .192x.080 normal clock-width patch, AREA >= .00752
    pitch=DCM.DEFAULT_TRACKS['M8']['pitch_um'];phase=DCM.DEFAULT_TRACKS['M8']['offset_um']
    for tap in taps:
        ep=endpoints[tap['port']];x,refy=ep['xy'];x0,y0,x1,y1=ep['rect_um']
        if x-hx<x0-1e-6 or x+hx>x1+1e-6:
            raise ValueError(f'VIA78 enclosure cannot fit actual M7 pin: {tap["port"]}')
        ks=range(math.ceil((y0+hy-phase)/pitch-1e-8),math.floor((y1-hy-phase)/pitch+1e-8)+1)
        candidates=sorted((round(phase+k*pitch,6) for k in ks),key=lambda y:(abs(y-refy),y))
        selected=None
        for y in candidates:
            landing=('M8',ep['net'],'access',y-my,y+my,x-mx,x+mx)
            if not landing_ix.hits(landing,first=True):
                selected=y;landing_ix.add(landing);router.ix.add(landing);break
        if selected is None:
            endpoint_failures.append(dict(port=tap['port'],inst=ep['inst'],pin=ep['pin'],
                rect_um=ep['rect_um'],reference_xy_um=ep['xy'],legal_in_pin_rows_um=candidates,
                kind='no VIA78 landing clear of real PG/power inside actual M7 conductor'))
            continue
        tap['xy']=[x,selected];ports[tap['port']]['xy']=[x,selected]
        endpoint_access[tap['port']]=dict(inst=ep['inst'],pin=ep['pin'],net=ep['net'],
            reference_xy_um=ep['xy'],entry_xy_um=tap['xy'],rect_um=ep['rect_um'],
            entry_offset_um=[0,round(selected-refy,6)],via='VIA78',m7_enclosure_inside=True,
            access_kind='zero-length VIA78 landing enclosure',m8_enclosure_half_um=[mx,my],
            landing_min_spacing_um=CR.SPACE['M8'],tree_spacing_um=nd['space'])
    (out/'endpoint_access.json').write_text(json.dumps(endpoint_access)+'\n')
    if endpoint_failures:
        (out/'prebuild.json').write_text(json.dumps(dict(status='FAIL',physical_route=False,
            cause='native M7 clock pin / actual PG access incompatibility',
            source_cells=len(cells),tap_iterms=len(taps),findings=endpoint_failures),indent=1)+'\n')
        raise ValueError(f'{len(endpoint_failures)} actual M7 pins have no legal VIA78 landing')
    _NATIVE_M7.extend((ep['net'],tuple(ep.get('m7_stub_um',ep['rect_um']))) for ep in endpoint_access.values())
    for port,ep in endpoint_access.items():
        key=tuple(round(v,6) for v in ep['entry_xy_um'])
        nm=ep['net']
        if key in _ENDPOINT_NET and _ENDPOINT_NET[key]!=nm:raise ValueError('different-net native pin coordinate alias')
        _ENDPOINT_NET[key]=nm
    windows,net_windows,window_report=access_windows(P,cells,nets,access,args.max_move)
    column_report=clock_column_windows(windows,nets)
    backbone_records={}
    if args.backbone_plan:
        planned=json.loads(Path(args.backbone_plan).read_text())
        if planned['status']!='PASS_GEOMETRY':raise ValueError('M6-entry backbone plan has not passed geometry')
        for record in planned['records']:
            key=(record['cell'],record['pin']);actual=windows[key][:2]
            if max(abs(a-b) for a,b in zip(actual,record['entry_xy_um']))>1e-6:
                raise ValueError(f'M6 entry plan changed actual pin base: {key}')
            x,y=record['backbone_xy_um'];lo,hi=record['m7_window_um']
            if abs(y-actual[1])>1e-6 or not lo<=y<=hi:raise ValueError(f'illegal M6 entry row/window: {key}')
            windows[key]=(x,y,lo,hi);backbone_records[key]=record
        router.stack_backbone_xy=lambda cell,pin,actual:backbone_records[(cell,pin)]['backbone_xy_um'] if (cell,pin) in backbone_records else actual
    pin_net={}
    for n in nets:
        if not n['drv'].startswith('port:'):pin_net[(n['drv'],'Y')]=n['name']
        pin_net.update({(ld,'A'):n['name'] for ld in n['loads'] if not ld.startswith('port:')})
    native_bins=defaultdict(list)
    for nr in _NATIVE_M7:
        _nm,(_x0,_y0,_x1,_y1)=nr
        for xb in range(math.floor((_x0-.064)/.1),math.floor((_x1+.064)/.1)+1):native_bins[xb].append(nr)
    native_clipped=0
    for key,(x,y,lo,hi) in list(windows.items()):
        before=(lo,hi)
        for nnet,(x0,y0,x1,y1) in native_bins[math.floor(x/.1)]:
            if nnet==pin_net[key] or x+.016+CR.SPACE['M7']<=x0+1e-7 or x-.016-CR.SPACE['M7']>=x1-1e-7:continue
            if y0-(.036+CR.SPACE['M7'])<y<y1+(.036+CR.SPACE['M7']):
                raise ValueError(f'fixed clock stack base intersects native M7 pin: {key} {nnet}')
            if y<y0:hi=min(hi,y0-(.036+CR.SPACE['M7']))
            else:lo=max(lo,y1+(.036+CR.SPACE['M7']))
        if (lo,hi)!=before:native_clipped+=1
        windows[key]=(x,y,lo,hi)
    print(f'NATIVE_M7 clipped {native_clipped} fixed clock stack windows',flush=True)
    def endpoint_window(net,what):
        if what in ('trunk','driver jog'):cell,pin=net['drv'],'Y'
        elif what.startswith(('jog ','drop ')):cell,pin=what.split(' ',1)[1],'A'
        else:return None
        if cell.startswith('port:'):return None
        return windows[(cell,pin)][2:]
    router.access_window=endpoint_window
    router.riser_legal=lambda cell,pin,y:windows[(cell,pin)][2]-1e-6<=y<=windows[(cell,pin)][3]+1e-6
    summary = dict(status='PREBUILD', physical_route=False, source_cells=len(cells), source_nets=len(nets),
                   tap_iterms=len(taps), source_masters=sorted(masters), pin_access=access,
                   inputs={k:dict(path=getattr(args,k),sha256=hashlib.sha256(Path(getattr(args,k)).read_bytes()).hexdigest())
                           for k in ('tree','netlist','lef','plan','endpoints')})
    if args.reserved_access:
        summary['power_access_reservation']=dict(file=args.reserved_access,rectangles=len(power_access),
            sha256=hashlib.sha256(Path(args.reserved_access).read_bytes()).hexdigest())
    summary['actual_tech_vias']=dict(path=args.tech_vias,sha256=hashlib.sha256(Path(args.tech_vias).read_bytes()).hexdigest(),enclosures_um=actual_vias)
    summary['access_minarea_patches']=dict(m8_dimensions_um=[.192,.080],m8_area_um2=.01536,short_m7_dimensions_um=[.032,.072],short_m7_area_um2=.002304,tree_width_um=nd['width'],tree_spacing_um=nd['space'])
    summary['physical_m7_windows']=window_report
    summary['clock_column_windows']=column_report
    if args.backbone_plan:summary['m6_entry_jogs']=dict(path=args.backbone_plan,count=len(backbone_records),sha256=hashlib.sha256(Path(args.backbone_plan).read_bytes()).hexdigest())
    try:
        with real_pin_access(access,args.max_move):
            wires = C128.fixed_wires(M,cells,nets,max(v[0] for v in sizes.values()),.27,off=0.,router=router,pin_stack=True,l_drops=True)
        for wire in wires:
            wire['enc']='r8'
            for stack in wire.get('stacks',[]):
                if abs(stack['riser_from'][1]-stack['xy'][1])<.015:stack['short_stack']=True
    except C128.PlanError as error:
        summary.update(status='FAIL', cause='no legal fixed-wire geometry', findings=error.rows)
        (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
        raise
    (out/'fixed_wires.json').write_text(json.dumps(wires)+'\n')
    review_render(P,wires,cells,pg,args.review_region,out/'review_region.png')
    window_violations=[]
    for wire in wires:
        for stack in wire.get('stacks',[]):
            _,y,lo,hi=windows[(stack['cell'],stack['pin'])]
            end=stack['riser_from'][1]
            if min(y,end)<lo-1e-6 or max(y,end)>hi+1e-6:window_violations.append(dict(net=wire['name'],stack=stack,allowed=[lo,hi]))
    if window_violations:
        summary.update(status='FAIL',cause='actual host/halo M7 window',findings=window_violations)
        (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
        raise ValueError('M7 clock riser leaves actual legal glue window')
    print('PREBUILD_STAGE access shapes', flush=True)
    with real_pin_access(access,access_patches=True):
        shapes = CR.stair_shapes(wires,cells,ports,next(iter(masters)))
        _n1=len(shapes)
        shapes += port_access_shapes(wires,cells,ports,next(iter(masters)))
        _n2=len(shapes)
        shapes += clock_cell_via_shapes(wires)
        _n3=len(shapes)
        print(f'PREBUILD_STAGE access census {len(shapes)} shapes', flush=True)
        census = access_census(shapes+list(power_access))
        print(f'PREBUILD_STAGE encoder census={census["shorts"]}/{census["spacing"]}', flush=True)
        lines, rec = CR.routed_tcl(wires,cells,ports,next(iter(masters)),'QC_CLOCK_NDR')
    print('PREBUILD_STAGE top access reservation', flush=True)
    top_hits=[]; top_count=0
    _all=[]
    for _i,(net,layer,x0,y0,x1,y1) in enumerate(shapes):
        if layer not in ('M8','M9'):continue
        shape=(layer,net,'access',y0,y1,x0,x1) if layer=='M8' else (layer,net,'access',x0,x1,y0,y1)
        hit=router.ix.hits(shape,first=True)
        if hit:
            _src=1 if _i<_n1 else 2 if _i<_n2 else 3
            _all.append([_i,_src,net,layer,x0,y0,x1,y1,router.ix.shapes[hit[0][0]],hit[0][1]])
            top_count+=1
            if len(top_hits)<100:top_hits.append(dict(net=net,layer=layer,rect=[x0,y0,x1,y1],against=router.ix.shapes[hit[0][0]],kind=hit[0][1]))
    (out/'prov_stats.json').write_text(json.dumps(dict(mode=_PROV_MODE,nat=_NAT_MODE,land_res=_LAND_RES,jogx=_JOGX,near_a=_PROV_NEAR_A,**_PROV_STATS,**_JOG_STATS))+'\n')
    (out/'diag_top.json').write_text(json.dumps(dict(n=[_n1,_n2,_n3],hits=_all),default=list)+'\n')
    import pickle; pickle.dump(dict(shapes=shapes,n=[_n1,_n2,_n3],census=census),open(out/'diag_shapes.pkl','wb'))
    if census.get('shorts') or census.get('spacing') or top_count:
        summary.update(status='FAIL',cause='pin-access shorts',pin_access_census=census)
        summary['top_access_conflicts']=dict(count=top_count,examples=top_hits)
        (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
        raise ValueError('fixed-wire pin stacks short; revise before materializing')
    print('PREBUILD_STAGE endpoint graft', flush=True)
    text = '\n'.join(lines)+'\n'
    # One pass over the full-die encoder (thousands of tap endpoints).
    # Repeated full-string count/replace costs O(taps * full encoded tree).
    endpoint_counts = defaultdict(int)
    def graft_encoder(match):
        port = match.group(1)
        if port not in endpoints:
            return match.group(0)  # The root remains a real top-level BTerm.
        endpoint_counts[port] += 1
        ep = endpoints[port]
        return '$e addITerm [IT '+ep['inst']+' '+ep['pin']+']'
    text = re.sub(r'\$e addBTerm \[BT ([^\]\s]+)\]', graft_encoder, text)
    wrong = {p:endpoint_counts[p] for p in endpoints if endpoint_counts[p] != 1}
    if wrong:
        raise ValueError(f'endpoint encoder count is not one: {wrong}')
    header = '''set blk [ord::get_db_block]
set tech [[ord::get_db] getTech]
set l8 [$tech findLayer M8]
set l9 [$tech findLayer M9]
proc um {x} {expr {round($x*[[ord::get_db_block] getDbUnitsPerMicron])}}
set ::ot_clock_shield_swires {}
if {![array exists pg_vias]} {array set pg_vias {}}
create_ndr -name QC_CLOCK_NDR -width {M8 .08 M9 .08} -spacing {M8 .32 M9 .32}
'''
    pg_lines = pg_grid_tcl(pg)
    drawn = [tuple(seg)+(ext,) for w in wires for seg,mode,ext in
             zip(w['segs'],w.get('shield_modes') or [C128.DRAWN]*len(w['segs']),
                 w.get('shield_ext') or [None]*len(w['segs'])) if mode == C128.DRAWN]
    ties = C128.shield_ties(C128.shield_stripes(drawn,nd),pg,nd['width'])
    tie_record = C128.tie_record(ties)
    if ties['untied'] or ties['shorts']:
        summary.update(status='FAIL',cause='shield power continuity',shield=ties)
        (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
        raise ValueError('shield grid attachment fails before materialization')
    tie_lines=C128.tie_tcl(ties,'$fsw')
    for i,line in enumerate(tie_lines):
        if line.startswith('odb::dbSBox_create'):
            xy=re.findall(r'\[um ([\d.-]+)\]',line)
            if len(xy)!=2:raise ValueError('unexpected shield via emitter')
            key=f'VSS@[um {xy[0]}],[um {xy[1]}]'
            tie_lines[i]='set key "'+key+'"; if {![info exists pg_vias($key)]} {'+line+'; set pg_vias($key) 1}'
    shields = CR.shield_only_tcl(C128.combo_tcl(wires,nd,'VSS')) + tie_lines
    pg_lines += ['add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
                 'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground', 'global_connect']
    (out/'fixed_pg.tcl').write_text(header.split('create_ndr')[0]+'\n'.join(pg_lines)+'\n')
    (out/'fixed_clock_only.tcl').write_text(header+'\n'.join(shields)+'\n'+text)
    (out/'fixed_clock.tcl').write_text(header+'\n'.join(pg_lines+shields)+'\n'+text)
    (out/'fixed_wires.json').write_text(json.dumps(wires)+'\n')
    inventory = {n['name'] for n in nets} | {r[0] for r in pg if r[1] in ('M8','M9')}
    (out/'infra_nets.txt').write_text('\n'.join(sorted(inventory))+'\n')
    summary.update(status='PASS_PREBUILD',encoder=rec,pin_access_census=census,shield=tie_record,
                   pg=dict(actual_top_grid_rects=sum(r[1] in ('M8','M9') for r in pg),same_net_vias='every M8/M9 intersection',
                           clock_cell_power='logical VDD/VSS connected; M1-to-top-grid physical stacks NOT PROVIDED',
                           physical_clock_power_terms_unclosed=2*len(cells),ir_and_bump_qualification=False),
                   reset_routes='NOT PROVIDED by this clock-only adapter; must be separately materialized before infrastructure freeze',
                   note='No physical job or route proof. Render/review before materialization. Clock-cell physical power and reset remain explicit release gaps.')
    (out/'prebuild.json').write_text(json.dumps(summary,indent=1)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('inputs','pin_access_census')},indent=1))


if __name__ == '__main__':
    main()
