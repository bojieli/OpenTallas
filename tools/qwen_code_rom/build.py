#!/usr/bin/env python3
"""Program every actual TP8 tile code ROM from pinned released INT8 bytes."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,json,shutil,struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
REV='b968826d9c46dd6066d109eabc6255188de91218'
LOCK='5cd6273118054c4a9140682bcd7a32488d8697db26bedf5d7ece8de99e141607'
ROWS,TILES,BANKS,WORD_BYTES=20032,768,5,49152


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def physical(words):
    # Input4096x32bytes. Real macro bitline=8*logicalbit+word%8.
    bits=np.unpackbits(words,axis=1,bitorder='little').reshape(512,8,256)
    bitlines=np.packbits(bits.transpose(0,2,1),axis=2,bitorder='little').reshape(512,256)
    return np.concatenate((bitlines,np.zeros((512,10),dtype=np.uint8)),axis=1)


def readback(mask,expected):
    # Read each selected word as the macro model does,then compareall256usefulbits.
    bits=np.unpackbits(mask[:,:256],axis=1,bitorder='little').reshape(512,256,8)
    words=np.packbits(bits.transpose(0,2,1),axis=2,bitorder='little').reshape(4096,32)
    if not np.array_equal(words,expected) or np.any(mask[:,256:]):
        raise ValueError('actual physical mask decoder disagrees with released word bytes')


def rank_build(request):
    source,output,rank=request;source=Path(source);output=Path(output)
    destination=output/f'rank{rank}';destination.mkdir()
    masks=destination/'masks';masks.mkdir();expected_dir=destination/'expected';expected_dir.mkdir()
    words=np.zeros((BANKS*4096,WORD_BYTES),dtype=np.uint8)
    stages=[];cursor=0
    for layer in list(range(36))+['head']:
        directory=source/(f'head_images/rank{rank}' if layer=='head' else f'images/layer{layer}/die{rank}')
        metadata=directory/('head_rom.json' if layer=='head' else f'layer{layer}_rom.json')
        meta=json.loads(metadata.read_text())
        if (meta['tp'],meta['die'],meta['checkpoint_revision'],meta['checkpoint_lock_sha256'])!=(8,rank,REV,LOCK):
            raise ValueError(f'wrong released source identity:{metadata}')
        count=1600 if layer=='head' else 512
        if layer!='head' and meta['layer']!=layer:raise ValueError('wrong layer')
        path=directory/'matrix_int8.hex';stat=path.stat();digest=hashlib.sha256();actual=0
        with path.open('rb') as stream:
            for line in stream:
                digest.update(line);text=line.strip()
                if len(text)!=WORD_BYTES*2:raise ValueError(f'wrong actual code word width:{path}:{actual}')
                if actual>=count:raise ValueError('extra code words')
                words[cursor+actual]=np.frombuffer(bytes.fromhex(text.decode())[::-1],dtype=np.uint8)
                actual+=1
        if actual!=count or digest.hexdigest()!=meta['image_sha256']['matrix_int8.hex'] or path.stat()!=stat:
            raise ValueError(f'released code image pin mismatch:{path}')
        stages.append(dict(stage=layer,resident_base=cursor,words=count,path=str(path),sha256=digest.hexdigest(),
                           metadata_path=str(metadata),metadata_sha256=sha(metadata)))
        cursor+=count
    if cursor!=ROWS:raise ValueError('incomplete resident code cohort')
    pairs=[]
    for tile in range(TILES):
        for bank in range(BANKS):
            pair=words[4096*bank:4096*(bank+1),64*tile:64*(tile+1)]
            prefix=f'qtile_t{tile}_b{bank}'
            expected=expected_dir/(prefix+'.hex')
            expected.write_text(''.join(row[::-1].tobytes().hex()+'\n' for row in pair))
            columns=[]
            for col in range(2):
                data=np.ascontiguousarray(pair[:,32*col:32*(col+1)])
                mask=physical(data);readback(mask,data)
                path=masks/(prefix+f'_c{col}.viamap.hex')
                path.write_text(''.join(row[::-1].tobytes().hex()+'\n' for row in mask))
                columns.append(dict(instance=prefix+f'_c{col}',file=path.name,sha256=sha(path),
                                    group_first=4*tile+2*col,code_bytes_per_word=32,
                                    native_tile=tile,native_bank=bank,native_column=col))
            pairs.append(dict(tile=tile,bank=bank,resident_base=4096*bank,macro_rows=4096,
                              expected_file=expected.name,expected_sha256=sha(expected),columns=columns))
        if tile%128==0:print(f'code rank{rank} generatedtile{tile}/768',flush=True)
    record=dict(schema='opentallas.qwen-tp8-native-code-mask-rank.v1',rank=rank,tp=8,groups=3072,tiles=768,
                resident_words=ROWS,padded_words=20480,banks_per_tile=5,macros=7680,
                checkpoint_revision=REV,checkpoint_lock_sha256=LOCK,source_bytes_requantized=False,
                stages=stages,pairs=pairs,native_full_layer_qualified=False)
    path=destination/'manifest.json';path.write_text(json.dumps(record,separators=(',',':'))+'\n')
    print(f'PASS code rank{rank} actual20032residentrows,7680native ROM IDs',flush=True)
    return dict(rank=rank,manifest=str(path),manifest_sha256=sha(path),macros=7680)


def main():
    p=argparse.ArgumentParser();p.add_argument('--banks',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ranks',default='0,1,2,3,4,5,6,7');p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if sha(ROOT/'compiler/models/qwen3-8b/checkpoint_source.json')!=LOCK:raise ValueError('repository source lock mismatch')
    ranks=[int(x) for x in a.ranks.split(',')]
    # Physical masks+observer payloads total~4GB/rank; require actual disk headroom.
    if shutil.disk_usage(a.out).free<len(ranks)*5*1024**3+10*1024**3:raise ValueError('insufficient actual code-mask disk headroom')
    lookup=[struct.unpack('<I',struct.pack('<f',float(x if x<128 else x-256)))[0]>>16 for x in range(256)]
    (a.out/'int8_bf16_observer.hex').write_text(''.join(f'{v:04x}\n' for v in lookup))
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.jobs) as pool:
        results=list(pool.map(rank_build,[(str(a.banks),str(a.out),rank) for rank in ranks]))
    record=dict(schema='opentallas.qwen-tp8-native-code-masks.v1',checkpoint_revision=REV,checkpoint_lock_sha256=LOCK,
                rank_manifests=results,code_words_per_layer=512,head_code_words=1600,head_resident_base=18432,
                resident_words_per_rank=ROWS,padded_bank_words=20480,macros_per_rank=7680,
                actual_payload_requantized=False,sources={str(path.relative_to(ROOT)):sha(path) for path in
                    [Path(__file__),ROOT/'rtl/physical/ot_qwen_tile_rpair.sv',ROOT/'compiler/models/qwen3-8b/checkpoint_source.json']},
                native_layer_qualified=False,remaining=['static ROM_TILE constant must match actual die tile_id strap',
                  'actual native command code relocation512*layer/head18432','native layer/token and physical integration'])
    (a.out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':main()
