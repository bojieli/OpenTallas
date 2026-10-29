"""Opt-in P3 normal-MATVEC input packing; no production caller or timing adoption.

Preserves the old normal-front fragment bits. Width agreement does not establish
P3 position/context equivalence. Pinned halves and the numeric csum are untouched.
"""
SOURCE_COMMIT = '4d6f5439dcee43b97baffaa731aae826fdcb6a66'
HEADER_COMMIT = '4673cf757e'
BACKEND_COMMITS = ['0b5be908d', '131927b83']
ISA_SOURCE = 'e938fd6db25b462716bd170e83970780614e81e0:tools/hbm_next/isa_rows.py'
FRAGMENT_BITS, BEAT_BITS, ROW_BITS = 8 * 3152, 2069, 818


def uint(value, width):
    if type(value) is not int or not 0 <= value < (1 << width):
        raise ValueError(f'unsigned {width}-bit value required')
    return value


def xs_fields(column, pair, south):
    uint(column, 3); uint(pair, 1); uint(south, 1)
    row = 2 * pair + south
    fa, fb = column * 3152 + row * 532, column * 3152 + 2128 + row * 256
    return dict(sa1=(fa % 2048) >> 2, sg1=fa // 2048,
                sa2=(fb % 2048) >> 4, sg2=fb // 2048)


def xs_word():
    value = 0
    for c in range(8):
        for p in range(2):
            for south in range(2):
                f = xs_fields(c, p, south)
                word = f['sa1'] | f['sg1'] << 9 | f['sa2'] << 14 | f['sg2'] << 21
                value |= word << (52 * (2 * c + p) + 26 * south)
    return uint(value, 832)


def selector(target, active):
    uint(target, 3); uint(active, 3)
    if not target or not active or target & ~active:
        raise ValueError('nonempty target subset of active P3 lanes required')
    # OH all zero reserves this as control; ordinary group zero uses OH=1.
    return (1 << 2068) | target | active << 8


def activation_beat(data, group, address):
    uint(data, 2048); uint(address, 7)
    if type(group) is not int or not 0 <= group < 13:
        raise ValueError('normal fragment group must be 0..12')
    return (1 << 2068) | address << 2061 | (1 << group) << 2048 | data


def rows(north, south):
    return uint(north, ROW_BITS) | uint(south, ROW_BITS) << ROW_BITS


def input_packet(row_pairs, beat_pairs):
    """Pack two physical pairs per side, preserving already-formed normal rows."""
    if len(row_pairs) != 2 or len(beat_pairs) != 2:
        raise ValueError('exactly two physical pairs per boundary required')
    return dict(row=sum(uint(v, 1636) << (1636 * p) for p, v in enumerate(row_pairs)),
                beat=sum(uint(v, BEAT_BITS) << (BEAT_BITS * p) for p, v in enumerate(beat_pairs)))


def compile_load(fragments, *, fmt, address=0, first_edge=0, enabled=False, unit='SM.MATVEC'):
    """Emit selector + thirteen original-layout activation beats per P3 lane.

    Edge numbers refer ONLY to this candidate's backend input sampling boundary.
    No row may be scheduled from these dates until the write/read path is priced.
    """
    if not enabled:
        raise ValueError('P3 candidate requires explicit enabled=True')
    if unit != 'SM.MATVEC' or fmt not in (0, 1, 2):
        raise ValueError('only normal BF16/FP8/FP4 MATVEC; ATT and INT8 unsupported')
    if not 1 <= len(fragments) <= 3:
        raise ValueError('one to three independent position fragments required')
    uint(address, 7)
    if type(first_edge) is not int or first_edge < 0:
        raise ValueError('nonnegative backend sample edge required')
    active = (1 << len(fragments)) - 1
    events = []
    for lane, fragment in enumerate(fragments):
        uint(fragment, FRAGMENT_BITS)
        edge = first_edge + 14 * lane
        words = [selector(1 << lane, active)] + [
            activation_beat((fragment >> (2048 * g)) & ((1 << 2048) - 1), g, address)
            for g in range(13)]
        for offset, beat in enumerate(words):
            packet = input_packet([0, 0], [beat, beat])
            events.append(dict(edge=edge + offset, kind='select' if offset == 0 else 'activation',
                               lane=lane, row_left=0, row_right=0,
                               beat_left=packet['beat'], beat_right=packet['beat']))
    return dict(schema='opentallas.hbm.p3_normal_issue_candidate.v1', qualified=False,
                sources=dict(native=SOURCE_COMMIT, header=HEADER_COMMIT, backend=BACKEND_COMMITS, isa=ISA_SOURCE),
                xs_config=xs_word(), active_lanes=active, events=events,
                dates=dict(basis='backend input sampling edge', first_selector=first_edge,
                           last_activation=events[-1]['edge'], first_safe_row=None, first_gather=None,
                           pair_hardening_delta=dict(external_row=0, external_bout=0, gather=3, reset_release=2),
                           absolute_frontend_to_leaf_qualified=False),
                remaining=['P3 A/context/row mapping', 'write-to-read endpoint dates',
                           'normal-row issue and csum/gather integration', 'physical placement and loaded clock'])
