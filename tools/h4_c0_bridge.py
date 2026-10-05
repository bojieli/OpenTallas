#!/usr/bin/env python3
"""Default-off C0 software control bridge. No new numeric/provider implementation.

Decode all source PCs/templates; operate finite home/ACK state at <=128 lanes.
Logical template records are NOT executable hardware commands. Ordered dynamic
continuations must be supplied by the existing native compiler/runtime adapter.
"""
from dataclasses import dataclass
import math,json,gzip
from pathlib import Path
from h4_c0_model import sources,pinned,AUDIT,bits
from h3_qwen_bounded_native import QWEN_ALIASES

class AdmissionError(ValueError):pass

class NativeDecoder:
    def __init__(self,qwen,deepseek,residence):
        self.programs={'Qwen':qwen,'DeepSeek':deepseek};self.home_index={}
        audit=json.loads(gzip.decompress(pinned('results/uarch/h4_native_rtl_binding_audit_20261002/family_bindings.json.gz',AUDIT)))
        self.sequence_bits={'Qwen':bits(max(sum(op['calendar_export']['physical_primitives']['native_primitive_commands'].values()) for op in qwen['operations'])+1),'DeepSeek':bits(max(math.prod(i['shape'] or [1]) for t in deepseek['templates'].values() for i in t['code'])*max(len(t['code']) for t in deepseek['templates'].values())+1)}
        self.required={(x['model'],x['family']):set(x['required_primitives']) for x in audit}
        self.consumers={}
        for name,p in self.programs.items():
            for op in p['operations'] if name=='Qwen' else p['instructions']:
                for v in op['reads']:
                    version=v if isinstance(v,str) else v['version'];self.consumers.setdefault((name,version),set()).add(op['pc'])
        for name,homes in [('Qwen',[h for v in qwen['operands'] for h in v['homes']]),('DeepSeek',residence['homes'])]:
            by_version={}
            for h in homes:by_version.setdefault(h['version'],[]).append(h)
            self.home_index[name]=by_version
    def source_home(self,model,version,rank,SM):
        found=[h for h in self.home_index[model].get(version,[]) if rank in h.get('rank_group',[h.get('rank',0)]) and h.get('SM',0)==SM]
        if len(found)!=1:raise AdmissionError('no unique declared source home for rank/SM/version')
        return found[0]
    def decode(self,model,pc):
        p=self.programs[model];ops=p['operations'] if model=='Qwen' else p['instructions']
        if not 0<=pc<len(ops):raise AdmissionError('PC out of source range')
        op=ops[pc]
        if op['pc']!=pc:raise AdmissionError('PC identity mismatch')
        return {'model':model,'pc':pc,'family':op.get('opcode',op.get('family')),'dependencies':list(op['dependencies']),'reads':list(op['reads']) if model=='Qwen' else [x['version'] for x in op['reads']],'writes':list(op['writes']) if model=='Qwen' else [x['version'] for x in op['writes']],'software_source_only':True,'hardware_admitted':False}
    def leaf(self,model,pc,*,rank=None,template=None,kernel=None):
        self.decode(model,pc);p=self.programs[model]
        if model=='Qwen':
            allowed=p['operations'][pc]['calendar_export']['physical_primitives']['kernel_invocations']
            if kernel not in allowed:raise AdmissionError('kernel not bound at source PC')
            code=p['microcode'][kernel]
        else:
            rank_binding=next((x for x in p['instructions'][pc]['rank_bindings'] if x['rank']==rank),None)
            if rank_binding is None or rank_binding.get('empty_owned_extent'):raise AdmissionError('empty/nonowned source rank')
            allowed={rank_binding.get('template')}|{b['template'] for b in rank_binding.get('buffer_programs',[])}
            if template not in allowed:raise AdmissionError('template not bound at source PC/rank')
            code=p['templates'][template]['code']
        # Preserve source order/shape and attrs; no gather/numeric family callback.
        for index,step in enumerate(code):
            op=step['op']
            primitive_ops=(['BITCAST_U','XOR','BITCAST_F'] if op=='NEG' else ['COPY'] if op=='MOV' else [QWEN_ALIASES.get(op,op)]) if model=='Qwen' else [op]
            for substep,primitive in enumerate(primitive_ops):
                yield {'source_pc':pc,'microstep':index,'substep':substep,'native_opcode':primitive,'source_step':step,'logical_only':True,'requires_existing_bounded_continuation':True}

