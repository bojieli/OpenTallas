#!/usr/bin/env python3
"""TOK-FUNC-S81/MURATE (10-21): per-user stage-hop message plans of SAMPLED stage hops of the 241-stage MU calendar,
for the xdie XL5 stage-hop circuit bench (tools/xdie_s81_2/gen_golden.py --mu-hop-plan).

The calendar records (results/token_pass/mucal241_s81_1021/calendar_rel241_G4_{ar,mtp}.json) hold every user's shift and
copy colouring but not the link message list; the messages come from the SAME tool's single-user forward-x timeline
(tools/s81_dv/dv_mu_calendar_phys.py build(), --release241 --attn G4 --compose romopt --alap, as run_cal241.sh):
model['links'] = (sender stage index, send cycle s0, label, length cycles) -- 440 messages on 240 circuits.
`--links-out` writes that list once (committed), so the plans re-derive without the composer inputs (`--links`).

Per sampled hop i -> i+1 and per calendar link RESOURCE link.<Ri>.<ca>-<Ri+1>.<cb> (the checker's resource: users whose
sender / receiver copies match share one physical circuit), a plan lists every message of every user of that resource:
  absolute cycle T = shift_u + s0 (+ p * length for MTP verify position p = 0..5, the checker's x6 window), mod period,
  sorted; the vehicle cycle keeps every gap <= GAPC exactly and compresses a longer (idle, fully drained) gap to GAPC
  (GAPC 2000 > message issue 368 + crossing ~378 + drain 430).  Users / messages / order / intra-user spacing are the
  calendar's; only idle time between them is shortened (stated in the plan and in mu.json).
    mu_hop_plan.py --cal-dir results/token_pass/mucal241_s81_1021 --links L.json --out DIR [--hops 0,6,12,...]

STEWARD-TOKb-RATE1 (10-21): a calendar with the causal six-position `pipeline_graph` (claude/steward-tok-cal-1021
8020b90f3, mtp_law pipeline) is read directly: every user's (slots: shift + copy colour) per-position messages of the
sampled hop, already serialised by the composer on the ONE LINK5 circuit, become the same-user hop schedule.  Every msg
carries its graph receive bounds (receive_first = send + HOP - land_lead, receive_complete = send + HOP; for AR the same
HOP/land_lead of release241), relative to its send (rx_first_age / rx_complete_age), so a replay sets each beat's
deadline from its OWN graph message.  --inject-busy U:K moves user U's K-th message of the resource onto the busy
window of the message before it: --inject-mode check -> the collision check must FAULT (FAILED.json, exit 2);
--inject-mode rtl -> the plan is still emitted with the message issued after the busy window (what the one circuit
must do) but its deadline kept from the claimed (busy) slot, so a real-RTL replay must miss it (late > 0 -> FAIL).
--first-msgs N keeps the first N messages of each resource (short negative replays).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAP = 'results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json'
# sampled hops (sender stage index i: hop R<i> -> R<i+1>) and why
SAMPLE = {
    0: 'first stage: R000 L0 DENSE2 A -> R001 B (x + a_proj partial)',
    6: 'mid DENSE2 stage: R006 L1 A -> R007 L1 B (+ Engram L1 on R007)',
    12: 'L2-class idx stage: R012 L2 A -> R013 L2 B (copy-B duplicated, AR binding resource)',
    13: 'L2 B out: R013 (copy A/B) -> R014 experts (x L2 + partial L2)',
    84: 'L14 Engram stage: R084 L14 A -> R085 L14 B (copy-B, Engram RA640 / II 704)',
    85: 'L14 B out: R085 (copy A/B) -> R086',
    120: 'L20 stage: R120 L20 A -> R121 L20 B (copy-B, 52-user binding window)',
    121: 'L20 B out: R121 (copy A/B) -> R122',
    239: 'last stage hop: R239 -> R240 (x L39 + partial L39; R240 then hands to the head die)',
}
GAPC = 2000


def capture_links():
    sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
    import dv_mu_calendar_phys as C
    C.REL.update(C.REL241)
    C.REL['attn'] = 'G4'
    cap = {}
    orig = C.timeline

    def tl(stages, *a, **k):
        r = orig(stages, *a, **k)
        cap['links'] = [list(x) for x in r[2]]
        cap['stages'] = [s['stage'] for s in stages]
        return r
    C.timeline = tl
    recs = C.build(ROOT / MAP, 'romopt', True, False, 1)
    return dict(schema='opentallas.tokfunc_s81.mu_links.v1', tool='tools/s81_dv/dv_mu_calendar_phys.py build() --release241 '
                '--attn G4 --compose romopt --alap (timeline links captured)', map=MAP,
                map_sha256=hashlib.sha256((ROOT / MAP).read_bytes()).hexdigest(), H_MSG=C.H_MSG, HOP=C.HOP,
                users_ar=recs['ar']['users'], period_ar=recs['ar']['period'], users_mtp=recs['mtp']['users'],
                period_mtp=recs['mtp']['period'], stages=cap['stages'], links=cap['links'])


def plans(cal, L, hops, mode, preserve_idle=False, boundary_only=False, inject=None, inject_mode='check',
          first_msgs=0):
    if cal.get('checker', {}).get('result') != 'PASS':
        raise ValueError('Calendar checker failed; hop plans cannot qualify it')
    P = cal['period']
    copyb = set(cal['copy_b_stages'])
    st = L['stages']
    out = {}
    rel = cal.get('composition', {}).get('release241', {})
    HOP = rel.get('hop', L['HOP'])
    LEAD = rel.get('land_lead', 0)
    pipe = cal.get('pipeline_graph') if mode == 'mtp' else None
    for i in hops:
        a, b = st[i], st[i + 1]
        msgs = [(s0, what, ln) for j, s0, what, ln in L['links'] if j == i]
        res = {}
        for sl in cal['slots']:
            u, sh = sl['user'], sl['shift']
            ca = sl['copy'].get(a, 'A') if a in copyb else 'A'
            cb = sl['copy'].get(b, 'A') if b in copyb else 'A'
            r = f'link.{a}.{ca}-{b}.{cb}'
            graph = cal.get('position_graph', {}).get('positions', [])
            if pipe:
                # causal pipeline graph: the sender's messages of all six positions, already serialised on the circuit
                mine = sorted((m for m in pipe['links'] if m['sender_index'] == i), key=lambda m: m['send_start'])
                emissions = [(m['position'], k, m['send_start'], m['label'], m['send_end'] - m['send_start'],
                              HOP - LEAD, HOP) for k, m in enumerate(mine)]
            elif mode == 'mtp' and graph:
                emissions = [(p['position'], n, message['send_start'], message['label'],
                              message['send_end'] - message['send_start'])
                             for p in graph for n, message in enumerate(p['links'])
                             if message['sender_index'] == i]
            else:
                emissions = [(p, m, s0 + (p * ln if mode == 'mtp' else 0), what, ln)
                             for m, (s0, what, ln) in enumerate(msgs)
                             for p in range(6 if mode == 'mtp' else 1)]
            if boundary_only:
                if mode != 'mtp' or not graph:
                    raise ValueError('Boundary replay requires an explicit corrected MTP position graph')
                emissions = [max((x for x in emissions if x[0] == 0), key=lambda x: x[2]),
                             min((x for x in emissions if x[0] == 1), key=lambda x: x[2])]
            if not pipe:
                rx = {}
                if mode == 'mtp' and graph:
                    rx = {(p['position'], n): (mm['receive_first'] - mm['send_start'],
                                               mm['receive_complete'] - mm['send_start'])
                          for p in graph for n, mm in enumerate(p['links']) if mm['sender_index'] == i}
                emissions = [e + rx.get((e[0], e[1]), (HOP - LEAD, HOP)) for e in emissions]
            for position, message, send, label, length, rx_first, rx_complete in emissions:
                T = (sh + send) % P
                res.setdefault(r, []).append(dict(user=u, T=T, position=position,
                    m=message if pipe else (message * 6 + position if mode == 'mtp' else message),
                    label=label + (f' pos {position}' if mode == 'mtp' and not pipe else ''), length=length,
                    rx_first_age=rx_first, rx_complete_age=rx_complete,
                    copy_a=r.split('-')[0].rsplit('.', 1)[1], copy_b=r.rsplit('.', 1)[1]))
        for r, ms in sorted(res.items()):
            ms.sort(key=lambda x: x['T'])
            if first_msgs:
                del ms[first_msgs:]
            negative = None
            if inject is not None:
                u_inj, k_inj = inject
                own = [n for n, x in enumerate(ms) if x['user'] == u_inj]
                if k_inj < len(own) and own[k_inj] > 0:
                    n = own[k_inj]
                    busy = ms[n - 1]
                    claimed = busy['T'] + busy['length'] // 2          # onto the busy window of the message before it
                    negative = dict(user=u_inj, k=k_inj, index=n, graph_T=ms[n]['T'], claimed_T=claimed,
                                    busy=dict(user=busy['user'], label=busy['label'], T=busy['T'],
                                              end=busy['T'] + busy['length']), mode=inject_mode)
                    ms[n]['T'] = claimed
                    ms[n]['injected'] = True
                    if inject_mode == 'rtl':
                        # the one circuit cannot carry both: it serialises the moved message after the busy window,
                        # but the claimed slot's receive deadline is kept -> the real RTL must land late
                        ms[n]['claimed_T'] = claimed
                        issue = busy['T'] + busy['length'] + 4
                        ms[n]['rx_first_age'] -= issue - claimed
                        ms[n]['rx_complete_age'] -= issue - claimed
                        ms[n]['T'] = issue
                        negative['rtl_issue_T'] = issue
                        negative['deadline_T'] = claimed + HOP
                        ms.sort(key=lambda x: x['T'])
            # Preserve the admitted absolute timeline. A local TX delay would leave
            # receiver owner/engine arrivals and every downstream stage stale.
            sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
            from dv_mu_calendar_phys import interval_collisions
            bad = interval_collisions({r: [(x.get('claimed_T', x['T']), x['length'], x['user']) for x in ms]}, P)
            if negative is not None:
                negative['collisions'] = len(bad)
                negative['first'] = bad[0] if bad else None
                negative['result'] = 'FAULT' if bad else 'NO_FAULT'
            if bad and not (negative is not None and inject_mode == 'rtl'):
                raise ValueError(json.dumps(dict(verdict='FAILED', mode=mode, resource=r,
                    reason='Calendar occupancy collision; no local serialization permitted',
                    first=bad[0], collisions=len(bad))))
            delays = []
            # gen_golden adds WARM=12000 (phase zero). Preserve the graph's
            # q4 phase as well as every idle gap; rebasing first T to zero can
            # silently change the actual sender/landing phase by two edges.
            rebase = (ms[0]['T'] // 4) * 4 if preserve_idle else ms[0]['T']
            t, comp = float(ms[0]['T'] - rebase), 0
            for k, x in enumerate(ms):
                if k:
                    g = x['T'] - ms[k - 1]['T']
                    assert g >= ms[k - 1]['length'], f'{r}: overlapping messages (checker would fault)'
                    if x['user'] == ms[k - 1]['user']:
                        delays.append(dict(user=x['user'], gap=g, label=x['label']))
                    if not preserve_idle and g > GAPC:
                        g, comp = GAPC, comp + 1
                    t += g
                x['t'] = int(round(t))
            out[(i, r)] = dict(schema='opentallas.tokfunc_s81.mu_hop_plan.v1', mode=mode, hop=f'{a}->{b}', sender_index=i,
                               why=SAMPLE.get(i, ''), resource=r, period=P, users=sorted({x['user'] for x in ms}),
                               gap_compress=dict(cap=None if preserve_idle else GAPC, gaps_compressed=comp),
                               replay_scope=('isolated exact position-boundary link mechanism; not whole-stage execution'
                                             if boundary_only else 'sampled link resource messages'),
                               compiled_position_graph=bool(cal.get('position_graph')),
                               modeled_message_receive_age=max(
                                   (message['receive_complete'] - message['send_start']
                                    for pos in cal.get('position_graph', {}).get('positions', [])
                                    for message in pos['links'] if message['sender_index'] == i), default=L['HOP']),
                               absolute_rebase=rebase,
                               phase_quantum=4, phase_preserved=preserve_idle,
                               generator_warm_requirement='multiple of four edges',
                               same_user_serial_delays=dict(count=0, max=0, first=[]),
                               same_user_adjacent=dict(count=len(delays), min_gap=min([d['gap'] for d in delays] or [0]),
                                                       first=delays[:3]),
                               graph=('pipeline_graph' if pipe else 'position_graph' if graph else 'links'),
                               hop_cycles=HOP, land_lead=LEAD, users_shift={sl['user']: sl['shift'] for sl in cal['slots']
                                                                           if sl['user'] in {x['user'] for x in ms}},
                               overlaps=len(bad), negative=negative, msgs=ms)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cal-dir', default='results/token_pass/mucal241_s81_1021')
    ap.add_argument('--links', help='captured links json (else captured now from dv_mu_calendar_phys)')
    ap.add_argument('--links-out')
    ap.add_argument('--out')
    ap.add_argument('--hops', default=','.join(str(k) for k in SAMPLE))
    ap.add_argument('--modes', default='ar,mtp', help='Comma-separated ar/mtp modes')
    ap.add_argument('--preserve-idle', action='store_true', help='Keep exact gaps in compiled calendar replay')
    ap.add_argument('--boundary-only', action='store_true', help='Minimum pos0 last-TX to pos1 first-TX; requires preserved idle')
    ap.add_argument('--inject-busy', help='U:K negative: move user U\'s K-th message of each resource onto a busy window')
    ap.add_argument('--inject-mode', default='check', choices=('check', 'rtl'))
    ap.add_argument('--first-msgs', type=int, default=0, help='keep only the first N messages of each resource')
    a = ap.parse_args()
    if a.boundary_only and not a.preserve_idle:
        ap.error('--boundary-only requires --preserve-idle')
    L = json.loads(Path(a.links).read_text()) if a.links else capture_links()
    if a.links_out:
        Path(a.links_out).write_text(json.dumps(L, indent=0) + '\n')
    if not a.out:
        return
    hops = [int(x) for x in a.hops.split(',')]
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    index = []
    for mode in a.modes.split(','):
        if mode not in ('ar', 'mtp'):
            ap.error('Invalid --modes')
        cal = json.loads((ROOT / a.cal_dir / f'calendar_rel241_G4_{mode}.json').read_text()
                         if not Path(a.cal_dir).is_absolute() else (Path(a.cal_dir) / f'calendar_rel241_G4_{mode}.json').read_text())
        assert cal['map_sha256'] == L['map_sha256']
        try:
            inj = tuple(int(x) for x in a.inject_busy.split(':')) if a.inject_busy else None
            mode_plans = plans(cal, L, hops, mode, a.preserve_idle, a.boundary_only, inj, a.inject_mode, a.first_msgs)
        except ValueError as error:
            (o / 'FAILED.json').write_text(json.dumps(dict(verdict='FAILED', mode=mode, reason=str(error),
                full_calendar_qualified=False), indent=2) + '\n')
            print(error, file=sys.stderr)
            return 2
        for (i, r), pl in mode_plans.items():
            name = f'{mode}_h{i:03d}_{r.split(".", 1)[1].replace(".", "").replace("-", "_")}'
            (o / f'{name}.json').write_text(json.dumps(pl, indent=0) + '\n')
            index.append(dict(name=name, mode=mode, hop=pl['hop'], resource=r, users=len(pl['users']), negative=pl['negative'],
                              overlaps=pl['overlaps'], same_user_adjacent=pl['same_user_adjacent']['count'],
                              messages=len(pl['msgs']), vehicle_cycles=pl['msgs'][-1]['t'] + 1000, why=pl['why'],
                              serial_delays=pl['same_user_serial_delays']['count'],
                              serial_delay_max=pl['same_user_serial_delays']['max']))
    (o / 'index.json').write_text(json.dumps(index, indent=1) + '\n')
    for x in index:
        print(x['name'], x['users'], x['messages'], x['vehicle_cycles'], x['serial_delays'], x['serial_delay_max'])


if __name__ == '__main__':
    sys.exit(main())
