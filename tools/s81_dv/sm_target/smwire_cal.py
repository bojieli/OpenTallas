#!/usr/bin/env python3
"""S81-SMWIRE (10-19): compiler side of the SO target wiring (static calendar, no credits).

  sot_frame()     the SOT q frame (svc type 14, len 2) the compiler emits right after the job's WIN_LOAD: the target's
                  authority (owner = WIN_LOAD tag / user + host allocation epoch) and its booked edges.  The job's
                  descriptor q-frame count (ot_s81_svc_job arg[14:7]) counts it (+1); the header carries the job tag.
  wo_a_group()    the wo_a row placement the wiring needs: group 0 (heads 0..7, E svc half) on the S-tier slices
                  (even sid), group 1 (heads 8..15, W half) on the N-tier slices (odd sid).  Each injector reaches
                  exactly its group's 8 slices: E entry -> s_4S band, route 1 (S tier line both ways + own XS);
                  W entry -> s_3S band, route 2 (V rung through the G-unit -> s_3N, which delivers and fans out on N).
                  tools/s81_dv/layer_prog/xs_bf.py must deal the rank rows to slices in this group order (owed patch,
                  see lanes/S81-SMWIRE.md).
  schedule()      per half: disjoint entry gather windows (a head's 32 read edges, 24 words), read edges back-computed
                  through the return tree depth (5 edges a hop), read > last SO write + 1, retire after the 8th beat.
  price()         every added edge from the last SO write to the last x-streamer arrival per group, from the measured
                  bench constants (tb_smwire_e2e) and the die link ages (plan p4l_lkcol_mu_pf + landing p4l3: ceil(n/2)
                  half-cycle stations + K + 1).

  python3 tools/s81_dv/sm_target/smwire_cal.py [--json OUT]       (self-test + the priced record)
"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# svc_rs role ROM (dsdv_svc_rs_roles.svh): sid -> (tile = head, depth, parent face code); half W = sid 0..7, E = 8..15
ROLE = {0: (12, 3), 1: (13, 2), 2: (15, 2), 3: (14, 1), 4: (8, 1), 5: (9, 0), 6: (11, 2), 7: (10, 1),
        8: (2, 2), 9: (3, 1), 10: (0, 1), 11: (4, 0), 12: (1, 2), 13: (5, 1), 14: (6, 3), 15: (7, 2)}
HALF = {'W': dict(entry=5, sids=range(0, 8), band='s_3S', lane='pv_W', route=2, tier='N', group=1),
        'E': dict(entry=11, sids=range(8, 16), band='s_4S', lane='pv_E', route=1, tier='S', group=0)}
HOP = 5                      # return-tree hop: o0, o1 (source) + p0, p1 (parent pins) + merge register
# measured on tb_smwire_e2e (filled from the bench logs; MEAS['line'] = target beat g_v -> gather port at the injector
# for the head at the entry, MEAS['v'] = the same at the V partner; the bench's lane = 2 relay regs + landing K 2)
MEAS = dict(line=None, v=None, bench_lane_stations=2, bench_K=2)
TARGET_READ_TO_BEAT0 = 6     # dsdv_sm_so_target: read edge R -> first g_v (R + 6), then one beat every 4 edges
WORDS_SPAN = 32              # a head's 8 beats: g_v at R + 6 + 4 k, words to R + 6 + 28 + 3 = R + 37


def sot_frame(owner, se_jid, so_jid, obase, route, gw_first, gw_last, heads):
    """heads: {head: dict(first, last, read, retire)} -> (header, payload0, payload1) as 512-bit ints"""
    tag = owner & 0xFF
    h = (14 << 508) | (1 << 503) | (tag << 495) | (2 << 480)
    h |= (owner & 0xFFFFF) | (se_jid & 0xFF) << 20 | (so_jid & 0xFF) << 28 | (obase & 0x3FFF) << 36
    h |= (route & 3) << 50 | (gw_first & 0xFFFF) << 52 | (gw_last & 0xFFFF) << 68
    p0 = p1 = 0
    for t, e in heads.items():
        assert e['read'] > e['last'] + 1 and e['retire'] > e['read'] + 34, (t, e)
        p0 |= ((e['last'] & 0xFFFF) << 16 | (e['first'] & 0xFFFF)) << (32 * t)
        p1 |= ((e['retire'] & 0xFFFF) << 16 | (e['read'] & 0xFFFF)) << (32 * t)
    return h, p0, p1


def sot_decode(h, p0, p1, tile):
    """the dsdv_svc_sot field map (reference for the RTL)"""
    f = lambda x, lo, w: (x >> lo) & ((1 << w) - 1)
    return dict(type=f(h, 508, 4), mine=f(h, 503, 1), len=f(h, 480, 12), tag=f(h, 495, 8), owner=f(h, 0, 20),
                se=f(h, 20, 8), so=f(h, 28, 8), obase=f(h, 36, 14), route=f(h, 50, 2), gw_first=f(h, 52, 16),
                gw_last=f(h, 68, 16), first=f(p0, 32 * tile, 16), last=f(p0, 32 * tile + 16, 16),
                read=f(p1, 32 * tile, 16), retire=f(p1, 32 * tile + 16, 16))


def wo_a_group(sid):
    """wo_a group whose rows slice sid holds (sid = 2 col + tier; tier 1 = N)"""
    return 1 if sid & 1 else 0


def schedule(last_write, half, e0=None):
    """last_write: {head: edge of its last SO write (slice-local, after config install)}.  Returns per head read /
    retire and the entry window; windows in SO write order (the compiler's operand-frame order), back to back"""
    H = HALF[half]
    hs = sorted(((ROLE[s][0], ROLE[s][1], s) for s in H['sids']), key=lambda x: (last_write[x[0]], -x[1], x[0]))
    # entry arrival of a head's words = R + 7 + 5 depth + 1 (merge) .. + WORDS_SPAN; window k = [E0 + 32 k, E0 + 32 k + 31]
    lead = TARGET_READ_TO_BEAT0 + 1 + 1
    need = max(last_write[t] + 2 + lead + HOP * d - WORDS_SPAN * k for k, (t, d, s) in enumerate(hs))
    e0 = need if e0 is None else max(e0, need)
    out = {}
    for k, (t, d, s) in enumerate(hs):
        r = e0 + WORDS_SPAN * k - lead - HOP * d
        out[t] = dict(sid=s, depth=d, read=r, retire=r + 40, first=0, last=last_write[t], win=(e0 + WORDS_SPAN * k,
                      e0 + WORDS_SPAN * k + WORDS_SPAN - 1))
    return dict(heads=out, gw_first=e0, gw_last=e0 + WORDS_SPAN * len(hs) - 1, order=[t for t, _, _ in hs])


def link_age(lp, name):
    x = lp.get(name)
    return None if x is None else math.ceil(x['stages'] / 2) + x['K'] + 1


def price(meas=None):
    meas = meas or MEAS
    lp = {x['link']: x for x in json.loads((ROOT / 'results/arch/s81_dv_1016/landing/p4l3/land_plan.json').read_text())['links']}
    rec = {}
    for hf, H in HALF.items():
        lane = link_age(lp, H['lane'])
        bench_lane = math.ceil(meas['bench_lane_stations'] / 2) + meas['bench_K'] + 1
        base = meas['line'] if H['route'] == 1 else meas['v']
        r = dict(route=H['route'], injector=H['band'], lane_age=lane, tier=H['tier'], group=H['group'])
        if base is not None:
            r['injector_or_partner'] = base - bench_lane + lane
        col = 4 if hf == 'E' else 3
        if H['route'] == 1:
            # line both ways from s_4S: farthest S slice = s_0S (4 stops W) / s_7S (3 E); per stop link age + rstop 2
            far = 0
            for (c0, step, n) in ((col, -1, col), (col, 1, 7 - col)):
                t, c = 0, c0
                for _ in range(n):
                    a, b = (c + step, c) if step < 0 else (c, c + step)
                    nm = (f'xrW_{a}S_l0' if step < 0 else f'xrE_{a}S_l0')
                    t += (link_age(lp, nm) or 0) + 2
                    c += step
                far = max(far, t)
            r['line_far_extra'] = far
        else:
            # V rung col 3: s_3S -> tvN_s_3S -> G-unit (4 edges below + 6 above the stop, dsdv_gunit header) -> tvN_gunit
            # -> s_3N; then s_3N fans out on N: farthest s_0N (3 stops W) / s_7N (4 E)
            rung = (link_age(lp, 'tvN_s_3S') or 0) + 10 + (link_age(lp, 'tvN_gunit') or 0)
            far = 0
            for (step, n) in ((-1, 3), (1, 4)):
                t, c = 0, 3
                for _ in range(n):
                    a = c + step if step < 0 else c
                    nm = f'xrW_{a}N_l0' if step < 0 else f'xrE_{a}N_l0'
                    t += (link_age(lp, nm) or 0) + 2
                    c += step
                far = max(far, t)
            r['v_rung_age'] = rung
            r['line_far_extra'] = far
        rec[hf] = r
    return rec


def selftest():
    heads = {t: dict(first=0, last=600 + t, read=700 + 40 * t, retire=750 + 40 * t) for t in range(16)}
    h, p0, p1 = sot_frame(0x54123, 7, 8, 0x300, 2, 1300, 1420, heads)
    for t in (0, 5, 10, 15):
        d = sot_decode(h, p0, p1, t)
        assert d['type'] == 14 and d['mine'] == 1 and d['len'] == 2 and d['tag'] == 0x23 and d['owner'] == 0x54123
        assert (d['first'], d['last'], d['read'], d['retire']) == (0, 600 + t, 700 + 40 * t, 750 + 40 * t)
        assert d['route'] == 2 and d['gw_first'] == 1300 and d['gw_last'] == 1420 and d['obase'] == 0x300
    assert [wo_a_group(s) for s in range(16)] == [0, 1] * 8
    for hf in HALF:
        lw = {ROLE[s][0]: 560 + 33 * i for i, s in enumerate(HALF[hf]['sids'])}
        sc = schedule(lw, hf)
        ws = sorted(v['win'] for v in sc['heads'].values())
        assert all(a[1] < b[0] for a, b in zip(ws, ws[1:])), ws
        for t, v in sc['heads'].items():
            assert v['read'] > v['last'] + 1 and v['retire'] > v['read'] + 34
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json'); ap.add_argument('--line', type=int); ap.add_argument('--v', type=int)
    a = ap.parse_args(argv)
    selftest()
    meas = dict(MEAS, line=a.line, v=a.v)
    lw = {}
    for hf in HALF:   # the SO operand frames: head h at S + 6 + 33 h on the q pins, its o rows 54 edges after (SMS)
        for i, s in enumerate(HALF[hf]['sids']):
            lw[ROLE[s][0]] = 6 + 33 * i + 32 + 54
    sch = {hf: schedule(lw, hf) for hf in HALF}
    rec = dict(schema='opentallas.s81_smwire_cal.v1', price=price(meas), schedule=sch, meas=meas,
               wo_a_group={s: wo_a_group(s) for s in range(16)})
    for hf, H in HALF.items():
        sc = sch[hf]
        last = sc['gw_last'] - max(v['last'] for v in sc['heads'].values())
        rec['price'][hf]['tail_last_write_to_entry_window_end'] = last
    print(json.dumps(rec['price'], indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(rec, indent=1) + '\n')
    print('SMWIRE_CAL selftest PASS')


if __name__ == '__main__':
    main()