@dataclass
class Home:
    version:str
    kind:str
    base:int
    span:int
    visible:bool=False
    completed:bool=False
    mirror_mask:int=0
    consumer_done:bool=False
    reverse_grant:bool=False
    provider_lease:str|None=None
    temporary:bool=False

class Bridge:
    def __init__(self,decoder,model,*,enabled=False,software_model=False,rank=0,SM=0,generation=0,entries=512):
        if not enabled:raise AdmissionError('C0 default off')
        if not software_model:raise AdmissionError('all51 family hardware gates remain closed')
        if generation<0 or generation>=2**64 or not 0<=SM<32 or not 0<=rank<(2 if model=='Qwen' else 96):raise AdmissionError('identity width/range')
        self.decoder=decoder;self.model=model;self.rank=rank;self.SM=SM;self.generation=generation;self.capacity=entries
        if entries<1:raise AdmissionError('finite positive capacity required')
        self.homes={};self.pc=None;self.done_pcs=set();self.sequence=0;self.pending=None;self.scratch_pending=None;self.provider_publications={};self.trace=[]
    def begin(self,pc):
        if self.pc is not None or self.pending or self.scratch_pending:raise AdmissionError('prior PC/command not completed')
        d=self.decoder.decode(self.model,pc)
        if not set(d['dependencies'])<=self.done_pcs:raise AdmissionError('dependency completion missing')
        if pc in self.done_pcs:raise AdmissionError('PC replay requires fresh drained generation')
        self.pc=pc;self.sequence=0;self.trace.append(('pc_accept',pc));return d
    def install(self,version,kind,base,span,*,external_visible=False,provider_lease=None):
        if self.pc is None:raise AdmissionError('no accepted source PC')
        source=self.decoder.source_home(self.model,version,self.rank,self.SM)
        declared=source.get('home',{});expected_kind=declared.get('class','control')
        if kind!=expected_kind:raise AdmissionError('source home class mismatch')
        if kind=='RF' and (base!=declared['slot_first'] or span!=declared['vectors']):raise AdmissionError('source RF encoding mismatch')
        if kind=='spill' and (base!=declared['byte_offset'] or span!=declared['bytes']):raise AdmissionError('source spill range mismatch')
        if source['birth_pc']>self.pc:raise AdmissionError('home born after current PC')
        if external_visible and source['birth_pc']>=0 and not provider_lease:raise AdmissionError('existing producer/provider visibility receipt required')
        if version in self.homes or sum(not h.temporary for h in self.homes.values())>=self.capacity:raise AdmissionError('finite table capacity or live tag reuse')
        if kind=='RF':
            if not isinstance(base,int) or not isinstance(span,int) or base<0 or span<1 or base+span>512:raise AdmissionError('RF512 vectors; no wrap')
            if any(h.kind=='RF' and base<h.base+h.span and h.base<base+span for h in self.homes.values()):raise AdmissionError('live RF home alias')
        elif kind=='scratch':
            if base<0 or span<1 or base%64 or span%64 or base+span>65536:raise AdmissionError('finite64B aligned scratch')
            if any(h.kind=='scratch' and base<h.base+h.span and h.base<base+span for h in self.homes.values()):raise AdmissionError('live scratch alias')
        elif kind in {'spill','control'}:
            if not provider_lease:raise AdmissionError('existing provider identity/lease required')
        else:raise AdmissionError('unknown home kind')
        self.homes[version]=Home(version,kind,base,span,external_visible,external_visible,3 if external_visible and kind=='RF' else 0,provider_lease=provider_lease)
    def install_temporary(self,slot,SSA_id,*,compiler_lease,paired_words=False):
        span=2 if paired_words else 1
        if self.pc is None or not compiler_lease or slot<0 or slot+span>32:raise AdmissionError('existing compiler lease and finite RF0..31 workspace required')
        version=f'C0.tmp.{self.pc}.{SSA_id}'
        if version in self.homes or any(h.kind=='RF' and slot<h.base+h.span and h.base<slot+span for h in self.homes.values()):raise AdmissionError('live temporary slot or SSA reuse')
        self.homes[version]=Home(version,'RF',slot,span,provider_lease=compiler_lease,temporary=True)
        return version
    def issue_publication(self,src,dst,*,provider_lease):
        family=self.decoder.decode(self.model,self.pc)['family'] if self.pc is not None else None
        if family not in {'KV_FENCE','QKV_SPLIT'} or not provider_lease:raise AdmissionError('typed existing fence/view adapter required')
        return self.issue('CONTROL_PUBLICATION',src,dst,publication_lease=provider_lease)
    def issue(self,opcode,src,dst,*,lanes=128,logical_shape=None,publication_lease=None):
        if self.pc is None or self.pending:raise AdmissionError('single outstanding RF transaction')
        family=self.decoder.decode(self.model,self.pc)['family']
        if opcode=='CONTROL_PUBLICATION':
            if family not in {'KV_FENCE','QKV_SPLIT'} or not publication_lease:raise AdmissionError('control publication unbound')
        elif opcode not in self.decoder.required[(self.model,family)]:raise AdmissionError('opcode not in pinned family primitive contract')
        if not 1<=lanes<=128 or (logical_shape is not None and math.prod(logical_shape or [1])>128):raise AdmissionError('logical full shape requires existing bounded compiler continuation')
        for v in src:
            if v not in self.homes or not self.homes[v].visible:raise AdmissionError('read before actual completion/visibility ACK')
        if dst not in self.homes:raise AdmissionError('unbound output home')
        # Numeric capability never follows from being decoded or emulated.
        if self.sequence+1>=2**self.decoder.sequence_bits[self.model]:raise AdmissionError('finite command sequence requires drained new generation, no wrap')
        self.sequence+=1;ticket=(self.generation,self.pc,self.sequence,self.rank,self.SM)
        self.pending={'ticket':ticket,'opcode':opcode,'dst':dst,'completed':False,'mirror_mask':0,'accepted':False,'reads':tuple(src)}
        h=self.homes[dst];h.visible=False;h.completed=False;h.mirror_mask=0;h.consumer_done=False;h.reverse_grant=False
        self.trace.append(('issued',ticket,opcode));return ticket
    def _owned(self,ticket):
        if self.pending is None or self.pending['ticket']!=ticket:raise AdmissionError('stale/wrong/no command owner')
        return self.pending
    def complete(self,ticket):
        p=self._owned(ticket)
        if p['completed']:raise AdmissionError('duplicate completion')
        p['completed']=True;self.homes[p['dst']].completed=True;self.trace.append(('completed',ticket))
    def ack(self,ticket,mirror):
        p=self._owned(ticket);h=self.homes[p['dst']]
        if not p['completed']:raise AdmissionError('ACK before produced completion')
        if h.kind!='RF' or mirror not in (0,1) or p['mirror_mask']&(1<<mirror):raise AdmissionError('wrong/duplicate mirror ACK')
        p['mirror_mask']|=1<<mirror;h.mirror_mask=p['mirror_mask'];h.visible=h.mirror_mask==3
        self.trace.append(('mirror_ACK',ticket,mirror))
    def provider_visible(self,ticket,lease):
        p=self._owned(ticket);h=self.homes[p['dst']]
        if h.kind not in {'scratch','spill','control'} or not p['completed'] or lease!=h.provider_lease or not lease:raise AdmissionError('owned provider visibility missing')
        h.visible=True;self.trace.append(('provider_visibility_ACK',ticket,lease))
    def accept_done(self,ticket):
        p=self._owned(ticket)
        if not p['completed'] or not self.homes[p['dst']].visible:raise AdmissionError('completion acceptance before visibility')
        self.trace.append(('done_accept',ticket));self.pending=None
    def retire(self,version,*,consumers_done=False,reverse_grant=False):
        if version not in self.homes:raise AdmissionError('unknown/released version')
        h=self.homes[version]
        if self.pending and self.pending['dst']==version:raise AdmissionError('transaction still owns home')
        needed=self.decoder.consumers.get((self.model,version),set())
        if consumers_done and not needed<=self.done_pcs:raise AdmissionError('source consumers not all completed')
        h.consumer_done|=consumers_done;h.reverse_grant|=reverse_grant
        if not (h.visible and h.consumer_done and h.reverse_grant):return False
        del self.homes[version];self.trace.append(('home_release',version));return True
    def scratch_issue(self,byte_address,*,frame_lease,size=64):
        if self.pc is None or self.scratch_pending:raise AdmissionError('finite single scratch owner')
        if not frame_lease or byte_address<0 or byte_address%64 or size!=64 or byte_address+size>65536:raise AdmissionError('existing frame lease,64B beat,10-bit address required')
        if self.sequence+1>=2**self.decoder.sequence_bits[self.model]:raise AdmissionError('finite command sequence requires drained new generation, no wrap')
        self.sequence+=1;ticket=(self.generation,self.pc,self.sequence,self.rank,self.SM)
        self.scratch_pending={'ticket':ticket,'frame_lease':frame_lease,'address':byte_address//64,'done':False}
        self.trace.append(('scratch_accept',ticket,byte_address//64));return ticket
    def scratch_complete(self,ticket):
        if not self.scratch_pending or self.scratch_pending['ticket']!=ticket or self.scratch_pending['done']:raise AdmissionError('scratch stale/duplicate completion')
        self.scratch_pending['done']=True;self.trace.append(('scratch_completed',ticket))
    def scratch_accept_done(self,ticket,frame_lease):
        p=self.scratch_pending
        if not p or p['ticket']!=ticket or not p['done'] or p['frame_lease']!=frame_lease:raise AdmissionError('scratch completion owner/lease missing')
        self.trace.append(('scratch_done_accept',ticket));self.scratch_pending=None
    def external_publication(self,version,*,provider_owner_tag,generation):
        if self.pc is None or version not in self.decoder.decode(self.model,self.pc)['writes'] or not provider_owner_tag or generation!=self.generation:raise AdmissionError('existing provider publication identity mismatch')
        if version in self.decoder.home_index[self.model]:raise AdmissionError('resident home requires actual local visibility ACK')
        self.provider_publications[version]=(provider_owner_tag,generation)
        self.trace.append(('existing_provider_publication',version,provider_owner_tag))
    def finish(self):
        if self.pc is None or self.pending or self.scratch_pending or any(h.temporary for h in self.homes.values()):raise AdmissionError('PC completion requires command transactions and compiler temporaries drained')
        for version in self.decoder.decode(self.model,self.pc)['writes']:
            try:self.decoder.source_home(self.model,version,self.rank,self.SM)
            except AdmissionError:
                if version not in self.decoder.home_index[self.model] and version not in self.provider_publications:raise AdmissionError('nonresident output requires existing provider publication')
                continue  # explicitly nonowned/empty rank/SM home
            if version not in self.homes or not self.homes[version].visible:raise AdmissionError('PC output not visible at declared home')
        self.done_pcs.add(self.pc);self.trace.append(('pc_completed',self.pc));self.pc=None

class ExistingPrimitiveAdapter:
    """CPU-only wrapper over existing native primitive VM; never RTL capability."""
    def __init__(self,bridge,primitive_vm):self.bridge=bridge;self.vm=primitive_vm
    def execute(self,opcode,args,src,dst,*,attrs=None,shape=None):
        n=math.prod(shape or [1]);t=self.bridge.issue(opcode,src,dst,lanes=n,logical_shape=shape)
        # Existing VM owns numerical semantics and faults; failed primitive retains ownership.
        value=self.vm.primitive(opcode,args,attrs=attrs,shape=shape)
        self.bridge.complete(t)
        if self.bridge.homes[dst].kind!='RF':raise AdmissionError('external provider owns nonRF visibility, no automatic ACK')
        self.bridge.ack(t,0);self.bridge.ack(t,1);self.bridge.accept_done(t)
        return value,{'scope':'CPU_PRIMITIVE_ONLY','hardware_qualified':False,'ticket':t}

# Reuse Dewey's exact committed control validator; no alternate finite calendar.
from functools import lru_cache
import ast,hashlib,copy
from h4_c0_model import pinned,DEWEY
@lru_cache(maxsize=1)
def dewey_scoreboard_class():
    raw=pinned('tools/h3_complete_native_calendar.py',DEWEY)
    tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'positive','C0VersionScoreboard'}]
    if len(nodes)!=2:raise AdmissionError('pinned Dewey control ABI missing')
    ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'Dewey@'+DEWEY,'exec'),ns)
    return ns['C0VersionScoreboard']

