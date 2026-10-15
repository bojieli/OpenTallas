"""Source-exact compute parent pin plans shared by the die and tile kits.

Only unclosed parent frames are changed.  Child clock entries retain their
source-published physical locations and the phase-minus-insertion contract.
"""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from die_port_bind import parse_modules


def rtl_ports(path, name):
    mods = [m for m in parse_modules(path.read_text(), str(path)) if m.name == name]
    if len(mods) != 1 or mods[0].port_parse_errors:
        raise ValueError(f'{name}: cannot resolve one complete RTL port list')
    m = mods[0]
    out = {p: (m.width(p, m.env()), m.ports[p][0]) for p in m.order}
    if any(n is None or d not in ('input', 'output') for n, d in out.values()):
        raise ValueError(f'{name}: unresolved RTL widths/directions')
    return out


def snap(z):
    return round(.012 + round((z - .012) / .048) * .048, 4)


def apply_tile(q, entries):
    q.w, q.h = 449.28, 1442.88  # actual parent-kit outline, never legacy SHAVE
    ports = rtl_ports(ROOT / 'rtl/physical/qfd_tile_nk_slot.sv', q.name)
    old = q.ports
    q.ports, q.order = {}, []
    # Four 514-bit words need 197.4 um at 96-nm pitch.  Separate real
    # W-face windows replace the four coincident M8 interior groups.
    for j, p in enumerate(('n_a', 'n_b', 'n_y', 't_out')):
        if p in ports:
            q.face(p, ports[p][0], 'W', 'M4', q.h / 2 + (j - 1.5) * 56.0, 2)
    # Preserve the station-facing registered tap location.  Straps/ties stay
    # beside it, with fixed disjoint ranges on the same E face.
    tap = old.get('tap')
    centre = tap[4] if tap and tap[0] == 'face' else q.h / 2
    q.face('tap', ports['tap'][0], 'E', 'M4', centre, 2)
    q.face('rst_n', 1, 'E', 'M4', centre - 32., 2)
    q.face('tile_id', 16, 'E', 'M4', centre - 36., 2)
    q.face('tie_hi', 1, 'E', 'M4', centre - 38., 2)
    q.face('tie_lo', 1, 'E', 'M4', centre - 40., 2)
    q.face('ck', 1, 'N', 'M5', snap(q.w / 2), 1)
    clocks = entries[q.name]['children']
    for p, (n, _) in ports.items():
        if p.startswith('ck_'):
            ch = clocks[p]  # absent child evidence is a hard error
            xy = tuple(ch['at'])  # published child rectangle center, already transformed by orientation
            if not (0 <= xy[0] <= q.w and 0 <= xy[1] <= q.h):
                raise ValueError(f'{q.name}.{p}: child clock outside parent: {xy}')
            # Parent entry is M5 over the child's M4 rectangle: same XY,
            # one local via; parent CTS must measure that entry wire.
            q.ports[p] = ('xy', 1, 'M5', [xy], 1)
            q.order.append(p)
    q.obs_top = 7
    if set(q.ports) != set(ports):
        raise ValueError(f'{q.name}: source/pin mismatch {set(q.ports)^set(ports)}')
    return ports


def apply_slabs(M):
    """Pack actual static-slab RTL ports on legal parent layers.

    Clock entries are distinct physical entry pins; their individual child
    insertion must still be supplied before the parent can be qualified.
    """
    for q in M.values():
        if not q.name.startswith('qfd_port_tiles_'):
            continue
        q.w, q.h = 1036.8, 2462.4
        ports = rtl_ports(ROOT / 'rtl/qwen_split/qfd_port_tiles.sv', q.name)
        old = q.ports
        q.ports, q.order = {}, []
        faces = {f: [] for f in 'WENS'}
        for p, (n, _) in ports.items():
            if p.startswith('ck') or p == 'rst_n':
                f = 'N'
            elif p.startswith('bw'):
                f = 'W' if not q.name.endswith('_f1') else 'E'
            elif p in ('tw', 'ty') and n == 4096:
                f = 'S'
            elif p in ('cf1', 'rqe', 'ame', 'tc_e', 'tye'):
                f = 'E'
            elif q.name.endswith('_f1') and p in ('cw0', 'rq', 'am', 'tc', 'ty'):
                f = 'W'
            else:
                s = old.get(p)
                f = s[2] if s and s[0] in ('face', 'pins') else 'W'
            faces[f].append((p, n))
        for f, groups in faces.items():
            L = q.w if f in 'NS' else q.h
            need = sum(n * .096 + 1.0 for _, n in groups)
            if need > L - 8:
                raise ValueError(f'{q.name}.{f}: {need:.1f}um pins exceed {L-8:.1f}um face')
            cursor = (L - need) / 2
            for p, n in groups:
                q.face(p, n, f, 'M5' if f in 'NS' else 'M4', snap(cursor + n * .096 / 2), 2)
                cursor += n * .096 + 1.
        q.obs_top = 7


