"""Additive addressed-journal observation; pinned functional observer unchanged.

Software sector receipts remain distinct from hardware ACK and full-token proof.
"""
import hashlib
from h4_c0_forward_observer import ProviderTap as FunctionalProviderTap

class ProviderTap(FunctionalProviderTap):
    def record(self,kind,key,data,movement_receipt=None):
        if movement_receipt is not None:
            if (movement_receipt.get('status')!='SOFTWARE_ADDRESSED_MOVEMENT_REVERSE_DRAINED'
                or movement_receipt.get('key')!=list(key)
                or movement_receipt.get('payload_sha256')!=hashlib.sha256(data).hexdigest()):
                raise ValueError('actual movement receipt not bound to this provider return')
        super().record(kind,key,data)
        if movement_receipt is not None:
            row=self.events[-1]
            row['actual_address_receipt']=movement_receipt
            row['validated_reverse_grant']='software sector journal identity/tag/generation verified'
            row['qualification']='actual addressed software provider movement; no RTL/full-program qualification'

    def transact(self,key,*,write=False,payload=None):
        self.guard()
        result=self.backend.transact(key,write=write,payload=payload)
        self.record('write_return' if write else 'read_return',key,payload if write else result,
                    movement_receipt=getattr(self.backend,'last_receipt',None))
        return result
