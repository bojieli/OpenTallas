"""Opt-in capture of REAL synchronous addressed provider movement.

Delegates arithmetic/storage unchanged. Sector journals are software causality,
not RTL ACKs. Missing/partial/stale receipts fail closed, with evidence retained.
No full-program or hardware qualification is inferred from passing controls.
"""
import hashlib, json, pathlib

PHASES=('request_accept', None, 'consumer_accept', 'reverse_credit_accept', 'validated_reverse_grant')

def digest(data):return hashlib.sha256(data).hexdigest()

def prove_sector_span(events, *, model, rank, PC, generation):
    """Validate every accepted identity/tag/generation, including RMW reads.

    Recycled provider tags are keyed by the complete accepted generation. The
    event cursor belongs to one delegated call; no search of prior successes.
    """
    transactions={};order=[]
    for ordinal,event in enumerate(events):
        identity=event.get('identity',{})
        if event.get('hardware') is not False:raise ValueError('software provider scope required')
        if (identity.get('target'),identity.get('rank'),identity.get('pc'),identity.get('epoch'))!=(model,rank,PC,generation):
            raise ValueError('actual sector source PC/rank/generation mismatch')
        key=(json.dumps(identity,sort_keys=True),event.get('tag'),event.get('generation'))
        name=event['event']
        if name=='request_accept':
            if key in transactions:raise ValueError('duplicate accepted sector identity')
            if type(event['tag'])!=int or type(event['generation'])!=int or event['generation']<=0:raise ValueError('finite accepted tag/generation required')
            transactions[key]=dict(identity=dict(identity),tag=event['tag'],generation=event['generation'],phase=1,ordinals=[ordinal]);order.append(key)
        elif key not in transactions:raise ValueError('event without source acceptance')
        else:
            row=transactions[key];phase=row['phase']
            if name in ('software_backing_visible','software_read_capture'):
                if phase!=1:raise ValueError('duplicate/out-of-order backing return')
                row['direction']='write' if name=='software_backing_visible' else 'read';row['phase']=2;row['ordinals'].append(ordinal)
            elif name in PHASES[2:]:
                if phase>=5 or name!=PHASES[phase]:raise ValueError('consumer/reverse out of order')
                row['phase']+=1;row['ordinals'].append(ordinal)
            elif name in ('write_residence_reserved','software_owned_issue','software_service_phases_reserved'):
                if phase!=1:raise ValueError('issue after immutable return')
            else:raise ValueError('fault/cancel/unknown provider lifecycle event: '+name)
    if not order or any(row['phase']!=5 for row in transactions.values()):raise ValueError('accepted sector reverse debt retained')
    return [transactions[k] for k in order]

