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
    84: 'L14 Engram stage: R084 L14 A -> R085 L14 B (copy-B, Engram RA640 / II 576)',
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


def plans(cal, L, hops, mode):
    if cal.get('checker', {}).get('result') != 'PASS':
        raise ValueError('Calendar checker failed; hop plans cannot qualify it')
    P = cal['period']
    copyb = set(cal['copy_b_stages'])
    st = L['stages']
    out = {}
    for i in hops:
        a, b = st[i], st[i + 1]
        msgs = [(s0, what, ln) for j, s0, what, ln in L['links'] if j == i]
        res = {}
        for sl in cal['slots']:
            u, sh = sl['user'], sl['shift']
            ca = sl['copy'].get(a, 'A') if a in copyb else 'A'
            cb = sl['copy'].get(b, 'A') if b in copyb else 'A'
            r = f'link.{a}.{ca}-{b}.{cb}'
            for m, (s0, what, ln) in enumerate(msgs):
                for p in range(6 if mode == 'mtp' else 1):
                    T = (sh + s0 + p * ln) % P
                    res.setdefault(r, []).append(dict(user=u, T=T, m=m * 6 + p if mode == 'mtp' else m, label=what +
                                                      (f' pos {p}' if mode == 'mtp' else ''), length=ln))
        for r, ms in sorted(res.items()):
            ms.sort(key=lambda x: x['T'])
            # Preserve the admitted absolute timeline. A local TX delay would leave
            # receiver owner/engine arrivals and every downstream stage stale.
            sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
            from dv_mu_calendar_phys import interval_collisions
            bad = interval_collisions({r: [(x['T'], x['length'], x['user']) for x in ms]}, P)
            if bad:
                raise ValueError(json.dumps(dict(verdict='FAILED', mode=mode, resource=r,
                    reason='Calendar occupancy collision; no local serialization permitted',
                    first=bad[0], collisions=len(bad))))
            delays = []
            t, comp = 0.0, 0
            for k, x in enumerate(ms):
                if k:
                    g = x['T'] - ms[k - 1]['T']
                    assert g >= ms[k - 1]['length'], f'{r}: overlapping messages (checker would fault)'
                    if g > GAPC:
                        g, comp = GAPC, comp + 1
                    t += g
                x['t'] = int(round(t))
            out[(i, r)] = dict(schema='opentallas.tokfunc_s81.mu_hop_plan.v1', mode=mode, hop=f'{a}->{b}', sender_index=i,
                               why=SAMPLE.get(i, ''), resource=r, period=P, users=sorted({x['user'] for x in ms}),
                               gap_compress=dict(cap=GAPC, gaps_compressed=comp),
                               same_user_serial_delays=dict(count=len(delays), max=max([d['delay'] for d in delays] or [0]),
                                                            first=delays[:3]), msgs=ms)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cal-dir', default='results/token_pass/mucal241_s81_1021')
    ap.add_argument('--links', help='captured links json (else captured now from dv_mu_calendar_phys)')
    ap.add_argument('--links-out')
    ap.add_argument('--out')
    ap.add_argument('--hops', default=','.join(str(k) for k in SAMPLE))
    a = ap.parse_args()
    L = json.loads(Path(a.links).read_text()) if a.links else capture_links()
    if a.links_out:
        Path(a.links_out).write_text(json.dumps(L, indent=0) + '\n')
    if not a.out:
        return
    hops = [int(x) for x in a.hops.split(',')]
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    index = []
    for mode in ('ar', 'mtp'):
        cal = json.loads((ROOT / a.cal_dir / f'calendar_rel241_G4_{mode}.json').read_text()
                         if not Path(a.cal_dir).is_absolute() else (Path(a.cal_dir) / f'calendar_rel241_G4_{mode}.json').read_text())
        assert cal['map_sha256'] == L['map_sha256']
        try:
            mode_plans = plans(cal, L, hops, mode)
        except ValueError as error:
            (o / 'FAILED.json').write_text(json.dumps(dict(verdict='FAILED', mode=mode, reason=str(error),
                full_calendar_qualified=False), indent=2) + '\n')
            print(error, file=sys.stderr)
            return 2
        for (i, r), pl in mode_plans.items():
            name = f'{mode}_h{i:03d}_{r.split(".", 1)[1].replace(".", "").replace("-", "_")}'
            (o / f'{name}.json').write_text(json.dumps(pl, indent=0) + '\n')
            index.append(dict(name=name, mode=mode, hop=pl['hop'], resource=r, users=len(pl['users']),
                              messages=len(pl['msgs']), vehicle_cycles=pl['msgs'][-1]['t'] + 1000, why=pl['why'],
                              serial_delays=pl['same_user_serial_delays']['count'],
                              serial_delay_max=pl['same_user_serial_delays']['max']))
    (o / 'index.json').write_text(json.dumps(index, indent=1) + '\n')
    for x in index:
        print(x['name'], x['users'], x['messages'], x['vehicle_cycles'], x['serial_delays'], x['serial_delay_max'])


if __name__ == '__main__':
    sys.exit(main())
