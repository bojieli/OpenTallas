"""Released expert descriptor and Engram payload preparation, not operator execution.
Owns new r35 paths only; producer/sparse ownership adapter belongs to Sagan.
Descriptor bases name exact checkpoint-file bytes, NOT physical HBM addresses.
"""
import argparse,fcntl,gzip,hashlib,json,os,struct
from pathlib import Path
import numpy as np
from ds_hbm_source_inputs_r34 import codecs,sha
from h3_ds_checkpoint_provider_r30 import LockedCheckpoint
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_hbm_checkpoint_payloads_r35_20261002'

def header(checkpoint,name):
    filename=checkpoint.index[name]
    if filename not in checkpoint.files:
        fd=os.open(checkpoint.path/filename,os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        n=struct.unpack('<Q',os.pread(fd,8,0))[0];raw=os.pread(fd,n,8)
        if len(raw)!=n:raise ValueError('complete source tensor header')
        checkpoint.files[filename]=(fd,json.loads(raw),8+n,os.fstat(fd),hashlib.sha256(raw).hexdigest())
    fd,h,base,stamp,hs=checkpoint.files[filename];now=os.fstat(fd)
    if (stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns)!=(now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns):raise ValueError('source descriptor header changed')
    m=h[name];return dict(tensor=name,filename=filename,shape=m['shape'],dtype=m['dtype'],checkpoint_file_byte_base=base+m['data_offsets'][0],payload_bytes=m['data_offsets'][1]-m['data_offsets'][0],header_sha256=hs)

def expert_descriptors(checkpoint,layer):
    table=np.empty((384,3,4),dtype=np.int64);locators=[]
    for expert in range(384):
        for j,kind in enumerate(('w1','w3','w2')):
            name=f'layers.{layer}.ffn.experts.{expert}.{kind}.weight';w=header(checkpoint,name);s=header(checkpoint,name.removesuffix('.weight')+'.scale')
            expected=[2304,2560] if kind!='w2' else [5120,1152]
            if w['dtype']!='I8' or w['shape']!=expected or s['dtype']!='F8_E8M0' or s['shape']!=[expected[0],expected[1]*2//32]:raise ValueError('released expert FP4 shape/scale contract')
            table[expert,j]=[w['checkpoint_file_byte_base'],expected[0],expected[1]*2,3]
            locators.append(dict(expert=expert,matrix=kind,code=w,scale=s,descriptor=table[expert,j].tolist(),descriptor_namespace='checkpoint file bytes; filename accompanies base; NOT AW34 physical translation'))
    table.flags.writeable=False;return table,locators

def engram_payloads(checkpoint,cfg,tokenizer,history):
    _,_,V,_=codecs();V.TOKENIZER=tokenizer
    layout=V.EngramTables(cfg,cfg['vocab_size']);out={}
    for li,layer in enumerate(layout.layer_ids):
        ids=layout.hashes(history,li);codes=[];exponents=[]
        for row in ids:
            a,dt=checkpoint.tensor(f'layers.{layer}.engram.embed.weight',rows=[int(row),int(row)+1]);s,st=checkpoint.tensor(f'layers.{layer}.engram.embed.scale',rows=[int(row),int(row)+1])
            if dt!='F8_E4M3' or st!='F8_E8M0' or a.shape!=(1,256) or s.shape!=(1,8):raise ValueError('released Engram paired row source codec')
            codes.append(a[0].astype(np.int64));exponents.append(s[0].astype(np.int64)-127)
        recent=list(reversed(history[-layout.n:]))
        recent+= [cfg['engram_pad_id']]*(layout.n-len(recent))
        out[layer]=dict(multipliers=layout.multipliers[li],offsets=layout.offsets[li],primes=layout.primes[li],raw_recent_tokens=np.asarray(recent,np.int64),selected_codes=np.stack(codes),selected_exp=np.stack(exponents),selected_row_ids=ids,token_map=layout.token_map)
    return out

def prepare(checkpoint,native,cfg,tokenizer,history,output):
    if output.exists():raise ValueError('fresh checkpoint provider output')
    output.mkdir();bindings={};locators=[];images={};descriptors={}
    for o in native['instructions']:
        if o['family']=='expert_fetch':
            layer=o['source_op']['layer'];a,ls=expert_descriptors(checkpoint,layer);descriptors[layer]=a;locators+=ls
    eng=engram_payloads(checkpoint,cfg,tokenizer,history)
    for o in native['instructions']:
        layer=o['source_op'].get('layer')
        for key,bs in o['provider_bindings'].items():
            for name,b in bs.items():
                if b['kind']!='explicit_auxiliary_provider':continue
                if o['family']=='expert_fetch' and name=='expert_descriptor_table':a=descriptors[layer]
                elif o['family']=='engram_fetch' and name in eng[layer]:a=eng[layer][name]
                else:continue
                spec=native['templates'][key]['providers'][name]
                if spec['dtype']!='I64' or list(a.shape)!=spec['shape']:raise ValueError('exact payload LOAD shape/type '+name)
                imagekey=(layer,name)
                if imagekey not in images:
                    p=output/f'L{layer:02d}_{name}.npy';np.save(p,a,allow_pickle=False);images[imagekey]=p
                p=images[imagekey]
                bindings[f"{o['pc']}/{key}/{name}"]=dict(path=str(p.resolve()),sha256=sha(p),shape=list(a.shape),dtype='I64',source_binding=b,generation=1,checkpoint_revision=checkpoint.path.name,scope='released checkpoint source initializer/selected immutable row payload only')
    (output/'bindings.json').write_text(json.dumps(bindings,sort_keys=True,indent=2)+'\n')
    (output/'expert_locators.json.gz').write_bytes(gzip.compress(json.dumps(locators,sort_keys=True).encode(),mtime=0))
    (output/'checkpoint_reads.json').write_text(json.dumps(checkpoint.receipts,sort_keys=True,indent=2)+'\n')
    receipt=dict(bound_refs=len(bindings),expert_descriptor_layers=len(descriptors),source_expert_matrices=len(locators),engram_layers=len(eng),tokenizer_sha256=sha(tokenizer),checkpoint_source_address_namespace='file byte offsets plus file identity; no physical HBM address/visibility claim',full_token_run=False,hardware_qualified=False)
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');return receipt

def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','native','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.manifest.read_bytes());ck=LockedCheckpoint(m['checkpoint_path'],m['checkpoint_revision'],m['checkpoint_index_sha256'])
    n=json.loads(gzip.decompress(a.native.read_bytes()));cfg=json.loads((ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002/inputs/inference_config.json').read_bytes());ref=json.loads((ROOT/'results/uarch/ds_hbm_source_inputs_views_r34_20261002/inputs/w17_reference_token.json').read_bytes())
    prepare(ck,n,cfg,ck.path/'tokenizer.json',ref['token_history'],a.out)
if __name__=='__main__':main()
