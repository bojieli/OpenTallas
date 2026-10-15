#!/usr/bin/env python3
"""Export exact FP32 HC bank segments from an explicit safetensors checkpoint.
Never instantiates the simulator's HC_STRIPE hook. No reduced shape is accepted.
Synthetic full-shape input is explicit, solely a standalone component stimulus.
"""
import argparse, hashlib, json, pathlib, struct
import numpy as np

def layout(row):
    row=np.asarray(row,dtype='<f4')
    if row.shape!=(20480,):raise ValueError(f'requires actual full K20480 row, got {row.shape}')
    # HC aperture per bank: r128 * quarter4 * lane8, zero beyond c2560.
    out=np.zeros((8,4096),dtype='<f4')
    for k in range(8):out[k,:2560]=row[k::8]
    return out

def checkpoint_row(checkpoint,key,row):
    checkpoint=pathlib.Path(checkpoint)
    with checkpoint.open('rb') as f:
        n=struct.unpack('<Q',f.read(8))[0];meta=json.loads(f.read(n));t=meta[key]
        if t['dtype']!='F32' or t['shape']!=[24,20480]:
            raise ValueError(f'requires FP32 [24,20480] checkpoint tensor: {t}')
        a,b=t['data_offsets'];f.seek(8+n+a+row*81920);raw=f.read(81920)
    if len(raw)!=81920:raise ValueError('truncated checkpoint row')
    return np.frombuffer(raw,dtype='<f4'),{'checkpoint':str(checkpoint.resolve()),'tensor':key,
        'tensor_metadata':t,'checkpoint_header_sha256':hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest(),
        'raw_checkpoint_row_sha256':hashlib.sha256(raw).hexdigest()}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',type=pathlib.Path)
    p.add_argument('--tensor');p.add_argument('--layer',type=int,default=0);p.add_argument('--which',choices=['attn','ffn'],default='attn')
    p.add_argument('--all-rows',action='store_true');p.add_argument('--row',type=int,default=0);p.add_argument('--synthetic',action='store_true');p.add_argument('--out',required=True,type=pathlib.Path)
    a=p.parse_args()
    if not(0<=a.layer<43 and 0<=a.row<24):p.error('production layer0..42 and row0..23 required')
    if a.all_rows:
        import subprocess, sys
        a.out.mkdir(parents=True,exist_ok=True);records=[]
        for r in range(24):
            cmd=[sys.executable,__file__,'--layer',str(a.layer),'--which',a.which,'--row',str(r),'--out',str(a.out/f'row{r:02d}')]
            if a.synthetic:cmd+=['--synthetic']
            else:cmd+=['--checkpoint',str(a.checkpoint),'--tensor',str(a.tensor)]
            subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
            records.append(json.loads((a.out/f'row{r:02d}'/'descriptor.json').read_text()))
        (a.out/'rows.json').write_text(json.dumps({'schema':'opentallas.hc.stripe4.tensor.v1','rows':records,'source_bytes':1966080,'native_full_chip_qualified':False},indent=2)+'\n')
        original=np.array([np.fromfile(a.out/f'row{r:02d}'/'row.bin',dtype='<u4').reshape(8,2560).T.reshape(-1) for r in range(24)],dtype='<u4')
        (a.out/'fn-original-layout-fp32.bin').write_bytes(original.tobytes())
        print(f'Exported24 fullshape rows to {a.out}')
        return
    if a.synthetic:
        if a.checkpoint:p.error('synthetic and checkpoint mutually exclusive')
        # All source sectors independently identifiable; exactly representable finite FP32.
        x=((np.arange(20480,dtype=np.int32)*37+11)%32749-16374).astype('<f4')/np.float32(1024)
        provenance={'scope':'external synthetic fullshape component stimulus; NOT checkpoint image'}
    else:
        if not a.checkpoint or not a.tensor:p.error('explicit checkpoint and tensor required, or --synthetic')
        x,provenance=checkpoint_row(a.checkpoint,a.tensor,a.row)
    w=layout(x);base=(20<<30)+((a.layer*2+(a.which=='ffn'))*24+a.row)*81920
    a.out.mkdir(parents=True,exist_ok=True)
    # Sector order in this test image is bank-major; actual HBM stacks/holes are in descriptor.json.
    raw=w[:,:2560].tobytes();(a.out/'row.bin').write_bytes(raw)
    (a.out/'row.hex').write_text(''.join(raw[i:i+32][::-1].hex()+'\n' for i in range(0,len(raw),32)))
    d={'schema':'opentallas.hc.stripe4.checkpoint-row.v1','layer':a.layer,'which':a.which,'row':a.row,
       'rank':4*a.row+3,'local_base':base,'local_row_bytes':81920,'source_words':20480,
       'production_layout':'bank k -> stack k%4, local base+k*10240; 320 sectors per bank',
       'source_sha256':hashlib.sha256(raw).hexdigest(),'provenance':provenance,
       'segments':[{'bank':k,'stack':k%4,'local_byte':base+k*10240,'sectors':320,'image_offset':k*10240} for k in range(8)],
       'destination':{'positions_per_bank':512,'source_positions':320,'zero_padding_positions':[320,512],
         'service_deliveries':2,'delivery_sectors':2048,'native_full_chip_qualified':False}}
    (a.out/'descriptor.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(d))
if __name__=='__main__':main()
