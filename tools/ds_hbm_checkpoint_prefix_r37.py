"""Opt-in PC0 CPU-native fusion and actual 96-rank addressed publication.

Not a fallback: chosen and modelled before launch. Original source Machine and
rounding execute each rank; no golden callback or precomputed native output.
Sagan's retirement/last-use loop is retained. Primitive intermediate arrays are
host SSA, NOT a measured physical RF/shared/HBM transport implementation.
The staged per-primitive transport cost is retained separately as a refusal.
"""
import argparse,gzip,hashlib,json,math,os,time,resource
from pathlib import Path
import numpy as np
from h3_ds_connected_provider_r37 import ROOT,D,peer,composed_class
from ds_hbm_connected_prepare_r37 import load,sha
from hbm_bound_event_journal_r30 import DiskEvents

def model(native,homes):
    op=native['instructions'][0]
    if (op['pc'],op['family'],op['dependencies'])!=(0,'hc_mixes',[]):raise ValueError('exact first source producer')
    if sorted(r['rank'] for r in op['rank_bindings'])!=list(range(96)) or len({r['template'] for r in op['rank_bindings']})!=1:raise ValueError('actual complete 96-rank source producer')
    p=native['templates'][op['rank_bindings'][0]['template']];sizes={};sectors=0;fragments=0
    for i in p['code']:
        for v in i['src']:sectors+=math.ceil(sizes[v]/32);fragments+=math.ceil(sizes[v]/512)
        sizes[i['dst']]=math.prod(i['shape'])*(8 if i.get('attrs',{}).get('dtype')=='I64' else 4)
        sectors+=math.ceil(sizes[i['dst']]/32);fragments+=math.ceil(sizes[i['dst']]/512)
    for v in p['outputs'].values():sectors+=math.ceil(sizes[v]/32);fragments+=math.ceil(sizes[v]/512)
    req=0
    for w in op['writes']:
        indices=[i for i in w['home_indices'] if 0 in homes[i]['rank_group']]
        for i in indices:
            n=homes[i]['word_count'];req+=3*math.ceil(n/8)+2*(n%8!=0)
    # All normal transactions log <=8 events. 2048B is a conservative schema
    # envelope checked against every actual serialized sector event at terminal.
    events=req*96*8;cap=131072+events*8*(2048+64)+(96*4096*8)
    return dict(status='MODELLED_PC0_SOURCE_NATIVE_FUSION_AND_ACTUAL_PUBLICATION',stop_after=0,ranks=96,
      staged_source_plan=peer('h3_deepseek_staged_native').plan(p),
      staged_scratch_sector_requests_per_rank=sectors,staged_scratch_sector_requests_all_ranks=sectors*96,
      staged_scratch_512B_fragments_per_rank=fragments,staged_transport_8GiB_journal_admission=False,
      CPU_SSA_declared_destination_bytes=sum(sizes.values()),native_source_stages=len(p['code']),
      publication_sector_request_bound_per_rank=req,publication_sector_event_bound=events,
      max_sector_event_serialized_bytes=2048,journal_capacity_bytes=cap,
      CPU_execution_threads=1,primitive_scratch_sector_transport_qualified=False,
      actual_output_RF_mirrors=2,publication_readback_mirrors=1,
      full_program_future_use_retained=True,physical_address_translation_qualified=False,
      hardware_qualified=False,full_token_GO=False,latency_cycles=None)

def driver_class(expected):
    source=peer('h3_deepseek_full_token_driver');base=peer('h4_c0_ds_native_execution').NativeExecution
    numeric=peer('h3_deepseek_complete_native')
    class Prefix(base):
        def run_buffer(self,op,owned,template,bindings,views,writes):
            if op['pc']!=0 or op['family']!='hc_mixes':raise ValueError('admitted PC0 source fusion boundary')
            program=self.native['templates'][template];rank=owned['rank']
            if set(views)!=set(program['providers']):raise ValueError('complete actual LOAD views')
            inputs={name:source.validate_view(name,v,bindings[name],program['providers'][name],rank,self.generation,self.revision) for name,v in views.items()}
            for name,a in inputs.items():
                want=expected['input_hashes'][name]
                if list(a.shape)!=want['shape'] or hashlib.sha256(a.tobytes()).hexdigest()!=want['sha256']:raise ValueError('independent golden input binding '+name)
            vm=numeric.Machine(program,inputs,numeric.primitive_div);outputs=vm.run()
            if vm.fault or any(not np.all(np.isfinite(a)) for a in outputs.values()):raise ValueError('native first producer numerical fault')
            comparisons=[]
            for write in writes:
                view=write['native_result_binding'];data=outputs[view['result']]
                if 'flat_slice' in view:data=data.reshape(-1)[slice(*view['flat_slice'])]
                indices=[i for i in write['home_indices'] if rank in self.homes[i]['rank_group']]
                identity=dict(PC=0,rank=rank,generation=self.generation,version=write['version'],home_indices=indices)
                receipt=self.provider.publish(identity,{'data':data},view)
                digest=hashlib.sha256(data.tobytes()).hexdigest();source.publication_receipt(receipt,identity,{'data':digest})
                reference=expected['results'][view['result']]
                exact=list(data.shape)==reference['shape'] and digest==reference['golden_sha256']
                self.journal.append(dict(event='independent_PC0_golden_comparison_after_actual_publication',identity=identity,result=view['result'],observed_sha256=digest,expected_sha256=reference['golden_sha256'],exact=exact,publication=receipt))
                if not exact:raise ValueError('actual published native output differs from parent independent golden')
                comparisons.append(view['result'])
            self.provider.release_views(0,rank,self.generation,views)
            self.journal.append(dict(PC=0,rank=rank,template=template,source_native_stages=len(program['code']),native_mode='original_Machine_host_SSA_no_primitive_transport_credit',compared_results=comparisons))
    return Prefix

