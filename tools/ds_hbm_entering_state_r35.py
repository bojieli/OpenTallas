"""Stream exact W19 entering-state initializer into source images and digest.
No token/operator execution. Not decoded prefix history. No new current rows.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from ds_hbm_source_inputs_r34 import codecs,sha
from h3_ds_checkpoint_provider_r30 import LockedCheckpoint
ROOT=Path(__file__).resolve().parents[1]

def preflight(ctx=1048576):
    sources=[2,8,14,20];rows={s:(ctx-1)//(2 if s!=20 else 1) for s in sources}
    return dict(context=ctx,window_payload_bytes=40*127*512*4,historical_payload_bytes=sum(rows.values())*(512+128)*4,source_rows=rows,source_chunk_rows=65536,conservative_live_array_proxy_bytes=65536*512*80,proxy_scope='80B per component scalar covers simultaneously materialized source quantizer/gained intermediates; not measured peak',output_scope='four global immutable source CKV/index files; rank homes/physical address translation separate; no32MiB scratch relabel')

def materialize(ck, windows, output, ctx=1048576, seed=20260930, sources=(2,8,14,20),expected=None):
    if output.exists():raise ValueError('fresh source state output')
    output.mkdir();ref,G,V,init=codecs();h=hashlib.sha256();records=[];pos=ctx-1
    # Source W19 hashes all40 windows first, then each CKV/index/open pair.
    for r in windows:
        a=np.load(r['path'],mmap_mode='r',allow_pickle=False)
        if sha(Path(r['path']))!=r['sha256'] or a.shape!=(127,512):raise ValueError('source window identity/shape')
        h.update(a.tobytes())
    for s in sources:
        ratio=1 if s==20 else 2;n=pos//ratio
        for kind,width,tensor,codec in [(1,512,f'layers.{s}.attn.compressor.norm.weight',lambda a:V.qdq_fp4_e4m3(a,16)),(2,128,f'layers.{s}.attn.indexer.k_norm.weight',V.qdq_fp4_e8m0)]:
            gain,dt=ck.tensor(tensor)
            if dt!='BF16' or gain.shape!=(width,):raise ValueError('released source history gain')
            path=output/f'{"ckv" if kind==1 else "ik"}_L{s}.npy';a=np.lib.format.open_memmap(path,mode='w+',dtype=np.float32,shape=(n,width));digest=hashlib.sha256();i=0
            for blk in init._gained(np.random.default_rng([seed,ctx,kind,s]),n,width,gain):
                q=codec(blk.reshape(-1)).reshape(blk.shape);a[i:i+len(q)]=q;raw=q.tobytes();h.update(raw);digest.update(raw);i+=len(q)
            if i!=n:raise ValueError('exact retained row count')
            a.flush();del a
            records.append(dict(path=str(path.resolve()),shape=[n,width],dtype='F32',payload_sha256=digest.hexdigest(),file_sha256=sha(path),layer=s,kind=kind,native_codec='source QDQ FP4E4 block16' if kind==1 else 'source QDQ FP4E8 block32',gain_tensor=tensor,seed=[seed,ctx,kind,s]))
        rng=np.random.default_rng([seed,ctx,3,s]);slots=[]
        if ratio>1 and pos%ratio:
            for p in range(pos-pos%ratio,pos):
                kv=rng.standard_normal(512).astype(np.float32);sc=rng.standard_normal(512).astype(np.float32);slots.append([kv,sc]);h.update(kv.tobytes());h.update(sc.tobytes())
        path=output/f'open_L{s}.npy';a=np.asarray(slots,np.float32).reshape(-1,2,512);np.save(path,a,allow_pickle=False)
        records.append(dict(path=str(path.resolve()),shape=list(a.shape),dtype='F32',file_sha256=sha(path),layer=s,kind=3,logical_positions=list(range(pos-pos%ratio,pos)) if ratio>1 else []))
        print('SOURCE_STATE_LAYER_COMPLETE',s,flush=True)
    actual=h.hexdigest();receipt=dict(status='PASS_EXACT_ENTERING_STATE_DIGEST' if expected is not None and actual==expected else 'FAIL_ENTERING_STATE_DIGEST' if expected is not None else 'SOURCE_FIXTURE_DIGEST_ONLY',actual_state_sha256=actual,expected_state_sha256=expected,full_token_run=False,hardware_qualified=False,provenance='exact seeded source benchmark entering state, not decoded prefix')
    (output/'images.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n');(output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');(output/'checkpoint_reads.json').write_text(json.dumps(ck.receipts,sort_keys=True,indent=2)+'\n')
    if expected is not None and actual!=expected:raise ValueError('immutable source state digest failure')
    return receipt

def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','windows','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.manifest.read_bytes());ck=LockedCheckpoint(m['checkpoint_path'],m['checkpoint_revision'],m['checkpoint_index_sha256']);ref,_,_,_=codecs()
    materialize(ck,json.loads(a.windows.read_bytes()),a.out,expected=ref['state']['state_sha256'])
if __name__=='__main__':main()
