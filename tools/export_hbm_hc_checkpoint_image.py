#!/usr/bin/env python3
"""Stage released F32 tensors, then stream all2064 HC rows into STRIPE4 images.

The stage step copies only exact checkpoint tensor byte ranges, with no numeric
conversion. Export/verify can run on the fleet against this bounded input set.
No hardware installation or loader ACK is implied by an image export.
"""
import argparse
import hashlib
import json
import pathlib
import resource
import shutil
import struct

ROW_BYTES=81920
TENSOR_BYTES=24*ROW_BYTES
TOTAL_ROWS=43*2*24
TOTAL_BYTES=TOTAL_ROWS*ROW_BYTES
BASE=20<<30
CHUNK=1<<20

def digest(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(CHUNK),b''):h.update(b)
    return h.hexdigest()

def js(path,obj):
    b=(json.dumps(obj,indent=2)+'\n').encode();path=pathlib.Path(path)
    if path.exists():
        if path.read_bytes()!=b:raise ValueError(f'refusing changed existing artifact {path}')
    else:path.write_bytes(b)

def headroom(path,allocation):
    path=pathlib.Path(path);path.mkdir(parents=True,exist_ok=True)
    free=shutil.disk_usage(path).free
    if free-allocation<(1<<30):raise ValueError(f'need1GiBheadroom after {allocation}B allocation; free={free}')
    return free

def book(path):
    d=json.loads(pathlib.Path(path).read_text())['hc_relocation']
    if d['new_local_base']!=BASE or d['bytes']!=TOTAL_BYTES or d['actual_source_descriptors']!=TOTAL_ROWS:
        raise ValueError('not the authoritative20GiB/43x2x24 HC descriptor book')
    rows={}
    for x in d['descriptors']:
        key=(x['layer'],x['which'],x['rank'])
        if key in rows:raise ValueError('duplicate descriptor')
        rows[key]=x
    if len(rows)!=TOTAL_ROWS:raise ValueError('descriptor count mismatch')
    return rows

