"""Opt-in software observation of actual KV calls; no arithmetic or oracle inputs.

Attach only in a fresh source-qualified successor. Never attach to a live job.
Records emitted Storage events, committed backing U8 bytes, actual read bytes,
and post-retirement persistent bytes. No event is inferred from PC order.
"""
import hashlib
import json
from pathlib import Path
import struct


def observed_storage(base, output, *, enabled=False, native=None):
    if not enabled:
        return base
    if native is None:
        raise ValueError("source native event plan required")
    from qwen_kv_observation_verify import event_plan
    plan = {(r["pc"],r["event"],r["stage"]):r for r in event_plan(native)}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)

    class Observed(base):
        def __init__(self, program):
            super().__init__(program)
            self.observed_payloads = {}
            self.observed_keys = {}

        def emit(self, cursor):
            with (output/'kv_journal.jsonl').open('a') as stream:
                for event in self.events[cursor:]:
                    kind=event['event'];identity=event.get('tag',event.get('lease'))
                    if 'key' in event:self.observed_keys[identity]=list(event['key'])
                    observed_key=self.observed_keys[identity]
                    binding=plan[self.pc,kind,event.get('stage')]
                    if observed_key!=binding['key']:raise ValueError('actual storage key vs source binding')
                    layer,rank,position=observed_key
                    extent=self.state[rank];record_offset=36864+16*layer;bitmap_offset=(layer*8192+position)//8
                    state_record=bytes(self.bytes.get((rank,extent['base']+record_offset+i),0)for i in range(16))
                    state=dict(observation_moment='after_storage_method_return',record_address=extent['base']+record_offset,
                        record_hex=state_record.hex(),bitmap_address=extent['base']+bitmap_offset,
                        bitmap_byte=self.bytes.get((rank,extent['base']+bitmap_offset),0),
                        pending_writers=len(self.pending),active_readers=len(self.leases))
                    stream.write(json.dumps(dict(event, state=state, key=observed_key, reads=binding['reads'],
                        writes=binding['writes'], pc=self.pc, cycles=None), sort_keys=True)+'\n')
                stream.flush()

        def payload(self, filename, key, addresses, values):
            addresses = list(map(int, addresses))
            values = list(map(int, values))
            if len(addresses) != len(values):
                raise ValueError('observed payload extent')
            data = b''.join(struct.pack('<QB', address, code) for address, code in zip(addresses, values))
            with (output/filename).open('ab') as stream:
                offset = stream.tell(); stream.write(data); stream.flush()
            with (output/'payload_inventory.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(file=filename, key=key, pc=self.pc, offset=offset,
                    records=len(addresses), bytes=len(data), record_format='<uint64_address,uint8_code>',
                    sha256=hashlib.sha256(data).hexdigest()), sort_keys=True)+'\n')

        def begin(self, layer, die, position):
            cursor = len(self.events)
            result = super().begin(layer, die, position)
            self.emit(cursor)
            return result

        def commit(self, tag):
            state = self.pending[int(tag)]
            key = tuple(state['key']); addresses = sorted(state['payload'])
            cursor = len(self.events)
            result = super().commit(tag)
            # Read committed backing, not the input argument or expected values.
            values = [self.bytes[key[1], address] for address in addresses]
            self.observed_payloads[key] = addresses
            self.payload('committed_U8.bin', key, addresses, values)
            self.emit(cursor)
            return result

        def acquire(self, fence, layer, die, position):
            cursor = len(self.events)
            result = super().acquire(fence, layer, die, position)
            self.emit(cursor)
            return result

        def read(self, lease, addresses):
            key = self.leases[int(lease)]['key']
            result = super().read(lease, addresses)
            self.payload('read_U8.bin', key, addresses.flat, result.flat)
            return result

        def done(self, lease, stage):
            cursor = len(self.events)
            result = super().done(lease, stage)
            self.emit(cursor)
            return result

        def finish_observation(self):
            if self.pending or self.leases:
                raise ValueError('observed KV has unretired state')
            for key, addresses in sorted(self.observed_payloads.items()):
                self.payload('final_U8.bin', key, addresses,
                    [self.bytes[key[1], address] for address in addresses])
            # Direct inspection does not introduce charged service reads.
            for rank, extent in sorted(self.state.items()):
                (output/f'final_state_rank{rank}.bin').write_bytes(bytes(
                    self.bytes.get((rank, extent['base']+offset), 0) for offset in range(extent['bytes'])))
            (output/'observation_terminal.json').write_text(json.dumps(dict(
                scope='actual software storage-call journal and U8 backing snapshots; numerical comparison separate',
                groups=len(self.observed_payloads), pending=0, leases=0,
                oracle_callbacks=0, actual_RTL=False, physical_credit=False), sort_keys=True)+'\n')

    return Observed
