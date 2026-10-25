#!/usr/bin/env python3
"""TOK-DS 10-25: the die-link framing words of the end-slice link lanes (lt_lk_*) as compiled, checked traffic.

Why: on the reclocked fc31 data cuts the strict lanes lt_lk_{WS,WN,ES,EN}<k> carry ~6,200 words each from reset on
(cut_0N / cut_7 FAIL 'unscheduled'), although the layer sends nothing off-die on them.  They are the gearbox beats of
the lane tile's reliable link layer (dsfd_coll_lane -> ot_s81ph_coll_lane_safe4 -> ot_s81ph_link_ep_safe4 +
ot_s81ph_link_gbx_safe3): the off-die boundary is elastic (owner 10-14: flow control at SerDes / d2d only), so these
words are not fixed-cycle programme words but a framing stream that runs from reset.  Its content is a pure function of
the link RTL parameters, so the compiler states it and the replay checks every beat of it:

  beat [0]       marker: FMT 1 fixed group format, one marker per MP = 4 gearbox (non-idle) beats
  beat [1]       idle: one beat every IDLE_P = 1024 cycles (no gearbox bits: the marker count skips it)
  beat [2]       reverse frame valid (0: no peer frame to acknowledge)
  beat [3 +: 53] the reverse frame r_tx = {rg_pay 21, crc32(rg_pay)} of ot_s81ph_link_ep_safe4: rg_pay = {nak_req,
                 exp_seq 10, freed 10} = 0 with no peer, crc = ot_link_crc32 (poly 04C11DB7, init FFFFFFFF, MSB first,
                 no reflection, no final XOR) of 21 zero bits = 16EC8FA0 (computed below, asserted)
  beat [56 +: ]  forward slot stream: empty (no frame is sent: no ring beat leaves the die in these layer windows;
                 the RD all-gather rows that do are 'offdie' events, beyond this stream's link layer)

Timing: the gearbox runs from the lane tile's reset release.  GBX0[lep] = the output-register edge of gearbox beat 0,
in edges after the die reset release (bench cycle 0), one per end-slice link endpoint (the four leps sit at different
depths of the die reset tree: N tier 81 / 83, S tier 58 / 59).  CALIBRATION constants, measured on the reclocked fc31
cuts (r4all L0: first idle beat at GBX0 + 1023 on every lane of the lep after subtracting the lane age; the marker
phase follows).  The lane's first visible beat lies 2..8 edges after GBX0 + age (its relay stations leave reset in
that window): the replay requires 0 before it and the exact stream from it on (LINKUP_MAX).
"""

LANE_PREFIX = 'lt_lk_'
MP = 4                 # ot_s81ph_link_gbx FMT 1: marker on group beat 0, 4 gearbox beats a group
IDLE_P = 1024          # ot_s81ph_coll_lane_safe4 IDLE_P (gbx idle beat period)
RVW = 21               # ot_s81ph_link_ep_safe4 RVW = 1 + SEQW 10 + $clog2(CREDITS 512 + 1)
LINKUP_MAX = 10        # first visible beat <= GBX0 + age + LINKUP_MAX (reset release of the lane's relay stations)
GBX0 = {'u_s_0S': 58, 'u_s_0N': 83, 'u_s_7S': 59, 'u_s_7N': 81}   # measured (see the module docstring)
POLY = 0x04C11DB7


def crc32_zero(w):
    """ot_link_crc32 of a w-bit all-zero frame = init 0xFFFFFFFF shifted w times through the LFSR"""
    c = 0xFFFFFFFF
    for _ in range(w):
        c = ((c << 1) & 0xFFFFFFFF) ^ (POLY if c >> 31 else 0)
    return c


REV_IDLE = crc32_zero(RVW)            # r_tx = {rg_pay 0, crc}: the low 32 bits are the crc
assert REV_IDLE == 0x16EC8FA0, hex(REV_IDLE)
BASE = REV_IDLE << 3                  # beat with marker 0, idle 0, reverse valid 0, empty slots


def beat(b):
    """value of gearbox beat b (b >= 0) of an idle link"""
    if (b + 1) % IDLE_P == 0:
        return BASE | 2
    n = b - (b + 1) // IDLE_P
    return BASE | (1 if n % MP == 0 else 0)


def changes(g0, age, start, end):
    """[(landed edge, value)] value changes of the landed lane from `start` (the first visible edge) to `end`"""
    out, prev = [], 0
    for c in range(start, end):
        v = beat(c - age - g0)
        if v != prev:
            out.append((c, v))
            prev = v
    return out


def check(trace, g0, age, end):
    """trace = [(edge, value)] value changes of the landed lane -> (link_up edge, missed, extra)"""
    nz = [c for c, v in trace if v]
    if not nz:
        return None, [('no link-up', g0 + age)], []
    up = nz[0]
    if not (g0 + age <= up <= g0 + age + LINKUP_MAX):
        return up, [('link-up outside window', g0 + age, g0 + age + LINKUP_MAX)], []
    t = [(c, v) for c, v in trace if up <= c < end]
    m = changes(g0, age, up, end)
    ts, ms = set(t), set(m)
    return up, sorted(c for c, _ in ms - ts), sorted(c for c, _ in ts - ms)


def emit(die, prog):
    """one LKFRAME event per die link lane of an end slice: the replay expands it on the lane (dir out)"""
    n = 0
    for lk, L in sorted(die.links.items()):
        if not lk.startswith(LANE_PREFIX):
            continue
        src = [tuple(x) for x in L['src']]
        insts = {i for i, _ in src}
        if len(insts) != 1:
            raise ValueError(f'link_frames: lane {lk} has {len(insts)} source instances')
        inst = insts.pop()
        if inst not in GBX0:
            raise ValueError(f'link_frames: no gearbox calibration for the lep of {inst} ({lk})')
        prog.events.append(dict(cycle=0, inst=inst, port=src[0][1], dir='out', kind='LKFRAME', tag=f'link.{lk}', lane=lk,
                                framing=dict(g0=GBX0[inst], mp=MP, idle_p=IDLE_P, base=f'{BASE:x}', rvw=RVW,
                                             linkup_max=LINKUP_MAX, clock='edges after die reset release'),
                                source='ot_s81ph_link_gbx_safe3 FMT 1 + ot_s81ph_link_ep_safe4 idle reverse frame'))
        n += 1
    return n
