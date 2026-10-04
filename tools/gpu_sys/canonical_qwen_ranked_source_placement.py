"""Injective r17 sector placement into the actual two-rank256-PC pin API.

Returns static component references only: no request, allocation, READY, ACK,
reverse receipt or clock is generated. Runtime ownership stays in hardware.
"""
from dataclasses import dataclass
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement,uint
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.gpu_sys.canonical_qwen_simulator import RF_HOST_ALIASES


@dataclass(frozen=True)
class RankedSector:
    rank:int
    PC:int
    address:int
    source_address:int
    bank:int

    def __post_init__(self):
        uint(self.rank,1,'outer rank');uint(self.PC,7,'inner PC')
        uint(self.address,34,'physical byte');uint(self.source_address,34,'source byte')
        uint(self.bank,5,'bank')
        if self.address%32 or self.source_address%32:
            raise TransportError('32B sector alignment')
        if self.inverse()!=self.source_address:
            raise TransportError('physical/source address does not round trip')
        p=SourcePlacement.stripe(self.rank,self.source_address)
        if self.PC!=(p['stack']*32+p['PC']) or self.address!=p['stack_local_byte'] or self.bank!=p['bank']:
            raise TransportError('ranked bank/PC/address source mismatch')

    def inverse(self):
        return (self.address//128)*512+(self.PC//32)*128+self.address%128

    def component(self,pins):
        # No get_client: W2PrimaryPort itself extracts the packed NC6 fields.
        component=pins.component('w2',self.PC,rank=self.rank)
        if (component.parameter('RANK_ID'),component.parameter('PC_ID'))!=(self.rank,self.PC):
            raise TransportError('actual physical instance does not match static placement')
        return component


def sector(rank,source_address):
    uint(rank,1,'outer rank');uint(source_address,34,'source address')
    if source_address%32:raise TransportError('sector source alignment')
    p=SourcePlacement.stripe(rank,source_address)
    return RankedSector(rank,p['stack']*32+p['PC'],p['stack_local_byte'],source_address,p['bank'])


def RF_component(pins,home):
    uint(home.rank,1,'RF rank');uint(home.sm,5,'RF SM')
    return pins.component('sm',home.rank*32+home.sm,aliases=RF_HOST_ALIASES)
