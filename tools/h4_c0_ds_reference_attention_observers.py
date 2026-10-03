"""Comparison-only original layer-one attention trajectory and source fragments.

Consumes the retained independent PC59 norm; original Model.attention performs
all arithmetic. Subtotal witnesses are checked against its actual wo_a output.
No native kernels/provider callbacks or regenerated entering state.
"""
import argparse
import json
import os
from pathlib import Path
import threading
import time
import numpy as np
import hdc_golden_v41 as V
import rtl_v41_fullshape_layer_campaign as LC
from h4_c0_ds_reference_layer_observers import build_reference_model
from h4_c0_ds_reference_trajectory import TrajectoryCheckpoint
from h4_c0_ds_whole_reference import ComparisonStore,slots,NATIVE,MANIFEST,sha,load,payload

UPSTREAM='f50f6203b64c2201fdefa6596a8feca026165c6c8b52b1d9150101d7a2009751'


def observe_attention(model,x,old):
    if threading.current_thread() is not threading.main_thread() or threading.active_count()!=1:
        raise ValueError('dedicated single-thread golden process required')
    if model.ratio[1]!=0:raise ValueError('layer-one sliding attention contract')
    originals={k:getattr(V,k) for k in ('linear_q','rmsnorm_fold','rope_tail','matvec_c')}
    captures={k:[] for k in originals}
    def hook(k):
        def call(*a,**kw):
            y=originals[k](*a,**kw);captures[k].append(np.asarray(y).copy());return y
        return call
    state={'win':{1:list(old)}}
    try:
        for k in originals:setattr(V,k,hook(k))
        y=V.Model.attention(model,1,x,1048575,state,{},{} )
    finally:
        for k,v in originals.items():setattr(V,k,v)
    if [len(captures[k]) for k in originals]!=[4,1,3,8]:raise ValueError('original attention call graph changed')
    qa,q,kvraw,y0=captures['linear_q'];qr=captures['rmsnorm_fold'][0]
    q_own,rotated_kv,attention=captures['rope_tail']
    if payload(y)!=payload(y0):raise ValueError('original final projection observer identity')
    window=np.stack(state['win'][1]);win_new=window[-1]
    if payload(window[:-1])!=payload(old) or window.shape!=(128,512):raise ValueError('exact source entering window append')
    wa=model.lw(1,'attn.wo_a.weight').reshape(8,1024,4096)
    parts=[V.matvec_c(wa[r//8,:,(r%8)*512:(r%8+1)*512],attention[r],V.WO_A_SPLIT) for r in range(64)]
    groups=[V.split_sum_parts(parts[8*g:8*g+8]) for g in range(8)]
    if any(payload(a)!=payload(b) for a,b in zip(groups,captures['matvec_c'])):
        raise ValueError('source ordered subtotal tree differs from original grouped wo_a')
    z=V.to_bf16(np.concatenate(groups))
    return dict(qa=qa,kvraw=kvraw,qr=qr,win_new=win_new,window=window,q=q.reshape(-1),q_own=q_own,
        attention=attention,parts=np.stack(parts),z=z,y=y)


def emit(native,observed,h,controls,x,store,provenance):
    names={60:'qa',61:'kvraw',64:'q',67:'parts',68:'z',69:'y'}
    for op in native['instructions'][60:74]:
        pc=op['pc']
        for rb in op['rank_bindings']:
            if rb.get('empty_owned_extent'):continue
            rank=rb['rank']
            for w in op['writes']:
                result=w['native_result_binding']['result']
                if pc in names:
                    a=observed[names[pc]]
                    if pc==67:a=a[rank]
                    elif pc in (60,61,64,69):lo,hi=rb['row_interval'];a=a[lo:hi]
                elif pc in (62,70):a=observed[w['native_result_binding']['buffer']]
                elif pc==63:a=observed[result]
                elif pc==65:a=observed['q_own'][rank]
                elif pc==66:a=observed['attention'][rank]
                elif pc==71:a=h
                elif pc==72:a=dict(pre=controls[0],post=controls[1],comb=controls[2],res=h)[result]
                elif pc==73:a=x
                else:raise ValueError('unbound source result')
                store.append((pc,w['version'],rank,'data'),np.ascontiguousarray(a,dtype='<f4'),provenance)


def generate(native,manifest,upstream,provider_root,source_root,out):
    if sha(native)!=NATIVE or sha(manifest)!=MANIFEST or sha(upstream)!=UPSTREAM:raise ValueError('immutable numerical lineage')
    n=load(native);m=load(manifest);u=load(upstream)
    for p,d in u['reference_source_sha256'].items():
        if sha(p)!=d:raise ValueError('upstream original source changed')
    artifact=Path(upstream).parent/'artifact_manifest.json';am=load(artifact)
    obsfile=Path(upstream).parent/'original_golden_observations.npz'
    if sha(obsfile)!=am['artifacts'][obsfile.name]:raise ValueError('retained original PC53-59 observations')
    with np.load(obsfile,allow_pickle=False) as f:incoming={k:f[k].copy() for k in f.files}
    normrows=[r for r in u['expectations'] if r['PC']==59]
    if not normrows or any(r['payload_sha256']!=payload(incoming['norm']) for r in normrows):raise ValueError('original PC59 complete norm identity')
    entering=next(r for r in m['initial_versions'] if r['version']=='DeepSeek.-1.window.L1.3' and r['rank']==0)
    path=Path(entering['path']);old=np.load(path,allow_pickle=False)
    if sha(path)!=entering['sha256'] or payload(old)!=entering['payload_sha256'] or old.shape!=(127,512) or old.dtype!=np.dtype('<f4'):raise ValueError('source entering window bytes')
    out=Path(out);store=ComparisonStore(out,[s for s in slots(n) if 60<=s['PC']<=73])
    receipt=dict(status='RUNNING_ORIGINAL_LAYER1_ATTENTION_REFERENCE',pid=os.getpid(),started_ns=time.time_ns(),
        arbitrary_resource_caps=False,native_execution=False,hardware_qualified=False,full_token_qualified=False)
    def save():(out/'record.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    save();ck=None
    try:
        ck=TrajectoryCheckpoint(m);config=Path(source_root)/'compiler/models/deepseek-v4.1-flash/inference_config.json'
        if sha(config)!=u['reference_source_sha256'][str(config.resolve())]:raise ValueError('same released configuration')
        V.set_arith('chunk8');V.set_fuse('');model,init_hash=build_reference_model(ck,config)
        cs=V.rope_cs(model.freqs_plain,1048575);coefficient_pins={}
        for name,a in zip(('rope_cos','rope_sin'),cs):
            row=next(v for k,v in m['view_bindings'].items() if k.startswith('63/') and k.endswith('/'+name))
            p=Path(row['path']);p=p if p.is_absolute() else Path(provider_root)/p
            if sha(p)!=row['sha256'] or payload(np.load(p,allow_pickle=False))!=payload(a):raise ValueError('original source RoPE coefficient')
            coefficient_pins[str(p)]=sha(p)
        observed=observe_attention(model,incoming['norm'],old)
        h=V.Model.hc_post(model,observed['y'],incoming['h'],incoming['post'],incoming['comb'])
        controls=V.Model.hc_mixes(model,h,1,'ffn')
        x=V.rmsnorm_fold(model.hc_pre(h,incoming['pre']),model.lw(1,'ffn_norm.weight'),model.eps)
        np.savez(out/'original_golden_observations.npz',**observed,h=h,pre=controls[0],post=controls[1],comb=controls[2],x=x)
        provenance=dict(independent_golden=True,runtime_operand_source=False,
            observer='unchanged original Model.attention/hc_post/hc_mixes; original wo_a subtotal tree checked against grouped result',
            original_model_init_hash=init_hash,parent_reference_sha256=sha(upstream))
        emit(n,observed,h,controls,x,store,provenance)
        if store.observed.keys()!=store.required.keys():raise ValueError('complete source fragment coverage')
        ck.check_locks()
        sources=[__file__,V.__file__,LC.__file__,Path(V.__file__).with_name('hdc_golden.py'),config,native,manifest,upstream,artifact,obsfile,path,
            Path(__file__).with_name('h4_c0_ds_reference_layer_observers.py'),Path(__file__).with_name('h4_c0_ds_reference_trajectory.py'),
            Path(__file__).with_name('h4_c0_ds_whole_reference.py'),Path(__file__).with_name('h4_c0_ds_prefix_golden.py')]
        contract=store.contract();contract.update(PCs=list(range(60,74)),output_count=len(store.observed),
            status='INDEPENDENT_PC60_73_ORIGINAL_GOLDEN_NOT_YET_COMPARED',input_manifest_sha256=sha(manifest),
            checkpoint_revision=m['checkpoint_revision'],checkpoint_reads=ck.reads,
            reference_source_sha256={str(Path(p).resolve()):sha(p) for p in sources},coefficient_source_sha256=coefficient_pins,
            independent_golden_scope='original layer-one attention and FFN HC entering state; no old PC0-59 arithmetic repeated',
            entering_window_payload_sha256=payload(old),group_tree_exact_against_original=True)
        (out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
        receipt.update(status='PASS_ORIGINAL_PC60_73_REFERENCE_NOT_YET_COMPARED',fields=len(store.observed),expected_outputs_sha256=sha(out/'expected_outputs.json'))
    except Exception as e:receipt.update(status='FAIL_PRESERVED',error=repr(e));raise
    finally:
        receipt['finished_ns']=time.time_ns();save()
        if ck is not None:
            for fd,_ in ck.locks.values():os.close(fd)
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},source_pins=contract['reference_source_sha256']),sort_keys=True,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','manifest','upstream','provider_root','source_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(**vars(a)),sort_keys=True))
