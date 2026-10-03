"""Materialize the exact declared W19/W17 entering-state window initializer.

This is seeded reference benchmark state using released checkpoint norm gains,
NOT a historical million-token prefix. No model operator or Executor callback.
Only source initialization/codec functions run before native execution.
"""
import argparse,hashlib,importlib.util,json,sys,gzip
from importlib.machinery import SourceFileLoader
from pathlib import Path
import numpy as np
from h3_ds_checkpoint_provider_r30 import LockedCheckpoint
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_hbm_source_inputs_views_r34_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
    loader=SourceFileLoader(name,str(path));spec=importlib.util.spec_from_loader(name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m);return m
def codecs():
    ref=json.loads((D/'inputs/w17_reference_token.json').read_bytes())
    for n in ['hdc_golden.py','hdc_golden_v41.py']:
        if sha(D/('inputs/'+n+'.source'))!=ref['source_sha256']['tools/'+n]:raise ValueError('reference storage codec pin')
    G=load('r34_source_G',D/'inputs/hdc_golden.py.source');old=sys.modules.get('hdc_golden');sys.modules['hdc_golden']=G
    try:V=load('r34_source_V',D/'inputs/hdc_golden_v41.py.source')
    finally:
        if old is None:sys.modules.pop('hdc_golden',None)
        else:sys.modules['hdc_golden']=old
    pin=json.loads((D/'inputs/gained_source_provenance.json').read_bytes())
    if sha(D/'inputs/source_gained.py.source')!=pin['fragment_sha256']:raise ValueError('source retained-state initializer pin')
    init=load('r34_source_init',D/'inputs/source_gained.py.source');init.to_bf16=G.to_bf16
    return ref,G,V,init
def materialize(checkpoint,output):
    if output.exists():raise ValueError('fresh source-input output required')
    output.mkdir();ref,G,V,init=codecs();images=[]
    if (ref['context'],ref['seed'],ref['state']['window_rows_per_layer'])!=(1048576,20260930,127):raise ValueError('source benchmark entering-state contract')
    for layer in range(40):
        tensor=f'layers.{layer}.attn.kv_norm.weight';gain,dtype=checkpoint.tensor(tensor)
        if dtype!='BF16' or gain.shape!=(512,):raise ValueError('released source KV norm gain')
        rng=np.random.default_rng([ref['seed'],ref['context'],0,layer])
        gained=np.concatenate(list(init._gained(rng,127,512,gain)))
        window=V.qdq_fp8(gained.reshape(-1)).reshape(127,512)
        path=output/f'window_L{layer:02d}.npy';np.save(path,window,allow_pickle=False)
        record=dict(layer=layer,path=str(path.resolve()),sha256=sha(path),payload_sha256=hashlib.sha256(window.tobytes()).hexdigest(),shape=[127,512],dtype='F32',provenance='exact source reference entering-state initializer; not decoded prefix history',seed=[20260930,1048576,0,layer],norm_gain_tensor=tensor,norm_gain_sha256=hashlib.sha256(gain.tobytes()).hexdigest(),whole_reference_state_digest_verified=False,expected_whole_state_sha256=ref['state']['state_sha256'])
        images.append(record)
    (output/'window_images.json').write_text(json.dumps(images,indent=2,sort_keys=True)+'\n')
    return images
