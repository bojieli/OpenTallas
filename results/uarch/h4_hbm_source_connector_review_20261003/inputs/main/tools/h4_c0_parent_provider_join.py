"""Immutable full-program source binding for actual provider movement.

Reuses Dewey's actual forward catalog/resolver and original C0 NativeDecoder.
No new compiler/calendar/arithmetic, numerical job, or hardware qualification.
"""
import ast, functools, gzip, hashlib, json, types, pathlib
from h4_c0_model import sources, pinned, NATIVE
from h4_c0_bridge import NativeDecoder
from h4_c0_ordered_movement import strict_api

DEWEY='5b71cd17cebe109a1dab6141aa2812bd6f02b2a8'
BASE='results/uarch/h3_complete_native_calendar_20261002/ds_forward_leaf_join_r3/review/'

def immutable(name):return json.loads(gzip.decompress(pinned(BASE+name,DEWEY)))

@functools.lru_cache(maxsize=1)
def forward_resolvers():
    names={'resolve_ds_forward_parent_home','resolve_ds_forward_leaf_reference'}
    raw=pinned('tools/h3_complete_native_calendar.py',DEWEY)
    selected=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(selected)!=len(names):raise ValueError('actual Dewey forward resolver missing')
    ns=dict(hashlib=hashlib,json=json,resolve_ds_movement_reference=strict_api().resolve_ds_movement_reference)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'Dewey-forward@'+DEWEY,'exec'),ns)
    return types.SimpleNamespace(**{name:ns[name] for name in names})

class _PinnedPath:
    """Read-only path facade for Dewey's unchanged retained-builder loader."""
    def __init__(self,path=''):self.path=pathlib.PurePosixPath(path)
    def __truediv__(self,part):return _PinnedPath(self.path/part)
    @property
    def name(self):return self.path.name
    @property
    def parent(self):return _PinnedPath(self.path.parent)
    def read_bytes(self):return pinned(str(self.path),DEWEY)
    def __str__(self):return 'git@'+DEWEY+':'+str(self.path)

@functools.lru_cache(maxsize=1)
def forward_builders():
    # Run the original loader on immutable Git blobs, no alternate compiler and
    # no numerical/provider runtime. Its original internal hash checks remain.
    raw=pinned('tools/h3_complete_native_calendar.py',DEWEY)
    body=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='load_ds_forward_builders']
    import collections, math
    ns=dict(ROOT=_PinnedPath(),OUT='results/uarch/h3_complete_native_calendar_20261002',
        read_json=lambda path:json.loads(path.read_bytes()),types=types,ast=ast,hashlib=hashlib,Counter=collections.Counter,math=math)
    exec(compile(ast.Module(body=body,type_ignores=[]),'Dewey-original-builder-loader','exec'),ns)
    return ns['load_ds_forward_builders']()

