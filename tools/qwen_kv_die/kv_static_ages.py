#!/usr/bin/env python3
"""KVJ-E item 8 (Q-KVJOIN 10-17): price the static KV join's unset latency parameters from the die plan.

    kv_static_ages.py [--source results/arch/qwen_kv_static_programme_1017/kvs13l4_plan_ages_source.json]
                      [--out results/arch/qwen_kv_static_programme_1017/die_ages.json] [--template-out DIR]

Input: the relay-stage table of the chosen die plan (kv_die.py plan of kvs13l4-pvclean, extracted by bus id; one
stage = one registered relay = one core edge, pin registers excluded).  Output: every parameter the static-join
template (kv_static.template) leaves None, plus the link/control ages the programme compiler (kv_static_programme.py)
needs.  Each value names its class:

  PLAN_RELAY   counted relay stages of a bus that exists in the kvs13l4 plan;
  PLAN_ANALOG  the static element replaces a legacy element in place (k_issuer folded into ECTL-A <-> static landing
               group = the legacy ectl_<st>_<e>.rq / land_<st>.rs<e> buses krq / krs);
  COLOCATED    the folding plan (kv_static_join_plan.md (b)) puts producer and consumer in one tile or abutting tiles;
  DIE_CONTRACT a die clock/reset contract shared with an element already in the template;
  DERIVED      arithmetic on the above.

The static landing groups (slg_*) are not placed by any die plan yet (kv_die.py refuses OT_KV_STATIC physical
graphs), so PLAN_ANALOG / COLOCATED values must be re-read from the first OT_KV_STATIC plan's relay_stages.json; this
tool re-runs unchanged on that table once the static buses (pvvq / pvrs / ki<->slg) exist (they are preferred when
present).
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
STACKS = ('WS', 'WN', 'ES', 'EN')
OUT_DIR = 'results/arch/qwen_kv_static_programme_1017'
SOURCE = OUT_DIR + '/kvs13l4_plan_ages_source.json'

# Element constants (each names its source).
LANDING_SEG_LAT = 8      # qkd_static_kv_landing_seg header: request -> response 8 edges (VREQ=1), pin-registered tile
ISSUER_RING_EXTRA = 7    # kv_static.validate_native_edges / static_qk_calendar: ECTL ROW_RETURN_LAT = RESPONSE_LAT + 7
QK_WRITE_BEFORE_READ = 11  # static_qk_calendar.compile_calendar: write 7 + (seg + 2) + s < read age - 1 + s
QK_ISSUE_AGE_KIT = 34    # template / attn_calendar QK_CONSUME (the bench-measured ECTL A age)
# KV-ECTL4 2026-10-18 (coordinator 0gs (d)): ONE K round trip for all 32 ECTL frames (qkd_ectl3_kiss_st's hardened
# children carry RESPONSE_LAT / ROW_RETURN_LAT / QK_ISSUE_AGE as RTL parameters): the die pads each frame's K request
# chain to K_RT_BUDGET (kv_k_rt_eq.py) and fails when a natural round trip exceeds it.  Budget 80: kvs14q-8503e0c89
# measured 8 + krq + krs = 12..70 on the 648 x 129.6 slots; the 725.76 x 261.36 frame adds 131.76 um a row engine; the
# margin keeps the hardened children valid across plan iterations.  QK_ISSUE_AGE = budget + QK_WRITE_BEFORE_READ.
K_RT_BUDGET = int(__import__('os').environ.get('OT_KV_K_RT', '80'))
VPORT_RT_LANDING = 9     # qkd_pv16_vport r5/r6: RT = abutted landing seg -> vport 9 (KVJ-F b4d7accd4 tb_static_landing_vport:
                         # 'landing 8 + relays' faults every slot; kv_die VPORT_RT_SEG = 9) + request / return relays
REACH_WIDE_UM = 340     # kvs13l4 OT_KV_REACH_W 36:400,296:370,100000:340 (words > 296 b)
VPORT_RL_BASE = 4        # qkd_pv16_vport: RL = 4 + W + DQ + RT; pair FIRST_INPUT_AGE = RL + 1
CORE_U, HBM_U = 625, 768  # qkd_static_kv_phase_launch / qkd_kv_landing_cal: core 833.33 ps = 625 u, HBM 1024 ps = 768 u
U_PS = 4 / 3
# Die clocking (owner rules): neighbour skew <= 80 ps between regional entries (neighbour-relative clocking 10-16),
# 60 ps setup / 25 ps hold uncertainty (AGENTS.md sign-off policy).  The window is the bench-proven component window
# [200, 600] u (tb_static_phase_launch, 401 of 768 phases) when it covers these budgets; never widened here.
SKEW_PS, SETUP_UNC_PS, HOLD_UNC_PS = 80, 60, 25
CELL_SETUP_SIDE_PS, CELL_HOLD_SIDE_PS = 126, 10   # budget left for clk->q + wire + setup (setup side) / hold - min clk->q
SAFE_WINDOW_U = (200, 600)
META_HOLD_BENCH = 8      # tb_static_phase_launch held-metadata budget


def stages(src, bid):
    for b in src['buses']:
        if b['bid'] == bid:
            return b['stages'], b['id']
    return None, None


def need(src, bid):
    s, i = stages(src, bid)
    if s is None:
        raise SystemExit(f'die plan source lacks bus {bid}')
    return s, i


def derive(src):
    out = dict(schema='opentallas.qwen_kv_static.die_ages.v1', status='PLAN_PRICED_NOT_ROUTED',
               source=dict(path=SOURCE, plan=src['plan'], source_commit=src['source_commit'],
                           plan_json_sha256=src['plan_json_sha256'], relay_stages_json_sha256=src['relay_stages_json_sha256'],
                           stage_definition=src['stage_definition'], reach_um=src['reach_um']),
               k_issuer={}, ectla={}, vport={}, phase_launch={}, link={}, notes=[])
    # ---- K issuer <-> static landing group (k_issuer folded into the ECTL-A successor, plan (b)) ----
    rl = {}
    for st in STACKS:
        for g in range(8):
            static_q, _ = stages(src, f'kiq_{st}_{g}')          # a future OT_KV_STATIC plan's own bus wins
            static_s, _ = stages(src, f'kis_{st}_{g}')
            if static_q is not None and static_s is not None:
                q, s, cls, ids = static_q, static_s, 'PLAN_RELAY', [f'kiq_{st}_{g}', f'kis_{st}_{g}']
            else:
                (q, iq), (s, is_) = need(src, f'krq_{st}_{g}'), need(src, f'krs_{st}_{g}')
                cls, ids = 'PLAN_ANALOG', [iq, is_]
            r = LANDING_SEG_LAT + q + s
            rl[(st, g)] = r
            out['k_issuer'][f'ki_{st}_{g}'] = dict(RESPONSE_LAT=r, request_relays=q, response_relays=s, landing_seg=LANDING_SEG_LAT,
                                                   cls=cls, buses=ids)
    worst = max(rl.values())
    natural = [min(rl.values()), worst]
    if worst > K_RT_BUDGET:
        raise SystemExit(f'K round trip {worst} > K_RT_BUDGET {K_RT_BUDGET}: move the ECTL frames or raise the budget and '
                         're-harden the qkd_ectl3_kiss_st children')
    # KV-ECTL4: every frame padded to the budget (kv_k_rt_eq): one RESPONSE_LAT, one ROW_RETURN_LAT, one QK age
    for k_ in out['k_issuer']:
        out['k_issuer'][k_].update(RESPONSE_LAT=K_RT_BUDGET, natural_response_lat=out['k_issuer'][k_]['RESPONSE_LAT'],
                                   request_pad=K_RT_BUDGET - out['k_issuer'][k_]['RESPONSE_LAT'])
    rl = {k_: K_RT_BUDGET for k_ in rl}
    worst = K_RT_BUDGET
    qk_age = max(QK_ISSUE_AGE_KIT, worst + QK_WRITE_BEFORE_READ)
    for (st, g), r in rl.items():
        out['ectla'][f'ectl_a_{st}_{g}'] = dict(ROW_RETURN_LAT=r + ISSUER_RING_EXTRA, QK_ISSUE_AGE=qk_age, cls='DERIVED')
    out['qk'] = dict(response_lat_range=[min(rl.values()), worst], natural_response_lat_range=natural, k_rt_budget=K_RT_BUDGET,
                     QK_ISSUE_AGE=qk_age, QK_ISSUE_AGE_kit=QK_ISSUE_AGE_KIT,
                     row_latency_for_calendar=worst + 2, rule='QK_ISSUE_AGE >= max RESPONSE_LAT + 11 (static_qk_calendar write-before-read); '
                     'one age for all 32 ECTL A: the slowest group binds the layer anyway, so equal ages cost nothing over it; '
                     'KV-ECTL4: every frame K round trip padded to K_RT_BUDGET on its request chain (kv_k_rt_eq.py)')
    # ---- PV16 V ports ----
    vt = src['pv144']['vport_timing']
    if not vt.get('r6', {}).get('W_equal'):
        raise SystemExit('V port die relay edges W = WP + O must be equalised (OT_KV_V144_R6)')
    W = vt['r6']['W_target']
    homes = src['pv144']['vport_homes']
    for vp, row in vt['ports'].items():
        st, k = vp.split('_')[1], int(vp.split('_')[2])
        rq = [stages(src, f'pvvq_{st}_{k}_{g}')[0] for g in (0, 1)]
        rs = [stages(src, f'pvrs_{st}_{k}_{g}')[0] for g in (0, 1)]
        h = homes[vp]
        c0, c1 = h['channel_um']
        x, w = h['xy'][0], h['size'][0]
        dx = round(x - c0 if st[0] == 'W' else c1 - (x + w), 3)
        if None not in rq + rs:
            rt, cls = VPORT_RT_LANDING + max(a + b for a, b in zip(rq, rs)), 'PLAN_RELAY'
        else:
            # kv_die pv144 home rule: the port sits in the landing-inner channel exactly level with the boundary of its
            # two groups (group pitch 1,512 um, port centre = boundary), so its V get / rsp words cross only the channel.
            if dx > REACH_WIDE_UM:
                raise SystemExit(f'{vp}: channel crossing {dx} um exceeds the 1,056-b word reach {REACH_WIDE_UM} um')
            rt, cls = VPORT_RT_LANDING, 'COLOCATED'
        dq = 0
        rlv = VPORT_RL_BASE + W + dq + rt
        out['vport'][vp] = dict(DQ=dq, RT=rt, WP=row['WP'], O=row['O'], W=W, RL=rlv, channel_crossing_um=dx, cls=cls)
    rls = {v['RL'] for v in out['vport'].values()}
    if len(rls) != 1:
        raise SystemExit(f'V ports see different RL {sorted(rls)}: pad DQ')
    rlv = rls.pop()
    out['pv'] = dict(RL=rlv, FIRST_INPUT_AGE=rlv + 1, plan_age_bound=vt['r6']['age_bound'],
                     age_ok=rlv + 1 == vt['r6']['age_bound'], rule='RL = 4 + W + DQ + RT equal on all 16 ports; pair FIRST_INPUT_AGE = RL + 1')
    if not out['pv']['age_ok']:
        out['notes'].append(f'PV pair FIRST_INPUT_AGE {rlv + 1} != the plan-accepted {vt["r6"]["age_bound"]}')
    # ---- core -> HBM fixed-phase launch (per-group control tile) ----
    lo, hi = SAFE_WINDOW_U
    setup_need_u = math.ceil((SKEW_PS + SETUP_UNC_PS + CELL_SETUP_SIDE_PS) / U_PS)
    hold_need_u = math.ceil((SKEW_PS + HOLD_UNC_PS + CELL_HOLD_SIDE_PS) / U_PS)
    if lo < setup_need_u or HBM_U - hi < hold_need_u:
        raise SystemExit('bench phase window does not cover the die clock budget')
    meta_min = math.ceil((hi + 3 * HBM_U) / CORE_U) + 1
    out['phase_launch'] = dict(PH0=0, SAFE_LOW_U=lo, SAFE_HIGH_U=hi, META_HOLD_CORE=max(META_HOLD_BENCH, meta_min, 6),
                               cls='DIE_CONTRACT',
                               basis=dict(PH0='die contract: the reset release edge is beat aligned (qkd_kv_landing_cal PH0; the template binds '
                                              'every landing calendar at PH0 0, and the phase launch must use the same origin)',
                                          window_u=[lo, hi], setup_side_ps=round(lo * U_PS, 1), hold_side_ps=round((HBM_U - hi) * U_PS, 1),
                                          setup_need_u=setup_need_u, hold_need_u=hold_need_u,
                                          budget=f'skew {SKEW_PS} + setup unc {SETUP_UNC_PS} + cell {CELL_SETUP_SIDE_PS} ps / '
                                                 f'skew {SKEW_PS} + hold unc {HOLD_UNC_PS} + cell {CELL_HOLD_SIDE_PS} ps',
                                          meta_hold_min=meta_min),
                               open='native CDC STA of the closed per-group control tile must confirm the window; token run starts '
                                    'must sit at a fixed HBM-beat phase or a launch can fall outside it (kv_static_programme reports)')
    if __import__('os').environ.get('OT_KV_CONTROLLER_CORE', '0') == '1':
        out['phase_launch'] = dict(PH0=0, SAFE_LOW_U=625, SAFE_HIGH_U=625,
                                   META_HOLD_CORE=META_HOLD_BENCH, SAME_CLOCK=1,
                                   cls='ONE_CORE_CLOCK_833PS',
                                   basis='625/625 dimensionless ticks, same clock tree; no reset-relative phase origin',
                                   open='propagated common-clock TT setup / FF hold STA')
    # ---- link / control ages for the programme compiler ----
    lst, lst_id = need(src, 'lprg_st')
    lp_seq, lp_id = need(src, 'seqst_lp')
    kvn = {st: need(src, f'kvn_{st}') for st in STACKS}
    rx, rx_id = need(src, 'seqst_rx')
    grp = lp_seq + max(s for s, _ in kvn.values())
    out['link'] = dict(
        programme_start=dict(edges=lst, cls='PLAN_RELAY', bus=lst_id,
                             note='dcal tok_start -> layer programme start pin: programme age a <-> KV run edge a - 1 + edges'),
        programme_to_attention=dict(edges=lst, cls='COLOCATED', note='attention control tile abuts the d2d end as dcal does '
                                    '(dcal.cal -> d2d 0 stages), so it is the dcal -> lprg distance'),
        d2d_to_attention_rx=dict(edges=0, cls='COLOCATED', note='att_rx 548 b local at the d2d end (plan (b) attention control tile); '
                                 f'the legacy sequencer home was {rx} stages away ({rx_id})'),
        programme_to_writer=dict(edges=lst, cls='COLOCATED', note='writer programme beside the writer at the d2d KVN end (kvnc_kvi 0 stages)'),
        d2d_to_writer=dict(edges=0, cls='COLOCATED', note='KVN words local at the d2d end'),
        programme_to_groups=dict(edges=grp, cls='PLAN_ANALOG', buses=[lp_id] + [i for _, i in kvn.values()],
                                 per_stack={st: lp_seq + s for st, (s, _) in kvn.items()},
                                 note='lprg -> per-group control tiles (phase launch, landing calendar, K issuer) along the legacy '
                                      'seq -> landing corridor; one equalised registered tree (the die pads the near stacks) so '
                                      'one root reaches all 32 groups on one edge'),
        group_internal=dict(edges=0, cls='COLOCATED', note='phase launch, front calendar and the four pc_path calendars share the '
                            'per-group control tile / abut it; landing calendar beside its landing segment'),
        return_to_landing_ld=dict(LD=1, cls='COLOCATED', note='qkd_kv_landing_cal LD = return-slot output register + relays; pc_path '
                                  'children abut their landing group'),
    )
    return out


def apply(graph, ages):
    """fill every template None parameter that the ages table prices (returns the names still unpriced)"""
    left = []
    for i in graph['instances']:
        p = i['parameters']
        r = i['role']
        if r == 'k_issuer':
            p['RESPONSE_LAT'] = ages['k_issuer'][i['name']]['RESPONSE_LAT']
        elif r == 'ectla':
            e = ages['ectla'][i['name']]
            p['ROW_RETURN_LAT'], p['QK_ISSUE_AGE'] = e['ROW_RETURN_LAT'], e['QK_ISSUE_AGE']
        elif r == 'vport':
            v = ages['vport'][i['name']]
            p['DQ'], p['RT'] = v['DQ'], v['RT']
        elif r == 'phase_launch':
            for k in ('PH0', 'SAFE_LOW_U', 'SAFE_HIGH_U', 'META_HOLD_CORE'):
                p[k] = ages['phase_launch'][k]
        left += [f'{i["name"]}.{k}' for k, v in p.items() if v is None]
    return left


def lane_bid(station):
    """the die bus id of a lane's station (rly_<bid>_<k>__s<j>; pin-repair chains rly_pinfix_<bid>_r<i>_<k>)"""
    import re
    n = re.sub(r'__s\d+$', '', station)
    n = re.sub(r'^rly_', '', n).rsplit('_', 1)[0]
    return re.sub(r'_r\d+$', '', re.sub(r'^pinfix_', '', n))