class DeweyControlAdapter:
    """Actual-source local endpoint beneath the shared finite lifecycle validator."""
    def __init__(self,bridge,ledger=None):
        self.bridge=bridge;self.ledger=ledger if ledger is not None else dewey_scoreboard_class()(entries=512)
        if bridge.generation<1:raise AdmissionError('Dewey requires positive generation')
    def identity(self,version):return (self.bridge.rank,self.bridge.SM,version,self.bridge.generation)
    def bind(self,version):
        if sum(i[:2]==(self.bridge.rank,self.bridge.SM) for i in self.ledger.live)>=512:raise AdmissionError('Dewey finite512 entries perSM')
        h=self.bridge.homes[version]
        if h.kind!='RF':raise AdmissionError('nonRF source needs existing certified physical provider extent; no fabricated HBM mapping')
        readers={('PC',pc,version) for pc in self.bridge.decoder.consumers.get((self.bridge.model,version),set()) if pc not in self.bridge.done_pcs}
        self.ledger.publish(self.identity(version),('RF',h.base*512,h.span*512),visible=h.visible,future_readers=readers)
    def issue(self,opcode,src,dst,**kwargs):
        owner=(self.bridge.rank,self.bridge.SM)
        if any(c['destination'][:2]==owner for c in self.ledger.commands.values()):raise AdmissionError('one command credit held through reverse retirement')
        # Shared validator checks before mutating local endpoint.
        if self.identity(dst) not in self.ledger.live or any(self.identity(v) not in self.ledger.live for v in src):raise AdmissionError('shared version/home identity unbound')
        # Trial the reused ledger before any local visibility mutation.
        trial=copy.deepcopy(self.ledger)
        t=(self.bridge.generation,self.bridge.pc,self.bridge.sequence+1,self.bridge.rank,self.bridge.SM)
        trial.accept(t,[self.identity(v) for v in src],self.identity(dst))
        actual=self.bridge.issue(opcode,src,dst,**kwargs)
        if actual!=t:raise AdmissionError('sequence identity disagreement')
        self.ledger.__dict__.clear();self.ledger.__dict__.update(trial.__dict__);return actual
    def complete(self,ticket):self.bridge.complete(ticket);self.ledger.transition(ticket,'complete')
    def ack(self,ticket,mirror):
        self.bridge.ack(ticket,mirror)
        if self.bridge.homes[self.bridge.pending['dst']].mirror_mask==3:self.ledger.transition(ticket,'mirrored_visible_ACK')
    def accept_done(self,ticket):self.bridge.accept_done(ticket);self.ledger.transition(ticket,'consumer_accept')
    def reverse_retire(self,ticket):self.ledger.transition(ticket,'reverse_grant');self.ledger.transition(ticket,'retire')
    def resolve_future_PC(self,pc):
        if pc not in self.bridge.done_pcs:raise AdmissionError('future reader not completed')
        for identity,e in self.ledger.live.items():e['future_readers'].discard(('PC',pc,identity[2]))
    def release(self,version):
        identity=self.identity(version);h=self.bridge.homes[version]
        needed=self.bridge.decoder.consumers.get((self.bridge.model,version),set())
        if not h.visible or not needed<=self.bridge.done_pcs or (self.bridge.pending and self.bridge.pending['dst']==version):raise AdmissionError('local source visibility/readers/command still own version')
        trial=copy.deepcopy(self.ledger);trial.release(identity)
        if not self.bridge.retire(version,consumers_done=True,reverse_grant=True):raise AdmissionError('local source lease remains')
        self.ledger.__dict__.clear();self.ledger.__dict__.update(trial.__dict__)

