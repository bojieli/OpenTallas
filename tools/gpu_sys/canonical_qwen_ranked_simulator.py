"""Actual two-rank enclosing pin API; no process, reset or provider emulation.

Only host pin slicing is flattened. Controller PC_ID remains seven bits and
rank is an explicit physical-bank context. Source mapping and native handlers
remain their owners' obligations; this module never manufactures those grants.
"""
import json, threading
from pathlib import Path
from tools.gpu_sys.canonical_qwen_simulator import (EnclosingPins, ComponentPins,
    PARAMETERS, NATIVE_KINDS, KVControllerPort, KVHandlers, RFPageHandlers, ALL_KINDS)
from tools.gpu_sys.canonical_qwen_sector_authority import (PhysicalSectorAuthority,
    SectorBoundPayload, _CallerAuthority)
from tools.gpu_sys.canonical_qwen_payload_w2 import PayloadRoute, PayloadW2Adapter
from tools.gpu_sys.canonical_qwen_transport import TransportError

PORTBOOK=Path(__file__).resolve().parents[2]/'rtl/model/qwen_hbm_integrated_20261003/ranked/ports.json'


class RankedEnclosingPins(EnclosingPins):
    def __init__(self,reader,writer,*,portbook=PORTBOOK):
        self.reader,self.writer=reader,writer
        self.book=json.loads(Path(portbook).read_text())
        inv=self.book['inventory']
        if (self.book['top']!='ot_gpu_qwen_hbm_integrated_ranked' or
            (inv['rank_count'],inv['W2_PC_per_rank'],inv['W2_total'])!=(2,128,256)):
            raise TransportError('rank-qualified actual topology required')
        self.hooks=[];self.edge_open=self.stopped=False;self.edges=0
        self.lock=threading.RLock()
        hello=self._rpc('HELLO')
        if hello!='ot_gpu_qwen_hbm_integrated_ranked ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128':
            self.stopped=True
            raise TransportError('compiled rank-qualified topology differs: '+hello)

    def component(self,block,index=0,*,rank=None,aliases=None):
        if block=='w2':
            if type(rank) is not int or rank not in (0,1) or type(index) is not int or not 0<=index<128:
                raise TransportError('W2 requires explicit rank0/1 and inner PC0..127')
            return RankedComponentPins(self,block,rank*128+index,aliases=aliases)
        if rank is not None:
            raise TransportError('rank argument reserved for physical W2 bank')
        return RankedComponentPins(self,block,index,aliases=aliases)

    def add_edge_hook(self,hook):
        if self.edge_open or self.hooks or self.stopped:
            raise TransportError('one enclosing hook enrollment before traffic')
        if not all(callable(getattr(hook,n,None)) for n in ('before_edge','after_edge')):
            raise TransportError('both actual edge hook methods required')
        if self.edges and (not self.get('kv_idle') or self.get('sector_grant_live') or
            self.get('sector_fault') or self.get('w2_idle')!=(1<<256)-1):
            raise TransportError('cannot enroll hook with actual accepted bank debt')
        self.hooks.append(hook)


class RankedComponentPins(ComponentPins):
    def __init__(self,root,block,index,*,aliases=None):
        counts={'sector':1,'kv':1,'native':1,'sm':64,'w2':256,'issuer':1,'state':1,'rfdrain':64,'rfjoin':2,'local':1,'state_rpc':1}
        if block not in counts or type(index) is not int or not 0<=index<counts[block]:
            raise TransportError('actual rank-qualified instance')
        self.root,self.block,self.index=root,block,index
        self.aliases=dict(aliases or {})

    def parameter(self,name):
        if self.block in ('issuer','state','rfdrain','rfjoin','local','state_rpc') and name=='ENABLE':return 1
        if self.block=='sm' and name=='OPT_CONTEXT':return 1
        if self.block=='sm' and name=='INSTANCE_ID':return self.index
        if self.block=='w2' and name=='PC_ID':return self.index%128
        if self.block=='w2' and name=='RANK_ID':return self.index//128
        return super().parameter(name)


class RankedPhysicalSectorAuthority(PhysicalSectorAuthority):
    def __init__(self,pins,w2_ports,*,enabled=False):
        if not enabled or pins.parameter('ENABLE')!=1 or pins.parameter('IDENTW')!=207:
            raise TransportError('ranked physical authority default off/width')
        self.pins,self.w2_ports=pins,dict(w2_ports)
        self.snapshot=None;self.release_armed=False
        required={(rank,pc) for rank in range(2) for pc in range(128)}
        if set(self.w2_ports)!=required:
            raise TransportError('both complete rank-local128 W2 banks required')
        for key,port in self.w2_ports.items():
            rank,pc=key
            if (port.ports.parameter('PC_ID'),port.ports.parameter('RANK_ID'))!=(pc,rank):
                raise TransportError('physical bank context differs from port binding')
            if isinstance(port.authority,_CallerAuthority):
                raise TransportError('W2 caller authority already bound')
        # Check all before wrapping any; refusal cannot partially enroll banks.
        for key,port in self.w2_ports.items():
            port.authority=_CallerAuthority(self,key,port.authority)

    @staticmethod
    def bank(fields):return ((fields['key']>>13)&1,fields['PC'])

    def _route(self,fields):
        port=self.w2_ports[self.bank(fields)]
        return PayloadRoute(port,fields['client'],fields['address'],fields['tag'],fields['generation'],self.snapshot)

    def payload_reverse(self,bank,client,tag,generation,write):
        fields=self._sample()
        if fields is None or (self.bank(fields),fields['client'],fields['tag'],fields['generation'])!=(bank,client,tag,generation):
            return None
        return self.pins.get('grant_phase')==(self.RELEASE if write else self.NEW_REQ)


class RankedSectorBoundPayload(SectorBoundPayload):
    def __init__(self,controller,authority_pins,w2_ports,*,enabled=False):
        self.authority=RankedPhysicalSectorAuthority(authority_pins,w2_ports,enabled=enabled)
        self.payload=PayloadW2Adapter(controller,self.authority,enabled=enabled)


def build(pins,authority,native_handlers,w2_ports,*,enabled=False):
    if not enabled or not isinstance(pins,RankedEnclosingPins):
        raise TransportError('actual ranked canonical simulator default off')
    if set(native_handlers)!=set(NATIVE_KINDS) or any(not callable(v) for v in native_handlers.values()):
        raise TransportError('four actual native/source handlers required')
    controller=KVControllerPort(pins.component('kv'),authority)
    payload=RankedSectorBoundPayload(pins.component('kv'),pins.component('sector'),w2_ports,enabled=True)
    kv=KVHandlers(authority,controller.handlers);rf=RFPageHandlers(authority)
    from tools.gpu_sys.canonical_qwen_state_rpc_join import StateRPCByteHandlers
    state=StateRPCByteHandlers(authority,pins.component('state_rpc'),enabled=True)
    handlers=dict(native_handlers,source_page_write=rf.source_page_write,source_page_read=rf.source_page_read,**kv.handlers)
    for kind in ('kv_state_read','kv_state_write'):handlers[kind]=state.handlers[kind]
    if set(handlers)!=set(ALL_KINDS):raise TransportError('sixteen actual handlers required')
    pins.add_edge_hook(payload)
    return dict(handlers=handlers,pins=pins,payload=payload,controller=controller,rf=rf,kv=kv,state=state)