def static_auxiliary(native, cfg, output):
    """Only exact immutable source constants; no activation/route substitutes."""
    _,G,V,_=codecs();bindings={};images={};output.mkdir()
    names={'attn_scale','index_w_scale','engram_scale','index_rope_cos','index_rope_sin','E4M3_decode'}
    for op in native['instructions']:
        for key,bs in op['provider_bindings'].items():
            for name,b in bs.items():
                if b['kind']!='explicit_auxiliary_provider' or name not in names:continue
                if name=='attn_scale':a=np.asarray(cfg['head_dim']**-0.5,dtype=np.float32)
                elif name=='index_w_scale':a=np.asarray(cfg['index_head_dim']**-0.5*cfg['index_n_heads']**-0.5,dtype=np.float32)
                elif name=='engram_scale':a=np.asarray(cfg['dim']**-0.5,dtype=np.float32)
                elif name=='E4M3_decode':a=V.E4M3.astype(np.float32)
                else:
                    ratio=cfg['compress_ratios'][b['layer']]
                    if ratio<=0:raise ValueError('index compressor source ratio')
                    # Compressor rotates at group FIRST position, not current append.
                    first=b['position']+1-ratio
                    freqs=V.rope_freqs(cfg['rope_head_dim'],cfg['original_seq_len'],cfg['compress_rope_theta'],cfg['rope_factor'],cfg['beta_fast'],cfg['beta_slow'])
                    a=V.rope_cs(freqs,first)[name=='index_rope_sin']
                spec=native['templates'][key]['providers'][name]
                if list(a.shape)!=spec['shape'] or spec['dtype']!='F32':raise ValueError('exact static auxiliary shape/type '+name)
                identity=(name,a.tobytes())
                if identity not in images:
                    path=output/f'{name}_{len(images)}.npy';np.save(path,a,allow_pickle=False);images[identity]=path
                path=images[identity]
                r=dict(path=str(path.resolve()),sha256=sha(path),shape=list(a.shape),dtype='F32',source_binding=b,generation=1,checkpoint_revision='dba1be0a40aa45a94ad051997016db3960a90277',scope='pinned source constant initializer only; no runtime operator callback')
                if name.startswith('index_rope'):r['source_group_first_position']=first
                bindings[f"{op['pc']}/{key}/{name}"]=r
    return bindings

def bind_initial_windows(images, homes):
    """Join actual source payloads to every reserved rank/version; no extra row."""
    by_layer={r['layer']:r for r in images}
    if len(by_layer)!=40 or len(images)!=40:raise ValueError('all40 unique source windows required')
    records=[];seen=set();ranges={}
    for h in homes['rows']:
        layer=int(h['version'].split('window.L')[1].split('.')[0]);r=by_layer[layer]
        if h['shape']!=r['shape'] or h['dtype']!=r['dtype'] or h['bytes']!=127*512*4 or h['AW']!=27 or h['generation']!=1:raise ValueError('source initial payload/home contract')
        if h['logical_positions']!=list(range(1048575-127,1048575)):raise ValueError('source ordered retained positions')
        rank=h['rank'];identity=(h['version'],rank)
        if not 0<=rank<96 or identity in seen:raise ValueError('unique native initial owner')
        seen.add(identity);lo,hi=h['base'],h['base']+h['reservation_bytes']
        if lo<33554432 or hi>67108864 or hi-lo!=r['shape'][0]*r['shape'][1]*4:raise ValueError('finite state aperture')
        if any(lo<b and a<hi for a,b in ranges.get(rank,[])):raise ValueError('initial home overlap')
        ranges.setdefault(rank,[]).append((lo,hi))
        records.append(dict(r,version=h['version'],rank=rank,generation=1,home=h,source_payload_required=False))
    if len(records)!=3840 or any(len(ranges.get(rank,[]))!=40 for rank in range(96)):raise ValueError('40x96 source home coverage')
    return records

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--checkpoint-manifest',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--native',type=Path);ap.add_argument('--initial-homes',type=Path);a=ap.parse_args();m=json.loads(a.checkpoint_manifest.read_bytes())
    if bool(a.native)!=bool(a.initial_homes):raise ValueError('native and reserved initial homes required together')
    ck=LockedCheckpoint(m['checkpoint_path'],m['checkpoint_revision'],m['checkpoint_index_sha256']);images=materialize(ck,a.out)
    if a.native:
        native=json.loads(gzip.decompress(a.native.read_bytes()))
        homes=json.loads(gzip.decompress(a.initial_homes.read_bytes()))
        cfg=json.loads((ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002/inputs/inference_config.json').read_bytes())
        bindings=static_auxiliary(native,cfg,a.out/'static_auxiliary')
        initial=bind_initial_windows(images,homes)
        (a.out/'static_auxiliary_bindings.json').write_text(json.dumps(bindings,sort_keys=True,indent=2)+'\n')
        (a.out/'initial_versions.json.gz').write_bytes(gzip.compress(json.dumps(initial,sort_keys=True).encode(),mtime=0))
    (a.out/'checkpoint_reads.json').write_text(json.dumps(ck.receipts,indent=2,sort_keys=True)+'\n')
    (a.out/'receipt.json').write_text(json.dumps(dict(status='MATERIALIZED_EXACT_SOURCE_REFERENCE_WINDOWS_NOT_PREFIX_HISTORY',images=40,payload_bytes=40*127*512*4,checkpoint_revision=m['checkpoint_revision'],full_state_hash_verified=False,full_token_run=False,hardware_or_rate_claim=False),indent=2)+'\n')
if __name__=='__main__':main()
