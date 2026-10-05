"""Additive r33 source-bound C0 join; original native/catalog stay immutable.

Validates the exact reviewed lowered byte artifacts and regenerates source leaf
bindings with Dewey's ORIGINAL compiler. Does not reprice a calendar, accept a
provider GO, or claim full-program movement/hardware qualification.
"""
import ast, collections, functools, gzip, hashlib, json, math, pathlib
from h4_c0_model import pinned
from h4_c0_ordered_movement import strict_api
from h4_c0_bridge import NativeDecoder
from h4_c0_parent_provider_join import ParentProviderJoin,DEWEY,forward_builders,_PinnedPath

R33='433ccff91c9ed6f0e61761bdbffa11f4878d6339'
BASE='results/uarch/ds_hbm_window_retirement_r33_20261002/'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def unpack(raw):return json.loads(gzip.decompress(raw))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

@functools.lru_cache(maxsize=1)
def compiler():
    names={'positive','ceil','native_value_specs','compile_ds_forward_leaf_catalog','compile_ds_forward_parent_interface','compile_g0_source_interface'}
    raw=pinned('tools/h3_complete_native_calendar.py',DEWEY)
    body=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(body)!=len(names):raise ValueError('original Dewey source compiler closure missing')
    ns=dict(math=math,hashlib=hashlib,json=json,Counter=collections.Counter,defaultdict=collections.defaultdict,
        ROOT=_PinnedPath(),OUT='results/uarch/h3_complete_native_calendar_20261002',read_json=lambda path:json.loads(path.read_bytes()))
    exec(compile(ast.Module(body=body,type_ignores=[]),'Dewey-original-r33-catalog-compiler','exec'),ns)
    return ns

