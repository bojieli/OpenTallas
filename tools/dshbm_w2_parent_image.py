#!/usr/bin/env python3
"""Bind finite W2 descriptors to an existing DS20 installed image.

This compiler does not allocate memory, create inputs/results, infer addresses
from logical PQ line numbers, or generate a kernel entry. Installation spans
and linked entry PCs must come from the selected source image producer.
The output is private 64-bit loader words for the bounded parent descriptor
bank; the DS20 doorbell, frame and completion ABI remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field(v,bits,name):
    if type(v)!=int or not 0<=v<1<<bits:
        raise ValueError(f'{name}: missing/out-of-range source field')
    return v


def compile_image(binding,root):
    if binding.get('schema')!='opentallas.ds20.w2.installed_source.v1':
        raise ValueError('selected source producer installation required')
    artifacts=binding['source_artifacts']
    if not artifacts:
        raise ValueError('missing immutable compiler image sources')
    for name,sha in artifacts.items():
        path=(root/name).resolve()
        if not path.is_file() or digest(path)!=sha:
            raise ValueError('missing/changed installed source: '+name)
    program=root/binding['program_path']
    if binding['program_path'] not in artifacts:
        raise ValueError('linked program not pinned')
    im=[int(w,16) for w in program.read_text().split()]
    linked=binding['linked_entries_path']
    if linked not in artifacts:
        raise ValueError('missing source-pinned linked W2 entry manifest')
    actual_entries=json.loads((root/linked).read_text())['w2_entry_pcs']
    bank=field(binding['descriptor_loader_base'],8,'descriptor_loader_base')
    descriptors=binding['descriptors']
    if not 1<=len(descriptors)<=4 or bank+16*len(descriptors)>256:
        raise ValueError('finite four-entry existing CMD64 loader bank')
    # The command producer must prove these existing loader words are free;
    # no reserved opcode, guessed upper bank, or image overwrite is emitted.
    commands=root/binding['command_path']
    if binding['command_path'] not in artifacts:
        raise ValueError('existing command image not pinned')
    cmd=[int(w,16) for w in commands.read_text().split()]
    if any(cmd[a] for a in range(bank,min(len(cmd),bank+16*len(descriptors)))):
        raise ValueError('descriptor bank overlaps existing command words')
    extent=field(binding['memory_bytes'],32,'memory_bytes')
    spans=[];ids=set();pcs=set();words=[];compiled=[]
    for k,d in enumerate(descriptors):
        pc=field(d['entry_pc'],32,'entry_pc')
        if pc>=len(im) or pc not in actual_entries or pc in pcs:
            raise ValueError('missing/nonunique actual linked W2 entry')
        pcs.add(pc)
        pair=d['pair']
        if type(pair)!=bool:
            raise ValueError('literal PAIR selection required')
        n=2 if pair else 1
        ops=d['operations']
        if len(ops)!=n:
            raise ValueError('immutable original operation association')
        fp4=d['format']==2 and d['groups']==2
        fp8=d['format']==1 and d['groups']==3 and not pair
        if d['c']!=8 or not (fp4 or fp8) or not d['group_stride']:
            raise ValueError('only paired FP4 or original final FP8 W2 shape')
        line_count=32 if fp4 else 48
        x_count=16 if fp4 else 24
        x_stride=512 if fp4 else 256
        bases={};ends={};xb=[];opids=[];logical=[]
        for side,o in enumerate(ops):
            ident=field(o['original_op'],32,'original_op')
            if ident in ids or o['rows']!=2 or o['lines']!=line_count or o['x_addresses']!=x_count:
                raise ValueError('duplicate identity/unqualified operation geometry')
            ids.add(ident);opids.append(ident)
            logical.append(field(o['logical_line_base'],32,'logical_line_base'))
            xb.append(field(o['x_ring_base'],7,'x_ring_base'))
            for kind,stride,count in [('weight',160,line_count),('x',x_stride,x_count),('result',32,2)]:
                s=o[kind+'_span'];base=field(s['base'],32,kind+'_base')
                end=field(s['end'],32,kind+'_end')
                if s['stride']!=stride or end-base!=stride*count or base%32 or end>extent:
                    raise ValueError('unbound/unaligned/out-of-capacity '+kind+' span')
                source=s['image_path']
                if source not in artifacts:
                    raise ValueError('span image not source pinned')
                image=root/source
                if image.stat().st_size!=extent:
                    raise ValueError('installed image capacity mismatch')
                # No reference output is read. Producer identity is source
                # binding metadata, not a software-generated hardware grant.
                if s['producer'] not in binding['source_producers'] or s['producer'] not in artifacts:
                    raise ValueError('missing actual '+kind+' source producer')
                spans.append((base,end,kind,ident,source))
                bases[kind,side]=base;ends[kind,side]=end
        if pair and ((xb[1]-xb[0])%128<16 or (xb[0]-xb[1])%128<16):
            raise ValueError('overlapping whole A/B x ownership')
        if pair and logical[1]!=logical[0]+32:
            raise ValueError('literal adjacent retained weight spans required')
        if not pair:
            xb.append(xb[0]);opids.append(opids[0]);logical.append(logical[0])
            for kind in ('weight','x','result'):
                bases[kind,1]=bases[kind,0];ends[kind,1]=ends[kind,0]
        # Sixteen real CMD64 writes, then hardware loaded-word mask/shape
        # validation. No op_bound/d_bound word or manufactured ready bit.
        w=[(0x57325031<<32)|pc,opids[0]|opids[1]<<32]
        for kind in ('weight','x','result'):
            w += [bases[kind,0]|bases[kind,1]<<32,ends[kind,0]|ends[kind,1]<<32]
        w += [(4 if pair else 2)|(2<<13)|(8<<26)|(d['groups']<<42)|(d['format']<<50)|(1<<52)|(xb[0]<<53),
              xb[1]|((xb[1]-xb[0])%128)<<7|int(pair)<<14,
              136|(160<<16)|(x_stride<<32)|(32<<48),line_count|(line_count<<32),
              logical[0]|logical[1]<<32,extent,0,0]
        if len(w)!=16:raise AssertionError('descriptor width')
        words += [dict(address=bank+k*16+j,data=v) for j,v in enumerate(w)]
        compiled.append(dict(entry_pc=pc,original_ops=opids,pair=pair,loader_slot=k))
    for i,a in enumerate(spans):
        for b in spans[i+1:]:
            if a[4]==b[4] and max(a[0],b[0])<min(a[1],b[1]):
                raise ValueError('installed producer/result lifetimes overlap')
    return dict(schema='opentallas.ds20.w2.parent_loader_words.v1',default_enabled=False,
        descriptor_bits=1024,loader_words=words,descriptors=compiled,
        source_sha256=artifacts,no_allocator=True,no_golden_generation=True,
        no_payload_generation=True,hardware_bound_bits_generated=False,
        production_installation_complete=False,physical_admitted=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=compile_image(json.loads(a.binding.read_text()),a.binding.parent)
    if a.output.exists():raise ValueError('preserve prior compiler result')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
