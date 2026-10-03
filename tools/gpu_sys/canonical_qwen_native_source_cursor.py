"""Owned native RPC source cursor, independent of controller commands.

Only literal recipe identity and typed source metadata are compiled here. No
operand value is evaluated; no owner, profile-valid or visibility is invented.
Nash's sealed collector retains this seed and qualifies Pauli's immutable ROM.
Its matching terminal/reverse/drain output is the sole advance authority.
"""
from dataclasses import dataclass
from math import prod

from tools.gpu_sys.canonical_qwen_native_factory import need, uint
from tools.gpu_sys.canonical_qwen_primitive_control import compile_source, PROGRAM_SHA

TYPES = {'<f4': (0, 4), '<u4': (1, 4), '<i8': (2, 8),
         '|u1': (3, 1), '|i1': (3, 1)}


@dataclass(frozen=True)
class SourceSeed:
    """Source metadata only; no RF allocations or numerical result bytes."""
    PC: int
    sequence: int
    descriptor: int
    operands: int
    types: int
    signed_i8: int
    counts: int
    vector_mask: int
    template: int
    step: int
    substep: int
    scalars: int
    tail: int

    def load_fields(self, tuple239, owner55):
        t = uint(tuple239, 239, 'retained source root')
        need((t >> 164) & 2047 == self.PC, 'source cursor root PC')
        return dict(cursor_load_tuple=t,
                    cursor_load_owner=uint(owner55, 55, 'retained source owner'),
                    **{'cursor_load_' + k: v for k, v in vars(self).items() if k != 'PC'})


class SourceCompiler:
    """Resolve all1737 PC admissions against the pinned13 literal recipes.

    `request` is DeliverySession's owned source RPC, before native_binding or
    command construction. Command dictionaries are deliberately not accepted.
    The immutable hardware profile validates logical output shape independently.
    """
    def __init__(self):
        self.source = compile_source()  # verifies canonical archive SHA

    def seed(self, request):
        need(request.get('program_sha256') == PROGRAM_SHA, 'source cursor program pin')
        pc = uint(request.get('source_PC'), 11, 'source PC')
        need(pc < self.source['source_operations'], 'source PC outside1737')
        sequence = uint(request.get('sequence'), 64, 'owned RPC sequence')
        rows = [r for r in self.source['descriptors']
                if all(r[k] == request.get(k) for k in
                       ('template', 'ordered_step', 'source_node', 'lowered_primitive', 'attrs'))]
        need(len(rows) == 1, 'literal source node/substep/attributes must resolve uniquely')
        row = rows[0]
        need(self.source['pc_template_masks'][pc] & (1 << row['template_id']),
             'source PC does not admit this recipe')
        need(request.get('explicit_shape') is None, 'immutable profile explicit-shape unsupported')
        args = request.get('operands')
        need(isinstance(args, list) and 1 <= len(args) <= 4, 'source operand census')
        arity = 2 if row['source_node']['op'] == 'NEG' and row['substep'] == 1 else len(row['source_node']['src'])
        need(len(args) == arity, 'literal source operand arity')
        types = signed = counts = ranks = scalars = tail = 0
        for i, a in enumerate(args):
            shape = a.get('shape'); dtype = a.get('dtype')
            need(dtype in TYPES and isinstance(shape, list) and len(shape) <= 1
                 and all(type(n) is int and 1 <= n <= 128 for n in shape),
                 'immutable source profile type/rank/count')
            count = prod(shape)
            need(1 <= count <= 128 and type(a.get('payload')) is bytes
                 and len(a['payload']) == count * TYPES[dtype][1], 'source payload extent')
            if dtype == '|i1':
                need(row['lowered_primitive'] == 'I2F', 'signed I8 requires actual I2F delegate')
                signed |= 1 << i
            types |= TYPES[dtype][0] << (2 * i)
            counts |= count << (8 * i)
            ranks |= bool(shape) << i
            scalars |= (count == 1) << i
            # Four 2bit fields: count mod4; zero means a full4lane lastbeat.
            tail |= (count % 4) << (2 * i)
        return SourceSeed(pc, sequence, row['id'], len(args), types, signed,
                          counts, ranks, row['template_id'], row['ordered_step'],
                          row['substep'], scalars, tail)

    def require_next(self, previous, seed):
        """Literal recipe progression; LOOP repetition stays the owned source's job."""
        if previous is None:
            need(seed.step == 0 and seed.substep == 0, 'source cursor must start recipe first step')
            return
        rows = [r for r in self.source['descriptors'] if r['template_id'] == previous.template]
        index = next(i for i, r in enumerate(rows) if r['id'] == previous.descriptor)
        if index + 1 < len(rows):
            need(seed.PC == previous.PC and seed.descriptor == rows[index+1]['id'],
                 'source cursor skipped or reordered native recipe substep')
        else:
            need(seed.step == 0 and seed.substep == 0, 'next recipe must start first step')


