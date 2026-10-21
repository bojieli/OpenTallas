"""Emit real D4 registered-enable lane classes, with parallel width slices.

Reservations precede placement; the existing reach and native-calendar gates remain
mandatory. This adapter adds no edge, changes no K, and uses no data-path exception.
"""
import copy
import math
import re
from pathlib import Path
from qwen_split import fwd_lane_classes as C


def slices(bits):
    n = math.ceil(bits / 600)
    width = math.ceil(bits / n)
    return [(lo, min(bits, lo + width)) for lo in range(0, bits, width)]


def reservation(bits):
    parts = slices(bits)
    wc = C.wclass(max(hi - lo for lo, hi in parts))
    frames = [C.frame(wc, g) for g in C.REP]
    w, h = max(f[0] for f in frames), max(f[1] for f in frames)
    return w, round((h + C.SHAVE) * len(parts) - C.SHAVE, 3)


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
        names = lane['stations'] + ([lane['landing']] if lane.get('landing') else [])
        for name in names:
            it = by[name]
            g = C.NAME.fullmatch(it.master)
            if not g:
                raise ValueError(f'class emission: unsupported master {it.master}')
            fam, bits, faces = g[1], int(g[2]), g[3]
            parts = slices(bits)
            made = []
            reserve_w, reserve_h = reservation(bits)
            if it.w + 1e-3 < reserve_w or it.h + 1e-3 < reserve_h:
                raise ValueError(f'{name}: class reservation missing: {it.w}x{it.h} < {reserve_w}x{reserve_h}')
            for part, (lo, hi) in enumerate(parts):
                row = C.classify(f'qfd_{fam}_{hi-lo}_{faces}_1x1')
                ni = copy.copy(it)
                ni.name = name if len(parts) == 1 else slice_name(name,part)
                ni.master, ni.orient = row['cls'], row['orient']
                ni.w, ni.h = row['class_frame']
                ni.x = it.x
                ni.y = round(it.y + part * (reserve_h + C.SHAVE) / len(parts), 3)
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
                    landname = land if len(slices(lane['bits'])) == 1 else slice_name(land,landpart)
                    extra.append((f'fc_tie_{ni.name}', 'constant', 1,
                                  [(landname, 'tie_lo')] + [(ni.name, f'a[{j}]') for j in range(hi-lo,row['class_bits'])]))
            mapping[name] = made
    newb = []
    for bid, cl, bits, eps in m['buses']:
        data = [(i,p) for i,p in eps if i in mapping and p.lstrip('*') in ('a','b')]
        if data:
            parts = slices(bits)
            for part,(lo,hi) in enumerate(parts):
                ne = []
                for i,p in eps:
                    if i in mapping:
                        ni, il, ih, row = mapping[i][part]
                        if (il,ih) != (lo,hi):
                            raise ValueError(f'{bid}: source width mismatch')
                        ne.append((ni.name, f'{p}[{hi-lo-1}:0]'))
                    else:
                        ne.append((i, f'{p}[{hi-1}:{lo}]'))
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
        parts=slices(lane['bits'])
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
    follow = m.get('ck_follow',{})
    for (name,p),owner in list(follow.items()):
        if name in mapping:
            del follow[(name,p)]
            follow.update({(ni.name,p):owner for ni,*_ in mapping[name]})
    base_m, base_w, writer = v.masters, v.port_widths, v.write_netlist
    def masters(model,k=1,port_bits=None):
        out=base_m(model,k,port_bits)
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
                ordinary.append(f'.{pn}({{{", ".join(bits)}}})')
            return f'  {master} {name} ('+', '.join(ordinary)+');'
        text=re.sub(r'^\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$',instance,text,flags=re.M)
        text=text.replace('endmodule','\n'.join(declarations)+'\nendmodule')
        Path(path).write_text(text)
    v.masters,v.port_widths,v.write_netlist=masters,widths,write


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
