"""Production FFN down placement and exact VS13 combine encoder.

Down output rows are TP4-sharded; no four-rank arithmetic reduction belongs
here. Transport records describe real XR RD row pairs, never constant writes.
The caller must schedule these records on actual paths before admission.
"""
from __future__ import annotations

CAPTURE = 128
ASSEMBLED = 320
COMBINED = 448
PRE = 1008
POST = 1009
NEXPERT = 7
ROWS = 16
COMBINE_BOUND = 100  # conservative pre-measurement slot, not adopted token price


def owner(global_element):
    if not 0 <= global_element < 5120:
        raise ValueError('FFN global element outside5120')
    beat, word = divmod(global_element, 64)
    return dict(beat=beat, sid=beat // 5, leaf=beat % 5, word=word)


def capture(rank, sid, expert_slot):
    """Actual cap ABI: rbase is rank-local, obase is a WORD address."""
    if rank not in range(4) or sid not in range(16) or expert_slot not in range(7):
        raise ValueError('invalid rank/slice/expert slot')
    return dict(obase=4 * (CAPTURE + 16 * expert_slot), ops=0, np=0,
                fmt=2, rbase=80 * sid, rcnt=80, rsplit=0, lo32=0, hi32=0)


def transfers(rank):
    """Every real source pair once, with the precise destination owner/row.

    Each record is one256-bit RD payload (two four-word rows). Consecutive
    records can be packed only when source AND destination rows stay contiguous.
    Source and assembled buffers are disjoint, so this map cannot clobber an
    unsent capture. Seven phases are routed0..5 then shared6.
    """
    if rank not in range(4):
        raise ValueError('invalid TP4 rank')
    out = []
    for expert in range(7):
        for local in range(0, 1280, 8):
            source_sid, offset = divmod(local, 80)
            source_leaf, source_word = divmod(offset, 64)
            dst = owner(1280 * rank + local)
            out.append(dict(rank=rank, expert=expert, global_element=1280 * rank + local,
                            source_sid=source_sid, source_leaf=source_leaf,
                            source_row=CAPTURE + 16 * expert + source_word // 4,
                            sid=dst['sid'], leaf=dst['leaf'], beat=dst['beat'],
                            row=ASSEMBLED + 16 * expert + dst['word'] // 4,
                            pairs=1, words=8, kind=4))
    return out


def commands(sid, leaf):
    """Actual VP160 commands, not injected arithmetic results."""
    from layer_prog.lower_vs import vp_cmd, vs_imm
    if sid not in range(16) or leaf not in range(5):
        raise ValueError('invalid destination leaf')
    return dict(combine=vp_cmd(13, a0=ASSEMBLED, n=8, imm=vs_imm(ob=COMBINED)),
                post=vp_cmd(2, a0=POST, a1=COMBINED), pre=PRE,
                beat=5 * sid + leaf)


def verify_moves(records):
    """Fail closed on ownership, row order, missing/duplicate or changed data paths."""
    expected = [r for rank in range(4) for r in transfers(rank)]
    key = lambda r: (r['rank'], r['expert'], r['global_element'])
    by = {}
    for r in records:
        k = key(r)
        if k in by:
            raise ValueError('duplicate FFN source pair')
        by[k] = r
    if len(by) != len(expected):
        raise ValueError('missing FFN source pair')
    for e in expected:
        if by.get(key(e)) != e:
            raise ValueError('wrong FFN row/owner/order')
    return True


def check_lease(leases, start, end):
    """The VPX phase reuse must be explicit; gains/pre are not disposable."""
    if not 0 <= start <= end:
        raise ValueError('invalid FFN lease interval')
    for lease in leases:
        if not {'first', 'last', 'row0', 'row1', 'consumer'} <= lease.keys():
            raise ValueError('incomplete row lifetime')
        if lease['first'] <= end and start <= lease['last']:
            for lo, hi in ((CAPTURE, CAPTURE + 112), (ASSEMBLED, ASSEMBLED + 112),
                           (COMBINED, COMBINED + 16)):
                if lease['row0'] < hi and lo < lease['row1']:
                    raise ValueError('live row owner overlaps final FFN placement')
    return True


def local_program(sid, leaf, binding):
    """Bind real combine/POST words after a supplied static arrival calendar.

    The caller must give all56 pair-arrival entries for this destination and
    explicit row lifetimes. This proves local dependency ordering only; actual
    paths, collision reservations and POST/native timing remain other gates.
    """
    from layer_prog.lower_vs import ctl_payload
    if not {'arrivals', 'leases', 'combine_issue', 'post_issue', 'post_end'} <= binding.keys():
        raise ValueError('missing final FFN arrival/lifetime/calendar binding')
    required = [m for rank in range(4) for m in transfers(rank)
                if m['sid'] == sid and m['leaf'] == leaf]
    arrivals = binding['arrivals']
    if len(arrivals) != len(required):
        raise ValueError('missing or duplicate final FFN arrival')
    expected = {(m['expert'], m['row']) for m in required}
    seen = set()
    for arrival in arrivals:
        k = (arrival['expert'], arrival['row'])
        if k not in expected or k in seen or arrival['cycle'] < 0:
            raise ValueError('wrong final FFN arrival owner/row')
        seen.add(k)
    combine, post, end = (int(binding[k]) for k in ('combine_issue', 'post_issue', 'post_end'))
    first, last = min(x['cycle'] for x in arrivals), max(x['cycle'] for x in arrivals)
    if combine <= last or post < combine + COMBINE_BOUND + 3 or end < post:
        raise ValueError('early combine/POST or invalid lifetime')
    check_lease(binding['leases'], first, end)
    c = commands(sid, leaf)
    return dict(templates=[('ffn.combine.owner', ctl_payload(1 << sid, 0, 1 << leaf, c['combine'])),
                           ('ffn.hc_post.y', ctl_payload(1 << sid, 0, 1 << leaf, c['post']))],
                rows=[dict(eng=0, issue=combine, arg=0, what='VS13 routed-ID-order then shared'),
                      dict(eng=0, issue=post, arg=1, what='POST real combined rows448..463; pre1008 retained')],
                beat=c['beat'], latest_arrival=last)