class AddressedMovement:
    """One <=512B call, <=64 actual transactions, <=2048 journal events.

    Constructor takes the parent's actual addressed scratch provider. Named and
    arena addresses are obtained from its committed allocation, never allocated
    by the observer. An exception retains a failed receipt, never frees an owner.
    """
    def __init__(self,backend,*,source_sha256,model='DeepSeek',max_calls=32768):
        if len(source_sha256)!=64 or any(c not in '0123456789abcdef' for c in source_sha256):raise ValueError('provider source byte pin required')
        if model not in ('Qwen','DeepSeek') or type(max_calls)!=int or not 1<=max_calls<=32768:raise ValueError('bounded model/call capacity')
        if not hasattr(backend,'p') or not hasattr(backend.p,'events') or not hasattr(backend,'s'):raise ValueError('actual sector journal backend required; boolean ACK insufficient')
        self.source_path=pathlib.Path(backend.transact.__func__.__code__.co_filename)
        if not self.source_path.is_file() or digest(self.source_path.read_bytes())!=source_sha256:raise ValueError('actual provider implementation byte pin mismatch')
        self.backend=backend;self.source_sha256=source_sha256;self.model=model;self.max_calls=max_calls;self.calls=0;self.last_receipt=None;self.fault=None
    def __getattr__(self,name):return getattr(self.backend,name)
    def transact(self,key,*,write=False,payload=None):
        if self.fault is not None:raise ValueError('quarantined movement observer after failure')
        if self.calls>=self.max_calls:raise ValueError('finite movement call capacity exhausted')
        if digest(self.source_path.read_bytes())!=self.source_sha256:raise ValueError('provider source changed since binding')
        self.calls+=1;key=tuple(key);b=self.backend;p=b.p;start=len(p.events)
        self.last_receipt=dict(status='ACCEPTED_PENDING',journal_start=start,key=list(key),hardware_qualified=False)
        try:
            result=b.transact(key,write=write,payload=payload)
            end=len(p.events)
            if end-start>2048:raise ValueError('finite sector journal span exhausted')
            rows=prove_sector_span(p.events[start:end],model=self.model,rank=b.s.rank,PC=b.s.pc,generation=b.s.epoch)
            if len(rows)>64:raise ValueError('finite64 actual transactions exhausted')
            if p.live or p.queue or p.calendar or p.resident:raise ValueError('actual provider not reverse drained')
            raw=bytes(payload if write else result)
            if not 0<len(raw)<=512:raise ValueError('bounded actual payload required')
            offset=key[-1] if key[0]=='arena' else b.addresses[key]
            address=b.s.base+offset
            if address%32:raise ValueError('actual provider sector alignment')
            sectors={r['identity']['sector']:r for r in rows if r['direction']==('write' if write else 'read')}
            fragments=[]
            for base in range(address//64*64,(address+len(raw)+63)//64*64,64):
                lo=max(base,address);hi=min(base+64,address+len(raw));parts=[]
                for sector in range(lo//32,(hi-1)//32+1):
                    if sector not in sectors:raise ValueError('returned bytes lack actual addressed sector receipt')
                    r=sectors[sector];data=p.backing.get((self.model,b.s.rank,sector))
                    if data is None or any(v is None for v in data):raise ValueError('actual backing bytes unavailable')
                    left=max(lo,sector*32);right=min(hi,(sector+1)*32)
                    observed=bytes(data[left-sector*32:right-sector*32])
                    if observed!=raw[left-address:right-address]:raise ValueError('returned payload differs from actual addressed backing')
                    parts.append(dict(transaction=r,sector_payload_sha256=digest(bytes(data)),byte_start=left,byte_end=right))
                fragments.append(dict(byte_address=base,valid_byte_mask=hex(((1<<(hi-lo))-1)<<(lo-base)),payload_sha256=digest(raw[lo-address:hi-address]),sectors=parts))
            self.last_receipt=dict(status='SOFTWARE_ADDRESSED_MOVEMENT_REVERSE_DRAINED',model=self.model,PC=b.s.pc,rank=b.s.rank,generation=b.s.epoch,
                native_owner=list(b.owner),key=list(key),byte_address=address,payload_bytes=len(raw),payload_sha256=digest(raw),direction='write' if write else 'read',
                provider_source_sha256=self.source_sha256,journal_start=start,journal_end=end,
                actual_transactions=rows,scratch_port_bytes=64,fragments=fragments,
                lifecycle='Actual software backing -> consumer -> matching accepted tag/generation reverse grant',
                additional_sector_service_charges=0,existing_RMW_highword_service_preserved=True,
                hardware_qualified=False,full_program_qualified=False)
            return result
        except Exception as error:
            self.fault=repr(error);self.last_receipt.update(status='FAILED_EVIDENCE_RETAINED',error=self.fault,journal_end=len(p.events));raise

    def transfer_to_owner(self,lock,token,fragment,key,*,payload=None):
        """Reserve C0 BEFORE delegating a real provider call, retain debt on fail.

        Aggregate barriers prove ALL sectors reached each phase. They are not
        timestamped hardware events: Dewey retains the original sector calendar.
        An immutable byte contract supplies the expected read digest beforehand.
        """
        with lock.guard:
            state=lock.owner(token);command=state['command'];b=self.backend
            if (b.s.pc,b.s.rank,b.s.epoch)!=(command['source_PC'],command['rank'],command['generation']):
                raise ValueError('actual parent provider and C0 command ownership mismatch')
            if tuple(key[1:6])!=tuple(b.owner) or b.owner[3]!=command['SM']:
                raise ValueError('actual native provider SM/key owner mismatch')
            write=fragment['kind']=='destination_writeback'
            if write!=(payload is not None):raise ValueError('actual refill/writeback payload direction')
            if fragment['provider_source_sha256']!=self.source_sha256:raise ValueError('exact provider source pin mismatch')
            lock.provider_accept(token,fragment)
            result=self.transact(key,write=write,payload=payload);receipt=self.last_receipt
            if (receipt['byte_address'],receipt['payload_bytes'],receipt['payload_sha256'])!=(fragment['byte_address'],fragment['payload_bytes'],fragment['observed_payload_sha256']):
                self.fault='C0 immutable byte/address contract mismatch after actual provider';raise ValueError(self.fault)
            names=('software_backing_store_write_commit' if write else 'software_backing_store_read_return','consumer_accept','validated_reverse_grant')
            for phase,name in enumerate(names):
                event=dict(event=name,identity=fragment['identity'],sequence=state['last_sequence']+1,
                    byte_address=receipt['byte_address'],payload_bytes=receipt['payload_bytes'],payload_sha256=receipt['payload_sha256'],
                    evidence_scope='Aggregate SOFTWARE barriers over actual accepted sector journal; not hardware/timestamped calendar events',
                    actual_journal_start=receipt['journal_start'],actual_journal_end=receipt['journal_end'],
                    sector_phase_ordinals=[row['ordinals'][[1,2,4][phase]] for row in receipt['actual_transactions']])
                lock.provider_event(token,fragment['identity']['fragment_sequence'],event)
            return result