def apply_dvm_clocks(M):
    # Grown DVM column: four MX south leaves, head, four R0 north
    # leaves. These are actual IO-placement rectangle centers supplied by
    # Q-DVM, in the RTL ck0=head, ck1..4=north, ck5..8=south order.
    ys = [754.812,950.412,1086.492,1222.572,1358.652,
          483.828,347.748,211.668,75.588]
    for name in ('qfd_xcol_e','qfd_xcol_w'):
        q = M.get(name)
        if q is None:
            continue
        for k,y in enumerate(ys):
            p = f'ck{k}'
            q.ports[p] = ('xy',1,'M5',[(.042,y)],1)
            if p not in q.order:
                q.order.append(p)
    for name in ('qfd_xcst_n','qfd_xcst_s'):
        q = M.get(name)
        if q is None:
            continue
        for p,xy in (('ck',(52.065,103.637)),('rst_n',(52.353,103.637))):
            q.ports[p] = ('xy',1,'M3',[xy],1)
            if p not in q.order:
                q.order.append(p)


def apply_band(q):
    """Actual quarter-output ABI, retaining every legacy RTL output pin."""
    q.w,q.h=881.28,1131.84
    ports=rtl_ports(ROOT/'rtl/physical/ot_qwen_band_lanes_slots.sv',q.name)
    old=json.loads((ROOT/'results/arch/qwen_split_compute_1014/c15_preflight/qfd_sp_band_lanes.json').read_text())['ports']
    q.ports,q.order={},[]
    for p in ('ck',*[f'ck_l{k}' for k in range(16)],'rst_n','b0','lnk'):
        r=old[p]
        if r.get('interior'):
            q.ports[p]=('xy',1,r['layer'],[tuple(r['positions_xy_um'][0])],1);q.order.append(p)
        else:
            n=ports[p][0];lo,hi=r['range_um']
            points=[lo+(hi-lo)*k/(n-1) for k in range(n)] if n>1 else [lo]
            q.ports[p]=('pins',n,r['face'],r['layer'],points,1);q.order.append(p)
    for p,c in [('tw',650),('ty',230)]:q.face(p,ports[p][0],'N','M5',c,2)
    for p,c in [('tt',750),('pw',350),('f',400),('c',430),('f_up',460)]:
        q.face(p,ports[p][0],'E','M4',c,2)
    for k in range(4):q.face(f'pw_l{k}',129,'E','M4',520+(k-1.5)*(129*.096+.384),2)
    if set(q.ports)!=set(ports):raise ValueError('band source ABI not completely assigned')


def apply(M):
    entries = json.loads((ROOT / 'results/arch/qwen_compute_child_clocks_1014/entries.json').read_text())['masters']
    for name in ('qfd_tile_nk', 'qfd_tile_nl'):
        if name in M:
            apply_tile(M[name], entries)
    apply_slabs(M)
    apply_dvm_clocks(M)
    if 'qfd_sp_band_lanes' in M:apply_band(M['qfd_sp_band_lanes'])


