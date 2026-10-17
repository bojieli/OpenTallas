"""Opt-in BF front ABI transformation; no physical-view inheritance.

The die generator retains its packed transport nets. Only load endpoint slices
are renamed to the actual semantic1024-bit N data/44-bit S metadata ports.
Logical clocks share the fixed stream epoch; actual per-root phi-R delivery is
still required from this candidate's own insertion records before adoption.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FRONT_MASTER = 'dsfd_bf_front_roots'
FRONT_CLOCK_PORTS = ('ck', 'io_clk', 'io_n', 'io_w', 'io_e')
PIN_REQUEST = 'physical/ref_tile_specs/s81_bf_native_1015/front_five_roots/pin_request.json'
SOURCE_MANIFEST = 'results/rtl/s81_bf_clock_1015/c10/recovery_0253/front_roots_source.json'


def source_receipt():
    manifest=json.loads((ROOT/SOURCE_MANIFEST).read_text())
    for name,expected in manifest['outputs'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, f'BF source drift: {name}'
    assert manifest['physical_xb_reconstruction']=='legacy_xb[1067:0] = {xb_data[1023:0], xb_meta[43:0]}'
    return dict(source_sha256=manifest['outputs'], payload_cycles_added=0,
                boot_reset_release_edges_added=1, total_front_clock_roots=5,
                physical_qualification=False, parent_native_qualification=False,
                required_before_adoption=['own TT/FF/DRC/native closure',
                                          'own per-root R/phi-R die delivery',
                                          'all actual pin/PG/neighbor incidents',
                                          'static initialization release+1 ledger',
                                          'programme pin-to-core age2: source-bound OFF-1/DELTA0 producer and actual fault-observing calendar proof'])


def split_xb_endpoint(port, bus_width):
    """Return semantic loads preserving each source-net bit, including @offset."""
    match=re.fullmatch(r'xb(?:\[(\d+):(\d+)\])?(?:@(\d+))?',port)
    if not match:
        return [port]
    lo,hi,offset=match.groups()
    lo,hi=(0,1067) if lo is None else (int(lo),int(hi))
    offset=0 if offset is None else int(offset)
    assert 0<=lo<=hi<1068 and offset+hi-lo<bus_width, (port,bus_width)
    result=[]
    for start,end,name,base in [(0,43,'xb_meta',0),(44,1067,'xb_data',44)]:
        a,b=max(lo,start),min(hi,end)
        if a<=b:
            result.append(f'{name}[{a-base}:{b-base}]@{offset+a-lo}')
    return result


def rewrite_front(model):
    """Call after _bf_hier_nets, before final port/clock-tree assembly."""
    source=source_receipt()
    fronts={it.name:it for it in model['insts'] if it.master=='dsfd_bf_front_static'}
    assert fronts, 'BF roots require real static fronts'
    for it in fronts.values():
        assert abs(it.w-116.64)<1e-6 and abs(it.h-198.72)<1e-6, (it.name,it.w,it.h)
        assert it.orient=='R0', (it.name,it.orient)
        it.master=FRONT_MASTER
    rewritten=[]
    clock_owners={name:0 for name in fronts}
    coverage={name:{} for name in fronts}
    for bid,cls,bits,endpoints in model['buses']:
        new=[]
        for index,(name,port) in enumerate(endpoints):
            if name not in fronts:
                new.append((name,port));continue
            if port.startswith('xb[') or port=='xb':
                assert index>0, 'BF operand transport must enter the actual front'
                split=split_xb_endpoint(port,bits)
                for p in split:
                    mm=re.fullmatch(r'(xb_data|xb_meta)\[(\d+):(\d+)\]@(\d+)',p)
                    base,a,b,off=mm.groups();a,b,off=int(a),int(b),int(off)
                    for i in range(a,b+1):
                        key=(base,i);assert key not in coverage[name], (name,key,'multiple operand producers')
                        coverage[name][key]=(bid,off+i-a)
                    new.append((name,p))
            else:
                new.append((name,port))
            if cls=='col_clock' and port=='ck':
                clock_owners[name]+=1
                for clock in FRONT_CLOCK_PORTS[2:]:
                    assert (name,clock) not in endpoints
                    new.append((name,clock))
        rewritten.append((bid,cls,bits,new))
    expected={('xb_data',i) for i in range(1024)}|{('xb_meta',i) for i in range(44)}
    assert all(n==1 for n in clock_owners.values()), clock_owners
    for name in fronts:
        clock_counts={p:sum((name,p)==ep for _,cls,_,eps in rewritten if cls=='col_clock' for ep in eps)
                      for p in FRONT_CLOCK_PORTS}
        assert all(count==1 for count in clock_counts.values()), (name,clock_counts)
    assert all(set(c)==expected for c in coverage.values()), 'all1068 operand bits must have exact source joins'
    model['buses']=rewritten
    model['bf_front_root_abi']=dict(source,instances=sorted(fronts),
                                    operand_joins={name:{f'{p}[{i}]':v for (p,i),v in c.items()}
                                                   for name,c in coverage.items()})


def populate_front(master, ports):
    """Literal request shapes; does not bind any view or infer timing."""
    source_receipt()
    pins=json.loads((ROOT/PIN_REQUEST).read_text())['pins']
    expected={}
    for name,(_,width) in ports.items():
        for i in range(width):
            pin=f'{name}[{i}]'
            # The immutable pin request retains scalar syntax for scalar ports.
            key=pin if pin in pins else name if width==1 else None
            assert key is not None and key in pins, (name,i,'pin missing')
            expected[key]=True
            p=pins[key];w,h=float(p['w']),float(p['h'])
            # Match place_pin -force_to_die_boundary: normal extent lies
            # inside the die. Actual exported view must confirm these shapes.
            if p['face']=='W':rect=(0,p['y']-h/2,w,p['y']+h/2)
            elif p['face']=='E':rect=(master.w-w,p['y']-h/2,master.w,p['y']+h/2)
            elif p['face']=='S':rect=(p['x']-w/2,0,p['x']+w/2,h)
            else:rect=(p['x']-w/2,master.h-h,p['x']+w/2,master.h)
            if i==0:
                master.order.append(name);master.ports[name]=('rects',[])
            master.ports[name][1].append((pin,p['layer'],rect))
    assert set(expected)==set(pins), ('BF pin coverage',set(pins)-set(expected),set(expected)-set(pins))
