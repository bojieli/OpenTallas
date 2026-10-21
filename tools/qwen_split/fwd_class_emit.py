"""Emit real D4 registered-enable lane classes, with parallel width slices.

Reservations precede placement; the existing reach and native-calendar gates remain
mandatory. This adapter adds no edge, changes no K, and uses no data-path exception.
"""
import copy
import os
import math
import re
from pathlib import Path
from qwen_split import fwd_lane_classes as C


def slice_max():
    """Widest parallel part (bits). Default 600 = the widest class. QW-G5R3N 10-21 (opt-in
    OT_SPLIT_FWD_CLASS_MAXW=128): every part <= 128 b maps onto the closed 128-b classes, whose
    frame is 64.776 x 30.216 for ALL four direction groups, so a bent (HV/VH) or vertical lane fits
    the 64.8-um slice-gap data-landing columns (the 600-b bend frame is 104 um wide and found no site:
    dv2f21g5r3c/d W4). Parts keep the lane's E/K/n and compiler slot: zero added token cycles."""
    w = int(os.environ.get('OT_SPLIT_FWD_CLASS_MAXW', '600'))
    if w not in C.WCLS[1:]:
        raise ValueError(f'OT_SPLIT_FWD_CLASS_MAXW={w}: must be a closed width class {C.WCLS[1:]}')
    return w


def lane_maxw(m, bid):
    """Per-lane part width. Narrow split exempts the W0|E0 seam-lane words (m['dv_seam_lane']): their one
    station sits in the seam channel, where the 600-b class frame fits (dv2f21g5r3c/d passed it) and a
    column of 128-b parts does not (dv2f21g5r3f/g/f2/g2/f3: 'dv seam lane: no free station dv_x0_dr_dr').
    OT_SPLIT_FWD_CLASS_SEAM_WIDE=0 narrows them too."""
    w = slice_max()
    if w < 600 and os.environ.get('OT_SPLIT_FWD_CLASS_SEAM_WIDE', '1') == '1' and m is not None \
            and m.get('dv_seam') and bid in set(m.get('dv_seam_lane') or ()):
        return 600
    return w


def slices(bits, maxw=None):
    n = math.ceil(bits / (maxw or slice_max()))
    width = math.ceil(bits / n)
    return [(lo, min(bits, lo + width)) for lo in range(0, bits, width)]


def reservation(bits, group=None, maxw=None):
    parts = slices(bits, maxw)
    wc = C.wclass(max(hi - lo for lo, hi in parts))
    groups = [group] if group else list(C.REP)
    # Side-by-side paths can turn into EN/ES/WS/WN at a hop. Reserve
    # the native bend width before site allocation, instead of widening only
    # after emission. Keep non-EW vertical reservations directional.
    if group == 'H' and os.environ.get('OT_SPLIT_FWD_CLASS_BEND_RESERVE') == '1':
        groups += ['HV', 'VH']
    frames = [C.frame(wc, g) for g in groups]
    w, h = max(f[0] for f in frames), max(f[1] for f in frames)
    cols = grid_cols(len(parts), group, maxw)
    rows = math.ceil(len(parts) / cols)
    return round((w + C.SHAVE) * cols - C.SHAVE, 3), round((h + C.SHAVE) * rows - C.SHAVE, 3)


def grid_cols(n, group=None, maxw=None):
    """Narrow split (MAXW < 600) only: parts sit in a grid of columns. An E/W side-by-side lane ('H',
    the slice-gap landing columns) keeps one 64.8-um column; any other station (seam / corridor, vertical
    flow) takes up to OT_SPLIT_FWD_CLASS_COLS (default 2) columns, so its height stays near the 600-b
    frame's (dv2f21g5r3f/g: a 520-b seam station 5 x 30.24 = 151 um tall found no seam site)."""
    if (maxw or slice_max()) >= 600 or group == 'H':
        return 1
    return max(1, min(n, int(os.environ.get('OT_SPLIT_FWD_CLASS_COLS', '2'))))


def slice_name(name, part):
    base, hop = name.rsplit("_", 1)
    return f"{base}__s{part}_{hop}"


