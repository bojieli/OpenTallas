"""Publish independently reviewed PC0 outputs without repeating arithmetic."""
import gzip,hashlib,json,os
from pathlib import Path
import numpy as np
from h3_ds_checkpoint_provider_r30 import Provider,JournalBudget
from h3_ds_query_provider_r36 import SizedRF
from h3_deepseek_full_token_driver import publication_receipt
from h4_c0_group_operand_tiles import NATIVE
from h4_c0_provider_movement import prove_sector_span

def publish(native_path,comparison_path,record_path,outputs_path,source_root,out):
    out=Path(out)
    if out.exists():raise ValueError('fresh publication owner/evidence required')
    out.mkdir(parents=True)
    result=dict(status='IN_PROGRESS',PID=os.getpid(),native_arithmetic_reexecuted=False,
        production_group_calls_closed=0,full_token_qualified=False,hardware_qualified=False)
    def save():(out/'record.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    save()
    try:
        comparison=json.loads(Path(comparison_path).read_bytes())
        if comparison['status']!='PASS_PC0_GOLDEN_EXACT' or comparison['elements_compared']!=20504 or comparison['provider_publication'] or comparison['rank']!=0 or comparison['PC']!=0:
            raise ValueError('exact independently reviewed PC0 arithmetic gate required')
        pinned=comparison['independently_bound_sources_and_inputs']
        for path in (record_path,outputs_path):
            actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if pinned.get(str(Path(path).resolve()))!=actual:raise ValueError('reviewed PC0 source/outputs changed')
        numeric=json.loads(Path(record_path).read_bytes());raw=Path(native_path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=NATIVE or numeric['native_sha256']!=NATIVE:raise ValueError('current c65 native pin')
        native=json.loads(gzip.decompress(raw));op=native['instructions'][0]
        home_path=Path(source_root)/native['residence_archive'];home_raw=home_path.read_bytes();homes=json.loads(gzip.decompress(home_raw))['homes']
        values=np.load(outputs_path,allow_pickle=False)
        budget=JournalBudget(out/'actual-journal',512<<20)
        p=Provider.__new__(Provider);p.__dict__.update(native=native,homes=homes,generation=1,published={},views={},locations={},rf=SizedRF({}),state={},seq=0,trace=[],journal_budget=budget)
        source={'reviewed_source':dict(version='DeepSeek.-1.h.0',leased_versions=['DeepSeek.-1.h.0'],provenance_certified=True)}
        p.views[0,0,1,id(source)]=source
        receipts=[];phase_counts={}
        for w in op['writes']:
            field=w['native_result_binding']['result'];a=values[field];expected=comparison['results'][field]
            if list(a.shape)!=expected['shape'] or a.dtype!=np.float32 or expected['mismatches'] or hashlib.sha256(a.tobytes()).hexdigest()!=expected['golden_sha256']:
                raise ValueError('reviewed numerical output bit identity '+field)
            indices=[i for i in w['home_indices'] if 0 in homes[i]['rank_group']]
            if not indices or any(homes[i]['version']!=w['version'] for i in indices):raise ValueError('source-bound PC0 RF homes')
            identity=dict(PC=0,rank=0,generation=1,version=w['version'],home_indices=indices)
            engine=p.rf.get(0);start=len(engine.events) if engine else 0
            receipt=p.publish(identity,{'data':a},w['native_result_binding'])
            publication_receipt(receipt,identity,{'data':expected['golden_sha256']})
            engine=p.rf[0];end=len(engine.events)
            transactions=prove_sector_span(engine.events[start:end],model='DeepSeek',rank=0,PC=0,generation=1)
            receipts.append(dict(field=field,publication=receipt,journal_id=engine.events.id,start=start,end=end,sector_transactions=len(transactions)))
        engine=p.rf[0]
        if engine.live or engine.queue or engine.calendar or engine.resident:raise ValueError('publication reverse debt')
        p.release_views(0,0,1,source)
        summary=engine.events.summary();phase_counts=dict(summary['event_counts'])
        budget.db.commit();journal=budget.path.read_bytes();(out/'events.sqlite.gz').write_bytes(gzip.compress(journal,mtime=0))
        result.update(status='PASS_REVIEWED_REAL_PC0_OUTPUTS_RF_PUBLICATION',
            parent_comparison_sha256=hashlib.sha256(Path(comparison_path).read_bytes()).hexdigest(),
            native_artifact_sha256=NATIVE,home_archive_sha256=hashlib.sha256(home_raw).hexdigest(),
            input_record_sha256=hashlib.sha256(Path(record_path).read_bytes()).hexdigest(),
            output_npz_sha256=hashlib.sha256(Path(outputs_path).read_bytes()).hexdigest(),
            receipts=receipts,source_lease_released=True,RF_mirrored_readback_and_reverse_drained=True,
            phase_counts=phase_counts,total_events=len(engine.events),journal_sqlite_bytes=len(journal),
            journal_uncompressed_sha256=hashlib.sha256(journal).hexdigest(),
            declared_journal_reservation_bytes=512<<20,actual_journal_reserved_bytes=budget.used,
            resource_caps_injected=False,publication_calls_completed=4,rank0_PC0_only=True,
            primitive_intermediate_movement_qualified=False)
        budget.db.close();values.close();save();return result
    except Exception as exc:
        result.update(status='FAIL_PRESERVED',exception_type=type(exc).__name__,reason=str(exc));save();raise