def main():
    p=argparse.ArgumentParser()
    for n in ('native','dispatch','homes','manifest','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh prefix output required')
    a.out.mkdir();record=dict(status='PREPARING',full_token_GO=False,hardware_qualified=False,pid=os.getpid(),start_ns=time.time_ns())
    def save():(a.out/'receipt.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    save();provider=None
    try:
        native=load(a.native);dispatch=load(a.dispatch);manifest=load(a.manifest);homes=load(a.homes)['homes']
        if sha(a.native)!=manifest['native_program_sha256'] or sha(a.dispatch)!=manifest['source_dispatch_sha256']:raise ValueError('prefix exact program/source dispatch')
        if any(manifest.get(k) for k in ('full_token_GO','full_token_inputs_bound','full_token_launch_ready','hardware_admitted')):raise ValueError('prefix must not borrow full-token/hardware GO')
        priced=model(native,homes);(a.out/'model.json').write_text(json.dumps(priced,sort_keys=True,indent=2)+'\n')
        parent=load(D/'inputs/parent_PC0_independent_golden.json')
        first=load(D/'inputs/Sagan_PC0_input_receipt.json')
        if parent['status']!='PASS_PC0_GOLDEN_EXACT' or first['native_sha256']!=sha(a.native) or first['checkpoint_revision']!=manifest['checkpoint_revision']:raise ValueError('source-bound parent arithmetic comparison')
        for name,result in parent['results'].items():
            if result['native_sha256']!=first['outputs'][name]['sha256']:raise ValueError('independent reference/output join')
        expected=dict(results=parent['results'],input_hashes=first['inputs'])
        manifest['journal_root']=str((a.out/'actual-prefix-journal').resolve());manifest['journal_capacity_bytes']=priced['journal_capacity_bytes']
        manifest['prefix_admission']=dict(stop_after=0,ranks=list(range(96)),scope=priced['status'],full_token_GO=False)
        (a.out/'actual_manifest.json.gz').write_bytes(gzip.compress(json.dumps(manifest,sort_keys=True).encode(),mtime=0))
        free=os.statvfs(a.out).f_bavail*os.statvfs(a.out).f_frsize
        if free<priced['journal_capacity_bytes']:raise ValueError('actual free disk below model-derived journal allowance')
        record.update(status='INITIALIZING_ACTUAL_PROVIDER',source_pins=dict(native=sha(a.native),dispatch=sha(a.dispatch),homes=sha(a.homes),manifest=sha(a.out/'actual_manifest.json.gz')),disk_available_bytes=free,model=priced);save()
        provider=composed_class()(manifest,native,dispatch,homes)
        engine=driver_class(expected)(native,dispatch,provider,manifest['checkpoint_revision'],manifest['generation'],homes,native_artifact_path=a.native,dispatch_artifact_path=a.dispatch)
        record['status']='RUNNING_ACTUAL_96_RANK_PC0_PREFIX';save()
        terminal=engine.run(stop_after=0)
        if terminal['PCs_retired']!=[0] or provider.views:raise ValueError('actual prefix retirement/live reader debt')
        summaries=[]
        for rank,rf in sorted(provider.rf.items()):
            if rf.live or rf.queue or rf.calendar or rf.resident:raise ValueError('actual RF accepted reverse debt')
            summaries.append(dict(rank=rank,journal=rf.events.summary()))
        if [s['rank'] for s in summaries]!=list(range(96)):raise ValueError('actual96rank publication coverage')
        max_event=0;event_counts={}
        for value, in provider.journal_budget.db.execute('select value from event'):
            import zlib
            raw=zlib.decompress(value);row=json.loads(raw)
            if 'identity' in row and 'stack' in row:max_event=max(max_event,len(raw))
            name=row['event'];event_counts[name]=event_counts.get(name,0)+1
        if max_event>priced['max_sector_event_serialized_bytes']:raise ValueError('schema journal model envelope exceeded')
        record.update(status='PASS_ACTUAL_96_RANK_PC0_NATIVE_PUBLICATION_AND_GOLDEN',terminal=terminal,RF_journals=summaries,retained_versions=[dict(version=v,rank=r) for v,r in sorted(provider.locations)],checkpoint_reads=provider.checkpoint.receipts,event_counts=event_counts,max_sector_event_serialized_bytes=max_event,journal_bytes=provider.journal_budget.path.stat().st_size,aggregate_reserved_bytes=provider.journal_budget.used,primitive_scratch_transport_qualified=False)
    except Exception as exc:
        record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(exc).__name__,reason=str(exc));save();raise
    finally:
        if provider is not None:provider.journal_budget.db.commit()
        record.update(end_ns=time.time_ns(),max_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save()
if __name__=='__main__':main()
