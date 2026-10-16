"""Compiler ABI for S81 engine12: dense v1 and stride4 sparse SU compact v2.
All cycles are sampled engine pin edges; every command retires at pin+7.
Only declared commit observations establish operand completion; no runtime issue gating.
"""
DLAT = 7   # r2 seq tile: +1 pin stage on commit/read observations (native seq_tile TT -69.45)


def local_observation_cost():
    """Per-instance source and measured pre-repair mapping costs; no token estimate."""
    return {
        'command_done_old_stream_edges': 6,
        'command_done_stream_edges': DLAT,
        'command_ii_stream_edges': 1,
        'extra_command_retirement_ps': 1000.0 / 1.2,
        'commit_groups': 8, 'commit_ports_per_group': 16,
        'read_groups': 8, 'read_ports_per_group': 4,
        'slots': 8,
        'source_local_state_copy_bits': 16 * 8 * (1 + 1 + 14 + 15),
        'source_observation_stage_bits': 128 + 1152 + 512 + 32 + 448,
        'measured_unprotected_mapped_ff_bits': 8920,
        'measured_unprotected_unique_group_state_bits': 232,
        'required_distinct_mapped_group_state_bits': 16 * 232,
        'projected_mapped_ff_bits_with_local_enables': 8920 + 15 * 232,
        'external_clock_and_port_changes': 0,
        'whole_token_cost': None,
        'scope': 'Per-instance structural candidate; actual mapping, native timing and issuer calendar remain gates. No accepted-cost ledger row.',
    }
NSLOT = 8
ROWS = 16384
CHECK_FIELD = 0x3FF


def arm_arg(slot, client, base_row, nrows):
    if not 0 <= slot < 4 or client not in ('su', 'hc'):
        raise ValueError('dense slot0..3 and client su/hc required')
    if base_row % 16 or not 1 <= nrows <= 1024 or base_row < 0 or base_row + nrows > ROWS:
        raise ValueError('ARM range must be 16-row aligned, 1..1024 rows, inside16384')
    return slot << 21 | (client == 'hc') << 20 | base_row // 16 << 10 | nrows - 1


def check_arg(slot, client):
    if not 0 <= slot < 4 or client not in ('su', 'hc'):
        raise ValueError('dense slot0..3 and client su/hc required')
    return slot << 21 | (client == 'hc') << 20 | 0xfffff


def sparse_arm_arg(slot, base_row, nrows):
    if not 0 <= slot < 8 or base_row < 0 or base_row % 16 > 3 or not 1 <= nrows <= 128 or base_row + 4*(nrows-1) >= ROWS:
        raise ValueError('sparse SU slot0..7, base%16 in0..3, 1..128 stride4 rows inside16384 required')
    return (5 if slot < 4 else 7) << 21 | (slot % 4) << 19 | (base_row // 16) << 9 | (base_row % 4) << 7 | nrows - 1


def sparse_check_arg(slot):
    if not 0 <= slot < 8:
        raise ValueError('sparse slot0..7 required')
    return (5 if slot < 4 else 7) << 21 | (slot % 4) << 19 | 0x7ffff


def validate(commands, commits=(), reads=()):
    """Validate dense arm/check or sparse_arm/sparse_check command dictionaries.
    Commits are (cycle,row) full-row observations or (cycle,row,nwords) masked
    word counts; reads are (cycle,row). Neither holes nor other colors count.
    This aggregate-count checker mirrors RTL; it cannot distinguish a missing
    word replaced by an equal-count duplicate. Native producer identity gates
    must separately prove unique word coverage.
    """
    errors, done, live, windows, occupied = [], {}, {}, [], set()
    for i,c in sorted(enumerate(commands), key=lambda pair: pair[1]['cycle']):
        t=c['cycle']; done[i]=t+DLAT
        if t in occupied: errors.append(f'two engine-12 commands at cycle {t}')
        occupied.add(t)
        kind=c['kind']
        if kind=='native': continue
        s=c['slot']; sparse=kind.startswith('sparse_')
        if kind in ('arm','sparse_arm'):
            lo=c['base_row']; n=c['nrows']; stride=4 if sparse else 1
            (sparse_arm_arg(s,lo,n) if sparse else arm_arg(s,c['client'],lo,n))
            owned=set(range(lo,lo+stride*n,stride)); cl='su' if sparse else c['client']
            if s in live: errors.append(f'[4] ARM slot {s} at {t} before its CHECK')
            for other,(_,rows,_,_,_) in live.items():
                if other!=s and rows & owned: errors.append(f'[5] ARM slot {s} at {t} overlaps live slot {other}')
            live[s]=(t,owned,cl,sparse,n*16)
        elif kind in ('check','sparse_check'):
            if s not in live:
                errors.append(f'[2] CHECK slot {s} at {t} not armed'); continue
            ta,rows,cl,sp,need=live.pop(s)
            if cl!=('su' if sparse else c['client']) or sp!=sparse: errors.append(f'[3] CHECK slot {s} at {t} client/ABI mismatch')
            windows.append((ta,t,rows,need))
        else: errors.append(f'unknown kind {kind}')
    for s,(ta,*_) in live.items(): errors.append(f'slot {s} armed at {ta} never CHECKed')
    for ta,tc,rows,need in windows:
        count=0
        for event in commits:
            cy,row=event[:2]; words=event[2] if len(event)>2 else 16
            if row in rows and ta<cy<=tc: count+=words
            elif row in rows and cy==ta: errors.append(f'commit of row {row} at its ARM cycle {ta} is not counted (ARM pin + 1)')
        if count!=need: errors.append(f'[0] expected {need} words, observed {count} by CHECK {tc}')
        if count>need: errors.append('[1] count exceeded nelems')
        for cy,row in reads:
            if row in rows and ta<cy<=tc: errors.append(f'[7] read of row {row} at {cy} before its CHECK {tc}')
    return done,errors
