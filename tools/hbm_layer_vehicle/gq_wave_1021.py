"""Opt-in real GQ one-sender transport; no data images or expected-value inputs.

Microarchitecture price: existing 256b/ring/edge, F/2 ring indices, 3-edge pair
schedule. Four serial F12 waves (384 gathered FP32 words) or three serial F16
waves (384 TOPK words). VM plain reads retain +16; ring-A inject +29+VM_RT;
landing/KQ-share writes +34+VM_RT+2h, self +29+VM_RT. No added stage/storage,
ports, arithmetic, CP ABI bits, clock crossing or physical view qualification.
Source candidate requires OT_COLL_GQ_SINGLE_SENDER and all four real stops;
the SW-only 563-instance cut cannot qualify remote producers.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE = 'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv'
ORIGINAL_SHA256 = 'd4990b482a26674449f61722eb44c246bce525c41d7682704e7d94bd5abcd0fa'
DEFINE = 'OT_COLL_GQ_SINGLE_SENDER'
NEXT = (1, 3, 0, 2)
PREV = (2, 0, 3, 1)


def _issue(k):
    return 1 + 3 * (k // 2) + k % 2


def _source(q, direction, hops):
    for _ in range(hops):
        q = (PREV if direction == 0 else NEXT)[q]
    return q


def wave_plan(*, F, senders, source_sectors, destination_sectors, vm_rt,
              first_fire=40, rings=2, read_request_delays=None):
    """Absolute stream edges relative to GQ programme-start/fire origin.

    source_sectors/destination_sectors: four explicit 13-bit local addresses.
    vm_rt: four exact selected source parameters. Every quarter receives each
    wave; TOPK consumes the dense SW copy. No absent NE source is read.
    Caller reserves/loads all calendars, installs rows and issues common launch;
    add actual launch_sample+FIRE_FROM_LAUNCH to listed edge values.
    """
    if F not in (12, 16) or rings != 2:
        raise ValueError('bounded selected F12/F16 two-ring transport only')
    if tuple(senders) not in ((0, 1, 2, 3), (0, 1, 2), (0,)) or (tuple(senders) == (0,) and F != 16):
        raise ValueError('only actual 4-quarter COLL, 3-quarter TOPK or SW F16 P-page source')
    if len(vm_rt) != 4 or len(set(vm_rt)) != 1 or min(vm_rt) < 0:
        raise ValueError('equal explicit VM_RT on four coherent GQ sources required')
    if len(source_sectors) != 4 or len(destination_sectors) != 4:
        raise ValueError('four explicit VM allocations required')
    n = len(senders) * F
    for q in range(4):
        if not 0 <= destination_sectors[q] <= 8192-n:
            raise ValueError('dense destination crosses quadrant VM boundary')
        if q in senders and not 0 <= source_sectors[q] <= 8192-F:
            raise ValueError('source crosses quadrant VM boundary')
        if q in senders and max(source_sectors[q], destination_sectors[q]) < min(source_sectors[q]+F, destination_sectors[q]+n):
            raise ValueError('source and dense destination must not overlap')
    if read_request_delays is not None:
        if (len(read_request_delays) != 4 or any(len(x) != 8 for x in read_request_delays)
                or any(type(x) is not int or x < 0 for row in read_request_delays for x in row)):
            raise ValueError('explicit nonnegative 4x8 GQ-request-to-bank delays required')
    V = vm_rt[0]
    # Last event fully drains ND=40+V before next fire. No timing inferred from
    # data and no shortening from idle stops; preserve existing busy semantics.
    wave_span = 100 + V  # bounded four-stop bench programme spacing, including drain
    starts = [first_fire + j*wave_span for j in range(len(senders))]
    period = starts[-1] + wave_span
    if first_fire < 0 or period >= 65536:
        raise ValueError('programme period exceeds descriptor field')
    rows = [[] for _ in range(4)]
    reads, writes, ring = [], [], []
    for j, sender in enumerate(senders):
        fire = starts[j]
        for q in range(4):
            src = (q << 13) | (source_sectors[q] if q == sender else 0)
            dst = (q << 13) | destination_sectors[q]
            payload = (2 | 4 | (fire << 3) | (F << 19) | ((128 | (1 << sender)) << 29)
                       | (src << 37) | (dst << 53) | (F << 69) | (period << 85))
            rows[q].append((0xc7a1 << 240) | (j << 224) | payload)
        for i in range(F):
            r, k = i % 2, i // 2
            ie, direction = fire + _issue(k), k % 2
            reads.append(dict(quarter=sender, edge=ie+16, sector=source_sectors[sender]+i,
                              bank=(source_sectors[sender]+i)%8, read_group=3))
            node = sender
            ring.append(dict(ring=r, quarter=node, direction=direction, edge=ie+29+V,
                             kind='inject', source=sender, tag=k%8, ttl=3))
            for h in range(1, 4):
                node = (NEXT if direction == 0 else PREV)[node]
                assert _source(node, direction, h) == sender
                ring.append(dict(ring=r, quarter=node, direction=direction, edge=ie+29+V+2*h,
                                 kind='receive_forward' if h<3 else 'receive', source=sender,
                                 tag=k%8, ttl=4-h))
                sec = destination_sectors[node]+sender*F+i
                writes.append(dict(quarter=node, edge=ie+34+V+2*h, sector=sec,
                                   bank=sec%8, write_code=2, source=sender, flit=i))
            sec = destination_sectors[sender]+sender*F+i
            writes.append(dict(quarter=sender, edge=ie+29+V, sector=sec,
                               bank=sec%8, write_code=2, source=sender, flit=i))
    reservations = []
    for kind, entries in [('read', reads), ('write', writes)]:
        seen = set()
        for e in entries:
            key = (e['quarter'], e['edge'], e['bank'])
            if key in seen:
                raise ValueError(('physical VM bank collision', kind, key))
            seen.add(key)
            assert e['bank'] == e['sector'] & 7
            delay = (read_request_delays[e['quarter']][e['bank']]
                     if kind == 'read' and read_request_delays is not None else 0)
            reservations.append(dict(e, kind=kind,
                edge_domain='GQ_client_request' if kind == 'read' else 'VM_bank_sample',
                calendar_index=(None if kind == 'read' and read_request_delays is None
                                else e['edge']+delay+1)))
    return dict(status='source_candidate_unqualified', define=DEFINE, rows=rows,
                descriptors=[dict(sender=s, F=F, stride=F, fire=starts[j], Bs=128|(1<<s),
                                  self_land=1, rings=2, period=period) for j,s in enumerate(senders)],
                vm_reads=reads, vm_writes=writes, ring_events=ring, reservations=reservations,
                last_commit=max(e['edge'] for e in writes), period=period,
                read_calendar_resolved=read_request_delays is not None,
                read_calendar_obligation=('bind 4x8 actual request-lane delays OR reserve all banks exclusively '
                    'to COLL read-group3/write-code2 over common full epoch, including existing run-out; '
                    'VM_RT alone does not resolve physical bank read edges'),
                sequence_completion_qualified=False,
                single_wave_proof_scope=('data transactions equal qualified F16 first wave; one-row programme completion not executed'
                                         if tuple(senders) == (0,) else None),
                source_quarters=list(senders), inactive_source_quarters=sorted(set(range(4))-set(senders)),
                required_cut='four real GQ/land/ring A+B/VM calendar paths; real producer writes before wave',
                qualifies_native_layer=False, qualifies_native_chain=False)


def install(bus, plan, *, gq_targets):
    """Use existing CpBus to emit actual F20/F28/F2c writes, no launch/calendar.

    Caller must supply exact selected strap target IDs and merge reservations
    into common calendar before launching all armed programmes together.
    """
    if len(gq_targets) != 4 or len(set(gq_targets)) != 4:
        raise ValueError('four exact distinct selected GQ target IDs required')
    for q, target in enumerate(gq_targets):
        bus.install(target, plan['rows'][q], 0)
        bus.desc(target, 0, len(plan['rows'][q]), 1)
    return bus


def stage_sources(bundle, outroot):
    """Controlled immutable selected-bundle overlay; never mutate frozen input."""
    source = Path(bundle)/SOURCE
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != ORIGINAL_SHA256:
        raise ValueError(('unqualified selected GQ source', actual))
    candidate = Path(__file__).resolve().parents[2]/SOURCE
    data = candidate.read_bytes()
    if DEFINE.encode() not in data or hashlib.sha256(data).hexdigest() == actual:
        raise ValueError('candidate source not materialized')
    dest = Path(outroot)/SOURCE
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dict(source=SOURCE, original_sha256=actual,
                candidate_sha256=hashlib.sha256(data).hexdigest(), defines=[DEFINE],
                status='unbound_new_source_no_closed_view_alias')