def fwd_overlay(src, fl):
    """KV-CLOCK: stage counts of the landed buses -> their landed latency (static: a fixed number of core edges).
    KVR-FWDAGE 10-19: the landed age REPLACES the relay stage count in both directions (a forwarded half-cycle lane is
    usually FASTER than its n-relay plan: L = E + 1 < n); a static schedule must charge exactly what the landing delivers"""
    import copy
    worst = {}
    for L in fl['lanes']:
        b = lane_bid(L['stations'][-1])
        lat = math.ceil(L['landed'] - 1)             # landed counts the block flop; a plan stage count does not
        worst[b] = max(worst.get(b, 0), lat)
    out, landed = copy.deepcopy(src), {}
    for b in out['buses']:
        if b['bid'] in worst and worst[b['bid']] != b['stages']:
            landed[b['bid']] = (b['stages'], worst[b['bid']])
            b['stages'] = worst[b['bid']]
    # HKV-STATIONS 10-19: relay stages kv_lane_stations inserted OUTSIDE a lane (plain replicas) are fixed edges too
    plain = fl.get('plain_added_stages') or {}
    for b in out['buses']:
        k = plain.get(b['bid'], 0)
        if k and b['bid'] not in worst:
            landed[b['bid']] = (b['stages'], b['stages'] + k)
            b['stages'] += k
    return out, landed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--source', type=Path, default=ROOT / SOURCE)
    ap.add_argument('--out', type=Path, default=ROOT / OUT_DIR / 'die_ages.json')
    ap.add_argument('--template-out', type=Path, help='also write the priced static-join template here')
    ap.add_argument('--fwd-lanes', type=Path, help='KV-CLOCK 10-18: RUN/fwd_lanes.json (kv_fwd_lanes.py); every landed bus '
                    'takes its landed latency (worst lane of the bus: ceil(landed - 1) = E + 1 (+ post stages), the block flop excluded)')
    a = ap.parse_args()
    src = json.loads(a.source.read_text())
    if a.fwd_lanes:
        src, landed = fwd_overlay(src, json.loads(a.fwd_lanes.read_text()))
        print(json.dumps(dict(fwd_landed_buses=len(landed), added_stages=sum(v[1] - v[0] for v in landed.values()))))
    ages = derive(src)
    if a.fwd_lanes:
        ages['fwd_landed'] = {k: dict(stages_relay=v[0], stages_landed=v[1]) for k, v in sorted(landed.items())}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(ages, indent=1) + '\n')
    if a.template_out:
        import kv_static as K
        g, _ = K.template()
        left = apply(g, ages)
        a.template_out.mkdir(parents=True, exist_ok=True)
        (a.template_out / 'static_join.priced.json').write_text(json.dumps(g, indent=1) + '\n')
        print(json.dumps(dict(unpriced_left=left)))
    print(json.dumps(dict(response_lat=ages['qk']['response_lat_range'], QK_ISSUE_AGE=ages['qk']['QK_ISSUE_AGE'],
                          pv=ages['pv'], phase={k: ages['phase_launch'][k] for k in ('PH0', 'SAFE_LOW_U', 'SAFE_HIGH_U', 'META_HOLD_CORE')},
                          groups_age=ages['link']['programme_to_groups']['edges'], notes=ages['notes'])))


if __name__ == '__main__':
    main()