class SourceCursorProducer:
    """Emit first/next source seed into the SAME physical collector record.

    Constructor has no SET/EDGE. `prepare` precedes native_binding/staging/cmd.
    `finish` must follow pump result/reverse acceptance; it cannot advance on
    command acceptance. No additional context, clock, MatrixFactory or hook.
    """
    def __init__(self, root, collector, compiler=None):
        need(collector.root is root, 'one enclosing source cursor clock')
        self.root, self.collector = root, collector
        self.compiler = compiler if compiler is not None else SourceCompiler()
        self.active = None
        self.last_sequence = None
        self.previous = None
        self.stopped = False

    def _scope(self, t, owner):
        p = self.collector
        need(not p.get('fault') and p.get('issuer_held_valid')
             and not p.get('issuer_held_fault')
             and p.get('issuer_held_tuple') == t and p.get('issuer_held_owner') == owner,
             'source cursor issuer scope not actually retained')

    def prepare(self, request, tuple239, owner55):
        need(not self.stopped and self.active is None, 'source cursor retained/debt/fault')
        seed = self.compiler.seed(request)
        self.compiler.require_next(self.previous, seed)
        fields = seed.load_fields(tuple239, owner55)
        need(self.last_sequence is None or seed.sequence > self.last_sequence,
             'source cursor stale or wrapped RPC sequence')
        p = self.collector
        with self.root.lock:
            try:
                self._scope(tuple239, owner55)
                for k, v in fields.items(): p.set(k, v)
                p.set('cursor_load_valid', 1)
                try:
                    while True:
                        self.root.settle(); self._scope(tuple239, owner55)
                        accept = bool(p.get('cursor_load_ready'))
                        self.root.tick()
                        if accept: break
                finally: p.set('cursor_load_valid', 0)
                self.root.settle(); self._scope(tuple239, owner55)
                need(p.get('source_cursor_valid'), 'source cursor load not actually retained')
                for k, v in vars(seed).items():
                    output = {'PC': 'authority_PC', 'sequence': 'authority_sequence',
                              'step': 'source_ordered_step', 'signed_i8': 'source_signed_i8_mask'}.get(k, 'source_' + k)
                    need(p.get(output) == v, 'sealed source cursor mismatch ' + k)
                self.active = (seed, tuple239, owner55)
                return seed
            except BaseException:
                self.stopped = True
                raise

    def finish(self):
        need(not self.stopped and self.active is not None, 'no retained source cursor')
        seed, t, owner = self.active
        p = self.collector
        with self.root.lock:
            try:
                while True:
                    self.root.settle(); self._scope(t, owner)
                    need((p.get('authority_tuple'), p.get('authority_owner'), p.get('authority_sequence'))
                         == (t, owner, seed.sequence), 'stale source terminal/reverse scope')
                    if p.get('source_cursor_advance_valid'): break
                    self.root.tick()
                p.set('source_cursor_advance_ready', 1)
                try:
                    self.root.settle(); self._scope(t, owner)
                    need(p.get('source_cursor_advance_valid'), 'source advance withdrawn')
                    self.root.tick()
                finally: p.set('source_cursor_advance_ready', 0)
                self.root.settle()
                need(not p.get('source_cursor_advance_valid') and not p.get('source_cursor_valid'),
                     'source cursor advance not actually accepted')
                self.last_sequence = seed.sequence
                self.previous = seed
                self.active = None
            except BaseException:
                self.stopped = True
                raise


