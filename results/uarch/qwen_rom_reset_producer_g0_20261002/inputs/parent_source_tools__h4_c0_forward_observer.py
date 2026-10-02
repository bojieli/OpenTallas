"""Opt-in observation of existing streaming leaf execution; CPU evidence only.

No provider implementation or arithmetic replacement. Callers bind a parent
PC/template and exact shape before using this in a full-program run. Fixture
observation is deliberately labelled separately. No automatic job is launched.
"""
import collections, gzip, hashlib, json, math, pathlib, weakref
import h3_deepseek_streaming_linear as STREAM
from h4_c0_ordered_movement import strict_api, emit_template, CapacityGate, DISPATCH
from h4_c0_model import pinned, NATIVE, DPATH

class ProviderTap:
    """Observe an existing provider, never replace its backing or completion.

    A returned synchronous value is functional software evidence. It is NOT
    promoted to a validated reverse grant or to an addressed physical receipt.
    """
    def __init__(self,backend,on_event=None,max_events=32768):
        self.backend=backend;self.events=[];self.on_event=on_event;self.writes={};self.max_events=max_events
    def guard(self):
        if len(self.events)>=self.max_events:raise ValueError('finite observer provider trace capacity exhausted')
    def __getattr__(self,name):return getattr(self.backend,name)
    def record(self,kind,key,data):
        row=dict(sequence=len(self.events),kind=kind,key=list(key),
            payload_bytes=len(data),payload_sha256=hashlib.sha256(data).hexdigest(),
            workspace_extent=getattr(self.backend,'workspace_extent',None),
            actual_address_receipt=None,validated_reverse_grant=None,
            qualification='functional provider call/return only')
        if self.on_event:row['source_output_origin']=self.on_event(kind,key,data)
        identity=json.dumps(key,separators=(',',':'))
        if kind.startswith('write'):
            self.writes[identity]=row
        elif kind.startswith('read') and identity in self.writes:
            writer=self.writes[identity]
            if writer['payload_sha256']!=row['payload_sha256'] or writer['payload_bytes']!=row['payload_bytes']:
                raise ValueError('actual provider return differs from observed source writeback')
            row['matched_writeback_sequence']=writer['sequence']
            row['source_output_origin']=writer.get('source_output_origin')
        self.events.append(row)
    def transact(self,key,*,write=False,payload=None):
        self.guard()
        result=self.backend.transact(key,write=write,payload=payload)
        self.record('write_return' if write else 'read_return',key,payload if write else result)
        return result
    def write_object(self,key,data):
        self.guard()
        result=self.backend.write_object(key,data);self.record('write_object_return',key,data);return result
    def read_object(self,key):
        self.guard()
        result=self.backend.read_object(key);self.record('read_object_return',key,result);return result

