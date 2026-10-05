"""Additive corrected constructor successor; historical entry remains immutable.

One original released-checkpoint reference continuation, opt-in execution.

Starts AFTER the independently retained layer zero, never reexecutes PC0..19.
Intermediate expert observers are source-bound; uncovered families remain gaps.
This is a golden reference producer, never a native/provider execution entry.
"""
import argparse
import json
import os
from pathlib import Path
import time
import numpy as np
import hdc_golden_v41 as V
import rtl_v41_fullshape_layer_campaign as LC
from h4_c0_ds_prefix_golden import ReferenceCheckpoint,sha,load,payload_sha
from h4_c0_ds_reference_state import ActualEnteringState,observed_model
from h4_c0_ds_whole_reference import verify_retained,ComparisonStore,slots,NATIVE


class TrajectoryCheckpoint(ReferenceCheckpoint):
    def rows(self,name,ids):
        # Original golden ordered Engram row reads, selected raw rows audited.
        ids=np.asarray(ids,dtype=np.int64).reshape(-1)
        for i in sorted(set(ids.tolist())):self.audit(name,[i,i+1])
        return LC.Checkpoint.rows(self,name,ids)


def produce(native,manifest,reference,record,archive,source_root,out,*,execute=False):
    if sha(native)!=NATIVE:raise ValueError('canonical corrected source program')
    retained,ref,rec=verify_retained(reference,record,archive,manifest,source_root)
    plan=dict(status='PREPARED_SINGLE_REFERENCE_TRAJECTORY',start_layer=1,last_layer=39,
        original_function='unchanged hdc_golden_v41.Model.layer then original golden head',
        existing_prefix='released retained golden layer0 state; PC0..19 not reexecuted',
        actual_state_reader='ActualEnteringState locked windows/history/open groups, whole digest required',
        intermediate_observers='original Model.expert linear inputs/results, cumulative source sparse/alias mapping, all layers',
        remaining_observers='HC, attention, projection groups, index/query/compressor/candidates, Engram and final compound fragments',
        arbitrary_resource_caps=False,hardware_qualified=False,full_token_qualified=False)
    if not execute:return plan
    out=Path(out)
    if out.exists():raise ValueError('fresh independent full-reference output')
    n=load(native);required=[s for s in slots(n) if s['PC']>=53]
    store=ComparisonStore(out,required)
    receipt=dict(plan,status='RUNNING_ORIGINAL_REFERENCE_TRAJECTORY',pid=os.getpid(),started_ns=time.time_ns())
    def save():(out/'record.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    save();ck=None
    try:
        with ActualEnteringState(manifest) as entering:
            state,proof=entering.load_state(reference)
            (out/'actual_state_join.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
            ck=TrajectoryCheckpoint(load(manifest));config=Path(source_root)/'compiler/models/deepseek-v4.1-flash/inference_config.json'
            if sha(config)!=ref['source_sha256']['compiler/models/deepseek-v4.1-flash/inference_config.json']:raise ValueError('original released inference configuration')
            V.set_arith('chunk8');V.set_fuse('')
            model, original_init_hash=LC.build_model(ck,config=config)
            if not isinstance(model,V.Model):raise ValueError("original golden constructor tuple model")
            provenance=dict(independent_golden=True,runtime_operand_source=False,original_reference_sha256=sha(reference),
                observer='original Model.layer/expert, actual source entering images; no native runtime callbacks', original_model_init_hash=original_init_hash)
            model=observed_model(model,n,store,provenance)
            state['win'][0].append(retained['win0'])
            ctx=dict(h=retained['h_out'].copy(),pre=retained['pre_out'].copy(),pos=ref['position'],hist=ref['token_history'])
            for layer in range(1,40):
                inp=LC.digest(ctx['h'],ctx['pre'])
                if inp!=ref['layers'][layer]['input_sha256']:raise ValueError('original independent layer entering state differs')
                trace={};model.layer(layer,ctx,state,trace)
                digest=LC.digest(ctx['h'],ctx['pre'])
                if digest!=ref['layers'][layer]['output_sha256']:raise ValueError('original independent layer complete output differs')
                np.savez(out/f'layer_{layer:02d}.npz',h=ctx['h'],pre=ctx['pre'])
                receipt.update(completed_layer=layer,published_reference_fields=len(store.observed));save()
                for key in list(model.w):
                    if key.startswith(f'layers.{layer}.'):del model.w[key]
                ck.check_locks();entering.check_locks()
            x=V.rmsnorm_fold(model.hc_pre(ctx['h'],ctx['pre']),model.w['norm.weight'],model.eps)
            logits=V.mv(model.w['head.weight'],x)
            if payload_sha(logits)!=ref['logits_sha256'] or int(np.argmax(logits))!=ref['next_token']:raise ValueError('original complete logits/token differ')
            np.save(out/'logits.npy',logits,allow_pickle=False)
            contract=store.contract();contract.update(PCs=sorted({k[0] for k in store.observed}),
                output_count=len(store.observed),input_manifest_sha256=sha(manifest),checkpoint_revision=load(manifest)['checkpoint_revision'],
                reference_source_sha256={str(Path(p).resolve()):sha(p) for p in [__file__,Path(__file__).with_name('h4_c0_ds_reference_trajectory.py'),V.__file__,LC.__file__,config,native,manifest,reference,record,archive,
                    Path(__file__).with_name('h4_c0_ds_reference_state.py'),Path(__file__).with_name('h4_c0_ds_reference_observers.py'),
                    Path(__file__).with_name('h4_c0_ds_prefix_golden.py'),Path(__file__).with_name('h4_c0_ds_whole_reference.py')]},
                checkpoint_reads=ck.reads,full_logits_sha256=payload_sha(logits),next_token=int(np.argmax(logits)),
                complete_native_field_reference=False,missing_fields=len(store.required)-len(store.observed))
            (out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
            receipt.update(status='PASS_ORIGINAL_REFERENCE_TRAJECTORY_PARTIAL_NATIVE_WITNESS_COVERAGE',
                full_logits_sha256=payload_sha(logits),next_token=int(np.argmax(logits)),
                missing_fields=contract['missing_fields'],complete_native_field_reference=False)
    except Exception as e:receipt.update(status='FAIL_PRESERVED',error=repr(e));raise
    finally:
        receipt['finished_ns']=time.time_ns();save()
        if ck is not None:
            for fd,_ in ck.locks.values():os.close(fd)
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','manifest','reference','record','archive','source_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    p.add_argument('--execute',action='store_true',default=False)
    a=p.parse_args();print(json.dumps(produce(a.native,a.manifest,a.reference,a.record,a.archive,a.source_root,a.out,execute=a.execute),sort_keys=True))