class R33SourceJoin(ParentProviderJoin):
    def __init__(self,bundle):
        bundle=pathlib.Path(bundle)
        bridge=json.loads(pinned(BASE+'bridge.json',R33))
        nr=(bundle/'lowered_native.json.gz').read_bytes();dr=(bundle/'lowered_dispatch.json.gz').read_bytes()
        if sha(nr)!=bridge['lowered_native_sha256'] or sha(dr)!=bridge['lowered_dispatch_sha256']:raise ValueError('exact reviewed r33 lowered native/dispatch byte hashes required; old source rejected')
        native=unpack(nr);dispatch=unpack(dr)
        if dispatch['source_program_sha256']!=sha(nr):raise ValueError('r33 dispatch/source mismatch')
        self.r33_bridge=bridge;self.r33_bundle=bundle;self.r33_inputs=dict(native=sha(nr),dispatch=sha(dr))
        super().__init__()
        original_native=self.d;original_catalog=self.catalog
        witnesses=bridge['window_template_joins'];changed={w['PC'] for w in witnesses}
        if len(changed)!=40 or len(native['instructions'])!=2213:raise ValueError('exact40PC successor/whole2213PC scope required')
        for pc,(old,new) in enumerate(zip(original_native['instructions'],native['instructions'])):
            if pc not in changed and old!=new:raise ValueError('r33 changed an unrelated source PC')
            if (old['pc'],old['family'],old['dependencies'],old['reads'],old['writes'])!=(new['pc'],new['family'],new['dependencies'],new['reads'],new['writes']):raise ValueError('r33 source PC/version/dependency contract changed')
        for row in witnesses:
            pc=row['PC'];key=row['new_template'];template=native['templates'][key]
            old=row['old_template'];op=native['instructions'][pc]
            if key==old or any(b.get('template')==old for b in op['rank_bindings']):raise ValueError('old128 template alias retained in changed PC')
            load=next(n for n in template['code'] if n['op']=='LOAD' and n['attrs'].get('name')=='window')
            sl=next(n for n in template['code'] if n['op']=='SLICE' and n['src']==[load['dst']])
            if load['shape']!=[127,512] or sl['attrs']['start']!=0 or template['providers']['window']['shape']!=[127,512]:raise ValueError('actual127 LOAD/drop0 source shape required')
            for bindings in op['provider_bindings'].values():
                view=bindings['window']
                if view['window_representation']!='pretrimmed127' or view['window_position']!=1048575 or view['version']!=row['input_version']:raise ValueError('actual r33 source window view required')
        initial=json.loads((bundle/'initial_window_homes.json').read_bytes())
        expected_initial=unpack(pinned(BASE+'initial_window_homes.json.gz',R33))
        if initial!=expected_initial:raise ValueError('exact committed r33 initial home directory required')
        self.initial_homes=initial
        self.initial_index={(h['PC_first_consumer'],h['rank']):h for h in initial['rows']}
        for row in witnesses:
            op=native['instructions'][row['PC']]
            for rank in [b['rank'] for b in op['rank_bindings'] if not b.get('empty_owned_extent')]:
                home=self.initial_index[row['PC'],rank]
                if home['version']!=row['input_version'] or home['shape']!=[127,512] or home['bytes']!=127*512*4 or home['representation']!='pretrimmed127':raise ValueError('initial home typed window/version mismatch')
        self.rope_bindings=json.loads((bundle/'rope_bindings.json').read_bytes())
        expected_rope=unpack(pinned(BASE+'source_owned_rope_bindings.json.gz',R33))
        if set(self.rope_bindings)!=set(expected_rope):raise ValueError('all264 source RoPE typed views required')
        for key,view in self.rope_bindings.items():
            # Fresh directories differ. Immutable bytes and every source field do not.
            expected=expected_rope[key]
            if {k:v for k,v in view.items() if k!='path'}!={k:v for k,v in expected.items() if k!='path'}:raise ValueError('r33 RoPE source view contract mismatch')
            if sha(pathlib.Path(view['path']).read_bytes())!=view['sha256']:raise ValueError('r33 immutable RoPE payload mismatch')
        api=compiler();N,S=forward_builders()
        self.d=native;self.dispatch=dispatch;self.programs['DeepSeek']=native['instructions']
        self.catalog=api['compile_ds_forward_leaf_catalog'](dispatch,native,N,S)
        # Original compiler stores staged template refs at the original canonical
        # path. Rebind those refs to the exact accepted successor blob, not old IDs.
        for leaf in self.catalog['leaves'].values():
            if leaf['source_builder']=='retained_original_template':
                leaf['original_dewey_program_ref']=leaf['program_ref']
                leaf['program_ref']='sha256:'+sha(nr)+'#/templates/'+leaf['source_builder_args'][0]
        self.parent_interface=api['compile_ds_forward_parent_interface'](self.catalog,native,self.residence)
        self.g0=api['compile_g0_source_interface'](self.q,self.catalog)
        self.PC_catalog['DeepSeek']={row['pc']:row for row in self.g0['DeepSeek']['PC_bindings']}
        self.source_hashes['DeepSeek']=sha(nr);self.decoder=NativeDecoder(self.q,native,self.residence)
        self.count_delta={op:self.catalog['native_scalars'].get(op,0)-original_catalog['native_scalars'].get(op,0) for op in set(self.catalog['native_scalars'])|set(original_catalog['native_scalars'])}
        self.count_delta={op:n for op,n in self.count_delta.items() if n}
        self.batch_delta={op:self.catalog['native_batches128'].get(op,0)-original_catalog['native_batches128'].get(op,0) for op in set(self.catalog['native_batches128'])|set(original_catalog['native_batches128'])}
        self.batch_delta={op:n for op,n in self.batch_delta.items() if n}
        self.catalog_digest=sha(canonical(self.catalog));self.calendar_admitted=False
    def bind_DS_forward_operand(self,context,reference,*,streaming_builder=None):
        # Source-order window templates are retained leaves, not forward-builder
        # leaves. Bind their NEW source bytes through the same strict resolver.
        expected=self.context('DeepSeek',context['PC'],context['rank'],context['SM'],context['generation'])
        if context!=expected:raise ValueError('r33 source parent context changed')
        tid=reference.get('parent_template');ci=reference.get('call_index')
        row=self.catalog['PC_bindings'][context['PC']]
        if not any(b['rank']==context['rank'] and b['template']==tid for b in row['bindings']):raise ValueError('r33 source PC/rank/new template required; old template rejected')
        if tid not in self.catalog['templates']:raise ValueError('r33 template missing')
        calls=self.catalog['templates'][tid]['calls']
        if type(ci)!=int or not 0<=ci<len(calls):raise ValueError('actual r33 leaf call index required')
        call=calls[ci]
        if reference.get('template')!=call['leaf']:raise ValueError('actual r33 leaf hash mismatch')
        leaf=self.catalog['leaves'][call['leaf']]
        if leaf['source_builder']!='retained_original_template':
            return super().bind_DS_forward_operand(context,reference,streaming_builder=streaming_builder)
        if reference.get('invocation_index')!=0 or reference.get('source_parameters',{}):raise ValueError('retained r33 source leaf has one invocation')
        ref=dict(reference,template=tid)
        return strict_api().resolve_ds_movement_reference(self.d,tid,ref)

    def bind_current_provider(self,provider,dispatch):
        """Bind source metadata BEFORE any actual provider read/phase starts.

        This does not execute/qualify a provider or inspect checkpoint payloads.
        Passing source identity cannot supply missing initial histories or ACKs.
        """
        source=pathlib.Path(provider.retire_operation.__func__.__code__.co_filename)
        expected=pinned('tools/h3_ds_checkpoint_provider_r33.py',R33)
        if not source.is_file() or source.read_bytes()!=expected:raise ValueError('actual integrated r33 provider source bytes required')
        if provider.native!=self.d or dispatch!=self.dispatch:raise ValueError('r33 provider cannot bind old128 native/dispatch to successor join')
        if provider.generation!=1:raise ValueError('current source-owned initial views bind generation1; successor generation needs explicit source directory')
        return dict(provider_source_sha256=sha(expected),native_sha256=self.r33_inputs['native'],dispatch_sha256=self.r33_inputs['dispatch'],
            source_identity_bound=True,initial_payloads_verified=False,actual_provider_phase_executed=False,hardware_qualified=False)

    def validate_initial_view(self,PC,rank,generation,view,revision):
        from h3_deepseek_full_token_driver import validate_view
        home=self.initial_index.get((PC,rank))
        if home is None:raise ValueError('actual r33 initial window home absent')
        op=self.d['instructions'][PC];key=next(iter(op['provider_bindings']))
        result=validate_view('window',view,op['provider_bindings'][key]['window'],self.d['templates'][key]['providers']['window'],rank,generation,revision)
        if view.get('concrete_home')!=home or generation!=home['generation']:raise ValueError('exact source-owned initial address/version/generation required')
        return result
    def accept_Dewey_reprice(self,commit,path):
        receipt=json.loads(pinned(path,commit))
        expected=dict(native_sha256=self.r33_inputs['native'],dispatch_sha256=self.r33_inputs['dispatch'],catalog_sha256=self.catalog_digest,
            actual_scalar_count_delta=self.count_delta,RF_highword_RMW_recharged=False,C0_control_recharged=False,reprice_count=1)
        if receipt.get('schema')!='H4_R33_DEWEY_ONCE_REPRICE_V1' or any(receipt.get(k)!=v for k,v in expected.items()):raise ValueError('exact source-bound Dewey once-only reprice receipt required')
        if self.calendar_admitted:raise ValueError('Dewey successor costs already admitted once')
        self.calendar_admitted=True
    def report(self):
        return dict(schema='H4_C0_R33_SOURCE_ADAPTER_V1',status='SOURCE_JOIN_ACCEPTED_CALENDAR_AND_FULL_MOVEMENT_HELD',r33_pin=R33,
            inputs=self.r33_inputs,source_catalog_sha256=self.catalog_digest,PCs=2213,families=30,changed_window_PCs=40,
            window=dict(input_shape=[127,512],drop_rows=0,output_shape=[128,512]),
            typed_initial_homes=len(self.initial_homes['rows']),source_RoPE_views=len(self.rope_bindings),
            actual_scalar_count_delta=self.count_delta,actual128lane_batch_count_delta=self.batch_delta,
            source_window_LOAD_byte_delta=self.count_delta.get('LOAD',0)*4,
            source_window_LOAD64B_span_delta=self.count_delta.get('LOAD',0)*4//64,
            source_byte_span_scope='Source span only; original conservative128-input service reservations retained until Dewey reprice; no free bandwidth/latency credit',
            Qwen=dict(PCs=1737,families=21,source_unchanged=True),
            owner_API='tools/h4_c0_v1_owner_lock_addressed.py; no original owner/observer changes',
            Dewey_once_reprice_schema='H4_R33_DEWEY_ONCE_REPRICE_V1',
            required_reprice_fields=dict(native_sha256=self.r33_inputs['native'],dispatch_sha256=self.r33_inputs['dispatch'],catalog_sha256=self.catalog_digest,actual_scalar_count_delta=self.count_delta,RF_highword_RMW_recharged=False,C0_control_recharged=False,reprice_count=1),
            calendar_admitted=self.calendar_admitted,initial_payloads_supplied=False,full_movement_qualified=False,hardware_qualified=False,RTL_allowed=False)