def install(v, m):
    rows = m.get('fwd_lanes', {}).get('lanes', [])
    # _relays installs before publishing fwd_lanes in older generators; reject
    # that ordering rather than emitting an unpriced calendar.
    if not rows:
        raise ValueError('class emission requires published forwarded-lane calendar')
    by = {i.name: i for i in m['insts']}
    mapping, classes, receipts, extra = {}, {}, [], []
    for lane in rows:
        mw = lane_maxw(m, lane['bid'])
        names = lane['stations'] + ([lane['landing']] if lane.get('landing') else [])
        for name in names:
            it = by[name]
            g = C.NAME.fullmatch(it.master)
            if not g:
                raise ValueError(f'class emission: unsupported master {it.master}')
            fam, bits, faces = g[1], int(g[2]), g[3]
            if bits != lane['bits']:
                raise ValueError(f'{name}: source width {bits} != calendar width {lane["bits"]}')
            parts = slices(bits, mw)
            made = []
            compact = os.environ.get('OT_SPLIT_FWD_CLASS_PACK') == '1'
            reserve_w, reserve_h = (it.w,it.h) if compact else reservation(bits, None, mw)
            if not compact and (it.w + 1e-3 < reserve_w or it.h + 1e-3 < reserve_h):
                raise ValueError(f'{name}: class reservation missing: {it.w}x{it.h} < {reserve_w}x{reserve_h}')
            for part, (lo, hi) in enumerate(parts):
                row = C.classify(f'qfd_{fam}_{hi-lo}_{faces}_1x1')
                ni = copy.copy(it)
                ni.name = name if len(parts) == 1 else slice_name(name,part)
                ni.master, ni.orient = row['cls'], row['orient']
                ni.w, ni.h = row['class_frame']
                # narrow split: as many columns as the reserved frame holds (1 in a 64.8-um landing column)
                cols = 1 if mw >= 600 else max(1, min(len(parts), int((reserve_w + C.SHAVE + 1e-6) // (ni.w + C.SHAVE))))
                nrows = math.ceil(len(parts) / cols)   # QW2-DIEFIX: was 'rows', shadowing the lane list (TypeError below)
                slot_w=(reserve_w+C.SHAVE)/cols-C.SHAVE
                slot_h=(reserve_h+C.SHAVE)/nrows-C.SHAVE
                ni.x = round(it.x + (part % cols)*(slot_w+C.SHAVE) + math.floor((slot_w-ni.w)/2/C.GX+1e-9)*C.GX,3)
                ni.y = round(it.y + (part // cols)*(slot_h+C.SHAVE) + math.floor((slot_h-ni.h)/2/C.GY+1e-9)*C.GY,3)
                classes[ni.master] = row
                made.append((ni, lo, hi, row))
                receipts.append(dict(instance=ni.name, source_instance=name, source_master=it.master,
                                     master=ni.master, orient=ni.orient, source_slice=[lo, hi],
                                     bits=hi-lo, class_bits=row['class_bits'], E=lane.get('E'), K=lane.get('K'),
                                     n=lane['n'], spare_bits=row['spare_bits']))
                if row['spare_bits']:
                    land = lane.get('landing')
                    if land is None:
                        raise ValueError(f'{name}: no native tie source for spare inputs')
                    landpart = part if len(parts) > 1 else 0
                    landname = land if len(slices(lane['bits'], mw)) == 1 else slice_name(land,landpart)
                    extra.append((f'fc_tie_{ni.name}', 'constant', 1,
                                  [(landname, 'tie_lo')] + [(ni.name, f'a[{j}]') for j in range(hi-lo,row['class_bits'])]))
            mapping[name] = made
    newb = []
    for bid, cl, bits, eps in m['buses']:
        data = [(i,p) for i,p in eps if i in mapping and p.lstrip('*') in ('a','b')]
        if data:
            # parts of this net = the parts of its (per-lane width) class endpoints
            parts = [(il, ih) for _, il, ih, _ in mapping[data[0][0]]]
            for part,(lo,hi) in enumerate(parts):
                ne = []
                for i,p in eps:
                    if i in mapping and p.lstrip('*') in ('a','b'):
                        ni, il, ih, row = mapping[i][part]
                        if (il,ih) != (lo,hi):
                            raise ValueError(f'{bid}: source width mismatch')
                        ne.append((ni.name, p if bits==1 else f'{p}[{hi-lo-1}:0]'))
                    elif i in mapping:
                        if bits!=1:raise ValueError(f'{bid}: scalar class endpoint on a wide data net')
                        ne.extend((ni.name,p) for ni,*_ in mapping[i])
                    else:
                        ne.append((i, p if bits==1 else f'{p}[{hi-1}:{lo}]'))
                newb.append((bid if len(parts)==1 else f'{bid}__s{part}',cl,hi-lo,ne))
        else:
            # Scalar clocks/epoch/reset fan out; forwarded clock outputs are
            # separate nets per slice, each driving its matching next station.
            drivers = mapping.get(eps[0][0]) if eps else None
            if drivers and len(drivers)>1:
                for part,(ni,*_) in enumerate(drivers):
                    ne=[(ni.name,eps[0][1])]
                    for i,p in eps[1:]:
                        ne.append((mapping[i][part][0].name,p) if i in mapping else (i,p))
                    newb.append((f'{bid}__s{part}',cl,bits,ne))
            else:
                ne=[(ni.name,p) for i,p in eps for ni,*_ in mapping.get(i,[(by[i],)])]
                newb.append((bid,cl,bits,ne))
    # A physical tie output drives one scalar net, including all spare bits.
    tied, merged = {}, []
    for b in newb + extra:
        if b[1] == 'constant' and b[3] and b[3][0][1] in ('tie_lo','tie_hi'):
            key=b[3][0]
            if key in tied:
                tied[key][3].extend(b[3][1:])
            else:
                b=(b[0],b[1],b[2],list(b[3])); tied[key]=b; merged.append(b)
        else: merged.append(b)
    m['buses'] = merged
    physical_rows=[]
    for lane in rows:
        parts=slices(lane['bits'], lane_maxw(m, lane['bid']))
        for part,(lo,hi) in enumerate(parts):
            r=copy.deepcopy(lane)
            if len(parts)>1:
                r['bid']=f"{lane['bid']}__s{part}"
                r['stations']=[slice_name(n,part) for n in lane['stations']]
                r['landing']=slice_name(lane['landing'],part) if lane.get('landing') else None
            r['bits']=hi-lo
            r['source_slice']=[lo,hi]
            physical_rows.append(r)
    m['fwd_lanes']['lanes']=physical_rows
    m['insts'] = [ni for it in m['insts'] for ni,*_ in mapping.get(it.name,[(it,)])]
    # Retain logical calendar rows: slices have identical clocks, n, E and K.
    m['fwd_class_emission'] = dict(schema='opentallas.qwen.fwd-class-emission.v1',
                                  instances=receipts, logical_calendar=copy.deepcopy(rows),
                                  physical_instances=len(receipts), classes=sorted(classes))
    m['fwd_lanes']['class_emission'] = m['fwd_class_emission']
    m['fwd_lanes']['stations'] = sum(len(r['stations']) for r in physical_rows)
    m['fwd_lanes']['landings'] = len(physical_rows)
    follow = m.get('ck_follow',{})
    for (name,p),owner in list(follow.items()):
        if name in mapping:
            del follow[(name,p)]
            follow.update({(ni.name,p):owner for ni,*_ in mapping[name]})
    base_m, base_w, writer = v.masters, v.port_widths, v.write_netlist
    def masters(model,k=1,port_bits=None):
        out=base_m(model,k,port_bits)
        for old in {by[name].master for name in mapping} - set(classes):
            out.pop(old,None)
        for name,row in classes.items():
            pins=C.class_pins(name)
            mst=v.Master(name,*row['class_frame'],3,'closed D4 registered-enable forwarded lane class')
            for p,s in pins['ports'].items():
                if s.get('interior'):
                    x,y=s['positions_xy_um'][0]; mst.area(p,s['bits'],x,y,1)
                else:
                    a,b=s['range_um']; pitch=1 if s['bits']==1 else round((b-a)/(s['bits']-1)/0.048)
                    mst.face(p,s['bits'],s['face'],s['layer'],(a+b)/2,pitch)
            out[name]=mst
        return out
    def widths(model,k):
        out=base_w(model,k)
        for (name,p),n in list(out.items()):
            if '[' in p:
                del out[(name,p)]; base=p.split('[')[0]
                hi=int(p.split('[')[1].split(':')[0].rstrip(']'))+1
                out[(name,base)]=max(out.get((name,base),0),math.ceil(hi/k))
        for name,row in classes.items():
            out[(name,'a')]=out[(name,'b')]=math.ceil(row['class_bits']/k)
        return out
    def write(model,k,path,top='qfd_die'):
        if k!=1: raise ValueError('class source emission requires k=1')
        writer(model,k,path,top)
        text=Path(path).read_text(); declarations=[]; portw=widths(model,1)
        def instance(match):
            master,name,body=match.groups(); groups={}; ordinary=[]
            for p,e in re.findall(r'\.([^()]+)\(([^()]*)\)',body):
                z=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',p)
                if not z: ordinary.append(f'.{p}({e})'); continue
                pn,hi,lo=z[1],int(z[2]),int(z[3] or z[2]); slots=groups.setdefault(pn,{})
                for offset,j in enumerate(range(lo,hi+1)):
                    if j in slots: raise ValueError(f'{name}.{pn}[{j}]: duplicate connection')
                    slots[j]=e if hi==lo else f'{e}[{offset}]'
            for pn,slots in groups.items():
                width=portw[(master,pn)]; bits=[]
                for j in reversed(range(width)):
                    if j not in slots:
                        if pn!='b': raise ValueError(f'{name}.{pn}[{j}]: missing source')
                        net=f'fc_open_{name}_{pn}_{j}'; declarations.append(f'  wire {net};'); slots[j]=net
                    bits.append(slots[j])
                compressed=[]; j=0
                while j<len(bits):
                    q=re.fullmatch(r'(\w+)\[(\d+)\]',bits[j])
                    end=j+1
                    if q:
                        while end<len(bits) and bits[end]==f'{q[1]}[{int(q[2])-(end-j)}]': end+=1
                    compressed.append(f'{q[1]}[{q[2]}:{int(q[2])-(end-j)+1}]' if end-j>1 else bits[j])
                    j=end
                ordinary.append(f'.{pn}({{{", ".join(compressed)}}})')
            return f'  {master} {name} ('+', '.join(ordinary)+');'
        text=re.sub(r'^\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$',instance,text,flags=re.M)
        text=text.replace('endmodule','\n'.join(declarations)+'\nendmodule')
        Path(path).write_text(text)
    v.masters,v.port_widths,v.write_netlist=masters,widths,write
    if os.environ.get('OT_SPLIT_FWD_CLASS_PACK') == '1':
        pack_classes(v,m,{r['instance'] for r in receipts})


def merge_fanout(m, legs):
    """Restore shared producer nets after each parallel leg was placed."""
    first={}
    for original,(cl,bits,src,names) in legs.items():
        parts=slices(bits)
        for part,(lo,hi) in enumerate(parts):
            for name in names:
                physical=name if len(parts)==1 else f'{name}__s{part}'
                first[physical]=(original,part,lo,hi,len(parts))
    gathered={}; buses=[]
    for bid,cl,bits,eps in m['buses']:
        if bid not in first:
            buses.append((bid,cl,bits,eps));continue
        original,part,lo,hi,count=first[bid]
        gathered.setdefault((original,part),[]).extend(eps[1:])
    for original,(cl,bits,src,names) in legs.items():
        parts=slices(bits)
        for part,(lo,hi) in enumerate(parts):
            loads=gathered.get((original,part),[])
            if len(loads)!=len(names):
                raise ValueError(f'{original}: split fanout lost loads ({len(loads)} != {len(names)})')
            port=src[1] if len(parts)==1 else f'{src[1]}[{hi-1}:{lo}]'
            buses.append((original if len(parts)==1 else f'{original}__s{part}',cl,hi-lo,[(src[0],port)]+loads))
    m['buses']=buses
    m['r21_relays']['fanout_legs']={o:ns for o,(_,_,_,ns) in legs.items()}


def pack_classes(v,m,names):
    """Place actual closed outlines after directional planning, without a new edge.

    Only local legal sites are considered. Every move checks actual matching bit
    geometry on all incident data nets against 405um; no centroid substitution.
    The normal final GEN gates still check all untouched data/reset/clock nets.
    """
    from qwen_rom_fulldie_b3r2 import _pin_pos
    pos=_pin_pos(v,m,strict=True)
    by={i.name:i for i in m['insts']}
    bucket=216.0; cells={}; members={}
    def rect(i): return (i.x,i.y,i.x+i.w+C.SHAVE,i.y+i.h+C.SHAVE)
    def keys(r):
        return [(x,y) for x in range(math.floor(r[0]/bucket),math.floor((r[2]-1e-6)/bucket)+1)
                for y in range(math.floor(r[1]/bucket),math.floor((r[3]-1e-6)/bucket)+1)]
    def add(i):
        ks=keys(rect(i));members[i.name]=ks
        for k in ks: cells.setdefault(k,set()).add(i.name)
    def remove(i):
        for k in members.pop(i.name): cells[k].remove(i.name)
    for i in m['insts']:add(i)
    def collision(i):
        r=rect(i); nearby=set().union(*(cells.get(k,set()) for k in keys(r)))
        for other in nearby-{i.name}:
            q=rect(by[other])
            if r[0]<q[2]-1e-6 and q[0]<r[2]-1e-6 and r[1]<q[3]-1e-6 and q[1]<r[3]-1e-6:return other
        return None
    incident={n:[] for n in names}
    local={}
    for bid,cl,width,eps in m['buses']:
        if cl in ('clock_trunk','reset','constant') or len(eps)<2:continue
        if not any(n in names for n,p in eps):continue
        for n,p in eps:
            key=(n,p,width)
            if key not in local:
                pts=pos.bits(n,p,width)
                if pts is None:raise ValueError(f'class packing: missing actual bit geometry {n}.{p} width{width}')
                it=by[n];local[key]=[(x-it.x,y-it.y) for x,y in pts]
        for load in eps[1:]:
            pair=(bid,width,eps[0],load)
            for n in {eps[0][0],load[0]} & names:incident[n].append(pair)
    def pin_reach(i):
        worst=0.0
        for bid,width,a,b in incident[i.name]:
            ia,ib=by[a[0]],by[b[0]]
            for qa,qb in zip(local[(a[0],a[1],width)],local[(b[0],b[1],width)]):
                d=abs(ia.x+qa[0]-ib.x-qb[0])+abs(ia.y+qa[1]-ib.y-qb[1])
                worst=max(worst,d)
                if d>405.0001:return False,worst,bid
        return True,worst,None
    die=m['die']; moves=[]
    # Largest closed outlines first. Search is bounded by the data reach itself,
    # not a timing exception or a larger acceptable route length.
    order=sorted(names,key=lambda n:(-by[n].w*by[n].h,n))
    offsets=[(0,0)]
    for ring in range(1,95):
        offsets.extend((x*4.32,y*4.32) for x,y in
                       [(x,sy*ring) for x in range(-ring,ring+1) for sy in (-1,1)] +
                       [(sx*ring,y) for y in range(-ring+1,ring) for sx in (-1,1)])
    for name in order:
        i=by[name];origin=(i.x,i.y);remove(i);chosen=None;reason=None
        for dx,dy in offsets:
            i.x=round(origin[0]+dx,3);i.y=round(origin[1]+dy,3)
            if i.x<0 or i.y<0 or i.x+i.w>die['w'] or i.y+i.h>die['h']:continue
            reason=collision(i)
            if reason:continue
            ok,worst,why=pin_reach(i)
            if ok:chosen=(i.x,i.y,worst);break
            reason=f'{why} matching-bit reach {worst:.3f}'
        if chosen is None:
            i.x,i.y=origin;add(i)
            raise ValueError(f'class packing: no legal <=405um site for {name} ({i.master}), last {reason}')
        add(i)
        if chosen[:2]!=origin:moves.append(dict(instance=name,old_xy=origin,xy=chosen[:2],worst_data_um=chosen[2]))
    # A later move checks its earlier neighbour, so every final pair is checked.
    for name in names:
        i=by[name]
        if collision(i):raise ValueError(f'class packing final overlap {name}')
        ok,worst,why=pin_reach(i)
        if not ok:raise ValueError(f'class packing final reach {name} {why} {worst}')
    m['fwd_lanes']['class_emission']['packing']=dict(rule='actual closed outlines and matching-bit <=405um',moves=moves)
