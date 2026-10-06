#!/usr/bin/env python3
"""Byte-only adapter fixture: literal Opt4 cfg, released W2 and original issue order.

The fixture memory is not an installed production span or a runtime lease.
Production callers supply their actual installed addresses/full allocated tags
through the adapter's explicit lookup ports. No arithmetic or input inference.
"""
import argparse
from pathlib import Path
from types import SimpleNamespace
import ast
import csv
import shutil
import numpy as np
from dshbm_expert_workgroup_interleave import w2_exported_reader,w2_source_rows,w2_compact_stream
from rtl_gpu_sm_exact import issue_order


def emit(service,weights,installed,out):
    out.mkdir(parents=True,exist_ok=False)
    # Original allocator/byte emitter, private RAM fixture ONLY. L=0 means no
    # transformer compilation; Program.__init__/put/wr run unchanged, no model,
    # checkpoint, arithmetic or reconstructed installer authority.
    source=Path(__file__).resolve().parent/'gpu_sys/v41_hbm.py'
    cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Program')
    put=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='put')
    ns={};exec(compile(ast.Module(body=[put],type_ignores=[]),str(source),'exec'),ns)
    sectors={}
    for r in csv.DictReader((installed/'sectors.csv').open()):
        key=tuple(int(r[k]) for k in ('slot','sm','local_line','quarter'))
        addr=int(r['provider_byte_address'])
        if key in sectors or addr%32 or not 119160832<=addr<119265280:
            raise ValueError('actual installer sector ownership/aperture')
        sectors[key]=addr
    if len(sectors)!=3264 or len(set(sectors.values()))!=3264:raise ValueError('installed sector coverage/alias')
    for layer,ids in [(20,(41,65,158,164,259,266))]:
        program=SimpleNamespace(cur=max(sectors.values())+32,a={})
        maps=[];expected=[]
        output=out/f'L{layer}';output.mkdir()
        d=service/f'L{layer}'
        raw=[int(x,16).to_bytes(128,'little') for x in (d/'w2.hex').read_text().split()]
        lut=[int(x,16) for x in (d/'cfg_lut.hex').read_text().split()]
        counts=[int(x,16) for x in (d/'cfg_lines.hex').read_text().split()]
        if len(raw)!=816 or len(lut)!=136 or counts!=[10,10,0,0,29,29,29,29]:
            raise ValueError('literal Opt4 W2 extent/counts required')
        lookup={}
        for a,cfg in enumerate(lut):
            if cfg==0xffff:
                if any(any(raw[k*136+a]) for k in range(6)):
                    raise ValueError('nonzero transport padding')
                continue
            key=(cfg>>8,cfg&255)
            if key in lookup:raise ValueError('cfg alias')
            lookup[key]=a
        result_base=ns['put'](program,'W2_ADAPTER_UNIT_RESULT',128,align=64)
        # Actual output allocation is a private successor after the installed
        # input extents. It is not a production output lease or index sink.
        for part in range(2):shutil.copyfile(installed/f'w2_p{part}.hex',output/f'w2_p{part}.hex')
        reader=w2_exported_reader(weights/f'L{layer}',layer,ids)
        for k,e in enumerate(ids):
            views=w2_source_rows(reader,e,2,0)
            for sm,v in enumerate(views):
                if not v['rows']:continue
                compact,native=w2_compact_stream(v['packed'],v['scale'])
                captured=b''.join(raw[k*136+lookup[sm,q]] for q in range(counts[sm]))
                if captured!=compact+bytes(len(captured)-len(compact)):
                    raise ValueError('released bytes/cfg/tail mismatch')
                offset=0
                for n,(_,g,_) in enumerate(issue_order(len(v['rows']),2,8,True)):
                    lanes=8 if g==0 else 1;length=17*lanes
                    first=offset//32;count=((offset%32)+length+31)//32
                    addresses=tags=cfgs=0
                    for part in range(count):
                        local,q=divmod(first+part,4)
                        slot=lookup[sm,local]
                        addr=sectors[k,sm,local,q]
                        # Tags are allocated/held by the bench's parent caller
                        # at native acceptance, NOT by this layout compiler.
                        addresses|=addr<<(32*part)
                        cfgs|=lut[slot]<<(16*part)
                    # Full logical native address, not a compact byte address.
                    native_addr=k*len(native)+n
                    fields=[(count,3),(lanes,4),(offset,16),(sm,3),(native_addr,32),
                            (addresses,192),(tags,96),(cfgs,96)]
                    word=shift=0
                    for value,bits in fields:
                        if not 0<=value<(1<<bits):raise ValueError('fixture field overflow')
                        word|=value<<shift;shift+=bits
                    maps.append(word);expected.append(native[n]);offset+=length
                if offset!=len(compact):raise ValueError('source issue order incomplete')
        if len(maps)!=1344:raise ValueError('selected source row coverage')
        memory={}
        for k in range(6):
            for (sm,line),slot in lookup.items():
                for q in range(4):
                    addr=sectors[k,sm,line,q]
                    memory[addr]=int.from_bytes(raw[k*136+slot][32*q:32*q+32],'little')
        for q in range(4):memory[result_base+32*q]=0
        addresses=sorted(memory)
        for name,data,width in [('memory_addresses.hex',addresses,8),
                                ('memory.hex',[memory[a] for a in addresses],64),
                                ('maps.hex',maps,112),('expected.hex',expected,272)]:
            (output/name).write_text(''.join(f'{w:0{width}x}\n' for w in data))
        (output/'args.txt').write_text(f'+NWORDS={len(memory)} +NCASES={len(maps)} '
                                      f'+OUT_BASE={result_base:x} +OUT_LIMIT={result_base+128:x}\n')
        print(f'INSTALLED_NS2_RELEASED_W2_BYTE_FIXTURE L{layer} lines={len(maps)} memory_sectors={len(memory)}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('service','weights','installed','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();emit(a.service,a.weights,a.installed,a.out)
