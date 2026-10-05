"""Owned caller join sources; Nash mapping/Claude native4/Euclid factory unchanged.

rpc_* are original source-byte command pins, not a done/idle callback. Connect
root_accept/root_identity/root_retire/root_retire_identity and matching ready
outputs to metadata cohort3. Connect actual map_* from held source-sector grant;
never static allocated addresses or Python grant dictionaries. Child offers
retain source id/rank/address/write while actual mapping/tap capacity stalls.
Wire tap_command_* to STATE tap command_*, tap_reply_* to its reply_*. Tap raw
NC6 permit/completion/reverse wiring remains Euclid/Nash's actual source wiring.
sector_capture_* is the actual returned capture ready/valid at the byte caller;
all source sectors must be consumed before the joint parent/cohort retirement.
Host may pack original source bytes, but cannot signal completion or infer grants.
No clock, memory, mapper or native handler is implemented in this module.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOP='ot_gpu_qwen_kv_state_rpc_join'
def source_files(root=ROOT):
    return (Path(root)/'rtl/model/qwen_kv_connections_20261003'/(TOP+'.sv'),)

from tools.gpu_sys.canonical_qwen_kv_ports import KVByteHandlers
from tools.gpu_sys.canonical_qwen_transport import TransportError, PROGRAM_SHA
import hashlib

class StateRPCByteHandlers(KVByteHandlers):
    """Actual byte caller driving this root hardware; mappings stay with Nash.

    rpc_ports get/set/settle/tick/parameter operate on the SAME enclosing clock.
    This caller drives original command offers and destination readiness only.
    It never sets root_accept/retire, map/grant, tap completion, clean or reverse.
    Physical W2 sector reads/writes/reverses still use inherited real transactors.
    Euclid enrolls the two state handlers in the existing sixteen-handler server;
    payload_read and all native/lifecycle handlers keep their owners.
    """
    def __init__(self,authority,rpc_ports,*,enabled=False):
        if not enabled or rpc_ports.parameter('ENABLE')!=1:
            raise TransportError('actual state RPC join default off')
        super().__init__(authority)
        self.rpc_ports=rpc_ports
        # Sample matching retained source ownership BEFORE joint hardware RPC
        # retirement; checking the temporary root after its retirement is wrong.
        for kind in ('kv_state_read','kv_state_write'):
            self.handlers[kind]=self._root_handler(kind)

    def _root_handler(self,kind):
        def transact(request):
            if self.stopped or self.pending is not None:
                raise TransportError('STATE pending/faulted; no source reuse')
            self.pending=(kind,request)
            try:
                if type(request.get('rank')) is not int or request['rank'] not in (0,1):
                    raise TransportError('STATE original source rank')
                result=self._state(request,kind=='kv_state_write')
                result.update({k:request[k] for k in ('program_sha256','source_PC','sequence')})
                result.update(accepted=True,fault=False)
                self.pending=None
                return result
            except BaseException:
                self.stopped=True
                raise
        return transact

    def _check(self):
        p=self.rpc_ports;p.settle()
        if p.get('fault') or not p.get('por_n') or p.get('local_reset'):
            raise TransportError('actual STATE RPC fault/reset; retain root debt')

    def _state(self,request,write):
        p=self.rpc_ports
        base,size=self.authority.kv_aperture(request,'state')
        address=request['address'];payload=request.get('payload')
        count=len(payload) if write and type(payload) is bytes else request.get('bytes')
        if (request.get('program_sha256')!=PROGRAM_SHA or type(address) is not int or
            type(count) is not int or count<=0 or type(base) is not int or type(size) is not int or
            size!=37504 or address<base or address+count>base+size or
            (write and (type(payload) is not bytes or count>32))):
            raise TransportError('STATE source extent/actual32B command payload port')
        identity=request['sequence']
        if type(identity) is not int or not 0<=identity<1<<64:
            raise TransportError('STATE original source RPC identity')
        try:
            for n,v in dict(rpc_identity=identity,rpc_rank=request['rank'],rpc_write=int(write),
                            rpc_address=address,rpc_bytes=count,
                            rpc_payload=int.from_bytes(payload,'little') if write else 0,
                            rpc_valid=1,rpc_reply_ready=0,sector_capture_ready=0).items():p.set(n,v)
            while True:
                self._check();accept=bool(p.get('rpc_ready'));p.tick()
                if accept:break
            p.set('rpc_valid',0)
            result=bytearray();end=address+count
            for sector in range(address//32*32,end,32):
                lo,hi=max(address,sector)-sector,min(end,sector+32)-sector
                # Mandatory physical OLD capture, also for a full-sector write.
                old=self._read_sector(request,sector)
                if write:
                    new=bytearray(old);new[lo:hi]=payload[sector+lo-address:sector+hi-address]
                    self._sector(request,sector,bytes(new))
                else:result.extend(old[lo:hi])
                while True:
                    self._check()
                    if p.get('sector_capture_valid'):
                        if (p.get('sector_capture_source_addr')!=sector or
                            p.get('sector_capture_old_data').to_bytes(32,'little')!=old):
                            raise TransportError('STATE actual tap/source OLD capture disagreement')
                        p.set('sector_capture_ready',1);p.settle()
                        self._check()
                        if not p.get('sector_capture_valid'):
                            raise TransportError('STATE held capture withdrawn before acceptance')
                        p.tick();p.set('sector_capture_ready',0);break
                    p.tick()
            while True:
                self._check()
                if p.get('rpc_reply_valid'):
                    if (p.get('rpc_reply_identity'),p.get('rpc_reply_rank'),p.get('rpc_reply_address'),p.get('rpc_reply_bytes'))!=(identity,request['rank'],address,count):
                        raise TransportError('STATE whole source RPC retirement identity')
                    if self.authority.kv_owner_retained(request) is not True:
                        raise TransportError('STATE source owner lost before hardware root retirement')
                    p.set('rpc_reply_ready',1);p.settle();self._check()
                    if not p.get('rpc_reply_valid'):
                        raise TransportError('STATE held parent reply withdrawn before retirement')
                    p.tick();p.set('rpc_reply_ready',0);break
                p.tick()
            response=dict(rank=request['rank'],address=address)
            if write:response.update(payload_sha256=hashlib.sha256(payload).hexdigest(),visible=True)
            else:response.update(payload=bytes(result),captured=True)
            return response
        except BaseException:
            for name in ('rpc_valid','rpc_reply_ready','sector_capture_ready'):p.set(name,0)
            raise  # Existing handler stops; no reset, grant/root clear or retry.
