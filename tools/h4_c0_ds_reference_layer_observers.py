"""Original golden Engram/HC observers with actual source fragment bindings.

Comparison-only continuation: released table rows, original Engram function,
original HC controls/norm. Never invokes native family execution/providers.
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
from h4_c0_ds_reference_trajectory import TrajectoryCheckpoint
from h4_c0_ds_whole_reference import ComparisonStore,slots,verify_retained,NATIVE,sha,load


def build_reference_model(checkpoint,config):
    # The existing constructor returns (model, original __init__ source hash).
    model,init_hash=LC.build_model(checkpoint,config=config)
    if not isinstance(model,V.Model):raise ValueError('original golden model constructor result')
    return model,init_hash


def observe_engram(model,h,layer,history):
    if threading.current_thread() is not threading.main_thread() or threading.active_count()!=1:
        raise ValueError('dedicated golden reference process required')
    decode=V.decode_engram_rows;linear=V.linear_q;observations={}
    def decoded(codes,scales,ids):
        y=decode(codes,scales,ids)
        if observations:raise ValueError('one original Engram decode per layer')
        observations.update(ids=np.asarray(ids,dtype='<i8').copy(),rows=y.copy())
        return y
    def projected(w,x):
        y=linear(w,x);observations['kv']=y.copy();return y
    try:
        V.decode_engram_rows=decoded;V.linear_q=projected
        y=V.Model.engram_layer(model,h,layer,history)
    finally:
        V.decode_engram_rows=decode;V.linear_q=linear
    if set(observations)!={'ids','rows','kv'}:raise ValueError('complete original Engram observations')
    observations['h']=y
    return observations


def owned_engram_rows(ids,rows,rank):
    ids=np.asarray(ids).reshape(-1);rows=np.asarray(rows).reshape(len(ids),-1)
    out=np.zeros_like(rows)
    out[ids%96==rank]=rows[ids%96==rank]
    return out.reshape(-1)


def emit_engram_hc(native,layer,observed,controls,norm,store,provenance):
    full_rows=observed['rows'].reshape(-1);full_kv=observed['kv'];h=observed['h']
    mappings={'engram_mix':dict(h=h,engram_h=h),
              'hc_mixes':dict(pre=controls[0],post=controls[1],comb=controls[2],res=h),
              'hc_pre_norm':dict(x=norm,which_x=norm)}
    PCs=[]
    for op in native['instructions']:
        so=op['source_op']
        if so.get('layer')!=layer:continue
        family=op['family']
        if family in ('hc_mixes','hc_pre_norm') and so.get('which')!='attn':continue
        if family=='engram_fetch':values=dict(eg_rows=full_rows)
        elif family=='all_gather' and so.get('bufs')==['eg_rows']:values=dict(out=full_rows)
        elif family=='linear_q' and so.get('w')==f'layers.{layer}.engram.wkv.weight':values=dict(out=full_kv)
        elif family=='all_gather' and so.get('bufs')==['eg_kv']:values=dict(out=full_kv)
        elif family in mappings:values=mappings[family]
        else:continue
        for rank in op['rank_bindings']:
            if rank.get('empty_owned_extent'):continue
            for w in op['writes']:
                a=values[w['native_result_binding']['result']]
                if family=='engram_fetch':a=owned_engram_rows(observed['ids'],observed['rows'],rank['rank'])
                elif family=='linear_q':
                    lo,hi=rank['row_interval'];a=a[lo:hi]
                store.append((op['pc'],w['version'],rank['rank'],'data'),np.ascontiguousarray(a,dtype='<f4'),provenance)
        PCs.append(op['pc'])
    return PCs


def generate(native,manifest,reference,record,archive,source_root,out):
    if sha(native)!=NATIVE:raise ValueError('exact canonical corrected source')
    retained,ref,rec=verify_retained(reference,record,archive,manifest,source_root)
    n=load(native);out=Path(out)
    store=ComparisonStore(out,[s for s in slots(n) if 53<=s['PC']<=59])
    receipt=dict(status='RUNNING_ORIGINAL_ENGRAM_HC_REFERENCE',pid=os.getpid(),started_ns=time.time_ns(),
        PCs=list(range(53,60)),no_PC0_19_reexecution=True,arbitrary_resource_caps=False,
        native_arithmetic_execution=False,hardware_qualified=False,full_token_qualified=False)
    def save():(out/'record.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    save();ck=None
    try:
        ck=TrajectoryCheckpoint(load(manifest));config=Path(source_root)/'compiler/models/deepseek-v4.1-flash/inference_config.json'
        if sha(config)!=ref['source_sha256']['compiler/models/deepseek-v4.1-flash/inference_config.json']:raise ValueError('released inference contract')
        V.set_arith('chunk8');V.set_fuse('')
        model,init_hash=build_reference_model(ck,config)
        if LC.digest(retained['h_out'],retained['pre_out'])!=ref['layers'][1]['input_sha256']:raise ValueError('exact layer1 entering state')
        observed=observe_engram(model,retained['h_out'],1,ref['token_history'])
        controls=V.Model.hc_mixes(model,observed['h'],1,'attn')
        norm=V.rmsnorm_fold(model.hc_pre(observed['h'],retained['pre_out']),model.lw(1,'attn_norm.weight'),model.eps)
        np.savez(out/'original_golden_observations.npz',**observed,pre=controls[0],post=controls[1],comb=controls[2],norm=norm)
        provenance=dict(independent_golden=True,runtime_operand_source=False,
            observer='unchanged original Model.engram_layer/hc_mixes/hc_pre and rmsnorm_fold',
            entering_layer_reference_sha256=sha(reference),original_model_init_hash=init_hash)
        pcs=emit_engram_hc(n,1,observed,controls,norm,store,provenance)
        if pcs!=list(range(53,60)) or store.observed.keys()!=store.required.keys():raise ValueError('complete seven-PC source fragment coverage')
        ck.check_locks()
        tokenizer=LC.HF/'tokenizer.json'
        contract=store.contract();contract.update(PCs=pcs,output_count=len(store.observed),
            status='INDEPENDENT_PC53_59_GOLDEN_NOT_YET_COMPARED',input_manifest_sha256=sha(manifest),
            checkpoint_revision=load(manifest)['checkpoint_revision'],checkpoint_reads=ck.reads,
            reference_source_sha256={str(Path(p).resolve()):sha(p) for p in [__file__,V.__file__,LC.__file__,config,tokenizer,
                Path(V.__file__).with_name('hdc_golden.py'),Path(__file__).with_name('h4_c0_ds_reference_trajectory.py'),
                Path(__file__).with_name('h4_c0_ds_prefix_golden.py'),Path(__file__).with_name('h4_c0_ds_whole_reference.py'),
                native,manifest,reference,record,archive]},
            independent_golden_scope='new original layer1 Engram/HC operation results; no independent duplicate stage reference yet',
            engram_ids=observed['ids'].reshape(-1).tolist(),
            numerical_rule='native publication must compare every source/rank/field byte; producing reference is not native PASS')
        (out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
        receipt.update(status='PASS_ORIGINAL_GOLDEN_PC53_59_REFERENCE_NOT_YET_COMPARED',fields=len(store.observed),
            expected_outputs_sha256=sha(out/'expected_outputs.json'),engram_ids=contract['engram_ids'])
    except Exception as e:receipt.update(status='FAIL_PRESERVED',error=repr(e));raise
    finally:
        receipt['finished_ns']=time.time_ns();save()
        if ck is not None:
            for fd,_ in ck.locks.values():os.close(fd)
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},source_pins=contract['reference_source_sha256']),sort_keys=True,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','manifest','reference','record','archive','source_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(a.native,a.manifest,a.reference,a.record,a.archive,a.source_root,a.out),sort_keys=True))
