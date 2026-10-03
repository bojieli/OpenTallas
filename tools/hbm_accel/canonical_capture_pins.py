"""Actual HA1 pins on Euclid's shared ranked assembly. No runtime authority store.
The inherited enclosing API owns the only clock and existing single edge hook.
"""
import json,threading
from pathlib import Path
from tools.gpu_sys.canonical_qwen_ranked_simulator import RankedEnclosingPins,RankedComponentPins
from tools.gpu_sys.canonical_qwen_simulator import ComponentPins
from tools.gpu_sys.canonical_qwen_transport import TransportError
ROOT=Path(__file__).resolve().parents[2]
PORTBOOK=ROOT/'rtl/hbm_accel/txcount/ranked/ports.json'
TOP='ot_gpu_qwen_hbm_integrated_ranked_ha1'

class ActualCapturePins(RankedEnclosingPins):
    def __init__(self,reader,writer,*,portbook=PORTBOOK):
        self.reader,self.writer=reader,writer
        self.book=json.loads(Path(portbook).read_text());inv=self.book['inventory']
        if self.book['top']!=TOP or (inv['rank_count'],inv['W2_PC_per_rank'],inv['W2_total'],inv['HA1_capture_join_count'])!=(2,128,256,64):
            raise TransportError('actual ranked HA1 source selection required')
        self.hooks=[];self.edge_open=self.stopped=False;self.edges=0;self.lock=threading.RLock()
        hello=self._rpc('HELLO')
        if hello!=TOP+' ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128' or not self.get('ha1_enabled'):
            self.stopped=True
            raise TransportError('compiled source lacks explicitly enabled actual HA1 join')

    def component(self,block,index=0,*,rank=None,aliases=None):
        if block!='ha1':return super().component(block,index,rank=rank,aliases=aliases)
        if rank is not None or type(index) is not int or not 0<=index<64:
            raise TransportError('explicit physical HA1 index rank*32+SM required')
        return CaptureComponent(self,block,index,aliases=aliases)

class CaptureComponent(ComponentPins):
    def __init__(self,root,block,index,*,aliases=None):
        self.root,self.block,self.index=root,block,index;self.aliases=dict(aliases or {})
    def parameter(self,name):
        if name=='ENABLE':return self.root.get('ha1_enabled')
        if name=='INDEX':return self.index
        raise TransportError('actual capture component parameter '+name)
    def dependency(self):
        """Read the held hardware result; never create a completion or retire debt."""
        self.settle()
        if self.get('fault'):raise TransportError('captured HA1 context quarantined')
        if not self.get('dependency_valid'):return None
        if not self.get('retained'):raise TransportError('completion without actual retained GO')
        return (self.get('dependency_tuple'),self.get('dependency_owner55'),self.get('dependency_page_mask'))
