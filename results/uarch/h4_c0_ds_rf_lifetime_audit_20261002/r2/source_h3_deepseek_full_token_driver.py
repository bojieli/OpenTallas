#!/usr/bin/env python3
"""Full source-PC primitive execution with an explicit data-only provider plugin.

All arithmetic executes in the committed forward kernels/original primitive VM.
Provider hooks bind payload views, addressed scratch, publication and ownership.
No reference executor/golden family handler, implicit weights or initial KV.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import h3_native_microop_adapter as A
import h3_deepseek_streaming_linear as S
import h3_deepseek_staged_native as V
ROOT=Path(__file__).resolve().parents[1]
PROGRAM='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
DISPATCH='results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz'
DTYPES={'F32':np.dtype('float32'),'U32':np.dtype('uint32'),'I64':np.dtype('int64')}
CAP=33554432


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def workspace_extent(allocation):
    if allocation.get('AW')!=27 or allocation.get('bytes')!=CAP:raise ValueError('exact AW27/32MiB workspace extent')
    base=allocation.get('base')
    if type(base) is not int or base<0 or base%512 or base+CAP>1<<27:raise ValueError('workspace alignment/range')
    occupied=allocation.get('occupied_extents')
    if occupied is None:raise ValueError('explicit occupied provider extents required')
    for e in occupied:
        start=e['base'];size=e['bytes']
        if type(start) is not int or type(size) is not int or start<0 or size<=0 or start+size>1<<27:raise ValueError('occupied extent range')
        if base<start+size and start<base+CAP:raise ValueError('workspace aliases provider extent')
    return allocation


def validate_view(name,value,required,spec,rank,generation,revision):
    if any(value.get(key)!=want for key,want in {'field':name,'rank':rank,'generation':generation,'kind':required['kind']}.items()):raise ValueError('typed provider identity '+name)
    if value.get('provenance_certified') is not True:raise ValueError('uncertified provider '+name)
    kind=required['kind']
    if kind=='versioned_operand':
        if value.get('version')!=required['version'] or value.get('view_contract')!=required['native_address_view']:raise ValueError('version/view mismatch '+name)
    elif kind in ('immutable_parameter_provider','immutable_weight_provider'):
        if value.get('logical_tensor')!=required['logical_tensor'] or value.get('revision')!=revision:raise ValueError('exact tensor/checkpoint revision '+name)
    elif value.get('source_binding')!=required:raise ValueError('auxiliary provider binding '+name)
    data=value['data']
    if not isinstance(data,np.ndarray) or list(data.shape)!=spec['shape'] or data.dtype!=DTYPES[spec['dtype']]:raise ValueError('exact provider shape/dtype '+name)
    return data


def execute_kernel(program,inputs,owner,memory):
    """Reuse full forward implementations, substituting only addressed storage."""
    f=program['family']
    if f=='linear_q':
        vm=S.StreamingLinear(owner);vm.memory=memory
        out,r=vm.run(inputs['x'],inputs['weight_codes'],inputs['weight_scale_codes'],program['source_attributes'].get('fmt','fp8'));out={} if out is None else {'out':out}
    elif f in ('mv','linear_bf16','wo_a_part'):
        vm=S.StreamingFloat(owner);vm.memory=memory
        out,r=vm.run_float(inputs['x'],inputs['weight'],f=='linear_bf16');out={} if out is None else {'out':out}
    elif f=='all_gather':
        vm=S.StreamingGather(owner);vm.memory=memory
        out,r=vm.run_gather(inputs['parts'],inputs['ownership_mask']);out={'out':out}
    elif f=='index_scores':
        vm=S.StreamingIndex(owner);vm.memory=memory;out,r=vm.run_index(inputs,owner[2])
    else:
        vm=V.StagedMachine(program,inputs,owner);vm.memory=memory;out,r=vm.run()
    memory.fence()
    if r['status'] not in A.PASS_STATUSES:raise ValueError('native fault prohibits successful output publication')
    return out,r


def publication_receipt(receipt,identity,hashes):
    # Backing mutation followed by matching reverse consume is SOFTWARE causality;
    # it never certifies PHY/service/clock qualification.
    if receipt.get('identity')!=identity or receipt.get('payload_sha256')!=hashes:raise ValueError('publication identity/payload mismatch')
    events=receipt.get('events',[])
    required=['software_backing_visible','consumer_accept','validated_reverse_grant']
    names=[e['event'] for e in events]
    if names!=required or any(e.get('identity')!=identity for e in events):raise ValueError('actual publication/consume/reverse sequence required')
    times=[e['sequence'] for e in events]
    if any(type(t) is not int for t in times) or not times[0]<times[1]<times[2]:raise ValueError('publication event causality')
    if receipt.get('pending_obligations')!=0:raise ValueError('accepted publication obligations retained')


class TokenDriver:
    def __init__(self,native,dispatch,provider,revision,generation,homes):
        if not isinstance(revision,str) or not revision or type(generation) is not int or generation<0:raise ValueError('exact checkpoint revision/generation required')
        self.native=native;self.dispatch=dispatch;self.provider=provider;self.revision=revision;self.generation=generation;self.homes=homes;self.retired=set();self.journal=[]
        self.last_use={r['version']:op['pc'] for op in native['instructions'] for r in op['reads']}
        ranks={r['rank'] for op in native['instructions'] for r in op['rank_bindings'] if not r.get('empty_owned_extent')}
        self.allocations={rank:workspace_extent(provider.workspace(rank)) for rank in ranks}
        if len(dispatch['PC_dispatch'])!=len(native['instructions']):raise ValueError('whole source/dispatch count mismatch')
        for op,d in zip(native['instructions'],dispatch['PC_dispatch']):
            if (op['pc'],op['family'])!=(d['pc'],d['family']):raise ValueError('dispatch/source identity')
        for method in ('read_views','scratch_memory','publish','release_views','retire_operation','release_version','drain'):
            if not callable(getattr(provider,method,None)):raise ValueError('missing actual provider hook '+method)
        if any(hasattr(provider,name) for name in ('execute_opcode','golden_handler','bound_handlers')):raise ValueError('high-level arithmetic callback provider forbidden')

    def run_buffer(self,op,owned,template,bindings,views,writes):
        rank=owned['rank'];p=self.native['templates'][template]
        if set(views)!=set(p['providers']):raise ValueError('exact source LOAD view set')
        inputs={name:validate_view(name,v,bindings[name],p['providers'][name],rank,self.generation,self.revision) for name,v in views.items()}
        owner=(op['pc'],tuple(w['version'] for w in writes),rank,0,self.generation)
        memory=self.provider.scratch_memory(owner,self.allocations[rank])
        if memory.workspace_extent!=self.allocations[rank]:raise ValueError('scratch not bound to allocated noalias extent')
        outputs,numeric=execute_kernel(p,inputs,owner,memory)
        for write in writes:
            view=write['native_result_binding'];data=outputs[view['result']]
            if 'flat_slice' in view:data=data.reshape(-1)[slice(*view['flat_slice'])]
            if any(type(i) is not int or not 0<=i<len(self.homes) or self.homes[i]['version']!=write['version'] for i in write['home_indices']):raise ValueError('source home/version identity')
            indices=[i for i in write['home_indices'] if rank in self.homes[i]['rank_group']]
            if not indices:raise ValueError('no source output homes for rank/version')
            fields={'data':data,**{name:outputs[name] for name in op.get('compound_output_fields',{}).get(view['result'],[])}}
            identity={'PC':op['pc'],'version':write['version'],'rank':rank,'generation':self.generation,'home_indices':indices}
            hashes={name:hashlib.sha256(array.tobytes()).hexdigest() for name,array in fields.items()}
            receipt=self.provider.publish(identity,fields,view)
            publication_receipt(receipt,identity,hashes)
        # Inputs remain logically leased until source computation and all writes
        # publish; the provider owns actual accepted fragment consume/grant events.
        self.provider.release_views(op['pc'],rank,self.generation,views)
        self.journal.append({'PC':op['pc'],'rank':rank,'template':template,'native':numeric,'published_versions':[w['version'] for w in writes],'physical_qualified':False})

    def run(self):
        for op in self.native['instructions']:
            if any(dep not in self.retired for dep in op['dependencies']):raise ValueError('dependency before source retirement')
            for owned in op['rank_bindings']:
                if owned.get('empty_owned_extent'):continue
                views=self.provider.read_views(op,owned,self.generation)
                if owned.get('buffer_programs'):
                    buffers=owned['buffer_programs']
                    if set(views)!={b['write_version'] for b in buffers}:raise ValueError('independent collective buffer provider set')
                    for b in buffers:
                        bindings={name:dict(value) for name,value in op['provider_bindings'][b['template']].items()}
                        for name,required in bindings.items():
                            if name=='parts':required.update(version=b['read_version'],additional_versions=[b['read_version']])
                            elif required['kind']=='explicit_auxiliary_provider':required['identity_from_versions']=[b['read_version']]
                        self.run_buffer(op,owned,b['template'],bindings,views[b['write_version']],[w for w in op['writes'] if w['version']==b['write_version']])
                else:self.run_buffer(op,owned,owned['template'],op['provider_bindings'][owned['template']],views,op['writes'])
            retired=self.provider.retire_operation(op['pc'],self.generation)
            if retired!={'PC':op['pc'],'generation':self.generation,'pending_obligations':0,'source_consumers_released':True}:raise ValueError('root retirement before exact drain')
            self.retired.add(op['pc'])
            for read in op['reads']:
                if self.last_use[read['version']]==op['pc']:self.provider.release_version(read['version'],self.generation)
        drained=self.provider.drain(self.generation)
        if drained!={'generation':self.generation,'pending_obligations':0,'live_consumers':0}:raise ValueError('token before end-to-end software drain')
        return {'status':'FULL_SOURCE_NATIVE_SOFTWARE_TOKEN_COMPLETED','PCs_retired':len(self.retired),'families':len({o['family'] for o in self.native['instructions']}),'journal':self.journal,'checkpoint_revision':self.revision,'generation':self.generation,'physical_visibility_qualified':False,'hardware_or_clock_qualified':False}


def load_programs():
    native=json.load(gzip.open(ROOT/PROGRAM,'rt'));dispatch=json.load(gzip.open(ROOT/DISPATCH,'rt'))
    if sha(ROOT/PROGRAM)!=dispatch['source_program_sha256']:raise ValueError('full native source pin')
    for name,want in dispatch['source_sha256'].items():
        if sha(ROOT/name)!=want:raise ValueError('kernel/dispatch source pin '+name)
    for name,want in native['source_sha256'].items():
        if sha(ROOT/name)!=want:raise ValueError('native/provider source pin '+name)
    if (len(native['instructions']),len(native['coverage']['families']))!=(2213,30):raise ValueError('full DS scope required')
    resident=json.load(gzip.open(ROOT/native['residence_archive'],'rt'))
    return native,dispatch,resident['homes']


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--provider-module',type=Path);ap.add_argument('--provider-manifest',type=Path);ap.add_argument('--model-only',action='store_true');args=ap.parse_args()
    if args.out.exists():raise ValueError('fresh output required')
    args.out.mkdir(parents=True);record={'status':'IN_PROGRESS','physical_qualified':False,'hardware_builds':0}
    def close(): (args.out/'record.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    close()
    try:
        native,dispatch,homes=load_programs()
        model={'schema':'H3_DS_FULL_SOURCE_PROVIDER_EXECUTION_DRIVER_V1','PCs':2213,'families':30,'ranks':96,'SMs_per_rank':32,'workspace_bytes_per_rank':CAP,'AW':27,'source_program_sha256':sha(ROOT/PROGRAM),'dispatch_sha256':sha(ROOT/DISPATCH),'kernel_execution':'original primitive/forward fullK source kernels; CPU collector scheduling not GPU clock','scratch_binding':'provider.scratch_memory must map every native scratch read/write to allocated AW27 extent; no logical callback shortcut','provider_hooks':['workspace','read_views','scratch_memory','publish','release_views','retire_operation','release_version','drain'],'checkpoint_revision':'exact per immutable view, never merely nonempty','provider_costs':'positive declared provider tick costs and causal backing events; hardware costs not inferred','unified_model_admitted':False,'wall_or_FSIZE_caps':None,'hardware_builds':0,'source_sha256':{str(Path(__file__).relative_to(ROOT)):sha(__file__)}}
        (args.out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
        if args.model_only:record.update(status='PASS_FULL_SOURCE_DRIVER_MODEL_NO_PAYLOAD_EXECUTION',PCs=2213,families=30);close();return
        if args.provider_module is None or args.provider_manifest is None:raise ValueError('Kepler actual provider module and source-pinned manifest required; no synthetic fallback')
        manifest=json.loads(args.provider_manifest.read_text())
        if manifest['provider_module_sha256']!=sha(args.provider_module) or manifest['native_program_sha256']!=sha(ROOT/PROGRAM):raise ValueError('provider module/fullprogram pin')
        record.update(provider_manifest_sha256=sha(args.provider_manifest),provider_module_sha256=sha(args.provider_module));close()
        spec=importlib.util.spec_from_file_location('actual_source_provider',args.provider_module);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        provider=module.create_provider(manifest,native,dispatch,homes)
        record=TokenDriver(native,dispatch,provider,manifest['checkpoint_revision'],manifest['generation'],homes).run();close()
    except Exception as exc:
        record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(exc).__name__,reason=str(exc));close();raise
if __name__=='__main__':main()
