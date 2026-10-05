"""Real range-owner pins and the EXISTING native/KV scratch arbiter.

No clock hook, allocation, reset, READY or arithmetic is synthesized here.
The caller enrolls these ports in its one existing shared-clock owner.
"""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_ranked_simulator import RankedEnclosingPins, RankedComponentPins
from tools.gpu_sys.canonical_qwen_transport import TransportError

PORTBOOK = Path(__file__).resolve().parents[2] / 'rtl/model/qwen_hbm_installed_services_20261003/ports.json'
WIDTHS = dict(valid=1, write=1, addr=10, wdata=512, ready=1, done=1, done_ready=1, rdata=512)
INPUTS = {'valid', 'write', 'addr', 'wdata', 'done_ready'}


class InstalledServicePins(RankedEnclosingPins):
    def __init__(self, reader, writer, *, portbook=PORTBOOK):
        super().__init__(reader, writer, portbook=portbook)
        if self.book['inventory'].get('source_owner_count') != 64:
            raise TransportError('actual 64 source-owner instances required')

    def component(self, block, index=0, *, rank=None, aliases=None):
        if block in ('source_owner', 'scratch_client'):
            if rank is not None or aliases or type(index) is not int or not 0 <= index < 64:
                raise TransportError('source-owner exact SM index0..63')
            return SourceOwnerPins(self, index, block=block)
        return super().component(block, index, rank=rank, aliases=aliases)


class SourceOwnerPins(RankedComponentPins):
    def __init__(self, root, index, *, block='source_owner'):
        if not any(p.get('block') == block and p.get('count') == 64 for p in root.book['pins'].values()):
            raise TransportError('physical component not installed: ' + block)
        self.root, self.block, self.index, self.aliases = root, block, index, {}

    def parameter(self, name):
        if name == 'ENABLE': return 1
        if self.block == 'source_owner' and name == 'SM_INDEX': return self.index
        raise TransportError('unknown source-owner parameter')


def installed_scratch_pins_class():
    # Import only when the actual owner source is installed, no fallback mux.
    from tools.gpu_sys.canonical_qwen_scratch_simulator import ScratchEnclosingPins

    class InstalledScratchPins(ScratchEnclosingPins):
        def __init__(self, reader, writer, *, portbook):
            super().__init__(reader, writer, portbook=portbook)
            if self.book['inventory'].get('source_owner_count') != 64:
                raise TransportError('actual64 range owners required with scratch')

        def component(self, block, index=0, *, rank=None, aliases=None):
            if block == 'source_owner':
                if rank is not None or aliases or type(index) is not int or not 0 <= index < 64:
                    raise TransportError('source-owner exact SM index0..63')
                return SourceOwnerPins(self, index)
            return super().component(block, index, rank=rank, aliases=aliases)

    return InstalledScratchPins


def scratch_component(pins, execution_rank, execution_SM):
    """Actual protected client mux, never the raw contender or SM outputs.

    The owner-selected adapter supplies offer owner/GO fields. Its workspace
    authorization is a separate hardware-held input, never a host grant.
    Missing installation refuses before any writes or clock edges.
    """
    if type(execution_rank) is not int or execution_rank not in (0, 1) or type(execution_SM) is not int or not 0 <= execution_SM < 32:
        raise TransportError('actual captured execution rank/SM')
    index = execution_rank * 32 + execution_SM
    for name, width in WIDTHS.items():
        p = pins._pin('scratch_client_' + name)
        if p['bits'] != width * 64 or p['direction'] != ('input' if name in INPUTS else 'output'):
            raise TransportError('installed protected scratch client port width/direction')
    from tools.gpu_sys.canonical_qwen_scratch_simulator import scratch_component as owner_component
    return owner_component(pins, execution_rank, execution_SM)
