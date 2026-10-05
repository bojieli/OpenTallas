"""Original released-checkpoint layer-one MoE continuation, comparison only.

Starts from saved independent PC73. Observes actual original Model.moe/expert
calls and retains scalar route weights and absolute seven-slot fragments.
PC78 actual HBM descriptor/acquisition lifecycle remains a runtime refusal.
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
from h4_c0_ds_reference_observers import observe_expert,ExpertFragments
from h4_c0_ds_whole_reference import ComparisonStore,slots,NATIVE,MANIFEST,REFERENCE,sha,load,payload

UPSTREAM='7b40c58cd4bfaea1aaed859fa4fdd4c70bf28d4f4138456450eaeac79cbe1669'


def observe_moe(model,x,out,progress):
    if threading.current_thread() is not threading.main_thread() or threading.active_count()!=1:
        raise ValueError('dedicated single-thread golden reference process')
    captures=[];descriptors=[];router={}
    class Observer(V.Model):
        def expert(self,prefix,a,weight=None):
            if payload(a)!=payload(x):raise ValueError('source expert entering vector changed')
            c=observe_expert(self,prefix,a,weight);slot=len(captures)
            captures.append(c);descriptors.append(dict(slot=slot,prefix=prefix,weight=None if weight is None else float(weight),
                weight_f32_hex=None if weight is None else np.asarray(weight,dtype='<f4').tobytes().hex(),
                matrices=[prefix+k+'.weight' for k in ('w1','w3','w2')]))
            np.savez(Path(out)/f'original_expert_{slot}.npz',**c)
            progress(slot+1);return c['d']
    obs=Observer.__new__(Observer);obs.__dict__.update(model.__dict__)
    gate=obs.lw(1,'ffn.gate.weight');mv=V.mv;sqrt=V.sqrt
    def observed_mv(w,a):
        y=mv(w,a)
        if w is gate:
            if 'raw' in router:raise ValueError('duplicate original router gate')
            router['raw']=y.copy()
        return y
    def observed_sqrt(a):
        y=sqrt(a)
        if np.asarray(y).shape==(384,):
            if 'scores' in router:raise ValueError('duplicate original router activation')
            router['scores']=y.copy()
        return y
    trace={}
    try:
        V.mv=observed_mv;V.sqrt=observed_sqrt
        y=V.Model.moe(obs,1,x,trace)
    finally:V.mv=mv;V.sqrt=sqrt
    if len(captures)!=7 or set(router)!={'raw','scores'}:raise ValueError('complete actual six routed plus shared MoE observations')
    ids=np.asarray(trace['L1.experts'],dtype='<i8')
    if ids.shape!=(6,) or ids.tolist()!=sorted(ids.tolist()) or len(set(ids.tolist()))!=6:raise ValueError('source six ordered expert IDs')
    expected=[f'layers.1.ffn.experts.{i}.' for i in ids]+['layers.1.ffn.shared_experts.']
    if [d['prefix'] for d in descriptors]!=expected or descriptors[-1]['weight'] is not None:raise ValueError('actual expert slot ordering')
    weights=np.asarray([d['weight'] for d in descriptors[:6]],dtype='<f4')
    router.update(ids=ids,weights=weights,router=trace['L1.router'],yf=y)
    return router,captures,descriptors


def emit_aux(native,observed,h,pre,store,provenance):
    for op in native['instructions'][74:111]:
        pc=op['pc']
        if pc not in (74,75,76,77,108,109,110):continue
        for rb in op['rank_bindings']:
            if rb.get('empty_owned_extent'):continue
            rank=rb['rank']
            for w in op['writes']:
                result=w['native_result_binding']['result']
                if pc in (74,75):
                    lo,hi=native['instructions'][74]['rank_bindings'][rank]['row_interval']
                    a=observed['raw' if pc==74 else 'scores'][lo:hi]
                elif pc==76:a=observed['scores']
                elif pc==77:a=dict(router=observed['router'],route_ids=observed['ids'],route_w=observed['weights'])[result]
                elif pc==108:lo,hi=w['producer_extent'][rank];a=observed['yf'][lo:hi]
                elif pc==109:a=observed['yf']
                else:a=dict(h=h,pre=pre)[result]
                dtype='<i8' if result=='route_ids' else '<f4'
                store.append((pc,w['version'],rank,'data'),np.ascontiguousarray(a,dtype=dtype),provenance)


def generate(native,manifest,upstream,reference,source_root,out):
    if sha(native)!=NATIVE or sha(manifest)!=MANIFEST or sha(upstream)!=UPSTREAM or sha(reference)!=REFERENCE:
        raise ValueError('immutable released source and exact prior reference lineage')
    n=load(native);m=load(manifest);u=load(upstream);ref=load(reference)
    for p,d in u['reference_source_sha256'].items():
        if sha(p)!=d:raise ValueError('original upstream source changed')
    amfile=Path(upstream).parent/'artifact_manifest.json';am=load(amfile);obsfile=Path(upstream).parent/'original_golden_observations.npz'
    if sha(obsfile)!=am['artifacts'][obsfile.name]:raise ValueError('exact retained independent state observations')
    with np.load(obsfile,allow_pickle=False) as f:incoming={k:f[k].copy() for k in f.files}
    expected={'x':73,'h':71,'pre':72,'post':72,'comb':72}
    for name,pc in expected.items():
        matching={w['version'] for w in n['instructions'][pc]['writes'] if w['native_result_binding']['result']==name}
        rows=[r for r in u['expectations'] if r['PC']==pc and r['version'] in matching]
        if not rows or any(r['payload_sha256']!=payload(incoming[name]) for r in rows):raise ValueError('actual independent entering state field '+name)
    out=Path(out);store=ComparisonStore(out,[s for s in slots(n) if 74<=s['PC']<=110])
    receipt=dict(status='RUNNING_ORIGINAL_PC74_110_REFERENCE',pid=os.getpid(),started_ns=time.time_ns(),
        arbitrary_resource_caps=False,earlier_prefix_reexecuted=False,native_execution=False,hardware_qualified=False,full_token_qualified=False)
    def save():(out/'record.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    def progress(count):receipt.update(completed_original_experts=count);save()
    save();ck=None
    try:
        ck=TrajectoryCheckpoint(m);config=Path(source_root)/'compiler/models/deepseek-v4.1-flash/inference_config.json'
        if sha(config)!=ref['source_sha256']['compiler/models/deepseek-v4.1-flash/inference_config.json']:raise ValueError('same released inference configuration')
        V.set_arith('chunk8');V.set_fuse('');model,init_hash=build_reference_model(ck,config)
        observed,captures,descriptors=observe_moe(model,incoming['x'],out,progress)
        if observed['ids'].tolist()!=ref['layers'][1]['experts']:raise ValueError('original retained full-trajectory expert selection differs')
        h=V.Model.hc_post(model,observed['yf'],incoming['h'],incoming['post'],incoming['comb']);pre=incoming['pre']
        digest=LC.digest(h,pre)
        if digest!=ref['layers'][1]['output_sha256']:raise ValueError('original complete layer-one state differs from independent retained full reference')
        np.savez(out/'original_golden_observations.npz',**observed,h=h,pre=pre)
        provenance=dict(independent_golden=True,runtime_operand_source=False,observer='unchanged original Model.moe/expert/hc_post; actual original scalar weights',
            original_model_init_hash=init_hash,parent_reference_sha256=sha(upstream),layer_output_sha256=digest)
        ExpertFragments(n,1,captures,store,provenance).emit();emit_aux(n,observed,h,pre,store,provenance)
        if store.observed.keys()!=store.required.keys():raise ValueError('complete source rank/version/field coverage')
        ck.check_locks()
        sources=[__file__,V.__file__,LC.__file__,Path(V.__file__).with_name('hdc_golden.py'),config,native,manifest,upstream,reference,amfile,obsfile,
            Path(__file__).with_name('h4_c0_ds_reference_layer_observers.py'),Path(__file__).with_name('h4_c0_ds_reference_observers.py'),
            Path(__file__).with_name('h4_c0_ds_reference_trajectory.py'),Path(__file__).with_name('h4_c0_ds_whole_reference.py'),Path(__file__).with_name('h4_c0_ds_prefix_golden.py')]
        contract=store.contract();contract.update(PCs=sorted({k[0] for k in store.observed}),output_count=len(store.observed),
            status='INDEPENDENT_PC74_110_ORIGINAL_GOLDEN_NOT_YET_COMPARED',input_manifest_sha256=sha(manifest),checkpoint_revision=m['checkpoint_revision'],
            checkpoint_reads=ck.reads,reference_source_sha256={str(Path(p).resolve()):sha(p) for p in sources},ordered_experts=observed['ids'].tolist(),
            actual_original_scalar_weights_hex=[d['weight_f32_hex'] for d in descriptors[:6]],selected_expert_descriptors=descriptors,
            complete_layer_state_comparison=dict(layer=1,output_sha256=digest,retained_reference_sha256=sha(reference),exact_hash_equal=True),
            independent_golden_scope='original layer-one MoE and final state; no old PC0-73 arithmetic repeated',
            zero_publication_refusals=[dict(PC=78,family='expert_fetch',required='actual executor selected descriptor identity and HBM acquisition/leases/ACK/reverse; independent checkpoint reads alone do not qualify acquisition')])
        (out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
        receipt.update(status='PASS_ORIGINAL_PC74_110_REFERENCE_AND_LAYER1_STATE_NOT_YET_COMPARED',fields=len(store.observed),
            expected_outputs_sha256=sha(out/'expected_outputs.json'),complete_layer_output_sha256=digest,ordered_experts=observed['ids'].tolist(),expert_fetch_qualified=False)
    except Exception as e:receipt.update(status='FAIL_PRESERVED',error=repr(e));raise
    finally:
        receipt['finished_ns']=time.time_ns();save()
        if ck is not None:
            for fd,_ in ck.locks.values():os.close(fd)
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},source_pins=contract['reference_source_sha256']),sort_keys=True,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','manifest','upstream','reference','source_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(**vars(a)),sort_keys=True))