@dataclass(frozen=True)
class SourceCursorBinding:
    """Actual issuer/collector view supplied by installed physical authority."""
    producer: SourceCursorProducer
    tuple239: int
    owner55: int


def compile_command(request, row, **owned):
    """Raw signed-I8 carrier plus original signed descriptor fingerprint.

    Original1bb compiler remains immutable. The temporary metadata carrier
    view affects only two-bit wire encoding; source bytes are never converted.
    Pauli compares mask and descriptor fingerprint to independent source ROM.
    """
    from tools.gpu_sys.canonical_qwen_native_banked_join import compile_command as base
    from tools.gpu_sys.canonical_qwen_native_factory import descriptor
    from tools.gpu_sys.canonical_qwen_service_calendar import canonical, sha
    operands = request['operands']
    signed = sum((a['dtype'] == '|i1') << i for i, a in enumerate(operands))
    need(not signed or request['lowered_primitive'] == 'I2F', 'signed I8 actual conversion only')
    carrier = dict(request, operands=[dict(a, dtype='|u1') if a['dtype'] == '|i1' else a for a in operands])
    fields = base(carrier, row, **owned)
    fields['cmd_signed_i8_mask'] = signed
    fields['cmd_shape_sha'] = int(sha(canonical(descriptor(request, list(owned['result_shape'])))), 16)
    return fields


def native_factory(authority, contexts):
    """Same four handlers/context set; primitive uses sealed source cursor.

    Required authority.native_source_cursor(request) returns SourceCursorBinding
    from actual installed issuer/collector. It must not obtain identity from a
    pending command. Missing provider binding refuses, with no legacy fallback.
    """
    from tools.gpu_sys.canonical_qwen_native_rf_pump import RFNativeHandlers, HeldRFCommand, OwnedPage
    class SourceHandlers(RFNativeHandlers):
        def native_primitive(self, request):
            resolver = getattr(self.authority, 'native_source_cursor', None)
            need(callable(resolver), 'actual source cursor authority hook missing')
            cursor = resolver(request)
            need(isinstance(cursor, SourceCursorBinding) and cursor.producer.root is self.base.root,
                 'actual enclosing source cursor binding required')
            cursor.producer.prepare(request, cursor.tuple239, cursor.owner55)
            try:
                binding = self.authority.native_binding('native_primitive_RF', request)
                need(isinstance(binding, HeldRFCommand) and
                     (binding.tuple239, binding.owner55) == (cursor.tuple239, cursor.owner55),
                     'command must use actual source cursor issuer scope')
                command = dict(binding.fields)
                seed = cursor.producer.active[0]
                need(all(command.get(k) == v for k, v in
                         dict(cmd_descriptor=seed.descriptor, cmd_operands=seed.operands,
                              cmd_types=seed.types, cmd_counts=seed.counts,
                              cmd_signed_i8_mask=seed.signed_i8, cmd_template=seed.template,
                              cmd_step=seed.step, cmd_substep=seed.substep,
                              cmd_scalars=seed.scalars).items()), 'command disagrees with owned source cursor')
                for index, operand in enumerate(request['operands']):
                    # Compiler already validates payload length/type; no numerical conversion.
                    raw = operand['payload']
                    for offset in range(0, len(raw), 512):
                        page = self.authority.native_input_page(request, index, offset // 512)
                        need(isinstance(page, OwnedPage) and page.tuple239 == cursor.tuple239
                             and page.slot == ((command['cmd_source_slots'] >> (18*index+9*(offset//512))) & 511)
                             and page.owner46 == ((command['cmd_source_owners'] >> (46*index)) & ((1<<46)-1)),
                             'actual source staging aperture mismatch')
                        self.initializer.write(page, raw[offset:offset+512].ljust(512, b'\0'))
                result = self.pump.run(request, binding)
                cursor.producer.finish()
                return result
            except BaseException:
                cursor.producer.stopped = True
                raise
    return SourceHandlers(authority, contexts).handlers()