class ParentProviderJoin:
    def __init__(self):
        self.q,self.d,self.residence=sources();self.decoder=NativeDecoder(self.q,self.d,self.residence)
        self.catalog=immutable('forward_leaf_catalog.json.gz')
        self.parent_interface=immutable('forward_parent_provider_interface.json.gz')
        self.g0=immutable('G0_both_program_interface.json.gz');self.api=forward_resolvers()
        self.programs={'Qwen':self.q['operations'],'DeepSeek':self.d['instructions']}
        self.source_hashes={'Qwen':hashlib.sha256(json.dumps(self.q,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'DeepSeek':self.catalog['source_program_sha256']}
        self.PC_catalog={model:{row['pc']:row for row in self.g0[model]['PC_bindings']} for model in self.programs}
        for model,count,families in [('Qwen',1737,21),('DeepSeek',2213,30)]:
            if len(self.programs[model])!=count or set(self.PC_catalog[model])!=set(range(count)):raise ValueError('complete current PC source set required')
            for pc,op in enumerate(self.programs[model]):
                if op['pc']!=pc or self.PC_catalog[model][pc]['family']!=op.get('opcode',op.get('family')):raise ValueError('actual source PC/family join mismatch')
            if len({row['family'] for row in self.PC_catalog[model].values()})!=families:raise ValueError('complete source family set required')
    def context(self,model,PC,rank,SM,generation):
        if model not in self.programs or type(PC)!=int or not 0<=PC<len(self.programs[model]):raise ValueError('actual source PC required')
        if type(rank)!=int or not 0<=rank<(2 if model=='Qwen' else 96) or type(SM)!=int or not 0<=SM<32 or type(generation)!=int or not 0<generation<2**64:raise ValueError('actual parent owner extent')
        op=self.programs[model][PC]
        if model=='Qwen':
            # Current bounded emitter is a serialized rank0/SM0 worker; source
            # 32SM residence homes do not prove executable dispatch elsewhere.
            if (rank,SM)!=(0,0):raise ValueError('current bounded Qwen dispatch requires actual rank0/SM0')
        elif not any(r['rank']==rank and not r.get('empty_owned_extent') for r in op['rank_bindings']):raise ValueError('source DeepSeek rank not owner')
        def versions(side):return op[side] if model=='Qwen' else [v['version'] for v in op[side]]
        return dict(model=model,PC=PC,rank=rank,SM=SM,generation=generation,
            family=op.get('opcode',op.get('family')),dependencies=list(op['dependencies']),
            reads=versions('reads'),writes=versions('writes'),program_sha256=self.source_hashes[model],
            SM_scope='Caller explicit actual parent SM; no implicit block partition to installed connector')
    def bind_DS_forward_operand(self,context,reference,*,streaming_builder=None):
        expected=self.context('DeepSeek',context['PC'],context['rank'],context['SM'],context['generation'])
        if context!=expected:raise ValueError('source parent context changed')
        pc=self.catalog['PC_bindings'][context['PC']]
        if not any(b['rank']==context['rank'] and b['template']==reference.get('parent_template') for b in pc['bindings']):raise ValueError('actual parent rank/template leaf mismatch')
        # Dynamic index refs require the existing compiler supplied by its owner;
        # no substitute row program or numerical callback is generated here.
        N,S=forward_builders()
        if streaming_builder is not None and streaming_builder is not S:raise ValueError('alternate dynamic streaming builder prohibited')
        return self.api.resolve_ds_forward_leaf_reference(self.catalog,N,S,reference,expected_rank=context['rank'])
    def bind_Qwen_leaf(self,context,*,kernel,microstep):
        expected=self.context('Qwen',context['PC'],context['rank'],context['SM'],context['generation'])
        if context!=expected:raise ValueError('source parent context changed')
        if type(microstep)!=int or microstep<0:raise ValueError('source microstep required')
        rows=[row for row in self.decoder.leaf('Qwen',context['PC'],kernel=kernel) if row['microstep']==microstep]
        if not rows:raise ValueError('actual Qwen instruction absent')
        return rows
    def bind_actual_receipt(self,context,receipt):
        expected=self.context(context['model'],context['PC'],context['rank'],context['SM'],context['generation'])
        if context!=expected:raise ValueError('source parent context changed')
        if receipt.get('status')!='SOFTWARE_ADDRESSED_MOVEMENT_REVERSE_DRAINED':raise ValueError('actual addressed receipt required')
        if any(receipt.get(k)!=context[k] for k in ('model','PC','rank','generation')):raise ValueError('actual receipt source PC/rank/generation mismatch')
        owner=receipt['native_owner']
        if tuple(owner)!=(context['PC'],tuple(context['writes']),context['rank'],context['SM'],context['generation']):raise ValueError('actual full output version/SM owner mismatch')
        return dict(parent_context=context,provider_receipt=receipt,source_binding_verified=True,
            operand_window_home_binding='REQUIRES exact native operand reference + source tile/view + installed connector',
            family_hardware_qualified=False,full_program_movement_qualified=False)
    def observe_Qwen_immutable_tile(self,context,backend,request):
        """Delegate the actual immutable checkpoint byte contract unchanged.

        This captures real returned bytes and their explicit extent/lease. Its
        synchronous boolean ACK is NOT promoted to an addressed reverse grant.
        """
        expected=self.context('Qwen',context['PC'],context['rank'],context['SM'],context['generation'])
        if context!=expected:raise ValueError('source parent context changed')
        op=self.q['operations'][context['PC']]
        providers=op['provider_binding']['external_providers']
        if request.get('provider_ref') not in {p['provider_ref'] for p in providers}:raise ValueError('actual Qwen PC immutable provider ref mismatch')
        source=pathlib.Path(backend.read_tile_bytes.__func__.__code__.co_filename)
        expected_source=pinned('tools/qwen_trained_byte_provider.py','9fb3ba94186bde39ebaee62895d9f55b557daed5')
        if not source.is_file() or source.read_bytes()!=expected_source:raise ValueError('actual Qwen immutable backend source pin mismatch')
        result=backend.read_tile_bytes(request)
        if result.get('provider_ref')!=request['provider_ref'] or result.get('lease')!=request['lease'] or result.get('state')!='visible':raise ValueError('actual Qwen byte return lease mismatch')
        ranges=request['byte_ranges'];payloads=result['payloads']
        if len(payloads)!=len(ranges):raise ValueError('actual Qwen byte ranges mismatch')
        fragments=[]
        for extent,raw in zip(ranges,payloads):
            if len(raw)!=extent['bytes']:raise ValueError('actual Qwen byte span mismatch')
            address=extent['address']
            for base in range(address//64*64,(address+len(raw)+63)//64*64,64):
                lo=max(base,address);hi=min(base+64,address+len(raw));data=raw[lo-address:hi-address]
                fragments.append(dict(byte_address=base,valid_byte_mask=hex(((1<<(hi-lo))-1)<<(lo-base)),payload_bytes=len(data),payload_sha256=hashlib.sha256(data).hexdigest(),
                    immutable_payload_returned=True,addressed_sector_reverse_receipt=None))
        return result,dict(parent_context=context,provider_ref=request['provider_ref'],lease=result['lease'],fragments=fragments,
            software_return_ACK=result.get('reverse_grant_ACK'),actual_addressed_reverse_qualified=False,
            source_operand_window_binding='Requires exact source kernel operand reference; no implicit LOAD mapping',
            hardware_qualified=False,full_program_movement_qualified=False)

    def transfer_DS_native_operand(self,context,reference,movement,lock,token,fragment,key,*,payload=None,streaming_builder=None):
        """Source-gated actual provider transfer, never a family callback.

        Caller has already reserved C0 with concrete version/home identities.
        The opcode/typed operand reference must resolve to Dewey's exact leaf.
        Rejected source bindings retain that owner; this never launches a job.
        """
        resolved=self.bind_DS_forward_operand(context,reference,streaming_builder=streaming_builder)
        command=lock.owner(token)['command']
        if any(command[k]!=context[v] for k,v in [('source_PC','PC'),('rank','rank'),('SM','SM'),('generation','generation'),('family','family'),('program_sha256','program_sha256')]):
            raise ValueError('atomic command differs from actual native source context')
        if (command['template_id'],command['ordered_step_index'],command['opcode'],command['source_attrs_rounding'])!=(reference['template'],reference['code_index'],reference['opcode'],reference['attrs']):
            raise ValueError('atomic command does not encode actual source leaf instruction')
        leaf=self.catalog['leaves'][reference['template']]['program']
        node=leaf['code'][reference['code_index']]
        specs=strict_api().native_value_specs({'templates':{reference['template']:leaf}},reference['template'])
        if command['source_bittypes']!=[specs[value]['width']*8 for value in node['src']] or command['destination_bittype']!=specs[node['dst']]['width']*8:
            raise ValueError('actual native source/result widths differ from atomic command')
        for home,value in zip(command['source_version_home_refs'],node['src']):
            if home.get('native_SSA_value',home['version'])!=value:raise ValueError('actual native source SSA/home binding mismatch')
        destination=command['destination_version_home_ref']
        if destination.get('native_SSA_value',destination['version'])!=node['dst']:raise ValueError('actual native destination SSA/home binding mismatch')
        if resolved[-1]!=fragment['payload_bytes']:raise ValueError('actual native operand/provider fragment typed span mismatch')
        if (reference['operand']=='dst')!=(fragment['kind']=='destination_writeback'):
            raise ValueError('actual native operand movement direction mismatch')
        result=movement.transfer_to_owner(lock,token,fragment,key,payload=payload)
        joined=self.bind_actual_receipt(context,movement.last_receipt)
        joined.update(native_instruction_ref=reference,typed_operand_resolution=resolved,
            source_programs_complete=False,hardware_qualified=False)
        return result,joined

    def report(self):
        paths=[BASE+n for n in ('forward_leaf_catalog.json.gz','forward_parent_provider_interface.json.gz','G0_both_program_interface.json.gz')]
        return dict(schema='H4_C0_ACTUAL_PARENT_PROVIDER_SOURCE_JOIN_V1',
            programs={m:dict(PCs=len(p),families=len({r['family'] for r in self.PC_catalog[m].values()})) for m,p in self.programs.items()},
            immutable_source_pins={p:dict(commit=DEWEY,sha256=hashlib.sha256(pinned(p,DEWEY)).hexdigest()) for p in paths},
            Qwen_byte_backend_pin='9fb3ba94186bde39ebaee62895d9f55b557daed5',
            Qwen_byte_backend_sha256=hashlib.sha256(pinned('tools/qwen_trained_byte_provider.py','9fb3ba94186bde39ebaee62895d9f55b557daed5')).hexdigest(),
            native_source_pin=NATIVE,DS_forward_parent_PC_bindings=len(self.parent_interface['PC_bindings']),
            missing_forward_version_homes=self.parent_interface['missing_version_home_refs'],
            remaining_unknown_shared_calls=189476,
            implemented='Executable full source PC/version/owner binding and reuse of actual forward leaf resolver; addressed parent journal bridge to SerializedOwner',
            remaining=['Full ordered bounded operand-window continuation and exact tile/view mapping',
                'Qwen immutable byte return has no addressed sector reverse journal; boolean ACK cannot close it',
                'Kepler route-fence failure must pass on unchanged released byte contracts',
                'Installed rank/SM connector and composed C0+V1 slot/distributed-cut G0',
                'Missing hardware families, actual connected ACK gates and SS/FF'],
            full_program_movement_executed=False,hardware_qualified=False,RTL_allowed=False,jobs=[])

def emit(output):
    from h4_c0_v1_owner_lock_addressed import export_contract,owner_model
    output=pathlib.Path(output)
    if output.exists():raise ValueError('fresh evidence directory required; preserve historical verdicts')
    root=pathlib.Path(__file__).resolve().parents[1]
    if (root/'tools/uarch_model.py').read_bytes()!=pinned('tools/uarch_model.py',NATIVE):raise ValueError('original unified model changed')
    report=ParentProviderJoin().report();output.mkdir(parents=True)
    records={'source_join.json':report,'atomic_owner_contract.json':export_contract(),'composed_owner_model.json':owner_model()}
    records['integration_API.json']=dict(
        status='SOURCE_BOUND_OPT_IN_SOFTWARE_API; not a launch or hardware authorization',
        entrypoints=dict(full_source_dispatch='ParentProviderJoin.context(model,PC,rank,SM,generation)',
            DS_native_operand='ParentProviderJoin.bind_DS_forward_operand(context,reference)',
            Qwen_native_leaf='ParentProviderJoin.bind_Qwen_leaf(context,kernel=...,microstep=...)',
            actual_parent_movement='AddressedMovement(parent_scratch,source_sha256=exact_source_digest)',
            DS_native_owner_transfer='ParentProviderJoin.transfer_DS_native_operand(context,reference,movement,lock,token,fragment,key,payload=...)',
            Qwen_immutable_read='ParentProviderJoin.observe_Qwen_immutable_tile(context,actual_TrainedByteBackend,request)'),
        preconditions=['Exact released checkpoint byte contracts and source-pinned parent scratch allocation',
            'C0 command from actual source leaf + concrete typed SSA/home leases; not family strings',
            'AtomicV1Owners source physical inventory, or explicitly protocol-only controls; candidate floorplan is not installed',
            'Expected payload/address digest before provider acceptance; bounded source tile/view lowering still required'],
        journal_contract='Actual sector identities/tags/generations; preserve original provider service calendar; aggregate C0 software barriers have no physical timestamp/ACK claim',
        failure='Retain atomic owner and provider fragment debt; preserve actual journal and failed receipt',
        next_G0='Popper expanded SM slot and actual distributed RF/scratch/C0 cuts plus installed rank/SM connector; Kepler actual route-fence lifecycle PASS; Dewey full ordered typed-window join',
        jobs=[],engine_RTL_written=False)
    for name,record in records.items():(output/name).write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    paths=['tools/h4_c0_parent_provider_join.py','tools/h4_c0_provider_movement.py','tools/h4_c0_v1_owner_lock.py','tools/h4_c0_v1_owner_lock_addressed.py','tools/h4_c0_forward_observer.py','tools/h4_c0_forward_observer_addressed.py',
        'tools/test_h4_c0_parent_provider_join.py','tools/test_h4_c0_provider_movement.py','tools/test_h4_c0_v1_owner_lock.py','tools/test_h4_c0_v1_owner_lock_addressed.py','tools/uarch_model.py']
    manifest=dict(source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
        records_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()},hardware_qualified=False)
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    emit(parser.parse_args().output)
