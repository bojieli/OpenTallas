"""Captured workspace staging; borrowed published RF sources stay readonly.

Additive successor of88f26. Same sealed cursor and same64 contexts. No perRPC
frame-close: issuer fullPC FRAME_ACCEPT remains the enclosing hardware's job.
"""
from tools.gpu_sys.canonical_qwen_native_factory import need
from tools.gpu_sys.canonical_qwen_native_source_cursor import (
    SourceCursorBinding, compile_command)
from tools.gpu_sys.canonical_qwen_native_rf_pump import (
    RFNativeHandlers, HeldRFCommand, OwnedPage, PageInitializer)


class SourceStaging:
    def __init__(self, root, collector):
        need(collector.root is root, 'one captured source clock')
        self.root, self.collector = root, collector
        self.initializer = PageInitializer(root)

    def workspace(self, request, binding, operand):
        """Read role from retained physical record, never a host staging flag."""
        p=self.collector; p.settle()
        need(not p.get('fault') and p.get('context_live') and p.get('source_cursor_valid')
             and (p.get('authority_tuple'), p.get('authority_owner'), p.get('authority_sequence'))
             == (binding.tuple239, binding.owner55, request['sequence']),
             'actual captured source scope lost')
        command=dict(binding.fields)
        need((p.get('lease_slots')>>(18*operand))&((1<<18)-1)
             == (command['cmd_source_slots']>>(18*operand))&((1<<18)-1)
             and (p.get('lease_owner')>>(46*operand))&((1<<46)-1)
             == (command['cmd_source_owners']>>(46*operand))&((1<<46)-1),
             'captured source aperture differs from command')
        workspace=bool((p.get('lease_workspace')>>operand)&1)
        need(bool((p.get('lease_write')>>operand)&1)==workspace,
             'captured input direction must match workspace role')
        if not workspace:
            need((p.get('source_owner_held')>>operand)&1,
                 'borrowed published source not physically retained')
        return workspace

    def write(self, request, binding, operand, page_index, page, raw):
        need(isinstance(page,OwnedPage), 'actual admitted workspace page required')
        p=self.collector; q=page.query.physical
        def check():
            need(self.workspace(request,binding,operand), 'borrowed source staging forbidden')
            need(page.tuple239==binding.tuple239
                 and q.parameter('SM_INDEX')==((p.get('lease_bank')>>(6*operand))&63)
                 and page.slot==((p.get('lease_slots')>>(18*operand+9*page_index))&511)
                 and page.owner46==((p.get('lease_owner')>>(46*operand))&((1<<46)-1)),
                 'captured workspace page identity')
            need(not page_index or (p.get('lease_double')>>operand)&1,
                 'workspace second page not captured')
            need(q.get('query_result_write') and q.get('query_result_workspace')
                 and q.get('query_result_version')==((p.get('lease_version')>>(11*operand))&2047)
                 and q.get('query_result_first')<=page.slot<q.get('query_result_end'),
                 'typed workspace query direction/version/bounds')
        check()
        actual=page.RF.ports
        class CheckedPorts:
            def __getattr__(_,name): return getattr(actual,name)
            def tick(_):
                check()
                return actual.tick()
        page.RF.ports=CheckedPorts()
        try:
            return self.initializer.write(page,raw)
        finally:
            page.RF.ports=actual


def native_factory(authority,contexts):
    """Select real borrowed read or workspace stage from sealed collector role."""
    class SourceHandlers(RFNativeHandlers):
        def native_primitive(self,request):
            resolver=getattr(self.authority,'native_source_cursor',None)
            need(callable(resolver),'actual source cursor authority hook missing')
            cursor=resolver(request)
            need(isinstance(cursor,SourceCursorBinding) and cursor.producer.root is self.base.root,
                 'actual enclosing source cursor binding required')
            cursor.producer.prepare(request,cursor.tuple239,cursor.owner55)
            try:
                binding=self.authority.native_binding('native_primitive_RF',request)
                need(isinstance(binding,HeldRFCommand) and
                     (binding.tuple239,binding.owner55)==(cursor.tuple239,cursor.owner55),
                     'command must use actual source cursor issuer scope')
                command=dict(binding.fields); seed=cursor.producer.active[0]
                need(all(command.get(k)==v for k,v in
                         dict(cmd_descriptor=seed.descriptor,cmd_operands=seed.operands,
                              cmd_types=seed.types,cmd_counts=seed.counts,
                              cmd_signed_i8_mask=seed.signed_i8,cmd_template=seed.template,
                              cmd_step=seed.step,cmd_substep=seed.substep,
                              cmd_scalars=seed.scalars).items()),
                     'command disagrees with owned source cursor')
                staging=SourceStaging(self.base.root,cursor.producer.collector)
                for index,operand in enumerate(request['operands']):
                    if not staging.workspace(request,binding,index):
                        # Actual controller reads the captured borrowed bank.
                        # No query acquisition, write, byte computation or ACK here.
                        continue
                    raw=operand['payload']
                    for offset in range(0,len(raw),512):
                        page=self.authority.native_input_page(request,index,offset//512)
                        staging.write(request,binding,index,offset//512,page,
                                      raw[offset:offset+512].ljust(512,b'\0'))
                result=self.pump.run(request,binding)
                cursor.producer.finish()
                return result
            except BaseException:
                cursor.producer.stopped=True
                raise
    return SourceHandlers(authority,contexts).handlers()
