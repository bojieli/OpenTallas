"""Contents-only calendar reuse for the existing immutable XS ROM pair.

No new action, reader state or port. Equal stream programmes share an address.
Each pipelined phase uses a short reader interval. ACCEPT/CFG of the next phase
stay in the preceding interval; all original functional action edges are exact.
PRIME/START use an existing idle gap, independent of completion or ready.
"""
from __future__ import annotations

ACTION_MASK = (1 << 75) - 1
END = 1 << 72


def dedup_stream(phase, stream):
    out, image, bases = list(phase), [], {}
    for p in range(len(out) // 2):
        w = out[2*p]
        n, base = (w >> 14) & 0xffff, (w >> 30) & 0xffff
        assert base + n <= len(stream), ('stream bounds', p, base, n)
        key = tuple(stream[base:base+n])
        if key not in bases:
            bases[key] = len(image)
            image.extend(key)
        b = bases[key]
        assert b < 16384 and b+n <= 16384
        out[2*p] = (w & ~(((1 << 16)-1) << 30)) | (b << 30)
        assert image[b:b+n] == list(key)
    return out, image


def split_intervals(cal):
    """Rows use the original absolute calendar age; intervals rebase time only.

    Phase n interval starts launch_n. The previous interval contains that
    phase's accept/CFG (launch-62/-52 at cfg_lead52) and ends >=2 edges after
    its last action. PRIME is20 edges before START. Admission checks the actual
    events, rather than assuming a shape's gap is wide enough.
    """
    raw = [(w >> 75, w & ACTION_MASK) for w in cal['packed'] if not w & END]
    candidates = [0] + [p['launch'] for p in cal['phases'][1:]]
    assert all(a < b for a,b in zip(candidates,candidates[1:]))
    starts = [0]
    for candidate in candidates[1:]:
        before = [t for t, _a in raw if starts[-1] <= t < candidate]
        # A phase boundary is only an address-reuse opportunity. Keep the
        # reader running when real actions leave no fixed PRIME/START gap.
        # Nothing moves in time; the layer ROM-capacity check still applies.
        if before and before[-1] + 2 < candidate - 20:
            starts.append(candidate)
    chunks = []
    for i,b in enumerate(starts):
        hi = starts[i+1] if i+1 < len(starts) else None
        events = [(t,a) for t,a in raw if t >= b and (hi is None or t < hi)]
        assert events, ('empty interval', cal['op'],i)
        end = events[-1][0]+2
        if hi is not None:
            assert end < hi-20, ('no fixed PRIME gap',cal['op'],i,end,hi-20)
        rows = tuple([((t-b) << 75)|a for t,a in events]+[((end-b) << 75)|END])
        assert rows[-1] >> 75 < (1 << 24)
        chunks.append(dict(start=b,end=end,rows=rows))
    replay = [(c['start']+(w >> 75),w & ACTION_MASK) for c in chunks for w in c['rows'] if not w & END]
    assert replay == raw, ('functional edge mismatch',cal['op'])
    # GO must still arrive while the calendar is active, including accept_tag0
    # actions whose all-zero action word alone cannot prove calendar availability.
    for p in cal['phases']:
        assert any(c['start'] <= p['accept'] <= c['end'] for c in chunks)
    return chunks


def pack_layer(order, starts):
    import xs_calendar as XC
    packed,lookup,iss,segments = [],{},{},[]
    intervals=[]
    for n,c in enumerate(order):
        S = starts[c['op']]
        for t,v in c['iss'].items():
            if t in (XC.TS-20, XC.TS) or (t == XC.T_OFFCFG and n):
                continue
            assert S+t not in iss, ('issuer collision',S+t)
            iss[S+t] = v
        for i,chunk in enumerate(split_intervals(c)):
            start=S+chunk['start']
            events=[(start+(w>>75),w&ACTION_MASK) for w in chunk['rows'] if not w&END]
            # ASAP op windows may touch: a next op's first ACCEPT is only
            # one edge after the previous RETIRE. Keep both in one interval;
            # re-priming there would overlap an active reader. The next phase
            # boundary has the checked fixed gap and resumes ordinary reuse.
            if intervals and intervals[-1]['end'] >= start-20:
                assert i==0, ('phase PRIME overlap',c['op'],i)
                prev=intervals[-1]
                assert prev['events'][-1][0] < events[0][0], 'op action overlap'
                prev['events'].extend(events)
                prev['end']=events[-1][0]+2
                prev['ops'].append(c['op'])
            else:
                intervals.append(dict(start=start,end=events[-1][0]+2,events=events,ops=[c['op']]))
    replay=[e for c in intervals for e in c['events']]
    original=[(starts[c['op']]+(w>>75),w&ACTION_MASK) for c in order for w in c['packed'] if not w&END]
    assert replay==original, 'layer functional action-edge mismatch'
    for chunk in intervals:
        start=chunk['start']
        rows=tuple([((t-start)<<75)|a for t,a in chunk['events']]+[((chunk['end']-start)<<75)|END])
        if rows not in lookup:
            lookup[rows]=len(packed)
            packed.extend(rows)
        base=lookup[rows]
        for delta,key in [(-20,'prime'),(0,'start')]:
            t=XC.TS+start+delta
            assert t not in iss, ('PRIME/START issuer collision',t)
            iss[t]=XC.isd(**{key:1},base=base,length=len(rows))
        segments.append(dict(ops=chunk['ops'],start=start,end=chunk['end'],base=base,rows=len(rows)))
    assert all(a['end'] < b['start']-20 for a,b in zip(segments,segments[1:])), 'reader re-prime while active'
    assert len(packed)<=4096, ('segmented calendar capacity',len(packed))
    ts=sorted(iss)
    assert all(sum(j <= t < j+XC.OFF+2 for j in ts)<=XC.ND for t in ts), 'issuer delay-line overflow'
    return dict(packed=packed,iss=iss,segments=segments,rows=len(packed),unique_intervals=len(lookup),PASS=True)