def stage(a):
    snapshot=pathlib.Path(a.snapshot);out=pathlib.Path(a.out)
    rows=book(a.book);c=json.loads(pathlib.Path(a.config).read_text())
    if c['n_layers']!=40 or c['n_mtp_layers']!=3:raise ValueError('requires actual40main+3MTP config')
    w=json.loads((snapshot/'model.safetensors.index.json').read_text())['weight_map']
    specs=[]
    for L in range(43):
        prefix=f'layers.{L}.' if L<40 else f'mtp.{L-40}.'
        for which in ['attn','ffn']:
            key=prefix+f'hc_{which}_fn';f=snapshot/w[key]
            if not f.is_file():raise ValueError(f'missing released shard {f}')
            specs.append((L,which,key,f))
    before=headroom(out,TOTAL_BYTES+(16<<20));entries=[]
    for L,which,key,f in specs:
        with f.open('rb') as src:
            n=struct.unpack('<Q',src.read(8))[0];header=src.read(n);meta=json.loads(header)[key]
            lo,hi=meta['data_offsets']
            if meta['dtype']!='F32' or meta['shape']!=[24,20480] or hi-lo!=TENSOR_BYTES:
                raise ValueError(f'not exactF32[24,20480] {key}: {meta}')
            src.seek(8+n+lo);raw=src.read(TENSOR_BYTES)
        if len(raw)!=TENSOR_BYTES:raise ValueError('truncated checkpoint tensor')
        sha=hashlib.sha256(raw).hexdigest();name=f'L{L:02d}-{which}.f32';dest=out/name
        if dest.exists():
            if digest(dest)!=sha:raise ValueError(f'staged tensor differs {dest}')
        else:dest.write_bytes(raw)
        entries.append({'layer':L,'which':which,'tensor':key,'file':name,'dtype':'F32','shape':[24,20480],
                        'bytes':TENSOR_BYTES,'sha256':sha,'checkpoint_shard':str(f.resolve()),
                        'checkpoint_data_offsets':[8+n+lo,8+n+hi],
                        'checkpoint_header_sha256':hashlib.sha256(header).hexdigest()})
    shutil.copyfile(a.book,out/'descriptor_book.json')
    shutil.copyfile(a.config,out/'inference_config.json')
    catalog={'schema':'opentallas.hc.released-checkpoint-tensors.v1','snapshot':str(snapshot.resolve()),
             'checkpoint_index_sha256':digest(snapshot/'model.safetensors.index.json'),
             'descriptor_book_sha256':digest(a.book),'config_sha256':digest(a.config),
             'source_tensors':86,'source_rows':TOTAL_ROWS,'source_bytes':TOTAL_BYTES,'tensors':entries,
             'stage_peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'disk_free_before':before,'disk_free_after':shutil.disk_usage(out).free,'hardware_installed':False}
    # Memory/disk measurements vary on repeat; source tensors themselves are immutable.
    (out/'input_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    print(f'HC_STAGE PASS tensors=86 rows={TOTAL_ROWS} exact_checkpoint_bytes={TOTAL_BYTES}')

def export(a):
    import numpy as np
    inputs=pathlib.Path(a.inputs);out=pathlib.Path(a.out)
    cat=json.loads((inputs/'input_catalog.json').read_text());rows=book(inputs/'descriptor_book.json')
    if digest(inputs/'descriptor_book.json')!=cat['descriptor_book_sha256']:raise ValueError('book changed')
    before=headroom(out,5*TOTAL_BYTES+(64<<20))
    if any((out/n).exists() for n in ['payload.bin','rows.jsonl','manifest.json']):raise ValueError('fresh output required')
    stacks=[(out/f'stack{s}.hc-window.bin').open('xb+') for s in range(4)]
    for f in stacks:f.truncate(TOTAL_BYTES)
    payload_hash=hashlib.sha256();ordinal=0
    try:
        with (out/'payload.bin').open('xb') as payload,(out/'rows.jsonl').open('x') as listing:
            for t in cat['tensors']:
                raw=(inputs/t['file']).read_bytes()
                if len(raw)!=TENSOR_BYTES or hashlib.sha256(raw).hexdigest()!=t['sha256']:raise ValueError('source tensor changed')
                values=np.frombuffer(raw,dtype='<u4').reshape(24,2560,8)
                for r in range(24):
                    local=BASE+ordinal*ROW_BYTES;rank=4*r+3
                    desc=rows[(t['layer'],t['which'],rank)]
                    if desc['local_bytes']!=[local,local+ROW_BYTES] or not desc['stripe4'] or desc['sectors_per_bank']!=320:
                        raise ValueError(f'actualLower.hc_row_load descriptor mismatch {ordinal}')
                    data=values[r].T.copy(order='C').tobytes();offset=ordinal*ROW_BYTES
                    payload.write(data);payload_hash.update(data);segments=[]
                    for k in range(8):
                        segment=data[k*10240:(k+1)*10240];position=offset+k*10240
                        stacks[k%4].seek(position);stacks[k%4].write(segment)
                        segments.append({'bank':k,'stack':k%4,'local_byte':BASE+position,'bytes':10240,
                                         'payload_offset':position,'stack_file_offset':position,
                                         'sha256':hashlib.sha256(segment).hexdigest()})
                    listing.write(json.dumps({'ordinal':ordinal,'layer':t['layer'],'which':t['which'],'row':r,'rank':rank,
                                               'local_bytes':[local,local+ROW_BYTES],'payload_offset':offset,
                                               'sha256':hashlib.sha256(data).hexdigest(),'segments':segments},sort_keys=True)+'\n')
                    ordinal+=1
    finally:
        for f in stacks:f.close()
    if ordinal!=TOTAL_ROWS or (out/'payload.bin').stat().st_size!=TOTAL_BYTES:raise ValueError('incomplete image')
    physical=[{'stack':s,'file':f'stack{s}.hc-window.bin','local_byte_base':BASE,'logical_bytes':TOTAL_BYTES,
               'actual_payload_bytes':TOTAL_BYTES//4,'sha256':digest(out/f'stack{s}.hc-window.bin')} for s in range(4)]
    manifest={'schema':'opentallas.hc.native-stripe4-checkpoint-image.v1','status':'EXPORTED_NOT_HARDWARE_INSTALLED',
              'source_tensors':86,'rows':ordinal,'payload_file':'payload.bin','payload_bytes':TOTAL_BYTES,
              'payload_sha256':payload_hash.hexdigest(),'row_manifest':'rows.jsonl','row_manifest_sha256':digest(out/'rows.jsonl'),
              'source_catalog_sha256':digest(inputs/'input_catalog.json'),'descriptor_book_sha256':cat['descriptor_book_sha256'],
              'config_sha256':cat['config_sha256'],'local_byte_base':BASE,'protected_capacity_bytes':256<<20,
              'physical_stack_windows':physical,'sparse_holes':'reserved HC region positions with no bank on this stack; zero in exported files',
              'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'disk_free_before':before,
              'disk_free_after':shutil.disk_usage(out).free,'hardware_install_and_ACK_proven':False}
    if manifest['disk_free_after']<1<<30:raise ValueError('lost1GiBheadroom')
    js(out/'manifest.json',manifest)
    print(f'HC_FULL_IMAGE EXPORT PASS rows={ordinal} payload_bytes={TOTAL_BYTES} payload_sha256={payload_hash.hexdigest()}')

def verify(a):
    import numpy as np
    inputs=pathlib.Path(a.inputs);out=pathlib.Path(a.out);m=json.loads((out/'manifest.json').read_text())
    cat=json.loads((inputs/'input_catalog.json').read_text());rows=book(inputs/'descriptor_book.json')
    if digest(inputs/'input_catalog.json')!=m['source_catalog_sha256']:raise ValueError('catalog changed')
    if digest(out/'rows.jsonl')!=m['row_manifest_sha256']:raise ValueError('row manifest changed')
    payload_path=pathlib.Path(a.payload) if a.payload else out/m['payload_file']
    tensors={(t['layer'],t['which']):t for t in cat['tensors']};current=None;raw=None;checked=0
    stacks=[(out/x['file']).open('rb') for x in m['physical_stack_windows']]
    try:
        with payload_path.open('rb') as payload,(out/'rows.jsonl').open() as lines:
            for line in lines:
                r=json.loads(line);key=(r['layer'],r['which']);t=tensors[key]
                if current!=key:
                    raw=(inputs/t['file']).read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=t['sha256']:raise ValueError('stagedsource changed')
                    current=key
                expected=np.frombuffer(raw,dtype='<u4').reshape(24,2560,8)[r['row']].T.copy(order='C').tobytes()
                if r['ordinal']!=checked or rows[(r['layer'],r['which'],r['rank'])]['local_bytes']!=r['local_bytes']:
                    raise ValueError('descriptor provenance mismatch')
                payload.seek(r['payload_offset']);actual=payload.read(ROW_BYTES)
                if actual!=expected or hashlib.sha256(actual).hexdigest()!=r['sha256']:
                    raise ValueError(f'actual row payload mismatch ordinal{checked}')
                for segment in r['segments']:
                    k=segment['bank'];s=segment['stack'];off=segment['stack_file_offset']
                    if s!=k%4 or segment['local_byte']!=BASE+off or off!=checked*ROW_BYTES+k*10240:
                        raise ValueError('physical STRIPE4 placement mismatch')
                    stacks[s].seek(off);data=stacks[s].read(10240)
                    if data!=expected[k*10240:(k+1)*10240] or hashlib.sha256(data).hexdigest()!=segment['sha256']:
                        raise ValueError('physical image source mismatch')
                checked+=1
    finally:
        for f in stacks:f.close()
    if checked!=TOTAL_ROWS or digest(payload_path)!=m['payload_sha256']:raise ValueError('payload count/hash mismatch')
    for s in m['physical_stack_windows']:
        if digest(out/s['file'])!=s['sha256']:raise ValueError('physical window hash mismatch')
    print(f'HC_FULL_IMAGE VERIFY PASS actual_rows={checked} bank_segments={checked*8} payload_bytes={TOTAL_BYTES} hardware_installed=0')

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    q=sub.add_parser('stage');q.add_argument('--snapshot',required=True);q.add_argument('--book',required=True);q.add_argument('--config',required=True);q.add_argument('--out',required=True)
    for mode in ['export','verify']:
        q=sub.add_parser(mode);q.add_argument('--inputs',required=True);q.add_argument('--out',required=True)
        if mode=='verify':q.add_argument('--payload')
    a=p.parse_args();{'stage':stage,'export':export,'verify':verify}[a.mode](a)
if __name__=='__main__':main()
