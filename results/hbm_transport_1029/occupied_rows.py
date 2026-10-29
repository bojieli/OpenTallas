"""Private planner adapter: project proposed FFs away from already used rows.

The legal-row allocator is authoritative, but the shared DP only knows macro
boxes. Occupied earlier FT banks can therefore make its chosen target impossible
within the fixed 40um legalization radius. Compress used candidate sites into
rectangular row runs and give those exact occupied candidate bands to DP too.
No radius, timing budget, row bound or legal-site test is relaxed.
"""
import collections,re,inspect

def used_bands(allocator):
    rows=collections.defaultdict(list)
    for index in allocator.used:
        rows[index//allocator.nx+allocator.iy0].append(index%allocator.nx+allocator.ix0)
    bands=collections.defaultdict(list)
    for iy, xs in rows.items():
        xs.sort();lo=last=xs[0]
        for x in xs[1:]:
            if x!=last+1:bands[lo,last].append(iy);lo=x
            last=x
        bands[lo,last].append(iy)
    out=[]
    for (left,right),ys in bands.items():
        ys.sort();lo=last=ys[0]
        def emit(lo,hi):
            out.append((allocator.ox+left*allocator.cp+allocator.cw/2-allocator.cp/2,
                        allocator.oy+lo*allocator.rp,
                        allocator.ox+right*allocator.cp+allocator.cw/2+allocator.cp/2,
                        allocator.oy+hi*allocator.rp+allocator.ch))
        for y in ys[1:]:
            if y!=last+1:emit(lo,last);lo=y
            last=y
        emit(lo,last)
    return out

def install(module):
    source=inspect.getsource(module.place_slot)
    edits=[('    base = set(alloc.used)\n','    base = set(alloc.used)\n    last_reason = "none"\n'),
           ('            except NoChain:\n                break\n','            except NoChain as error:\n                last_reason = str(error)\n                break\n'),
           ('after tightening by {extra:.0f} um")','after tightening by {extra:.0f} um: {last_reason}")')]
    for before,after in edits:
        if source.count(before)!=1:raise RuntimeError('ft_corridor wrapper mismatch')
        source=source.replace(before,after)
    exec(compile(source,__file__+':cause_preserving','exec'),module.__dict__)
    original=module.place_slot
    def occupied(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kwargs):
        base=set(alloc.used);avoid=used_bands(alloc)
        # A failed selected bank has no free row within its unchanged 40um
        # neighborhood. Backtrack that neighborhood instead of enlarging radius.
        for _ in range(24):
            alloc.used=set(base)
            try:return original(slot,a,b,fin,fout,w,h,list(boxes)+avoid,alloc,budget,**kwargs)
            except ValueError as error:
                match=re.search(r'only\d+ legal sites for\d+ at\(([-+\d.e]+),\s*([-+\d.e]+)\) within([-+\d.e]+)um',str(error))
                if not match:raise
                x,y,r=map(float,match.groups());avoid.append((x-r,y-r,x+r,y+r))
        raise ValueError(slot['name']+': no legal bank after occupied-row target backtracking')
    module.place_slot=occupied