class ForwardObserver:
    def __init__(self, *, parent_context, fixture=False,max_leaves=4096,typed_views=None,checkpoint_revision=None):
        if type(max_leaves)!=int or not 1<=max_leaves<=4096:raise ValueError('finite observer leaf cap required')
        self.max_leaves=max_leaves
        if not fixture:
            needed={'program_sha256','dispatch_sha256','PC','template','rank','SM','generation','version','expected_execution_path'}
            if not needed<=set(parent_context):raise ValueError('complete parent native instruction context required')
            if not parent_context['expected_execution_path'].startswith('forward_'):
                raise ValueError('actual forward execution path required')
            dispatch=json.loads(gzip.decompress(pinned(DISPATCH)))
            digest=hashlib.sha256(json.dumps(dispatch,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if parent_context['dispatch_sha256']!=digest or parent_context['program_sha256']!=dispatch['source_program_sha256']:
                raise ValueError('parent immutable program/dispatch mismatch')
            pc=parent_context['PC'];sm=parent_context['SM'];generation=parent_context['generation']
            if type(pc)!=int or not 0<=pc<len(dispatch['PC_dispatch']) or type(sm)!=int or not 0<=sm<32 or type(generation)!=int or not 0<=generation<2**64:
                raise ValueError('parent PC/SM/generation extent')
            if not any(c['rank']==parent_context['rank'] and c['template']==parent_context['template'] for c in dispatch['PC_dispatch'][pc]['calls']):
                raise ValueError('parent actual PC/rank/template call missing')
            if dispatch['templates'][parent_context['template']]['execution_path']!=parent_context['expected_execution_path']:
                raise ValueError('parent forward path mismatch')
            native=json.loads(gzip.decompress(pinned(DPATH)))
            op=native['instructions'][pc];template=parent_context['template']
            owned=next(r for r in op['rank_bindings'] if r['rank']==parent_context['rank'])
            buffers=[b for b in owned.get('buffer_programs',[]) if b['template']==template]
            versions=[w['version'] for w in op['writes']]
            supplied=list(parent_context['version']) if isinstance(parent_context['version'],(list,tuple)) else [parent_context['version']]
            buffer=next((b for b in buffers if supplied==[b['write_version']]),None)
            if supplied!=versions and buffer is None:raise ValueError('actual parent output version owner mismatch')
            if typed_views is None or not checkpoint_revision:
                raise ValueError('actual parent typed views and exact released checkpoint revision required')
            program=native['templates'][template]
            if set(typed_views)!=set(program['providers']):raise ValueError('complete parent typed LOAD view set required')
            from h3_deepseek_full_token_driver import validate_view
            bindings={name:dict(row) for name,row in op['provider_bindings'][template].items()}
            if buffer:
                for name,binding in bindings.items():
                    if name=='parts':binding.update(version=buffer['read_version'],additional_versions=[buffer['read_version']])
                    elif binding['kind']=='explicit_auxiliary_provider':binding['identity_from_versions']=[buffer['read_version']]
            for name,view in typed_views.items():
                validate_view(name,view,bindings[name],program['providers'][name],parent_context['rank'],generation,checkpoint_revision)
            self.parent_bindings=bindings
            self.checkpoint_revision=checkpoint_revision
        else:
            self.parent_bindings={};self.checkpoint_revision=None
        self.context=dict(parent_context);self.fixture=fixture;self.leaves=[];self.api=strict_api()
        if not fixture:self.context['version']=tuple(supplied)
        self.reads=[];self.origins={};self.provider_cursor=0;self.read_cursor=0;self.tap=None;self.last_outputs={}
        self.source_sha256=hashlib.sha256(pinned('tools/h3_deepseek_streaming_linear.py')).hexdigest()
        local=pathlib.Path(STREAM.__file__).read_bytes()
        if hashlib.sha256(local).hexdigest()!=self.source_sha256:
            raise ValueError('streaming source differs from immutable native pin')
    def observe_read(self,original,key,array):
        result=original(key,array)
        row=dict(sequence=len(self.reads),key=list(key),dtype=str(result.dtype),shape=list(result.shape),
                 payload_bytes=result.nbytes,payload_sha256=hashlib.sha256(result.tobytes()).hexdigest())
        self.reads.append(row)
        self.origins[id(result)]=(weakref.ref(result),dict(kind='actual_streaming_read',read_sequence=row['sequence'],key=list(key)))
        return result
    def output_origin(self,kind,key,data):
        if not kind.startswith('write') or not self.leaves:return None
        leaf=self.leaves[-1];prefix=key[0];fields=None;offset=0
        if prefix=='Q8block' and leaf['kind']=='quantize32':fields=['units','exponent']
        elif prefix=='BF16chunk' and leaf['kind']=='BF16_input8':fields=['out']
        elif prefix=='retained_query' and leaf['kind']=='query_decode_once':fields=[key[-1]]
        elif prefix=='output_staging' and leaf['kind']=='BF16_final':fields=['out'];offset=key[-1]
        elif prefix=='index_output_staging' and leaf['kind']=='index_row':fields=['is_v','is_i']
        elif prefix=='gather_output_staging' and leaf['kind']=='gather_columns128':fields=['out']
        elif prefix=='float_output_staging' and leaf['kind'] in ('FADD128','float_dot8','BF16_final'):fields=['out' if 'out' in self.last_outputs else 'block']
        if fields is None:return None
        values=[self.last_outputs.get(field,lambda:None)() for field in fields]
        if any(value is None for value in values):return None
        raw=b''.join(value.tobytes() for value in values)
        if raw[offset:offset+len(data)]!=data:raise ValueError('provider writeback is not actual native leaf output')
        if offset+len(data)>len(raw):raise ValueError('native writeback span extent')
        return dict(kind='actual_native_leaf_writeback',leaf_sequence=leaf['sequence'],
            leaf_program_sha256=leaf['source_program_hash'],fields=fields,logical_byte_offset=offset,
            payload_bytes=len(data),source_output_values={field:leaf['generated_program']['outputs'][field] for field in fields})
    def input_mapping(self,kind,inputs):
        """Resolve actual direct objects and source-ordered linear provider keys.

        ndarray copies/stack operations lose object lineage. Their mapping uses
        the pinned linear compiler's exact key roles and ordered returned bytes,
        never a search for a coincidentally matching value in a released image.
        Unresolved lane-local initialisers or indexed continuations stay UNKNOWN.
        """
        current_reads=self.reads[self.read_cursor:]
        current_events=self.tap.events[self.provider_cursor:] if self.tap else []
        result={}
        for name,value in inputs.items():
            prior=self.origins.get(id(value));origin=None
            if prior is not None and prior[0]() is value:origin=prior[1]
            if origin is None and kind=='dot32' and name in ('weight_codes','weight_scale_codes'):
                prefix='weight' if name=='weight_codes' else 'scale'
                chosen=[r for r in current_reads if r['key'][0]==prefix]
                if chosen:
                    # Keys retain owner, actual row and actual K-block. Require
                    # all rows, in source order, and a single source K-block.
                    rows=[r['key'][-2] for r in chosen];blocks={r['key'][-1] for r in chosen}
                    if len(chosen)==value.shape[0] and rows==list(range(rows[0],rows[0]+len(rows))) and len(blocks)==1:
                        fragments=[]
                        for r in chosen:
                            matching=[e for e in current_events if e['kind']=='read_return' and e['key'][:-1]==r['key']]
                            fragments.extend(matching)
                        # Each source read's byte digest was observed after the
                        # provider return. Reconstruct from actual typed input
                        # rows and compare each declared result row digest.
                        if all(hashlib.sha256(value[j].tobytes()).hexdigest()==r['payload_sha256'] for j,r in enumerate(chosen)):
                            origin=dict(kind='ordered_source_row_reads',read_sequences=[r['sequence'] for r in chosen],
                                        provider_return_sequences=[e['sequence'] for e in fragments],
                                        source_keys=[r['key'] for r in chosen])
            if origin is None and kind=='dot32' and name in ('units','exponent'):
                chosen=[e for e in current_events if e['kind']=='read_return' and e['key'][0]=='Q8block']
                if len(chosen)==1:
                    # units/exponent come from the actual 260B read, at the
                    # exact offsets used by StreamingLinear.run. The tap only
                    # stores hashes; the compound-read digest is checked below.
                    origin=dict(kind='source_Q8block_field',provider_return_sequence=chosen[0]['sequence'],
                                source_key=chosen[0]['key'],byte_offset=0 if name=='units' else 256,
                                payload_bytes=value.nbytes,compound_payload_sha256=chosen[0]['payload_sha256'],
                                matched_writeback_sequence=chosen[0].get('matched_writeback_sequence'),
                                source_output_origin=chosen[0].get('source_output_origin'))
            result[name]=dict(origin=origin,source_mapping_status='BOUND_FUNCTIONAL_SOURCE' if origin else 'UNKNOWN_INPUT_LINEAGE',
                dtype=str(value.dtype),shape=list(value.shape),payload_bytes=value.nbytes,
                payload_sha256=hashlib.sha256(value.tobytes()).hexdigest(),
                address_ACK_reverse_status='UNKNOWN_PENDING_KEPLER_CAUSAL_FRAGMENT_RECEIPT')
            parent_field=None
            if kind=='quantize32' and name=='x':parent_field='x'
            elif kind=='dot32' and name in ('weight_codes','weight_scale_codes'):parent_field=name
            result[name]['parent_field']=parent_field
            result[name]['parent_source_binding']=self.parent_bindings.get(parent_field)
        if kind=='dot32' and {'units','exponent'}<=set(inputs):
            digest=hashlib.sha256(inputs['units'].tobytes()+inputs['exponent'].tobytes()).hexdigest()
            for name in ('units','exponent'):
                row=result[name];origin=row['origin']
                if origin and origin['kind']=='source_Q8block_field' and digest!=origin['compound_payload_sha256']:
                    raise ValueError('Q8 producer-return units/exponent payload mismatch')
        return result
    def execute(self,runner,program,inputs,kind):
        if len(self.leaves)>=self.max_leaves:raise ValueError('finite observer leaf trace capacity exhausted; owner streaming sink required for longer execution')
        mapped_inputs=self.input_mapping(kind,inputs)
        # The existing primitive interpreter owns numerical semantics and order.
        vm=STREAM.N.Machine(program,inputs,STREAM.N.primitive_div);outputs=vm.run()
        if len(vm.events)!=len(program['code']):raise ValueError('actual native leaf instruction execution incomplete')
        digest=hashlib.sha256(json.dumps(program,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        counts=collections.Counter();references=[]
        wrapped={'templates':{digest:program}};specs=self.api.native_value_specs(wrapped,digest)
        for index,(node,event) in enumerate(zip(program['code'],vm.events)):
            if event['pc']!=index or event['op']!=node['op'] or event['batches128']!=math.ceil(max(1,math.prod(node['shape']))/128):
                raise ValueError('actual leaf source order/count mismatch')
            counts[node['op']]+=max(1,math.prod(node['shape']))
            refs=[]
            for role,value in [('dst',node['dst'])]+[('src:'+str(j),v) for j,v in enumerate(node['src'])]:
                ref=dict(template=digest,code_index=index,opcode=node['op'],attrs=node['attrs'],result_shape=node['shape'],
                         operand=role,value=value,logical_byte_offset=0,payload_bytes=specs[value]['bytes'])
                self.api.resolve_ds_movement_reference(wrapped,digest,ref,specs);refs.append(ref)
            references.append(dict(actual_primitive_event=event,native_operand_refs=refs))
        # Apply V1 only to the individual, exactly generated source-order leaf.
        # This NEVER relabels the parent's forward execution path for its join.
        t={'execution_path':'source_order_live_range_stages','executed_primitive_scalar_projection':dict(counts)}
        try:movement=emit_template(wrapped,digest,t,self.api);gate=None
        except CapacityGate as exc:movement=None;gate=str(exc)
        self.leaves.append(dict(sequence=len(self.leaves),kind=kind,source_program_hash=digest,
            generated_program=program,source_order_refs=references,primitive_scalars=dict(counts),
            proposed_finite_leaf_lowering=movement,finite_leaf_gate=gate,
            parent_context=self.context,parent_forward_shared_join_qualified=False,
            provider_refill_writeback_mapping='UNKNOWN_PENDING_ACTUAL_PARENT_PROVIDER_EVENTS',
            actual_LOAD_input_mapping=mapped_inputs,
            actual_provider_calls_before_leaf=self.tap.events[self.provider_cursor:] if self.tap else [],
            scope='fixture CPU leaf observation' if self.fixture else 'CPU leaf observation; parent handle/provider movement requires independent validation'))
        runner.fault|=vm.fault;runner.kernel_calls[kind]+=1;runner.counts.update(counts)
        leaf_sequence=len(self.leaves)-1
        self.last_outputs={name:weakref.ref(value) for name,value in outputs.items()}
        for name,value in outputs.items():
            self.origins[id(value)]=(weakref.ref(value),dict(kind='actual_native_leaf_output',leaf_sequence=leaf_sequence,
                leaf_program_sha256=digest,result=name,SSA_value=program['outputs'][name]))
        self.provider_cursor=len(self.tap.events) if self.tap else 0;self.read_cursor=len(self.reads)
        return outputs
    def attach(self,runner):
        if runner.kernel_calls or runner.counts:raise ValueError('cannot attach after a running leaf has started')
        if not self.fixture:
            expected=tuple(self.context[k] for k in ('PC','version','rank','SM','generation'))
            if tuple(runner.owner)!=expected:raise ValueError('runner differs from verified parent owner')
        self.tap=ProviderTap(runner.memory,self.output_origin);runner.memory=self.tap
        original_read=runner.read
        runner.read=lambda key,array:self.observe_read(original_read,key,array)
        runner.execute=lambda program,inputs,kind:self.execute(runner,program,inputs,kind)
        return runner
    def receipt(self):
        return dict(schema='H4_C0_ACTUAL_STREAMING_LEAF_OBSERVATION_V1',native_source_pin=NATIVE,
            streaming_source_sha256=self.source_sha256,parent_context=self.context,
            parent_typed_source_bindings=self.parent_bindings,exact_checkpoint_revision=self.checkpoint_revision,
            actual_provider_calls=self.tap.events if self.tap else [],actual_streaming_reads=self.reads,
            fixture=self.fixture,leaves=self.leaves,hardware_qualification=False,physical_admission=False,
            max_observed_leaves=self.max_leaves,max_observed_provider_calls=32768,
            whole_program_movement_qualified=False,provider_implementation_changed=False,
            missing_contract='Parent source count join plus actual provider refill/writeback ACK/reverse mapping; Dewey forward-leaf ABI extension required')