def export(q, out):
    """Publish assignment JSON and exact TCL using the die's pin rectangles."""
    from qwen_rom_fulldie import pin_rects
    source = ('rtl/physical/ot_qwen_band_lanes_slots.sv' if q.name=='qfd_sp_band_lanes' else
              'rtl/physical/qfd_tile_nk_slot.sv' if q.name.startswith('qfd_tile_n') else 'rtl/qwen_split/qfd_port_tiles.sv')
    ports = rtl_ports(ROOT / source, q.name)
    rects = []
    face_q = type(q)(q.name, q.w, q.h, q.obs_top, q.note)
    face_q.ports = {p: s for p,s in q.ports.items() if s[0] == 'face'}
    face_q.order = list(face_q.ports)
    rects += pin_rects(face_q, 1, {p: n for p,(n,_) in ports.items()})
    for p, s in q.ports.items():
        if s[0]=='pins':
            _,n,f,L,positions,_=s
            for k,pos in enumerate(positions):
                r=((0,pos-.012,.192,pos+.012) if f=='W' else
                   (q.w-.192,pos-.012,q.w,pos+.012) if f=='E' else
                   (pos-.012,0,pos+.012,.192) if f=='S' else
                   (pos-.012,q.h-.192,pos+.012,q.h))
                rects.append((p+f'[{k}]',L,r))
        if s[0] == 'xy':
            x,y = s[3][0]
            rects.append((p+'[0]', s[2], (x-.012,y-.012,x+.012,y+.012)))
    seen = {}
    tcl = []
    groups = {}
    bins = {}
    for p, layer, r in sorted(rects, key=lambda r: (r[1], r[2][0])):
        base, idx = p.split('[')
        index = int(idx[:-1])
        n, direction = ports[base]
        name = base if n == 1 else p
        x,y = (r[0]+r[2])/2,(r[1]+r[3])/2
        if name in seen:
            raise ValueError(f'duplicate {name}')
        keys = [(layer,x,y) for x in range(math.floor(r[0]*5),math.floor(r[2]*5)+1)
                for y in range(math.floor(r[1]*5),math.floor(r[3]*5)+1)]
        nearby = {pn:pr for k in keys for pn,pr in bins.get(k,[])}
        for pn,pr in nearby.items():
            if r[0] < pr[2] and pr[0] < r[2] and r[1] < pr[3] and pr[1] < r[3]:
                raise ValueError(f'pin overlap {name}/{pn}')
        if min(r) < -.001 or r[2] > q.w+.001 or r[3] > q.h+.001:
            raise ValueError(f'pin outside {name}: {r}')
        seen[name] = (layer,r)
        for k in keys:
            bins.setdefault(k,[]).append((name,r))
        tcl.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.4f} {y:.4f}}}')
        s = q.ports[base]
        face = s[2] if s[0] in ('face','pins') else min(dict(W=x,E=q.w-x,S=y,N=q.h-y), key=dict(W=x,E=q.w-x,S=y,N=q.h-y).get)
        groups.setdefault(base,[]).append((index,x,y,face,layer,direction,s[0]=='xy'))
    if len(seen) != sum(n for n,_ in ports.values()):
        raise ValueError('missing RTL pins')
    faces,ranges,rec = {},{},{}
    for p, positions in groups.items():
        positions.sort()
        f,L,d,inside = positions[0][3:]
        along = [y if f in 'WE' else x for _,x,y,*_ in positions]
        lo,hi = min(along),max(along)
        rec[p] = dict(face=f,layer=L,bits=len(positions),range_um=[lo,hi],direction=d,bit0_at='lo')
        if inside:
            rec[p].update(interior=True,positions_xy_um=[[x,y] for _,x,y,*_ in positions])
        else:
            faces.setdefault(f,[]).append((lo,p));ranges[p]=[lo,hi]
    data = dict(schema='opentallas.qwen-tp8.assigned-pins.v1',master=q.name,
                outline=dict(w=q.w,h=q.h),pins={f:[p for _,p in sorted(ps)] for f,ps in faces.items()},
                pin_ranges=ranges,ports=rec,overlapping_pin_pairs=0,
                source_rtl=source,note='Source-exact unclosed parent assignment. Child clock entries at published XY. Physical qualification still required.')
    out.mkdir(parents=True,exist_ok=True)
    (out/(q.name+'.json')).write_text(json.dumps(data,indent=1)+'\n')
    (out/(q.name+'.tcl')).write_text('\n'.join(tcl)+'\n')
    return dict(ports=len(ports),bits=len(seen),overlapping_pin_pairs=0)


if __name__ == '__main__':
    from qwen_rom_fulldie import Master
    out = Path(sys.argv[1])
    M = {n:Master(n,449.28,1442.88,7,'') for n in ('qfd_tile_nk','qfd_tile_nl')}
    M.update({f'qfd_port_tiles_{b}{s}':Master(f'qfd_port_tiles_{b}{s}',1036.8,2462.4,7,'') for b in range(3) for s in ('','_f1')})
    apply(M)
    evidence = {n:export(q,out) for n,q in M.items()}
    (out/'INDEX.json').write_text(json.dumps(evidence,indent=1)+'\n')
    print(json.dumps(evidence))
