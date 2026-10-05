"""Actual preloaded HA5 column/router/BD-weight source join; no numerical engine.

All payloads are read from evaluated RTL. An already restored source program
supplies descriptor lanes/format metadata. Expected outputs have no input API.
Source-order BD288 lines remain nine 32B sectors; a 128B union line is not a
complete tensor-core line. This module does not issue, grant, release or tick.
"""
import hashlib
import struct

REGIONS = dict(X=(0,2560), PRE=(2560,16), CTR=(2576,4), SEL=(2592,128),
               NSEL=(2720,4), MH=(2724,1920))


def uint(value, limit, name):
    if type(value) is not int or not 0 <= value < limit:
        raise ValueError(name+' outside source geometry')
    return value


class ColumnSource:
    def __init__(self, engine, program, *, source_sha256, mem_words, enable=False):
        if not enable:
            raise ValueError('explicit column source enable required')
        if source_sha256 != engine.source_sha256 or len(source_sha256) != 64:
            raise ValueError('same loaded native source required')
        if (engine.ndie, engine.nsm) != (2,2) or program.CSTR != 4736 or program.m.dim != 160:
            raise ValueError('admitted archived column topology/stride required')
        if type(mem_words) is not int or mem_words <= 0:
            raise ValueError('actual partition size required')
        if not callable(getattr(engine.pins, 'read_bytes', None)):
            raise ValueError('canonical actual RTL memory readback required')
        self.engine, self.p, self.pins = engine, program, engine.pins
        self.source_sha256, self.mem_words = source_sha256, mem_words
        self.columns = []; self.movements = []; self.seen = set()

    def _read(self, die, address, size):
        uint(die, 2, 'die')
        if type(address) is not int or type(size) is not int or min(address,size)<0 or address+size>self.mem_words*64:
            raise ValueError('actual source span; no modulo')
        result = self.pins.read_bytes(die, address, size, mem_words=self.mem_words)
        if type(result) is not bytes or len(result) != size:
            raise RuntimeError('short actual memory readback')
        return result

    def capture_column(self, column, receipt):
        uint(column, 13, 'column')
        if self.engine.sm_engine.state != 'IDLE' or not self.engine.receipts or receipt != self.engine.receipts[-1]:
            raise ValueError('authoritative completed owned kernel required')
        if receipt['kind'] != 'swapout' or receipt.get('input_token') != column or receipt['source_sha256'] != self.source_sha256:
            raise ValueError('actual SWAPOUT column identity required')
        before = self.pins.snapshot()
        values = []
        for die in range(2):
            fields = {name:self._read(die, self.p.a['COL']+column*self.p.CSTR+off, size)
                      for name,(off,size) in REGIONS.items()}
            values.append(fields)
        if self.pins.snapshot() != before:
            raise RuntimeError('column readback advanced actual RTL')
        result = dict(column=column, receipt=dict(receipt), values=values,
                      sha256=[{n:hashlib.sha256(b).hexdigest() for n,b in fields.items()} for fields in values],
                      CTR_scope='reserved slot bytes; original SWAPOUT does not persist CTR',
                      exactness='comparison pending; not token-only qualification')
        self.columns.append(result)
        return result

    def _weight_lines(self, die, sm, layer, ids, phase, issued_slot):
        # Descriptor namespace was primed by source.restore's word-exact replay.
        def base(field):
            lane = self.p.desc_fields[field]
            data = self._read(die, self.p.a['DESC']+512*layer+4*lane, 4)
            return struct.unpack('<I', data)[0]
        routed, shared = base(f'rexp{sm}'), base(f'shexp{sm}')
        rows, steps = (32, 5) if phase == 'prefix_begin' else (40, 2)
        spans = []
        # Preserve source row-slot order (rb, group, k-step, row-within-8).
        uint(issued_slot, len(ids)+1, 'actual native expert slot')
        slot = issued_slot
        expert = (*ids, None)[slot]
        for slot, expert in ((slot, expert),):
            off = 0 if phase == 'prefix_begin' else (self.p.sh_w2off if expert is None else self.p.ex_w2off)
            address = (shared if expert is None else routed+expert*self.p.ex_stride)+off
            for rb in range(0, rows, 8):
                for step in range(steps):
                    for inner in range(8):
                        row = rb+inner
                        index = rb*steps+step*8+inner
                        at = address+index*288
                        spans.append(dict(slot=slot, expert=expert, row=row, k_step=step,
                                          address=at, sectors=tuple(at+32*q for q in range(9)),
                                          payload=self._read(die, at, 288)))
        return spans

    def _entering_swapin(self, owner):
        """Retain the latest entering source column through layer-zero EMBED.

        Receipt input_token is the issued SWAPIN column. Completion token is
        a separate hardware result and must not be used as source identity.
        Only the same command's optional EMBED may intervene.
        """
        embedded = False
        for receipt in reversed(self.engine.receipts):
            if (receipt.get('job'), receipt.get('generation'), receipt.get('source_sha256')) != (owner.job, owner.generation, self.source_sha256):
                raise RuntimeError('entering SWAPIN command/source identity mismatch')
            kind = receipt.get('kind')
            if kind == 'swapin':
                if 'input_token' not in receipt:
                    raise RuntimeError('entering SWAPIN needs issued input_token receipt')
                if embedded and receipt['pos'] != 0:
                    raise RuntimeError('EMBED may only follow layer-zero SWAPIN')
                return receipt
            if kind != 'embed' or embedded or receipt.get('pos') != owner.position or receipt.get('input_token') != owner.token:
                raise RuntimeError('native layer entering SWAPIN interrupted')
            embedded = True
        raise RuntimeError('native layer has no actual entering column')

    def attach(self, compiled):
        """Enroll on ONE existing tick observer; never start a second engine.

        Caller supplies the actual loaded compiler result with linked markers.
        The engine entries must match. Shared probe capability is mandatory.
        """
        if compiled['entries'] != self.engine.entries:
            raise ValueError('loaded native entries differ')
        for name in ('read_shared', 'read_bd_activation', 'read_ur', 'read_instruction'):
            if not callable(getattr(self.pins,name,None)):
                raise ValueError('actual column probe binary required: '+name)
        if hasattr(self, '_observer'):
            raise ValueError('column observer already enrolled')
        rows = compiled['boundaries']
        markers = {(r['die']*2+r['sm'],r['linked_pc']):r for r in rows
                   if r['phase'] in ('prefix_begin','down_begin')}
        if not markers:
            raise ValueError('actual linked native MoE markers required')
        for (index, pc), marker in markers.items():
            die,sm = divmod(index,2)
            if self.pins.read_instruction(die,sm,pc) != compiled['images'][die,sm][pc]:
                raise ValueError('loaded native marker instruction differs')
        def observe(before, after):
            owner = self.engine.sm_engine
            if owner.state != 'WAIT' or owner.entry != self.engine.entries['layer']:
                return
            entering = self._entering_swapin(owner)
            layer, column = entering['pos'], entering['input_token']
            uint(layer, self.p.m.L, 'layer'); uint(column, 13, 'column')
            for index, state in enumerate(after['sms']):
                marker = markers.get((index,state['pc']))
                if not marker or marker['kind'] != 'layer' or not state['can_issue']:
                    continue
                key = (owner.job,owner.generation,owner.position,layer,column,index,state['pc'])
                if key in self.seen:
                    continue
                die,sm = divmod(index,2)
                ctr = struct.unpack('<I',self._read(die,self.p.a['CTR'],4))[0]
                if ctr != layer or self.pins.read_ur(die,sm,1) != owner.position:
                    raise RuntimeError('actual descriptor/position owner mismatch')
                ke = self.p.m.k_exp
                ids = struct.unpack('<'+'I'*ke,self.pins.read_shared(die,sm,0x7C80,ke*4))
                weights = self.pins.read_shared(die,sm,0x7CC0,ke*4)
                if tuple(sorted(set(ids))) != ids or any(e >= self.p.m.n_exp for e in ids):
                    raise RuntimeError('actual source expert ordering/range mismatch')
                phase = marker['phase']
                steps = 5 if phase == 'prefix_begin' else 2
                activation = tuple(self.pins.read_bd_activation(die,sm,j) for j in range(steps))
                spans = self._weight_lines(die,sm,layer,ids,phase,marker['slot'])
                if self.pins.snapshot() != after:
                    raise RuntimeError('source probe advanced actual RTL')
                self.movements.append(dict(source_sha256=self.source_sha256,job=owner.job,
                    generation=owner.generation,position=owner.position,layer=layer,column=column,
                    die=die,sm=sm,pc=state['pc'],time_ps=after['time_ps'],phase=phase,
                    issued_slot=marker['slot'],expert_ids=ids,route_weights=weights,
                    activation_bd266x8=activation,weight_lines=spans,
                    qualification='actual readback only; no grant/reuse/overlap credit'))
                self.seen.add(key)
        self.pins.observers.append(observe)
        self._observer = observe
        return observe
