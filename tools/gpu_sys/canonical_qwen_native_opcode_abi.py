"""Shared native dispatch IDs and source attributes; no numerical evaluation.

IDs0..16 preserve Boole's frozen stateless bits ABI. Global opcode uses6bits;
engine selection is explicit rather than truncating the opcode to5bits.
"""
OPCODES = dict(zip((
    'COPY','BITCAST_U','BITCAST_F','AND','OR','XOR','IADD','ISUB','SHR','SHL',
    'FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE','SELECT','FMAX','FMIN',
    'FADD','FMUL','DIV','SQRT','I2F','F2I','LDEXP','FP8_PACK','FP8_UNPACK',
    'LOAD','CONST','IOTA','RESHAPE','SLICE','TRANSPOSE','CONCAT','BROADCAST',
    'TAKE','SCATTER','ASSERT','PACKET_COMMIT','IMUL','IMOD'), range(40)))
TYPES = {'F32':0, 'U32':1, 'I64':2, 'U8':3}
ENGINE = {name: ('bits' if code <= 16 else 'fp32' if code <= 20 else
                 'convert' if code <= 25 else 'movement' if code <= 37 else
                 'UNBOUND_integer_multiply_modulo') for name,code in OPCODES.items()}
# Preserve the source VM default, not the attributes of another leaf.
CANONICAL_ZERO_OPS = frozenset(('FADD','FMUL','DIV','SQRT'))


def canonical_zero(op, attrs):
    value = attrs.get('canonical_zero', True) if op in CANONICAL_ZERO_OPS else False
    if type(value) is not bool: raise ValueError('canonical_zero must be a source boolean')
    return value


def dispatch(op, attrs):
    if op not in OPCODES: raise ValueError('unbound native opcode')
    return dict(opcode=OPCODES[op],engine=ENGINE[op],canonical_zero=canonical_zero(op,attrs))


def movement_model():
    """Prospective combinational gather under Pauli's existing protected seats.

    No new engine/controller state and no claimed clock/area/slot qualification.
    This model precedes the default-off movement RTL. Full retained buffers
    belong to the ONE controller and must not be counted a second time.
    """
    return dict(lanes=4,MACs_per_cycle=0,words_per_cycle=4,
                bytes_per_cycle=32,operand_retained_bus_bits=3*8192,
                result_boundary_bits=256,address_boundary_bits=4*(7+2+1),
                immutable_boundary_bits=256,extra_state_bits=0,
                buffer_words_per_operand=128,operands=3,
                mux_inputs_per_lane=3*128+1,
                mux_2to1_64bit_equivalents=4*(3*128)*64,
                address_fanout=64,replicas_per_endpoint=1,
                routes_required_tracks=3*8192+256+40+256,
                route_capacity=None,
                mux_area_mm2_estimate=4*(3*128)*64*(3*0.08748+0.04374)/1e6,
                mux_area_mm2_at_50pct=2*4*(3*128)*64*(3*0.08748+0.04374)/1e6,
                area_basis='source SS NAND2=.08748um2 INV=.04374um2;3NAND+INV per2:1mux, excludes loaded buffers/ports/addresslogic',
                area_source='results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json',
                floorplan_fit=None,
                service_edges_per_full128_min=32,latency_added_min_edges=1,
                clock='existing controller source clock; prospective, not SS/FF',
                token_latency='actual source command counts times accepted beat service plus physical waits; unknown until composed',
                controller_seats_owned_by='Pauli; do not duplicate protected operands/results',
                actual_take_scatter_indices='captured operand index, rangechecked; never host result bytes',
                lease_visibility='LOAD/PACKET_COMMIT require actual retained producer-visible authority',
                headline_adopt=False)
