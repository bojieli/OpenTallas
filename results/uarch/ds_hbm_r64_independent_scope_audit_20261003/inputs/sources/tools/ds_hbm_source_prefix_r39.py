"""Actual source-native CPU prefix, real provider reads/publication/retirement.
Uses unchanged committed Machine live-range executor for PC0-9; PC10 uses
Sagan's committed 128-lane tiled group continuation. CPU-private SSA carries
no physical RF/shared transport claim. No golden callback, precomputed output,
retry or arbitrary host memory/time/file-size cap.
"""
import argparse,gzip,hashlib,importlib.util,importlib.machinery,json,math,os,resource,time
from pathlib import Path
import numpy as np
from h3_ds_connected_provider_r37 import ROOT,D,peer
from h3_ds_source_prefix_provider_r39 import create_prefix_provider
from ds_hbm_connected_prepare_r37 import load,sha
R=ROOT/'results/uarch/ds_hbm_source_prefix_r39_20261002'
SAGAN_SHA=''
def sagan():
    # Boot all peer imports from retained byte-pinned source snapshots.
    for name in ('h3_deepseek_full_token_driver','h4_c0_ds_tiled_continuation','h4_c0_ds_expected_outputs'):peer(name)
    path=R/'inputs/h4_c0_ds_native_execution.py.source';pins=load(R/'source_pins.json')
    if sha(path)!=pins['sagan_native_execution_sha256']:raise ValueError('committed Sagan execution source pin')
    spec=importlib.util.spec_from_file_location('Sagan_committed_r39',path,loader=importlib.machinery.SourceFileLoader('Sagan_committed_r39',str(path)));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def model(native,homes,stop):
    f=peer('h3_deepseek_streaming_linear').footprint;rows=[];req=0;maxhost=0
    for op in native['instructions'][:stop+1]:
        perop=0;maxwork=0;calls=0
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            rank=owned['rank'];buffers=owned.get('buffer_programs') or [dict(template=owned['template'])]
            for b in buffers:
                p=native['templates'][b['template']];z=f(p);work=z['typed_live_bytes']+z['transient_and_output_reserve_bytes'];maxwork=max(maxwork,work);maxhost=max(maxhost,work);calls+=1
                # Conservative actual input bound: all declared versioned/aux
                # words may touch separate sectors; physical translation not claimed.
                for name,v in p['providers'].items():
                    binding=op['provider_bindings'][b['template']][name]
                    if binding['kind'] in ('versioned_operand','explicit_auxiliary_provider'):
                        words=math.prod(v['shape'])*(2 if v['dtype']=='I64' else 1)
                        producers=96 if name=='parts' else 1
                        # _owned_payload restores full contiguous per-SM source
                        # fragments, <=32 partial tails per contributor.
                        perop+=math.ceil(words/8)+32*producers
            for w in op['writes']:
                for idx in w['home_indices']:
                    h=homes[idx]
                    if rank in h['rank_group']:
                        count=h['word_count'];perop+=3*math.ceil(count/8)+2*(count%8!=0)
        if op['pc']==10:
            # Exact 8group*64tile*8source*128lane worst addressed receiver words.
            perop+=96*64*8*128
        req+=perop;rows.append(dict(PC=op['pc'],family=op['family'],numeric_calls=calls,CPU_native_live_and_transient_bytes=maxwork,software_sector_request_conservative_bound=perop))
    if maxhost>33554432:raise ValueError('source native live-range prefix exceeds priced32MiB workspace')
    envelope=load(R/'journal_schema_envelope_r2.json')['selected_envelope_bytes']
    cap=131072+req*8*8*(envelope+64)+len(native['instructions'][:stop+1])*96*65536
    return dict(status='MODELLED_SOURCE_NATIVE_PREFIX',prefix_stop=stop,ops=rows,CPU_native_workspace_upper_bytes=maxhost,logical_workspace_bytes=33554432,AW=27,CPU_host_private_SSA=True,primitive_scratch_transport_qualified=False,
      sector_requests_conservative_bound=req,sector_events_per_request_bound=8,event_serialization_envelope_bytes=envelope,journal_capacity_bytes=cap,
      full_program_future_use_retained=True,model_latency_cycles=None,unknown_costs_not_zero=True,physical_clock_or_rate_qualified=False,full_token_GO=False)

