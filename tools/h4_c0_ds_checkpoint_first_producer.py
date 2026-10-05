"""Execute actual first native producer from released checkpoint inputs.

This small arithmetic gate is not a provider-backed full-token run. No family
golden callback, invented activation, or precomputed native output is used.
"""
import gzip,hashlib,json
from pathlib import Path
import numpy as np
from h3_ds_checkpoint_provider_r30 import LockedCheckpoint,Provider,JournalBudget
from h3_deepseek_complete_native import Machine,primitive_div
from h3_deepseek_staged_native import plan
from h4_c0_group_operand_tiles import NATIVE
from h4_c0_provider_movement import prove_sector_span
from h3_deepseek_full_token_driver import publication_receipt

def execute(native_path,manifest_path,out,*,publish=False,source_root=None):
    out=Path(out)
    if out.exists():raise ValueError('fresh evidence directory required')
    out.mkdir(parents=True)
    record=dict(status='IN_PROGRESS',production_group_calls_closed=0,hardware_qualified=False,full_token_qualified=False)
    def save():(out/'record.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    save()
    try:
        raw=Path(native_path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=NATIVE:raise ValueError('exact c65 native artifact')
        native=json.loads(gzip.decompress(raw));op=native['instructions'][0]
        if (op['pc'],op['family'],op['dependencies'])!=(0,'hc_mixes',[]):raise ValueError('actual dependency-free first native producer')
        owned=next(r for r in op['rank_bindings'] if r['rank']==0);tid=owned['template'];program=native['templates'][tid]
        model=plan(program)
        if not model['fits']:raise ValueError('source native live-range model does not fit')
        manifest=json.loads(Path(manifest_path).read_bytes());recipe=manifest['checkpoint_initial_embedding']
        source=Path(recipe['initializer_source']).read_bytes();history=Path(recipe['token_history_source']).read_bytes()
        if hashlib.sha256(source).hexdigest()!=native['source_sha256']['tools/w19_hbm_tp96_isa.py'] or hashlib.sha256(source).hexdigest()!=recipe['initializer_sha256'] or hashlib.sha256(history).hexdigest()!=recipe['token_history_sha256']:
            raise ValueError('exact source initializer/token history binding')
        if recipe['version']!='DeepSeek.-1.h.0' or recipe['planes']!=4 or 0 not in recipe['ranks']:
            raise ValueError('actual four-plane initial embedding identity')
        ck=LockedCheckpoint(manifest['checkpoint_path'],manifest['checkpoint_revision'],manifest['checkpoint_index_sha256'])
        token=json.loads(history)['token_history'][-1];embedding,dtype=ck.tensor('embed.weight',rows=[token,token+1])
        if dtype!='BF16' or embedding.shape!=(1,5120):raise ValueError('actual released embedding codec/shape')
        inputs={};bindings=op['provider_bindings'][tid]
        for name,b in bindings.items():
            if name=='h':
                if b['version']!=recipe['version']:raise ValueError('native initial h version')
                value=np.repeat(embedding,4,axis=0)
            elif b['kind']=='immutable_parameter_provider':
                value,dt=ck.tensor(b['logical_tensor'])
                if dt not in ('BF16','F32'):raise ValueError('actual HC parameter codec')
            else:raise ValueError('unbound actual first producer input '+name)
            spec=program['providers'][name]
            if list(value.shape)!=spec['shape'] or value.dtype!=np.float32:raise ValueError('actual native typed input '+name)
            inputs[name]=value
        vm=Machine(program,inputs,primitive_div);outputs=vm.run()
        if vm.fault or any(not np.all(np.isfinite(a)) for a in outputs.values()):raise ValueError('actual native numerical fault')
        np.savez(out/'native_outputs.npz',**outputs)
        record.update(status='PASS_ACTUAL_RELEASED_CHECKPOINT_PC0_NATIVE_ARITHMETIC',
            PC=0,rank=0,template=tid,native_sha256=NATIVE,checkpoint_revision=manifest['checkpoint_revision'],
            checkpoint_reads=ck.receipts,source_initializer_sha256=hashlib.sha256(source).hexdigest(),token_history_sha256=hashlib.sha256(history).hexdigest(),
            inputs={n:dict(shape=list(a.shape),sha256=hashlib.sha256(a.tobytes()).hexdigest()) for n,a in inputs.items()},
            outputs={n:dict(shape=list(a.shape),sha256=hashlib.sha256(a.tobytes()).hexdigest()) for n,a in outputs.items()},
            model=model,source_instructions=len(program['code']),provider_publication=False,
            actual_provider_forward_prefix_still_required=True)
        if publish:
            if source_root is None:raise ValueError('source-pinned actual home archive required')
            home_path=Path(source_root)/native['residence_archive'];home_raw=home_path.read_bytes()
            homes=json.loads(gzip.decompress(home_raw))['homes']
            budget=JournalBudget(out/'actual-publication-journal',512<<20)
            provider=Provider.__new__(Provider)
            provider.__dict__.update(native=native,homes=homes,generation=manifest['generation'],
                published={},views={},locations={},rf={},state={},seq=0,trace=[],journal_budget=budget)
            lease={name:dict(version=b.get('version'),leased_versions=[b['version']] if b.get('version') else [],provenance_certified=True)
                for name,b in bindings.items()}
            provider.views[0,0,provider.generation,id(lease)]=lease
            receipts=[]
            for write in op['writes']:
                indices=[i for i in write['home_indices'] if 0 in homes[i]['rank_group']]
                if not indices or any(homes[i]['version']!=write['version'] for i in indices):raise ValueError('actual producer home/version/rank')
                value=outputs[write['native_result_binding']['result']]
                identity=dict(PC=0,rank=0,generation=provider.generation,version=write['version'],home_indices=indices)
                engine=provider.rf.get(0);start=len(engine.events) if engine is not None else 0
                receipt=provider.publish(identity,{'data':value},write['native_result_binding'])
                publication_receipt(receipt,identity,{'data':hashlib.sha256(value.tobytes()).hexdigest()})
                engine=provider.rf[0];end=len(engine.events)
                transactions=prove_sector_span(engine.events[start:end],model='DeepSeek',rank=0,PC=0,generation=provider.generation)
                receipts.append(dict(publication=receipt,journal_id=engine.events.id,start=start,end=end,transactions=len(transactions),hardware_qualified=False))
            engine=provider.rf[0]
            if engine.live or engine.queue or engine.calendar or engine.resident:raise ValueError('actual producer reverse debt')
            provider.release_views(0,0,provider.generation,lease)
            budget.db.commit();journal=budget.path.read_bytes()
            (out/'actual-publication-journal.sqlite.gz').write_bytes(gzip.compress(journal,mtime=0))
            record.update(status='PASS_ACTUAL_CHECKPOINT_PC0_NATIVE_AND_RF_PUBLICATION',
                provider_publication=True,publication_receipts=receipts,source_input_lease_released=True,
                home_archive_sha256=hashlib.sha256(home_raw).hexdigest(),home_archive_path=str(home_path),
                publication_journal_uncompressed_sha256=hashlib.sha256(journal).hexdigest(),
                publication_journal_budget_bytes=512<<20,production_group_calls_closed=0,
                numerical_source_calls_executed=1,rank0_outputs_mirrored_and_readback=True,
                primitive_intermediate_movement_qualified=False)
            budget.db.close()
        save();return record
    except Exception as exc:
        record.update(status='FAIL_PRESERVED',exception_type=type(exc).__name__,reason=str(exc));save();raise
