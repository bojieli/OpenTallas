"""Independent golden expert observers and source-owned comparison fragments.

Observes unchanged Model.expert in a dedicated single-thread reference process.
No native executor/provider callbacks. Expected payloads never runtime operands.
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
from h4_c0_ds_prefix_golden import ReferenceCheckpoint,sha,load,payload_sha
from h4_c0_ds_whole_reference import ComparisonStore,slots,verify_retained,NATIVE

_LOCK=threading.Lock()
UPSTREAM='75798a7c8de7adbade6c0f6a8a3303621bb78f49276d596f23c6e807e9062b74'


def observe_expert(model,prefix,x,weight=None):
    """Observe original function calls, including its exact post-clip activation."""
    if threading.current_thread() is not threading.main_thread() or threading.active_count()!=1 or not _LOCK.acquire(False):
        raise ValueError('dedicated nonnested single-thread golden process required')
    original=V.linear_q;calls=[]
    def observed(w,a):
        y=original(w,a)
        calls.append((np.ascontiguousarray(a).copy(),np.ascontiguousarray(y).copy()))
        return y
    try:
        V.linear_q=observed
        y=V.Model.expert(model,prefix,x,weight)
    finally:
        V.linear_q=original;_LOCK.release()
    if len(calls)!=3:raise ValueError('unchanged golden expert three-linear contract')
    return dict(g=calls[0][1],u=calls[1][1],a=calls[2][0],d=y)


class ExpertFragments:
    """Exact current seven-slot, cumulative rank-owned activation semantics."""
    def __init__(self,native,layer,captured,store,provenance):
        if len(captured)!=7 or any(c['a'].shape!=(2304,) for c in captured):raise ValueError('actual seven expert geometry')
        self.n=native;self.layer=layer;self.c=captured;self.store=store;self.provenance=provenance
        self.ea=[np.zeros(7*2304,dtype='<f4') for _ in range(96)]
    def emit(self):
        emitted=[]
        for op in self.n['instructions']:
            so=op['source_op']
            if so.get('layer')!=self.layer:continue
            if op['family']=='linear_q' and isinstance(so.get('w'),list) and len(so['w'])==2 and isinstance(so['w'][0],int):
                slot,mat=so['w'];full=self.c[slot][{'w1':'g','w3':'u','w2':'d'}[mat]]
                for r in op['rank_bindings']:
                    if r.get('empty_owned_extent'):continue
                    lo,hi=r['row_interval'];self._write(op,r,op['writes'][0],full[lo:hi])
                emitted.append(op['pc'])
            elif op['family']=='swiglu':
                slot=so['slot']
                for r in op['rank_bindings']:
                    rank=r['rank'];ext=op['writes'][0]['producer_extent']
                    lo,hi=ext['rank_local_slice'][rank]
                    # Source intervals are absolute offsets in the seven-slot buffer.
                    if not slot*2304<=lo<=hi<=(slot+1)*2304:raise ValueError('exact source absolute expert slot interval')
                    self.ea[rank][lo:hi]=self.c[slot]['a'][lo-slot*2304:hi-slot*2304]
                    self._write(op,r,op['writes'][0],self.ea[rank])
                emitted.append(op['pc'])
            elif op['family']=='all_gather' and so.get('bufs')==['ea']:
                full=np.concatenate([c['a'] for c in self.c])
                for r in op['rank_bindings']:
                    for w in op['writes']:
                        view=w['native_result_binding'];v=full
                        if 'flat_slice' in view:
                            lo,hi=view['flat_slice'];v=full[lo:hi]
                        self._write(op,r,w,v)
                emitted.append(op['pc'])
        return emitted
    def _write(self,op,r,w,a):
        self.store.append((op['pc'],w['version'],r['rank'],'data'),np.ascontiguousarray(a,dtype='<f4'),self.provenance)


def upstream_array(contract,path,PC,result,native):
    versions={w['version'] for w in native['instructions'][PC]['writes'] if w['native_result_binding']['result']==result}
    row=next(e for e in contract['expectations'] if e['PC']==PC and e['rank']==0 and e['version'] in versions)
    p=Path(path).parent/row['path'];a=np.load(p,allow_pickle=False)
    if sha(p)!=row['file_sha256'] or payload_sha(a)!=row['payload_sha256']:raise ValueError('immutable independent continuation bytes')
    return a


def generate(native,manifest,upstream,reference,record,archive,source_root,out):
    out=Path(out)
    if out.exists():raise ValueError('fresh uncapped independent continuation output')
    if sha(native)!=NATIVE or sha(upstream)!=UPSTREAM:raise ValueError('exact canonical/source reference pins')
    n=load(native);mfest=load(manifest);up=load(upstream)
    for p,h in up['reference_source_sha256'].items():
        if sha(p)!=h:raise ValueError('upstream independent source changed')
    if sha(manifest)!=up['input_manifest_sha256']:raise ValueError('same actual entering source state')
    retained,ref,rec=verify_retained(reference,record,archive,manifest,source_root)
    required=[s for s in slots(n) if 21<=s['PC']<=49]
    store=ComparisonStore(out,required)
    receipt=dict(status='RUNNING_INDEPENDENT_EXPERT_CONTINUATION',pid=os.getpid(),started_ns=time.time_ns(),
        arithmetic='chunk8',source_input_PCs=[15,19],no_PC0_19_numerical_reexecution=True,
        arbitrary_resource_caps=False,actual_native_execution=False,hardware_qualified=False,full_token_qualified=False)
    def save():(out/'record.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    save();ck=None
    try:
        x=upstream_array(up,upstream,15,'x',n);ids=upstream_array(up,upstream,19,'route_ids',n);rw=upstream_array(up,upstream,19,'route_w',n)
        if ids.tolist()!=ref['layers'][0]['experts'] or x.shape!=(5120,) or rw.shape!=(6,):raise ValueError('source selected actual golden experts/input')
        ck=ReferenceCheckpoint(mfest);c=load(ck.snap/'config.json')['text_config']
        V.set_arith('chunk8');V.set_fuse('')
        model=V.Model.__new__(V.Model);model.limit=V.F(c['swiglu_limit']);model.w=LC.LazyWeights(ck)
        captures=[];total=np.zeros(5120,dtype='<f4');descriptors=[]
        for slot in range(7):
            prefix=f'layers.0.ffn.experts.{int(ids[slot])}.' if slot<6 else 'layers.0.ffn.shared_experts.'
            result=observe_expert(model,prefix,x,rw[slot] if slot<6 else None)
            captures.append(result);total=V.add(total,result['d'])
            np.savez(out/f'independent_expert_{slot}.npz',**result)
            descriptors.append(dict(slot=slot,prefix=prefix,matrices=[prefix+k+'.weight' for k in ('w1','w3','w2')]))
            receipt.update(completed_experts=slot+1);save()
        total=V.to_bf16(total)
        if payload_sha(total)!=rec['trace_sha256']['L0.ffn'] or not np.array_equal(total.view('<u4'),retained['L0.ffn'].view('<u4')):
            raise ValueError('independent continuation differs from complete retained golden FFN bytes')
        receipt.update(complete_FFN_values=5120,zero_errors=True,complete_FFN_sha256=payload_sha(total));save()
        provenance=dict(independent_golden=True,runtime_operand_source=False,
            observer='unchanged original Model.expert, captured original linear_q inputs/results',
            entering_reference_sha256=UPSTREAM,retained_FFN_trace_sha256=payload_sha(total))
        pcs=ExpertFragments(n,0,captures,store,provenance).emit()
        if set(store.observed)!=store.required.keys():raise ValueError('every declared PC21_49 rank/version/field required')
        ck.check_locks()
        contract=store.contract();contract.update(PCs=pcs,output_count=len(store.observed),
            input_manifest_sha256=sha(manifest),checkpoint_revision=mfest['checkpoint_revision'],
            reference_source_sha256={str(Path(p).resolve()):sha(p) for p in [__file__,V.__file__,LC.__file__,
                Path(V.__file__).with_name('hdc_golden.py'),Path(__file__).with_name('h4_c0_ds_whole_reference.py'),
                Path(__file__).with_name('h4_c0_ds_prefix_golden.py'),ck.snap/'config.json',upstream,native,manifest,reference,record,archive]},
            checkpoint_reads=ck.reads,selected_expert_descriptors=descriptors,
            complete_FFN_retained_comparison=dict(values=5120,zero_errors=True,payload_sha256=payload_sha(total)),
            descriptor_scope='independent selected checkpoint identity only; no actual executor fetch/lease receipt',
            status='INDEPENDENT_PC21_49_REFERENCE_NOT_YET_COMPARED')
        (out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
        receipt.update(status='PASS_INDEPENDENT_PC21_49_REFERENCE_AND_RETAINED_FFN',output_fields=len(store.observed),PCs=pcs,
            expected_outputs_sha256=sha(out/'expected_outputs.json'),complete_FFN_values=5120,zero_errors=True)
    except Exception as e:
        receipt.update(status='FAIL_PRESERVED',error=repr(e));raise
    finally:
        receipt['finished_ns']=time.time_ns();save()
        if ck is not None:
            for fd,_ in ck.locks.values():os.close(fd)
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},source_pins=contract['reference_source_sha256']),sort_keys=True,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','manifest','upstream','reference','record','archive','source_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(a.native,a.manifest,a.upstream,a.reference,a.record,a.archive,a.source_root,a.out),sort_keys=True))
