"""Opt-in observation of existing streaming leaf execution; CPU evidence only.

No provider implementation or arithmetic replacement. Callers bind a parent
PC/template and exact shape before using this in a full-program run. Fixture
observation is deliberately labelled separately. No automatic job is launched.
"""
import collections, gzip, hashlib, json, math, pathlib
import h3_deepseek_streaming_linear as STREAM
from h4_c0_ordered_movement import strict_api, emit_template, CapacityGate, DISPATCH
from h4_c0_model import pinned, NATIVE

class ForwardObserver:
    def __init__(self, *, parent_context, fixture=False):
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
            if type(pc)!=int or not 0<=pc<len(dispatch['PC_dispatch']) or type(sm)!=int or not 0<=sm<32 or type(generation)!=int or not 0<generation<2**64:
                raise ValueError('parent PC/SM/generation extent')
            if not any(c['rank']==parent_context['rank'] and c['template']==parent_context['template'] for c in dispatch['PC_dispatch'][pc]['calls']):
                raise ValueError('parent actual PC/rank/template call missing')
            if dispatch['templates'][parent_context['template']]['execution_path']!=parent_context['expected_execution_path']:
                raise ValueError('parent forward path mismatch')
        self.context=dict(parent_context);self.fixture=fixture;self.leaves=[];self.api=strict_api()
        self.source_sha256=hashlib.sha256(pinned('tools/h3_deepseek_streaming_linear.py')).hexdigest()
        local=pathlib.Path(STREAM.__file__).read_bytes()
        if hashlib.sha256(local).hexdigest()!=self.source_sha256:
            raise ValueError('streaming source differs from immutable native pin')
    def execute(self,runner,program,inputs,kind):
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
            scope='fixture CPU leaf observation' if self.fixture else 'CPU leaf observation; parent handle/provider movement requires independent validation'))
        runner.fault|=vm.fault;runner.kernel_calls[kind]+=1;runner.counts.update(counts)
        return outputs
    def attach(self,runner):
        if runner.kernel_calls or runner.counts:raise ValueError('cannot attach after a running leaf has started')
        if not self.fixture:
            expected=tuple(self.context[k] for k in ('PC','version','rank','SM','generation'))
            if tuple(runner.owner)!=expected:raise ValueError('runner differs from verified parent owner')
        runner.execute=lambda program,inputs,kind:self.execute(runner,program,inputs,kind)
        return runner
    def receipt(self):
        return dict(schema='H4_C0_ACTUAL_STREAMING_LEAF_OBSERVATION_V1',native_source_pin=NATIVE,
            streaming_source_sha256=self.source_sha256,parent_context=self.context,
            fixture=self.fixture,leaves=self.leaves,hardware_qualification=False,physical_admission=False,
            whole_program_movement_qualified=False,provider_implementation_changed=False,
            missing_contract='Parent source count join plus actual provider refill/writeback ACK/reverse mapping; Dewey forward-leaf ABI extension required')