def driver_class():
    base=sagan().NativeExecution;source=peer('h3_deepseek_full_token_driver');numeric=peer('h3_deepseek_complete_native')
    class Prefix(base):
        def run_buffer(self,op,owned,template,bindings,views,writes):
            if op['pc']>9:raise ValueError('PC10 must use original Sagan group continuation')
            p=self.native['templates'][template];rank=owned['rank']
            if set(views)!=set(p['providers']):raise ValueError('exact actual prefix LOAD set')
            inputs={n:source.validate_view(n,v,bindings[n],p['providers'][n],rank,self.generation,self.revision) for n,v in views.items()}
            vm=numeric.Machine(p,inputs,numeric.primitive_div);outputs=vm.run()
            if vm.fault or any(not np.all(np.isfinite(a)) for a in outputs.values()):raise ValueError('actual source numerical fault')
            for w in writes:
                view=w['native_result_binding'];data=outputs[view['result']]
                if 'flat_slice' in view:data=data.reshape(-1)[slice(*view['flat_slice'])]
                fields={'data':data,**{n:outputs[n] for n in op.get('compound_output_fields',{}).get(view['result'],[])}}
                identity=dict(PC=op['pc'],rank=rank,generation=self.generation,version=w['version'],home_indices=[i for i in w['home_indices'] if rank in self.homes[i]['rank_group']])
                receipt=self.provider.publish(identity,fields,view)
                source.publication_receipt(receipt,identity,{n:hashlib.sha256(a.tobytes()).hexdigest() for n,a in fields.items()})
            self.provider.release_views(op['pc'],rank,self.generation,views)
            self.journal.append(dict(PC=op['pc'],rank=rank,template=template,source_native_stages=len(p['code']),native_mode='unchanged_source_Machine_live_range_CPU_SSA',native_opcode_counts=dict(__import__('collections').Counter(i['op'] for i in p['code'])),published_versions=[w['version'] for w in writes],full_token_exact_qualified=False,physical_qualified=False))
    return Prefix

def main():
    a=argparse.ArgumentParser();a.add_argument('--stop',type=int,choices=(9,10),required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    if args.out.exists():raise ValueError('fresh invocation; no retry/fallback')
    args.out.mkdir();record=dict(status='INITIALIZING',pid=os.getpid(),start_ns=time.time_ns(),prefix_stop=args.stop,full_token_GO=False,hardware_qualified=False);provider=None
    def save():(args.out/'receipt.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    save()
    try:
        nativepath=Path('/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz');dispatchpath=Path('/tmp/kepler-ds-r34-provider-joined-sealed/dispatch.json.gz');native=load(nativepath);dispatch=load(dispatchpath);homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes'];manifest=load(D/'inputs/prefix_input_manifest.json.gz')
        if sha(nativepath)!=manifest['native_program_sha256'] or sha(dispatchpath)!=manifest['source_dispatch_sha256']:raise ValueError('exact actual source artifacts')
        priced=model(native,homes,args.stop);manifest.update(prefix_inputs_bound=True,prefix_GO=True,prefix_stop=args.stop,provider_module='tools/h3_ds_source_prefix_provider_r39.py',provider_module_sha256=sha(ROOT/'tools/h3_ds_source_prefix_provider_r39.py'),journal_root=str((args.out/'actual-prefix-journal').resolve()),journal_capacity_bytes=priced['journal_capacity_bytes'])
        free=os.statvfs(args.out).f_bavail*os.statvfs(args.out).f_frsize
        if free<priced['journal_capacity_bytes']:raise ValueError('source matched projection exceeds fresh available disk; no fixed cap substitute')
        (args.out/'model.json').write_text(json.dumps(priced,sort_keys=True,indent=2)+'\n');(args.out/'actual_manifest.json.gz').write_bytes(gzip.compress(json.dumps(manifest,sort_keys=True).encode(),mtime=0))
        soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE);resource.setrlimit(resource.RLIMIT_NOFILE,(hard,hard))
        provider=create_prefix_provider(manifest,native,dispatch,homes,args.stop);engine=driver_class()(native,dispatch,provider,manifest['checkpoint_revision'],manifest['generation'],homes,native_artifact_path=nativepath,dispatch_artifact_path=dispatchpath)
        record.update(status='RUNNING_ACTUAL_SOURCE_PREFIX',model=priced,disk_available_bytes=free,manifest_sha256=sha(args.out/'actual_manifest.json.gz'));save();record.update(engine.run(stop_after=args.stop));record['status']='PASS_SOURCE_NATIVE_PREFIX_RETIRED_UNCOMPARED'
        record.update(checkpoint_reads=provider.checkpoint.receipts,retained_versions=[dict(version=v,rank=r) for v,r in sorted(provider.locations)],retained_future_source_windows=len(provider.source_images),journal_bytes=provider.journal_budget.path.stat().st_size,aggregate_reserved_bytes=provider.journal_budget.used,full_token_exact_qualified=False,primitive_scratch_transport_qualified=False)
    except Exception as e:record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(e).__name__,reason=str(e));save();raise
    finally:
        if provider is not None:provider.journal_budget.db.commit()
        record.update(end_ns=time.time_ns(),max_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);save()
if __name__=='__main__':main()
