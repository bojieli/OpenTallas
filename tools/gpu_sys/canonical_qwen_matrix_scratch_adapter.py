"""MATRIX client for Euclid's single held-GO scratch mux. No private clock.

The selected mux protects GO239, owner55 and aperture through actual done.
Nash drives workspace pins from his physical allocator, never this adapter.
Original SM output aliases and historical services remain unchanged.
"""
from copy import deepcopy
from tools.gpu_sys import canonical_qwen_matrix_services as S
from tools.gpu_sys import canonical_qwen_service_calendar as C

ALIASES={n:'client_'+n for n in ('valid','write','addr','wdata','ready','done','done_ready','rdata')}
FIELDS={'client_valid':('input',1),'client_write':('input',1),'client_addr':('input',10),
        'client_wdata':('input',512),'client_done_ready':('input',1),
        'client_owner':('input',55),'client_tuple':('input',239),
        'client_ready':('output',1),'client_done':('output',1),'client_rdata':('output',512),
        'workspace_valid':('input',1),'workspace_exclusive':('input',1),
        'workspace_owner':('input',55),'workspace_tuple':('input',239),
        'workspace_base':('input',10),'workspace_length':('input',11),
        'busy':('output',1),'drained':('output',1),'fault':('output',1)}

def fields_for_book(book):
    fields = dict(FIELDS)
    if 'manifest_contract' in book:
        from tools.gpu_sys.canonical_qwen_manifest_simulator import validate_manifest_book
        validate_manifest_book(book)
        for name, (_, width) in fields.items():
            if name.startswith('workspace_'):
                fields[name] = ('output', width)
    return fields


class ScratchPump(S.ScratchPump):
    def __init__(self,pins):
        C.need(getattr(pins,'block',None)=='scratch' and pins.aliases==ALIASES,
               'Euclid actual scratch INPUT client, never SM output aliases')
        C.need(pins.parameter('ENABLE_CLIENT')==1 and pins.parameter('INDEX')==pins.index,
               'actual enabled scratch client index')
        for n,(direction,width) in fields_for_book(pins.root.book).items():
            p=pins.root.book['pins'].get('scratch_'+n,{})
            C.need(p.get('direction')==direction and p.get('leaf_bits')==width
                   and p.get('count')==64 and p.get('bits')==64*width,
                   'actual scratch mux pin direction/width '+n)
        super().__init__(pins)
        self.context=pins.root.component('scratch',pins.index)
        self.binding=None;self.faulted=False
    def bind(self,reservation,origin):
        C.need(self.phase=='idle' and self.binding is None,'one source-owned scratch workspace')
        ident=reservation['identity'];go=origin['GO_tuple239']
        C.need(go==S.pack_GO(origin['identity']) and ident==origin['identity'],
               'workspace exact whole GO239 identity, no output inference')
        C.need(ident['rank']*32+ident['SM']==self.p.index,'captured execution rank/SM')
        self.binding=(go,ident['owner55'],reservation['scratch_base'],reservation['rows'])
        self.aperture=self.context.get('workspace_length')
        self._check()
    def _check(self):
        C.need(not self.faulted and self.binding is not None,'retained scratch source binding')
        try:
            go,owner,base,rows=self.binding;p=self.context
            C.need(not p.get('fault') and p.get('workspace_valid')==1
                   and p.get('workspace_exclusive')==1,'actual exclusive workspace retained')
            C.need((p.get('workspace_tuple'),p.get('workspace_owner'),p.get('workspace_base'),
                    p.get('workspace_length'))==(go,owner,base,self.aperture),
                   'actual protected workspace GO/owner/aperture unchanged')
            C.need(rows<=self.aperture<=1024 and base+self.aperture<=1024,'source workspace row bounds')
        except BaseException:
            self.faulted=True
            raise
    def start(self,address,data=None):
        self._check();base=self.binding[2]
        C.need(base<=address<base+self.aperture,'source-owned scratch address aperture')
        super().start(address,data)
    def before_edge(self):
        if self.phase not in ('idle','complete'):
            self._check()
            self.context.set('client_tuple',self.binding[0])
            self.context.set('client_owner',self.binding[1])
        super().before_edge()
    def unbind(self):
        C.need(not self.faulted and self.phase=='idle' and not self.context.get('fault')
               and self.context.get('drained')==1 and not self.context.get('busy'),
               'actual scratch done/reverse drained before workspace release')
        self.binding=None

class MatrixPhysicalServices(S.MatrixPhysicalServices):
    def __init__(self,authority,scratch_pins,*,enabled=False):
        super().__init__(authority,scratch_pins,enabled=enabled)
        self.scratch=ScratchPump(scratch_pins)
        from tools.gpu_sys.canonical_qwen_matrix_tc_pins import ConsumptionAuthority
        if isinstance(authority,ConsumptionAuthority):authority.attach(self)
    def before_edge(self):
        try:
            super().before_edge()
            from tools.gpu_sys.canonical_qwen_matrix_tc_pins import ConsumptionAuthority
            if isinstance(self.a,ConsumptionAuthority):self.a.before_edge()
        except BaseException:
            self.faulted=True
            raise
    def after_edge(self):
        try:
            super().after_edge()
            from tools.gpu_sys.canonical_qwen_matrix_tc_pins import ConsumptionAuthority
            if isinstance(self.a,ConsumptionAuthority):self.a.after_edge()
        except BaseException:
            self.faulted=True
            raise
    def reserve_tile(self,d):
        try:
            r=super().reserve_tile(d)
            if r is not None:self.scratch.bind(deepcopy(r),deepcopy(self.origin))
            return r
        except BaseException:
            self.faulted=True
            raise
    def release_tile(self,r,receipt):
        try:
            # Check physical debt BEFORE asking authority to release workspace.
            C.need(self.scratch.phase=='idle' and self.scratch.context.get('drained')==1
                   and not self.scratch.context.get('fault'),'actual scratch reverse before release')
            result=super().release_tile(r,receipt)
            if result:self.scratch.unbind()
            return result
        except BaseException:
            self.faulted=True
            raise