class CommandEncoder:
    """Fixed512-bit scalar control envelope; no payload or numerical implementation."""
    def __init__(self,fields,opcodes):
        self.fields=dict(sorted(fields.items()));self.opcodes={op:i for i,op in enumerate(sorted(opcodes))}
        if sum(self.fields.values())>512:raise AdmissionError('control envelope overflow')
    def encode(self,values):
        if set(values)!=set(self.fields):raise AdmissionError('missing or extra control fields')
        if values['opcode'] not in self.opcodes.values() or not 1<=values['active_lanes']<=128:raise AdmissionError('unknown opcode or non128lane active mask')
        result=offset=0
        for field,width in self.fields.items():
            value=values[field]
            if type(value)!=int or not 0<=value<2**width:raise AdmissionError('control field overflow: '+field)
            result|=value<<offset;offset+=width
        return result.to_bytes(64,'little')
    def decode(self,word):
        if len(word)!=64:raise AdmissionError('actual64B control word')
        value=int.from_bytes(word,'little');offset=0;out={}
        for field,width in self.fields.items():out[field]=(value>>offset)&(2**width-1);offset+=width
        if value>>offset:raise AdmissionError('reserved control bits nonzero')
        if out['opcode'] not in self.opcodes.values() or not 1<=out['active_lanes']<=128:raise AdmissionError('decoded opcode/lane range')
        return out


def shared_rank_ledger():
    '''One shared32SM ledger, preserving global HBM alias detection and local caps.'''
    return dewey_scoreboard_class()(entries=32*512)
