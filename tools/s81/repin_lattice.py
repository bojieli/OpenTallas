"""ASAP7 translation-preserving face packing for die pin search.

A group may translate only by an integer multiple of every member layer's
preferred-direction period. This preserves its source pin/track residue even
when that residue needs a nonzero macro origin. Assigned/native pins are never
repaired here. Callers must qualify the source and emitted complete masters.
"""
import math

PITCH_NM = {'M1':36, 'M2':270, 'M3':36, 'M4':48, 'M5':48,
            'M6':64, 'M7':64, 'M8':80, 'M9':80}


def translation_period_nm(layers):
    layers=set(layers)
    if not layers or layers-PITCH_NM.keys():
        raise ValueError(f'unknown or empty signal layers: {sorted(layers)}')
    return math.lcm(*(PITCH_NM[x] for x in layers))


def _nm(x):
    v=round(x*1000)
    if abs(x*1000-v)>1e-5:
        raise ValueError(f'non-integer nm face geometry: {x}')
    return v


def pack_lattice_face(rows, lo, hi, reorder=False):
    """Feasible ordered packing, with immutable anchors and per-row lattices.

    Each row supplies start,width,desired,w,anchored,period_nm. Starts remain
    congruent to the original start modulo period_nm. A backward pass reserves
    enough room for every remaining row before a forward nearest-desired pass.
    Reordering happens only between anchors. Raises when no feasible packing
    exists in the selected order. This is a bounded search heuristic, not a
    claim of a globally optimal placement.
    """
    out=[None]*len(rows)
    starts=[_nm(r['start']) for r in rows]
    widths=[_nm(r['width']) for r in rows]
    periods=[r['period_nm'] for r in rows]
    if any(not isinstance(p,int) or p<=0 for p in periods):
        raise ValueError('positive integer translation periods required')
    left=_nm(lo); upper=_nm(hi); seg=[]
    def floor(i,x):
        return starts[i]+((x-starts[i])//periods[i])*periods[i]
    def ceil(i,x):
        return starts[i]-((starts[i]-x)//periods[i])*periods[i]
    def flush(right):
        nonlocal left
        idx=sorted(seg,key=lambda i:rows[i]['desired']) if reorder else list(seg)
        latest={}; end=right
        for i in reversed(idx):
            latest[i]=floor(i,end-widths[i]); end=latest[i]
        pos=left
        for i in idx:
            earliest=ceil(i,pos)
            if earliest>latest[i]:
                raise ValueError(f'no lattice capacity for face group {i}')
            # Rounding target itself is fine: group origins and periods are nm.
            target=round(rows[i]['desired']*1000)
            low=floor(i,target); high=low+periods[i]
            x=min((max(earliest,min(v,latest[i])) for v in (low,high)),
                  key=lambda v:(abs(v-target),v))
            out[i]=x/1000; pos=x+widths[i]
    for i,r in enumerate(rows):
        if r.get('anchored'):
            if abs(r['desired']-r['start'])>1e-9:
                raise ValueError('anchored group requests translation')
            if starts[i]<left or starts[i]+widths[i]>upper:
                raise ValueError('anchored group outside face or overlapping anchor')
            flush(starts[i]);out[i]=r['start'];left=starts[i]+widths[i];seg=[]
        else:
            seg.append(i)
    flush(upper)
    return out
