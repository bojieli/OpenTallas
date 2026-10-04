"""Physical range-owner RF authority. Constructors never tick or grant a lease.

Requires installed `source_owner` components and actual W4 host arbitration.
The whole tuple comes from the captured hardware input binding, never from an
output-version inference or a Python owner/clean/READY dictionary.
"""
from tools.gpu_sys.canonical_qwen_source_mapping import uint
from tools.gpu_sys.canonical_qwen_ranked_source_placement import RF_component
from tools.gpu_sys.canonical_qwen_rf_ports import RFPorts
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA

ABI='canonical-qwen-range-owner-239-r2'

class RangeOwnerPort:
    def __init__(self,physical,index):
        uint(index,6,'source SM index')
        if physical.parameter('ENABLE')!=1 or physical.parameter('SM_INDEX')!=index:
            raise TransportError('actual enabled source-owner instance/index required')
        self.physical=physical
        # These reads check the installed ports, not their positive runtime values.
        for name in ('fault','issued_input_live','issued_input_started',
                     'inputs_bound_tuple','query_result_valid','source_owner_retained',
                     'query_result_tuple','query_result_owner','query_result_slot'):
            physical.get(name)

    def current_issue(self,PC):
        p=self.physical;p.settle()
        if p.get('fault') or not p.get('issued_input_live') or not p.get('issued_input_started'):
            raise TransportError('source issue is not actually held/accepted')
        t=uint(p.get('inputs_bound_tuple'),239,'hardware input association')
        if (t>>164)&2047!=PC:
            raise TransportError('source callback does not match actual accepted whole PC')
        return t

    def resolve(self,tuple239,version,slot,write):
        p=self.physical
        for k,v in dict(query_tuple=tuple239,query_version=version,query_slot=slot,
                        query_write=int(write),query_result_ready=0,query_valid=1).items():p.set(k,v)
        try:
            while True:
                p.settle()
                if p.get('fault'):raise TransportError('physical source query fault')
                accepted=bool(p.get('query_ready'));p.tick()
                if accepted:break
            p.set('query_valid',0)
            while True:
                p.settle()
                if p.get('fault'):raise TransportError('physical source query fault')
                if p.get('query_result_valid'):
                    if not p.get('source_owner_retained') or p.get('query_result_tuple')!=tuple239 or p.get('query_result_slot')!=slot:
                        raise TransportError('actual held source query identity changed')
                    return uint(p.get('query_result_owner'),46,'held original owner')
                p.tick()
        except BaseException:
            p.set('query_valid',0);p.set('query_result_ready',0)
            raise

    def complete_page(self,tuple239,slot,owner):
        p=self.physical;p.settle()
        if p.get('fault') or not p.get('query_result_valid') or not p.get('source_owner_retained'):
            raise TransportError('source lease not physically retained after actual W4 operation')
        if (p.get('query_result_tuple'),p.get('query_result_slot'),p.get('query_result_owner'))!=(tuple239,slot,owner):
            raise TransportError('retained whole source/slot/original owner mismatch')
        p.set('query_result_ready',1);p.settle()
        if not p.get('query_result_valid') or not p.get('source_owner_retained'):
            p.set('query_result_ready',0)
            raise TransportError('source query changed before positive capture edge')
        p.tick();p.set('query_result_ready',0)
        # This True follows the sampled held hardware and its real capture edge.
        # It releases the QUERY seat only, never the published source row.
        return True

class PhysicalRangeSourceAuthority:
    """RF part of the factory authority; retained KV/sector authority is separate.

    `resolve_source` and `source_owner_retained` implement the unchanged RFPage
    handler API. No constructor changes RF/HBM payload hooks or native handlers.
    """
    def __init__(self,pins,placement):
        self.pins=pins;self.placement=placement
        self.owners=tuple(RangeOwnerPort(pins.component('source_owner',i),i) for i in range(64))
        self.RF=tuple(RFPorts(RF_component(pins,type('Home',(),dict(rank=i//32,sm=i%32))())) for i in range(64))

    def _association(self,request):
        if request.get('program_sha256')!=PROGRAM_SHA:
            raise TransportError('canonical program identity')
        key=request.get('source_key')
        if not isinstance(key,list) or len(key)!=4 or key[0]!='RF':raise TransportError('RF source key')
        rank=uint(key[1],1,'RF rank');sm=uint(key[2],5,'RF SM');slot=uint(key[3],9,'RF slot')
        version=request.get('version');PC=uint(request.get('source_PC'),11,'whole native PC')
        h=self.placement.rf.get((version,rank,sm))
        if h is None or not h.first<=slot<h.end or request.get('lease')!='value:'+version:
            raise TransportError('source page/version/range is not canonical')
        port=self.owners[rank*32+sm]
        tuple239=port.current_issue(PC)
        return port,tuple239,slot,self.placement.version_ids[version],rank*32+sm

    def resolve_source(self,request,write):
        port,t,slot,vid,index=self._association(request)
        owner=port.resolve(t,vid,slot,write)
        return self.RF[index],owner

    def source_owner_retained(self,request,owner46):
        port,t,slot,_,_=self._association(request)
        return port.complete_page(t,slot,uint(owner46,46,'source owner'))


def build_RF_authority(pins,placement):
    """Enroll existing hardware only. Missing source_owner pins fail closed.

    Euclid installs these new components with actual row/GO/RF ACK connections.
    This function performs no clock edges, native dispatch or grant creation.
    """
    return PhysicalRangeSourceAuthority(pins,placement)