def emit(bundle,output):
    output=pathlib.Path(output)
    if output.exists():raise ValueError('fresh source evidence output required; historical records preserved')
    join=R33SourceJoin(bundle);output.mkdir(parents=True)
    records={'source_adapter.json':join.report(),'source_catalog.json.gz':join.catalog,
        'parent_provider_interface.json.gz':join.parent_interface,'G0_both_program_source_interface.json.gz':join.g0,
        'changed40_PC_bindings.json.gz':[{k:op[k] for k in ('pc','family','dependencies','reads','writes','rank_bindings','provider_bindings')}
            for op in join.d['instructions'] if op['pc'] in {r['PC'] for r in join.r33_bridge['window_template_joins']}]}
    for name,record in records.items():
        raw=canonical(record)
        (output/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else json.dumps(record,sort_keys=True,indent=2).encode()+b'\n')
    root=pathlib.Path(__file__).resolve().parents[1]
    sources=['tools/h4_c0_r33_source_adapter.py','tools/test_h4_c0_r33_source_adapter.py','tools/h4_c0_parent_provider_join.py',
        'tools/h4_c0_v1_owner_lock_addressed.py','tools/h4_c0_forward_observer_addressed.py','tools/h4_c0_model.py',
        'tools/h4_c0_bridge.py','tools/h4_c0_ordered_movement.py','tools/uarch_model.py']
    sourcepins={p:sha((root/p).read_bytes()) for p in sources}
    inputs={p.name:sha(p.read_bytes()) for p in pathlib.Path(bundle).iterdir() if p.is_file()}
    producerpins={p:dict(commit=R33,sha256=sha(pinned(p,R33))) for p in [
        'tools/ds_hbm_window_contract_r33.py','tools/ds_hbm_window_rope_prepare_r33.py','tools/h3_ds_checkpoint_provider_r33.py',
        BASE+'bridge.json',BASE+'initial_window_homes.json.gz',BASE+'source_owned_rope_bindings.json.gz']}
    manifest=dict(schema='H4_C0_R33_SOURCE_ADAPTER_MANIFEST_V1',intake_base='68a05aca992a86da70c2ef362a0815508a69a506',source_sha256=sourcepins,
        producer_pins=producerpins,external_bundle=str(pathlib.Path(bundle).resolve()),input_files_sha256=inputs,
        records_sha256={p.name:sha(p.read_bytes()) for p in output.iterdir()},
        jobs=[],source_only=True,calendar_admitted=False,hardware_qualified=False)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();emit(args.bundle,args.output)
