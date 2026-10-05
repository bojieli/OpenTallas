"""Opt-in full DS execution using retained numeric kernels and tiled groups.

Kepler owns provider construction/input GO. This driver never manufactures
activations, weights, query codes, append rows or completion receipts.
"""
import argparse,gzip,hashlib,importlib.util,json,os
from pathlib import Path
from h3_deepseek_full_token_driver import TokenDriver, publication_receipt
from h4_c0_ds_tiled_continuation import TiledContinuation
from h4_c0_group_operand_tiles import DISPATCH
from h4_c0_ds_source_views import canonical
from hbm_bound_event_journal_r30 import DiskEvents
from h4_c0_ds_expected_outputs import ObservedProvider
from h4_c0_ds_expected_outputs import ExpectedOutputs

class CallJournal:
    def __init__(self,budget,event):self.events=DiskEvents(budget);self.event=event
    def append(self,record):self.events.append(dict(event=self.event,record=record))
    def summary(self):return self.events.summary()

def journal_reference(value):
    return value.summary() if hasattr(value,'summary') else value

class NativeExecution(TokenDriver):
    def __init__(self,native,dispatch,provider,revision,generation,homes,*,native_artifact_path,dispatch_artifact_path,expected_outputs=None):
        raw=Path(dispatch_artifact_path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=DISPATCH or canonical(json.loads(gzip.decompress(raw)))!=canonical(dispatch):
            raise ValueError('exact corrected native dispatch artifact required')
        self.expected_outputs=expected_outputs
        if expected_outputs is not None:provider=ObservedProvider(provider,expected_outputs)
        super().__init__(native,dispatch,provider,revision,generation,homes)
        self.groups=TiledContinuation(provider,native_artifact_path=native_artifact_path)
        self.native_calls=CallJournal(provider.journal_budget,'C0_actual_native_group_call')
        self.journal=CallJournal(provider.journal_budget,'C0_actual_native_numeric_call')

    def execute_operation(self,op):
        if op['pc'] in self.retired:raise ValueError('already retired native operation; no duplicate')
        if any(dep not in self.retired for dep in op['dependencies']):
            raise ValueError('dependency before actual native source retirement')
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            rank=owned['rank']
            if op['pc'] in self.groups.plan.parents:
                if owned.get('buffer_programs') or len(op['writes'])!=1:
                    raise ValueError('exact single corrected group result required')
                write=op['writes'][0]
                indices=[i for i in write['home_indices'] if rank in self.homes[i]['rank_group']]
                identity=dict(PC=op['pc'],rank=rank,generation=self.generation,
                    version=write['version'],home_indices=indices)
                record=self.groups.run(op['pc'],rank,generation=self.generation,
                    identity=identity,source_store_view=write['native_result_binding'])
                publication_receipt(record['publication'],identity,
                    record['publication']['payload_sha256'])
                self.native_calls.append(record)
            else:
                views=self.provider.read_views(op,owned,self.generation)
                if owned.get('buffer_programs'):
                    buffers=owned['buffer_programs']
                    if set(views)!={b['write_version'] for b in buffers}:
                        raise ValueError('exact independent native buffer views required')
                    for b in buffers:
                        bindings={name:dict(value) for name,value in op['provider_bindings'][b['template']].items()}
                        for name,required in bindings.items():
                            if name=='parts':required.update(version=b['read_version'],additional_versions=[b['read_version']])
                            elif required['kind']=='explicit_auxiliary_provider':required['identity_from_versions']=[b['read_version']]
                        self.run_buffer(op,owned,b['template'],bindings,views[b['write_version']],
                            [w for w in op['writes'] if w['version']==b['write_version']])
                else:
                    # In particular compressor and index_q execute original
                    # numeric kernels, then run_buffer publishes their actual
                    # outputs/compound fields into unchanged r36 hooks.
                    self.run_buffer(op,owned,owned['template'],op['provider_bindings'][owned['template']],views,op['writes'])
        retired=self.provider.retire_operation(op['pc'],self.generation)
        if retired!=dict(PC=op['pc'],generation=self.generation,pending_obligations=0,source_consumers_released=True):
            raise ValueError('native root retirement before exact drain')
        self.retired.add(op['pc'])
        for read in op['reads']:
            if self.last_use[read['version']]==op['pc']:
                self.provider.release_version(read['version'],self.generation)

    def run(self,*,stop_after=None):
        if stop_after is not None and (type(stop_after)is not int or stop_after not in {o['pc'] for o in self.native['instructions']}):
            raise ValueError('exact source prefix boundary required')
        for op in self.native['instructions']:
            self.execute_operation(op)
            if stop_after==op['pc']:
                # Retain later-consumer versions. A prefix is not a full token.
                return dict(status='ACTUAL_NATIVE_PREFIX_RETIRED',last_PC=stop_after,
                    PCs_retired=sorted(self.retired),journal=journal_reference(self.journal),
                    group_calls=journal_reference(self.native_calls),full_token_qualified=False,hardware_qualified=False)
        drained=self.provider.drain(self.generation)
        if drained!=dict(generation=self.generation,pending_obligations=0,live_consumers=0):
            raise ValueError('native token before actual provider drain')
        comparison=self.expected_outputs.finish() if self.expected_outputs is not None else None
        return dict(status='FULL_SOURCE_NATIVE_SOFTWARE_TOKEN_EXACT_PASS' if comparison else 'FULL_SOURCE_NATIVE_SOFTWARE_EXECUTED_UNCOMPARED',
            PCs_retired=len(self.retired),families=len({o['family'] for o in self.native['instructions']}),
            journal=journal_reference(self.journal),group_calls=journal_reference(self.native_calls),checkpoint_revision=self.revision,
            generation=self.generation,numerical_comparison=comparison,
            full_token_exact_qualified=comparison is not None,hardware_qualified=False)

def main():
    """Source/GO-bound launcher. No time, AS, FSIZE, memory or swap caps."""
    parser=argparse.ArgumentParser()
    for name in ('native','dispatch','provider_module','manifest','homes','out'):
        parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--homes-sha256',required=True)
    parser.add_argument('--expected',type=Path)
    parser.add_argument('--prefix-stop',type=int)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('fresh actual execution/evidence directory required')
    args.out.mkdir(parents=True)
    record=dict(status='IN_PROGRESS',PID=os.getpid(),resource_caps_injected=False,hardware_qualified=False)
    def save():(args.out/'record.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    def load(path):
        raw=path.read_bytes();return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
    save()
    try:
        manifest=load(args.manifest)
        if args.prefix_stop is None:
            if manifest.get('full_token_inputs_bound') is not True or manifest.get('full_token_GO') is not True:
                raise ValueError('Kepler actual full input GO required; no metadata/synthetic fallback')
        elif not (manifest.get('prefix_inputs_bound') is True and manifest.get('prefix_GO') is True and manifest.get('prefix_stop')==args.prefix_stop):
            raise ValueError('Kepler source-bound prefix input GO required; final references not required for prefix')
        native_sha=hashlib.sha256(args.native.read_bytes()).hexdigest()
        module_sha=hashlib.sha256(args.provider_module.read_bytes()).hexdigest()
        homes_sha=hashlib.sha256(args.homes.read_bytes()).hexdigest()
        if native_sha!=manifest['native_program_sha256'] or module_sha!=manifest['provider_module_sha256'] or homes_sha!=args.homes_sha256:
            raise ValueError('actual native/provider/home source pin')
        if args.prefix_stop is None and args.expected is None:
            raise ValueError('full numerical execution requires independently committed expected logits/token')
        native=load(args.native);dispatch=load(args.dispatch);homes=load(args.homes)
        if isinstance(homes,dict):homes=homes['homes']
        record.update(native_sha256=native_sha,provider_module_sha256=module_sha,homes_sha256=homes_sha,
            input_manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),prefix_stop=args.prefix_stop)
        save()
        spec=importlib.util.spec_from_file_location('actual_ds_native_provider',args.provider_module)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        if args.prefix_stop is None:provider=module.create_provider(manifest,native,dispatch,homes)
        else:
            factory=getattr(module,'create_prefix_provider',None)
            if not callable(factory):raise ValueError('Kepler reviewed prefix constructor required')
            provider=factory(manifest,native,dispatch,homes,args.prefix_stop)
        witness=None
        if args.expected is not None:
            witness=ExpectedOutputs(args.expected,native_sha256=native_sha,
                checkpoint_revision=manifest['checkpoint_revision'],generation=manifest['generation'],
                input_manifest_sha256=record['input_manifest_sha256'],native=native,journal_budget=provider.journal_budget)
        driver=NativeExecution(native,dispatch,provider,manifest['checkpoint_revision'],manifest['generation'],homes,
            native_artifact_path=args.native,dispatch_artifact_path=args.dispatch,expected_outputs=witness)
        record.update(driver.run(stop_after=args.prefix_stop));save()
    except Exception as exc:
        record.update(status='FAIL_CLOSED_PRESERVED',exception_type=type(exc).__name__,reason=str(exc));save();raise

if __name__=='__main__':main()
