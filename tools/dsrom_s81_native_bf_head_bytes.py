#!/usr/bin/env python3
"""Synchronous raw-byte bridge to the existing ReleasedHeadByteProvider.

No new images, FP operations, expected-output sources, or ROM allocators.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import socket
import struct
from pathlib import Path


def response(provider, request: bytes) -> bytes:
    if len(request)!=16:
        raise ValueError('BF head request must be four uint32 coordinates')
    rank,row,h,b=struct.unpack('<4I',request)
    try:
        if not (rank<4 and row<32320 and h<40 and b<8):
            raise ValueError('outside released head extent')
        value=provider.native_bf_word(rank,row,h,b)
        if (value['rank'],value['local_row'],value['h'],value['b'])!=(rank,row,h,b):
            raise ValueError('released provider returned a different source coordinate')
        word=value['word274']
        if type(word) is not int or not 0<=word<1<<274:
            raise ValueError('released native word width')
        return struct.pack('<I',0)+request+word.to_bytes(36,'little')
    except (ValueError,KeyError,TypeError):
        return struct.pack('<I',1)+request+bytes(36)


def serve(provider, path: Path, record: Path | None = None) -> None:
    # Caller owns provider and its exact source enrollment; never unlink a
    # preexisting socket/record or replace another running source service.
    if path.exists() or (record is not None and record.exists()):
        raise FileExistsError('preserve existing native head provider output')
    journal=hashlib.sha256();count=0;raw_bytes=0;failed=False
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
        listener.bind(str(path));listener.listen(1)
        try:
            conn,_=listener.accept()
            with conn:
                while True:
                    request=b''
                    while len(request)<16:
                        part=conn.recv(16-len(request))
                        if not part:break
                        request+=part
                    if not request:break
                    if len(request)!=16:raise ValueError('partial live head byte request')
                    reply=response(provider,request)
                    conn.sendall(reply);journal.update(request+reply);count+=1
                    if reply[:4]!=bytes(4):
                        failed=True;break
                    raw_bytes+=256  # eight actual32B source reads, no cache credit
        finally:
            if record is not None:
                record.write_text(json.dumps({'schema':'dsrom.s81.released_native_bf_head_bytes.v1',
                    'requests':count,'raw_source_read_bytes':raw_bytes,
                    'coordinate_payload_journal_sha256':journal.hexdigest(),
                    'failed_source_request':failed,'host_arithmetic':False,
                    'hardware_bandwidth_or_latency_credit':False},indent=2)+'\n')
    # Keep socket pathname as evidence. Cleanup belongs to the run owner.


def run_component(args):
    # Source movement only. Native archives compute normalization/dots/tail.
    # The earlier component's logits are opened ONLY after every native END.
    import os
    import subprocess
    import time
    import numpy as np
    from dsrom_s81_head_source_binding import HeadSourceBinding,ReleasedHeadByteProvider
    from dsrom_s81_execution_binding import CanonicalS81Execution
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    carry=np.load(args.carry,allow_pickle=False)
    if carry.files!=['H','PF'] or carry['H'].shape!=(4,4,5120) or carry['PF'].shape!=(4,4):
        raise ValueError('actual produced TP4 carry extent')
    for key in carry.files:
        if carry[key].dtype!=np.dtype('float32'):
            raise ValueError('actual carry must raw F32, no quantization')
    for rank in range(4):
        for name in ['H','PF']:
            carry[name][rank].astype('<f4',copy=False).view('<u4').tofile(out/f'{name}_rank{rank}.u32')
    carry.close()
    binding=HeadSourceBinding();execution=CanonicalS81Execution(Path(__file__).resolve().parents[1])
    program=binding.compile(opt_in=True,entry14=0)
    ops=[execution.target_native_operation(f'Lhead.I{i}',position=1048575,native_units={2}) for i in range(5)]
    (out/'normalization.words').write_text(''.join(str(o['index'])+' '+
        ' '.join(f'{w:08x}' for w in o['instruction'])+'\n' for o in ops))
    with ReleasedHeadByteProvider(binding,args.snapshot) as provider:
        norm=[provider.norm_crom(i)['word64'] for i in range(5120)]
        (out/'norm.crom.hex').write_text(''.join(f'{w:016x}\n' for w in norm))
        fd,base,spec=provider.source.descriptor('head.weight')
        shard=Path(os.readlink(f'/proc/self/fd/{fd}'));offset=base+spec['data_offsets'][0]
        source=dict(carry=str(args.carry.resolve()),carry_sha256=hashlib.sha256(args.carry.read_bytes()).hexdigest(),
            checkpoint=str(args.snapshot.resolve()),head_shard=str(shard),head_byte_offset=offset,
            head_spec=spec,norm_tensor='norm.weight',norm_crom_sha256=hashlib.sha256((out/'norm.crom.hex').read_bytes()).hexdigest(),
            head_program=program,normalization_operations=ops,
            component_source=str(Path(__file__).resolve().parents[1]/'rtl/test/s81_native_bf_head_producer/retained_smoke.cpp'),
            executable=str(args.component.resolve()),executable_sha256=hashlib.sha256(args.component.read_bytes()).hexdigest(),
            argmax_bound=False,scope='actual produced L20 H/PF to native released head COMPONENT; not full40-layer TOKEN',
            hardware_timing_claim=False)
    (out/'source.json').write_text(json.dumps(source,indent=2)+'\n')
    streams=[];children=[];started=time.monotonic()
    for rank in range(4):
        command=[str(args.component.resolve()),str(rank),str(out),str(shard),str(offset),str(out),str(args.selected_dir.resolve())]
        (out/f'argv_rank{rank}.json').write_text(json.dumps(command)+'\n')
        stream=(out/f'runtime_rank{rank}.log').open('x');streams.append(stream)
        child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        children.append(child);(out/f'pid_rank{rank}').write_text(str(child.pid)+'\n')
        print('NATIVE_HEAD_LAUNCHED rank',rank,'pid',child.pid,flush=True)
    codes=[p.wait() for p in children]
    for stream in streams:stream.close()
    result=dict(completed=all(c==0 for c in codes),returncodes=codes,exact=None,
        elapsed_seconds=time.monotonic()-started,argmax_bound=False,headline_timing=False,
        source_sha256=hashlib.sha256((out/'source.json').read_bytes()).hexdigest())
    if result['completed']:
        # Retained exact reference computed from THIS carry; read only at END.
        reference=np.load(args.reference,allow_pickle=False).view('<u4')
        if reference.shape!=(129280,):raise ValueError('END-only reference extent')
        result['reference_sha256']=hashlib.sha256(args.reference.read_bytes()).hexdigest()
        errors=[]
        for rank in range(4):
            bits=np.fromfile(out/f'logits_rank{rank}.u32',dtype='<u4')
            if bits.shape!=(32320,):raise ValueError('native logits END extent')
            count=int(np.count_nonzero(bits!=reference[rank*32320:(rank+1)*32320]))
            errors.append(dict(rank=rank,bit_mismatches=count,
                output_sha256=hashlib.sha256((out/f'logits_rank{rank}.u32').read_bytes()).hexdigest(),
                native_terminal=json.loads((out/f'native_rank{rank}.json').read_text())))
        result['ranks']=errors;result['exact']=not any(e['bit_mismatches'] for e in errors)
    (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
    print('NATIVE_HEAD_TERMINAL',json.dumps(result),flush=True)
    return 0 if result['exact'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--socket',type=Path)
    parser.add_argument('--record',type=Path)
    parser.add_argument('--component',type=Path,help='opt-in existing-archive native head executable')
    parser.add_argument('--carry',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--reference',type=Path,help='comparison file opened only after native END')
    parser.add_argument('--selected-dir',type=Path,help='existing SourceTags selected PHROM/CFG namespace')
    args=parser.parse_args()
    if args.component:
        if not all([args.carry,args.output,args.reference,args.selected_dir]) or args.socket or args.record:
            parser.error('component requires carry/output/reference/selected-dir; no server socket')
        return run_component(args)
    if not args.socket or not args.record:parser.error('server requires socket and record')
    from dsrom_s81_head_source_binding import HeadSourceBinding,ReleasedHeadByteProvider
    with ReleasedHeadByteProvider(HeadSourceBinding(),args.snapshot) as provider:
        serve(provider,args.socket,args.record)
    return 0

if __name__=='__main__':raise SystemExit(main())
