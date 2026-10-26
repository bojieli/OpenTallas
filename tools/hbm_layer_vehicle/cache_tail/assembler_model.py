"""Source-contract model for one2048b ordered carry replacing words16x256.

MODEL ONLY, not an RTL validation. Existing cache predicates are transcribed
from ot_hbm_svc_static_sm_packed136.sv. Positive cases independently compare
both assemblers to canonical input bytes. Fault cases check sticky first edge.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RTL = ROOT / 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_sm_packed136.sv'


class Model:
    def __init__(self, carry):
        self.carry_backend = carry
        self.reset()

    def reset(self):
        self.running = self.sticky = False
        self.phase = self.elapsed = self.received = self.head = self.record_phase = 0
        self.emitted = self.rows = self.total = 0
        self.words = [bytes([91])*32 for _ in range(16)]
        self.present = [False]*16
        # Arbitrary power-up contents; length/epoch state, never these bytes,
        # establishes whether data exists. OPEN clears logical carry length.
        self.carry = bytes([173])*256
        self.carry_length = 0
        self.owned = [False, False]
        self.epochs = [0, 0]
        self.counts = [0, 0]
        self.data = [[], []]
        self.tag_bases = [0, 0]
        self.load_bank = 0
        self.load_epoch = 0
        self.first_fault = None
        self.edge = 0
        self.max_payload_bits = 0

    def tick(self, *, reset=False, opening=None, sectors=None, reading=None, retiring=None):
        if reset:
            self.reset()
            return dict(reset=True)
        self.edge += 1
        sectors = sectors or [None]*4
        assert len(sectors) == 4
        old = deepcopy(self)
        ready = [old.owned[b] and old.counts[b] > 0 and len(old.data[b]) == old.counts[b] for b in range(2)]
        open_ok = opening is not None and not old.running and not old.owned[opening[0]] and 0 < opening[2] <= 64 and not old.sticky and not (retiring and retiring[0] == opening[0])
        read_ok = reading is not None and ready[reading[0]] and reading[1] == old.epochs[reading[0]] and 0 <= reading[2] < old.counts[reading[0]] and (len(reading) < 4 or reading[3] == ((old.tag_bases[reading[0]]+reading[2]) & 1023)) and not old.sticky and not (retiring and retiring[0] == reading[0])
        row_slot = old.running and old.elapsed >= 2 and old.phase != 1 and old.emitted < old.rows
        fault_reasons = []
        if opening is not None and not open_ok:
            fault_reasons.append('OPEN')
        if reading is not None and not read_ok:
            fault_reasons.append('READ')
        output = old.data[reading[0]][reading[2]] if read_ok else None
        row = None
        collision = False
        expected = min(1 if old.phase == 4 else 4, old.total-old.received) if old.running and old.received < old.total else 0
        if open_ok:
            bank, epoch, count = opening[:3]
            self.running = True
            self.load_bank, self.load_epoch, self.rows = bank, epoch, count
            self.owned[bank] = True
            self.epochs[bank], self.counts[bank], self.data[bank] = epoch, count, []
            self.tag_bases[bank] = opening[3] if len(opening) > 3 else 100
            self.emitted = self.received = self.head = self.phase = self.elapsed = self.record_phase = 0
            self.total = ((count*136+127)//128)*4
            self.present = [False]*16
            self.carry_length = 0
        if old.running and not old.sticky:
            self.phase = (old.phase+1) % 5
            self.elapsed = old.elapsed+1
            incoming = []
            for lane, sector in enumerate(sectors):
                if (sector is not None) != (lane < expected):
                    fault_reasons.append('SECTOR_MASK')
                if sector is not None:
                    epoch, index, payload = sector
                    assert len(payload) == 32
                    if epoch != old.load_epoch or index != old.received+lane:
                        fault_reasons.append('SECTOR_EPOCH_INDEX')
                    else:
                        incoming.append(payload)
                    if old.present[(old.received+lane) % 16]:
                        collision = True
                        if not old.carry_backend:
                            fault_reasons.append('PRESENT_COLLISION')
                    if not old.carry_backend and epoch == old.load_epoch and index == old.received+lane and not old.present[(old.received+lane) % 16]:
                        self.words[(old.received+lane) % 16] = payload
                        self.present[(old.received+lane) % 16] = True
            self.received = old.received+expected
            if row_slot:
                if old.carry_backend:
                    complete = old.carry_length >= 136
                    row = old.carry[:136] if complete else None
                else:
                    complete = all(old.present[(old.head+j) % 16] for j in range(5))
                    gathered = b''.join(old.words[(old.head+j) % 16] for j in range(5))
                    row = gathered[old.record_phase*8:old.record_phase*8+136] if complete else None
                if not complete:
                    fault_reasons.append('ROW_INCOMPLETE')
                else:
                    self.data[old.load_bank].append(row)
                    self.emitted = old.emitted+1
                    for j in range(5 if old.record_phase == 3 else 4):
                        self.present[(old.head+j) % 16] = False
                    self.head = old.head + (5 if old.record_phase == 3 else 4)
                    self.record_phase = (old.record_phase+1) % 4
            if old.carry_backend:
                # The formatter consumes ONLY old carry. Incoming sector bytes
                # append after that decision; no current-edge bypass is used.
                consumed = 136 if row_slot and row is not None else 0
                remaining = old.carry[:old.carry_length][consumed:]
                new = remaining + b''.join(incoming)
                if len(new) > 256:
                    fault_reasons.append('CARRY_OVERFLOW')
                raw = b''.join(x[2] if x is not None else bytes([219])*32 for x in sectors)
                # These are the proposed hardware's FIVE CONSTANT byte-slices,
                # not a runtime indexed part-select or dynamic shift.
                physical = {
                    0: raw + bytes(128),
                    1: old.carry[:128] + raw,
                    2: old.carry[136:256] + raw + bytes(8),
                    3: old.carry[136:248] + raw + bytes(16),
                    4: old.carry[136:240] + raw[:32] + bytes(120),
                }[old.phase]
                assert len(physical) == 256
                if not fault_reasons and old.emitted < old.rows:
                    assert physical[:len(new)] == new, (old.rows,old.edge,old.phase,len(new))
                self.carry = physical
                self.carry_length = min(len(new), 256)
                self.max_payload_bits = max(old.max_payload_bits, len(new)*8)
            if old.emitted == old.rows and old.received == old.total:
                self.running = False
        elif opening is None and any(x is not None for x in sectors):
            fault_reasons.append('INACTIVE_SECTOR')
        if retiring is not None:
            bank, epoch = retiring
            if not old.owned[bank] or epoch != old.epochs[bank] or (old.running and old.load_bank == bank) or (reading and reading[0] == bank) or (opening and opening[0] == bank):
                fault_reasons.append('RETIRE')
            else:
                self.owned[bank] = False
        self.sticky = old.sticky or bool(fault_reasons)
        if not old.sticky and self.sticky:
            self.first_fault = self.edge
        return dict(row=row, running=self.running, ready=[self.owned[b] and self.counts[b] > 0 and len(self.data[b]) == self.counts[b] for b in range(2)],
                    sticky=self.sticky, first_fault=self.first_fault, output=output,
                    collision=collision, reasons=fault_reasons)


def payload(index):
    return bytes(((index*32+j)*73 ^ ((index*32+j) >> 3) ^ 181) & 255 for j in range(32))


def events_for(rows=64, change=None):
    total = ((rows*136+127)//128)*4
    index = 0
    events = [dict(opening=(0, 70, rows))]
    phase = 0
    while index < total:
        n = min(1 if phase == 4 else 4, total-index)
        sectors = [(70, index+j, payload(index+j)) if j < n else None for j in range(4)]
        events.append(dict(sectors=sectors))
        index += n
        phase = (phase+1) % 5
    events.extend([{}, {}, {}, {}])
    if change:
        change(events)
    return events


def drive(model, change=None, rows=64):
    return [model.tick(**event) for event in events_for(rows, change)]


def check():
    positives = []
    for rows in range(1, 65):
        old, new = Model(False), Model(True)
        a, b = drive(old, rows=rows), drive(new, rows=rows)
        for x, y in zip(a,b):
            assert not x['sticky'] and not y['sticky'], (rows,x,y)
            assert all(x[k] == y[k] for k in ['row','running','ready','output'])
            assert not x['collision'], rows
        expected = b''.join(payload(i) for i in range(((rows*136+127)//128)*4))[:rows*136]
        assert b''.join(old.data[0]) == expected == b''.join(new.data[0])
        assert new.max_payload_bits <= 2048
        positives.append(dict(rows=rows, max_payload_bits=new.max_payload_bits,
                              data_sha256=hashlib.sha256(expected).hexdigest()))

    def wrong_sector(field, value, edge=4, lane=0):
        def mutate(events):
            x=list(events[edge]['sectors'][lane]);x[field]=value;events[edge]['sectors'][lane]=tuple(x)
        return mutate
    negatives = {
        'missing_sector': lambda e:e[4]['sectors'].__setitem__(0,None),
        'extra_sector_partial': lambda e:e[5]['sectors'].__setitem__(1,(70,18,payload(18))),
        'wrong_epoch': wrong_sector(0,99),
        'wrong_index': wrong_sector(1,999),
        'duplicate_index': wrong_sector(1,8),
        'reordered_sectors': lambda e:e[4]['sectors'].__setitem__(slice(0,2),list(reversed(e[4]['sectors'][:2]))),
        'open_while_running': lambda e:e[4].update(opening=(1,71,64)),
        'retire_while_copying': lambda e:e[4].update(retiring=(0,70)),
        'early_read': lambda e:e[4].update(reading=(0,70,0)),
        'wrong_read_epoch': lambda e:e[-1].update(reading=(0,99,0)),
        'wrong_read_tag': lambda e:e[-1].update(reading=(0,70,0,999)),
        'read_out_of_range': lambda e:e[-1].update(reading=(0,70,63)),
        'wrong_retire_epoch': lambda e:e[-1].update(retiring=(0,99)),
        'retire_read_collision': lambda e:e[-1].update(retiring=(0,70), reading=(0,70,0)),
        'retire_open_collision': lambda e:e[-1].update(retiring=(1,71), opening=(1,71,64)),
        'open_owned_bank': lambda e:e[-1].update(opening=(0,70,64)),
        'inactive_sector': lambda e:e[-1].update(sectors=[(70,999,payload(999)),None,None,None]),
        'zero_count_open': lambda e:e[0].update(opening=(0,70,0)),
        'oversized_open': lambda e:e[0].update(opening=(0,70,65)),
    }
    faults = []
    for name, mutate in negatives.items():
        old, new = Model(False), Model(True)
        rows = 16 if name == 'read_out_of_range' else 64
        a,b = drive(old,mutate,rows),drive(new,mutate,rows)
        assert old.first_fault is not None and old.first_fault == new.first_fault, name
        for x,y in zip(a,b):
            assert x['sticky'] == y['sticky'], name
            if x['first_fault'] is None:
                assert all(x[k] == y[k] for k in ['row','running','ready','output']), name
        faults.append(dict(name=name,first_fault_edge=old.first_fault))
    # Exact source behavior ignores sectors on an otherwise legal OPEN edge.
    def on_open(events):
        events[0]['sectors']=[(999,999,payload(999))]*4
    for carry in [False,True]:
        model=Model(carry);drive(model,on_open);assert not model.sticky
        model=Model(carry)
        def tag_wrap(events):
            events[0]['opening']=(0,70,64,1000)
        drive(model,tag_wrap)
        for row in range(64):
            result=model.tick(reading=(0,70,row,(1000+row)&1023))
            assert not result['sticky'] and result['output'] == model.data[0][row]
    # Reset at every copy edge clears validity/ownership; a fresh complete run
    # reconstructs the same rows without relying on any prior contents.
    resets=0
    for offset in range(1,85):
        for carry in [False,True]:
            model=Model(carry)
            for event in events_for(64)[:offset]:
                assert not model.tick(**event)['sticky']
            model.tick(reset=True)
            assert not any(model.owned) and not model.running and not model.sticky
            drive(model, rows=64)
            assert not model.sticky and len(model.data[0]) == 64
            resets+=1
    return dict(scope=__doc__, rtl_sha256=hashlib.sha256(RTL.read_bytes()).hexdigest(),
                positive_all64=positives, first_fault_cases=faults,
                ignored_open_sector_case=True, reset_cases=resets,
                carry_payload_bits=2048, previous_ring_payload_bits=4096,
                metadata_control_counted_separately=True,
                rtl_qualified=False, native_qualified=False, schedule_qualified=False, price_qualified=False)


if __name__ == '__main__':
    print(json.dumps(check(),indent=2))
