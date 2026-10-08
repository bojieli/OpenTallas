#!/usr/bin/env python3
"""Allocate exact native seq/weight/full-NC8-X bytes in an existing workspace.

Output is a source-pinned installation image, not an ownership grant or proof
that a hardware loader has installed it. Source payload provenance is mandatory.
"""
import argparse, ast, hashlib, json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from gpu_sys.mem_image import placement
from hbm_sm_native_install_model import model
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def words(p,bits):
    v=[int(x,16) for x in p.read_text().split()]
    if any(x<0 or x>>bits for x in v): raise ValueError(f'{p.name} exceeds {bits} bits')
    return v

def install(book_path, manifest_path, out):
    bp,mp,out=Path(book_path),Path(manifest_path),Path(out)
    book=json.loads(bp.read_text()); src=json.loads(mp.read_text())
    if book['schema']!='opentallas.ds20.installed_workspace.v1' or book['memory_bytes']!=134217728:
        raise ValueError('actual current NS2 workspace required')
    if src['schema']!='opentallas.native_sm.payload.v1' or src['nc']!=8 or not src['provenance']:
        raise ValueError('full NC8 source provenance required')
    paths={}
    for name in ('seq.hex','lines.hex','x.hex'):
        item=src['artifacts'][name]; p=(mp.parent/item['path']).resolve()
        if sha(p)!=item['sha256']: raise ValueError('source hash mismatch: '+name)
        paths[name]=p
    seq=words(paths['seq.hex'],32); lines=words(paths['lines.hex'],1088); xs=words(paths['x.hex'],25216)
    if not seq or len(seq)%10 or len(seq)>2560: raise ValueError('bounded exact ten-word records required')
    records=[seq[i:i+10] for i in range(0,len(seq),10)]
    resident=None
    for r in records:
        rows,c,g,fmt,n,gs,load,extent,dep,xb=r
        if not(0<rows<=4096 and 0<c<=65535 and 0<g<=255 and fmt<=2 and 0<n<1<<24 and gs<=1 and load<=1 and dep<=1 and extent==c*g and 0<extent<=128 and xb<128):
            raise ValueError('invalid native record')
        key=(c,g,fmt,extent,xb)
        if not load and resident!=key: raise ValueError('reuse lacks exact resident operand')
        if load: resident=key
    if sum(r[4] for r in records)!=len(lines) or sum(r[7] for r in records if r[6])!=len(xs):
        raise ValueError('payload count does not match native records')
    recipe=book['recipe_successor']; allocs=recipe['allocations']; cursor=recipe['emitted_image_bytes']
    occupied=[a['end'] for a in allocs]+[a['end'] for a in book['occupied']]
    if type(cursor)!=int or cursor%4096 or cursor<max(occupied) or cursor>=book['memory_bytes']:
        raise ValueError('invalid live allocation boundary')
    allocator=ROOT/'tools/gpu_sys/v41_hbm.py'
    cls=next(n for n in ast.parse(allocator.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Program')
    nodes=[next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name) for name in ('put','wr')]
    ns={'np':np};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(allocator),'exec'),ns)
    state=SimpleNamespace(cur=cursor,a={a['name']:a['base'] for a in allocs},mem=[{}]); spans=[]
    def put(name,raw,align=32,reserve=False):
        if name in state.a: raise ValueError('existing allocation name: '+name)
        base=ns['put'](state,name,len(raw),align=align)
        if state.cur>book['memory_bytes']: raise ValueError('actual workspace capacity exhausted')
        if not reserve:
            ns['wr'](state,0,base,np.frombuffer(raw,dtype=np.uint8))
            if state.mem[0][base].tobytes()!=raw: raise ValueError('allocator byte roundtrip mismatch')
        spans.append(dict(name=name,base=base,end=state.cur,bytes=len(raw),reserved_only=reserve))
        return base
    program_raw=b''.join(v.to_bytes(4,'little') for v in seq)
    program=put('NATIVE_SM_PROGRAM',program_raw+bytes((-len(program_raw))%32))
    li=xi=0; installed=[]; resident_x=None
    for i,r in enumerate(records):
        rows,c,g,fmt,n,gs,load,extent,dep,xb=r
        raw=b''.join(v.to_bytes(136,'little')+bytes(24) for v in lines[li:li+n]);li+=n
        wb=put(f'NATIVE_SM_W{i}',raw,160)
        if load:
            raw=b''.join(v.to_bytes(3152,'little')+bytes(176) for v in xs[xi:xi+extent]);xi+=extent
            resident_x=put(f'NATIVE_SM_X{i}',raw)
        rb=put(f'NATIVE_SM_R{i}',bytes(rows*32),reserve=True)
        installed.append(dict(record=i,program_byte_address=program+40*i,
            weight_byte_base=wb,weight_line_base=wb//160,weight_lines=n,weight_stride=160,
            x_byte_base=resident_x,x_extent=extent,x_stride=3328,x_ring_base=xb,x_load=bool(load),
            result_byte_base=rb,result_rows=rows,result_stride=32))
    # Program tail padded only in its final sector, allocated span must not overlap.
    sectors={}
    for base,arr in state.mem[0].items():
        raw=arr.tobytes()
        for off in range(0,len(raw),32):
            addr=base+off
            if addr in sectors: raise ValueError('duplicate installation sector')
            sectors[addr]=raw[off:off+32].ljust(32,b'\0')
    partition=[[],[]]
    for addr,raw in sorted(sectors.items()):
        part,sector,_,lane=placement(addr,2,2097152)
        if lane or sector>=2097152: raise ValueError('provider sector alias')
        partition[part].append(f'@{sector:x}\n{raw[::-1].hex()}\n')
    result=dict(schema='opentallas.native_sm.installed_spans.v1',scope=src['provenance'],
        model=model(),source_sha256={str(bp):sha(bp),str(mp):sha(mp),str(allocator):sha(allocator),**{str(p):sha(p) for p in paths.values()}},
        program_base=program,program_limit=program+len(seq)*4,program_storage_limit=program+((len(seq)*4+31)//32)*32,record_count=len(records),
        allocation_start=cursor,allocation_end=state.cur,spans=spans,records=installed,
        installation_sectors=len(sectors),production_installation_complete=False,
        hardware_ownership_granted=False,loader_acknowledged=False)
    out.mkdir(parents=True,exist_ok=False)
    for i,p in enumerate(partition):(out/f'native_p{i}.hex').write_text(''.join(p))
    (out/'installed_spans.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=install(a.workspace,a.source,a.out);print(json.dumps({k:r[k] for k in ('record_count','installation_sectors','allocation_start','allocation_end')}))
