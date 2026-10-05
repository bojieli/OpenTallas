#!/usr/bin/env python3
"""Records and wire-stage pricing for the HBM accelerator die floorplan (tools/hbm_accel_die_fp.py).

record:  feasibility.json from the OpenROAD case directories (a: legality / track assert / pin access, b: bundled GRT,
         c: PSM IR windows); the IR summary covers every window of the die.
price:   wire_stages.json -- per critical path the GRT-routed length (sum over its forwarded segments of the longest
         bundle) and the stage bound sum(ceil(L_seg / 430.56 um)) (+ the meso crossing at the hub <-> group region
         boundary), then the per-token cost priced into the DS 1M matched reference / inherited composition and the
         Qwen 8K TP2 / TP4 compositions, one term per path class, each with its per-token occurrence count.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import qwen_rom_fulldie as Q  # noqa: E402
import hbm_accel_die_fp as F  # noqa: E402

MESO_CYC = 2          # measured meso FIFO crossing (results/uarch/meso_fifo_20261004: delta mean 2.01 periods)
OLD_BARRIER_WIRE = 29  # one-way wire cycles inside the 62-cycle gpu_supply_barrier RTL (leaf 7 + trunk 22,
#                        results/floorplan/hbm_gpu/v41_hbm_die.json barrier_network; uarch_model barrier basis)


def _grt_lengths(work):
    from chip_assembly import v41_die as VD
    return VD.parse_wirelength(work / 'wirelength.csv')


def record_b(work, m):
    from chip_assembly import v41_die as VD
    log = Q._log(work)
    rec = dict(case='b', exit=Q._exit(work), wall=Q._wall(log), peak_rss_mb=Q._rss_mb(log),
               manifest=json.loads((work / 'manifest.json').read_text()))
    p = VD.parse_log(log)
    rec['grt'] = {k_: v for k_, v in p.items() if k_ != 'mem'}
    mm_ = re.search(r'OT_TIME grt_s=(\d+)', log)
    rec['grt_s'] = int(mm_.group(1)) if mm_ else None
    k = rec['manifest']['bundle_k']
    cls_of = {f'n_{bid}': (c, bits) for bid, c, bits, _ in m['buses']}
    per = {}
    if (work / 'wirelength.csv').is_file():
        for net, um in _grt_lengths(work).items():
            c, bits = cls_of.get(net.split('[')[0], ('?', 0))
            e = per.setdefault(c, dict(bundle_nets=0, bundle_um=0.0, max_um=0.0))
            e['bundle_nets'] += 1
            e['bundle_um'] += um
            e['max_um'] = max(e['max_um'], um)
        for c, e in per.items():
            e['wire_m'] = round(e['bundle_um'] * k / 1e6, 2)
            e['bundle_um'], e['max_um'] = round(e['bundle_um'], 1), round(e['max_um'], 1)
    rec['wire_by_class'] = per
    rec['errors'] = re.findall(r'\[ERROR [^\]]+\].*|^Error: .*', log, re.M)[:10]
    return rec


def windows(work, m, base=None):
    W, H = m['geo']['W'], m['geo']['H']
    S = F.S
    S.DIE = (W, H)
    S.where = lambda _m, x, y: _where(m, x, y)
    return S.gcell_windows(work, m, base)


def _where(m, x, y):
    for r in m['regions']:
        a, b, c, e = r['rect']
        if a <= x < c and b <= y < e:
            return r['name']
    return 'channel'


def record(m, root, out=None, only=''):
    root = Path(root)
    cases = {}
    for d in sorted(root.rglob('manifest.json')):
        d = d.parent
        if only and not re.fullmatch(only, d.name):
            continue
        man = json.loads((d / 'manifest.json').read_text())
        key = f'{d.parent.name}/{d.name}'
        try:
            if man.get('case') == 'a':
                cases[key] = Q.record_a(d)
            elif man.get('case') == 'b':
                cases[key] = record_b(d, m)
                base = d.parent / (re.sub(r'_i\d+$', '_i5', d.name) + '_base')
                if not man.get('empty_baseline') and base.is_dir():
                    cases[key]['windows_baseline_subtracted'] = windows(d, m, base)
                else:
                    cases[key]['windows'] = windows(d, m)
                if d.parent.name != m.get('final_round', F.FINAL_ROUND):
                    cases[key]['note'] = ('earlier round: wire_by_class / window labels use the final net and region map '
                                          '(approximate); overflow figures are exact')
            elif man.get('case') == 'c':
                cases[key] = Q.record_c(d)
                cases[key]['group'] = d.parent.name
                if man.get('power_w', 1.0) == 0.0 and man.get('bump_sites', 1) == 0:
                    cases[key]['no_core_load'] = ('window lies wholly in a link / host strip: no core-grid load and '
                                                     'no core power bumps (the macros are on their own supplies)')
        except Exception as e:  # noqa: BLE001
            cases[key] = dict(error=repr(e))
    ir = defaultdict(list)
    for n, c in cases.items():
        if c.get('case') == 'c':
            if c.get('no_core_load'):
                ir[c['group'] + '#na'].append(n)
                continue
            ir[c['group']].append((c.get('rail_to_rail_interior_mv'), n, c.get('pass_interior'), c.get('exit')))
    summary = {}
    for g_, rows in ir.items():
        if g_.endswith('#na'):
            continue
        ok = [r for r in rows if r[0] is not None]
        worst = max(ok) if ok else None
        summary[g_] = dict(windows=len(rows), completed=len(ok), all_pass=bool(ok) and len(ok) == len(rows)
                           and all(r[2] for r in ok), worst_interior_rail_to_rail_mv=worst[0] if worst else None,
                           worst_window=worst[1] if worst else None, failing=[r[1] for r in ok if not r[2]],
                           incomplete=[r[1] for r in rows if r[0] is None],
                           no_core_load_windows=ir.get(g_ + '#na', []))
    rec = dict(schema='opentallas.hbm-accel-die-floorplan.feasibility.v1',
               tool_sha256=dict(fp=F.sha('tools/hbm_accel_die_fp.py'), price=F.sha('tools/hbm_accel_die_price.py')),
               cases=cases, ir_summary=summary)
    out = Path(out) if out else ROOT / F.OUT / 'feasibility.json'
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
    print(json.dumps(dict(cases=len(cases), ir_summary=summary), indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ pricing
def routed_paths(m, grt_work):
    """Per critical path: routed length (sum over its segments of the longest bundle of that segment's bus) and the
    stage bound sum(ceil(L / 430.56))."""
    lens = _grt_lengths(Path(grt_work))
    seg = defaultdict(float)
    tot, cnt = defaultdict(float), defaultdict(int)
    allv = defaultdict(list)
    for net, um in lens.items():
        b = net.split('[')[0][2:]
        seg[b] = max(seg[b], um)
        tot[b] += um
        cnt[b] += 1
        allv[b].append(um)
    med = {b: sorted(v)[len(v) // 2] for b, v in allv.items()}
    by = {it.name: it for it in m['insts']}
    bus = {b_[0]: b_ for b_ in m['buses']}

    pxy = m.get('pin_xy')

    def manh(b):
        def near(it, q):
            return (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))
        e = bus[b][3]
        A, B = by[e[0][0]], by[e[-1][0]]
        if pxy:                 # fixed-pin elements: from the pin (the box distance of abutting tiles is 0)
            pa, pb = pxy(*e[0]), pxy(*e[-1])
            if pa or pb:
                pa = pa or near(A, pb)
                pb = pb or near(B, pa)
                return abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
        a = near(A, (B.x + B.w / 2, B.y + B.h / 2))
        bb = near(B, a)
        a = near(A, bb)
        return abs(a[0] - bb[0]) + abs(a[1] - bb[1])
    out = {}
    for p, ids in m['paths'].items():
        Ls = [seg.get(b, None) for b in ids]
        if any(x is None for x in Ls):
            out[p] = dict(missing=[b for b, x in zip(ids, Ls) if x is None])
            continue
        Lm = [tot[b] / cnt[b] for b in ids]
        Ld = [med[b] for b in ids]
        Lh = [manh(b) for b in ids]
        out[p] = dict(segments=len(ids), routed_um=round(sum(Ls), 1), routed_mean_bundle_um=round(sum(Lm), 1),
                      stages_430=sum(math.ceil(x / F.LINK_STAGE_UM) for x in Ls if x > 0),
                      stages_430_mean_bundle=sum(math.ceil(x / F.LINK_STAGE_UM) for x in Lm if x > 0),
                      stages_430_median_bundle=sum(math.ceil(x / F.LINK_STAGE_UM) for x in Ld if x > 0),
                      stages_430_manhattan=sum(math.ceil(x / F.LINK_STAGE_UM) for x in Lh if x > 0),
                      routed_median_bundle_um=round(sum(Ld), 1), manhattan_um=round(sum(Lh), 1),
                      stages_504=sum(math.ceil(x / F.SS_REACH_UM) for x in Ls if x > 0),
                      longest_segment_um=round(max(Ls), 1))
    return out


def class_max(rp):
    out = {}
    for p, v in rp.items():
        c = F.path_class(p) or ('attn_out' if p.startswith('attn_out') else ('hub' if p.startswith('hub_') else None))
        if not c or 'stages_430' not in v:
            continue
        if p.startswith('hub_') and c == 'hub':
            c = p
        e = out.setdefault(c, dict(paths=0, routed_um=0.0, stages_430=0, stages_504=0, worst=None))
        e['paths'] += 1
        if v['stages_430'] > e['stages_430'] or (v['stages_430'] == e['stages_430'] and v['routed_um'] > e['routed_um']):
            e['worst'] = p
            e['routed_um'] = v['routed_um']
        e['stages_430'] = max(e['stages_430'], v['stages_430'])
        e['stages_504'] = max(e['stages_504'], v['stages_504'])
        for k2 in ('stages_430_mean_bundle', 'stages_430_median_bundle', 'stages_430_manhattan'):
            e[k2] = max(e.get(k2, 0), v[k2])
    return out


def _ds_counts(comp):
    """Per-token occurrences on the AR path of the composition."""
    c = defaultdict(int)
    for t in comp['path']:
        n, how = t['node'], t['how']
        if n.startswith('xload:'):
            mm = re.search(r'(\d+) op\(s\) not resident', how)
            if mm and int(mm.group(1)) > 0:
                c['x_first_load'] += 1
                c['x_load_phases'] += int(mm.group(1))
        elif n == 'barrier':
            c['barrier'] += 1
        elif n.startswith('coll:'):
            mm = re.search(r'(\d+) crossing\(s\)', how)
            c['coll_terms'] += 1
            c['coll_crossings'] += int(mm.group(1)) if mm else 1
        elif n == 'hbm:expert_fetch':
            c['expert_fetch'] += 1
        elif n.startswith('hbm:') and n != 'hbm:embedding_row':
            c['hbm_kv_rows'] += 1
        elif n == 'hbm:embedding_row':
            c['embedding_row'] += 1
        elif n == 'du:index_scores':
            c['index_scores'] += 1
        elif n.startswith('attn:'):
            c['attn'] += 1
    return dict(c)


def price(m, grt_work, out=None):
    grt_work = Path(grt_work)
    rp = routed_paths(m, grt_work)
    cm = class_max(rp)
    hz = F.CLK_HZ
    rec = _price(m, rp, cm, 'stages_430')
    rec['bases'] = {}
    for key, basis in (('stages_430', 'BOUND: longest k16 bundle of each routed segment (every bit registered in time)'),
                       ('stages_430_median_bundle', 'median bundle of each routed segment (GRT outlier detours excluded)'),
                       ('stages_430_mean_bundle', 'mean bundle of each routed segment'),
                       ('stages_430_manhattan', 'FLOOR: Manhattan length between the placed stations / pins of each '
                                                'segment (no detour)')):
        s_ = _price(m, rp, cm, key)
        g_ = s_['compositions']['ds_matched']['rows']['gate']
        rec['bases'][key] = dict(basis=basis, one_way_cycles=s_['one_way_cycles'],
                                 ds_matched_added_us=s_['compositions']['ds_matched']['added_us'],
                                 ds_gate_AR_priced_us=g_['AR_priced_us'], ds_gate_AR_tok_s_priced=g_['AR_tok_s_priced'],
                                 ds_gate_MTP_tok_s_priced=g_['MTP_tok_s_priced'],
                                 qwen_tp4_ar_tok_s_priced=s_['qwen_8k']['b_TP4_iso_silicon']['ar_tok_s_priced'],
                                 qwen_tp2_ar_tok_s_priced=s_['qwen_8k']['a_TP2_same_silicon']['ar_tok_s_priced'])
    rec.update(schema='opentallas.hbm-accel-die-floorplan.wire-stages.v1', grt_case=str(grt_work.name),
               stage_pitch_um=F.LINK_STAGE_UM, ss_reach_um=F.SS_REACH_UM, meso_crossing_cycles=MESO_CYC,
               clock_hz=hz, class_bounds=cm, paths=rp,
               tool_sha256=dict(fp=F.sha('tools/hbm_accel_die_fp.py'), price=F.sha('tools/hbm_accel_die_price.py')))
    out = Path(out) if out else ROOT / F.OUT / 'wire_stages.json'
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(one_way_cycles=rec['one_way_cycles'], ds={k: dict(added_us=v['added_us'], rows=v['rows'])
                                                                     for k, v in rec['compositions'].items()},
                          bases=rec['bases'],
                          qwen={k: v for k, v in rec['qwen_8k'].items() if k != 'scope'}), indent=1, default=str)[:6000])
    return 0


def _price(m, rp, cm, key):
    hz = F.CLK_HZ

    def st(c):
        return cm[c][key]
    # one-way die-level latencies (cycles at 1.2 GHz), hub <-> group paths pay one meso crossing
    def hubmax(rx):
        v = [e[key] for k_, e in cm.items() if re.fullmatch(rx, k_)]
        return max(v) if v else 0
    S = dict(
        xbcast=st('xbcast') + hubmax(r'hub_su_\w+_vm') + MESO_CYC,
        control=st('control') + MESO_CYC,
        result=st('result') + MESO_CYC,
        weight=st('weight'),
        expert_req=st('expert_req') + MESO_CYC,
        kv=st('kv') + MESO_CYC,
        ik=st('ik') + MESO_CYC,
        link=st('link'),
        su_coll=hubmax(r'hub_su_\w+_coll'),
        coll_su=hubmax(r'hub_coll_su_\w+'),
        attn_out=st('attn_out'),
    )
    comps = {}
    for tag, rel in (('ds_matched', F.MATCHED), ('ds_inherited', F.ALLMEAS)):
        comp = json.loads((ROOT / rel).read_text())
        n = _ds_counts(comp)
        terms = {}

        def add(name, count, cyc, basis):
            terms[name] = dict(count=count, cycles_each=cyc, us=round(count * cyc / hz * 1e6, 3), basis=basis)
        x_cnt = n.get('x_first_load', 0) if tag == 'ds_matched' else n.get('barrier', 0)
        add('x_broadcast', x_cnt, S['xbcast'],
            'root -> farthest SM multicast depth (SU -> VM hub hop + VM -> x face) + meso, once per serial x load '
            '(the first not-resident load after a producer; later loads of the group stream behind it)')
        bar_new = 2 * S['control']
        add('barrier_wire_delta', n.get('barrier', 0), bar_new - 2 * OLD_BARRIER_WIRE,
            f'arrive + release over the routed control tree ({S["control"]} each way incl. meso) replacing the '
            f'{OLD_BARRIER_WIRE} + {OLD_BARRIER_WIRE} wire cycles inside the measured 62-cycle barrier RTL')
        add('result_gather', n.get('barrier', 0), max(0, S['result'] - bar_new),
            'SM -> SU result gather travels with the arrive; exposed only beyond the barrier round trip')
        add('su_coll_endpoint', n.get('coll_terms', 0), S['su_coll'] + S['coll_su'],
            'SU -> collective endpoint and back, once per collective')
        add('endpoint_serdes', n.get('coll_crossings', 0), 2 * S['link'],
            'endpoint -> farthest SerDes macro (flit striped over 9 macros) and back, per switch crossing; the TU '
            'budget (PHY + switch + cable) excludes the on-die run')
        add('expert_fetch_wire', n.get('expert_fetch', 0), S['expert_req'] + S['weight'],
            'router -> stream service descriptor + stream service -> farthest SM weight line, per data-dependent '
            'expert fetch (the measured first access is at the controller)')
        add('kv_rows_wire', n.get('hbm_kv_rows', 0) + n.get('embedding_row', 0), S['kv'],
            'stream service -> scan quadrant (near-HBM attention) per first-access KV / window / embedding read')
        add('index_keys_wire', n.get('index_scores', 0), S['ik'], 'stream service -> index quarter per index scan')
        add('attn_out_wire', n.get('attn', 0), S['attn_out'], 'tile row end -> index quarter -> SU per attention step')
        tot_us = round(sum(v['us'] for v in terms.values()), 3)
        rows = {}
        if tag == 'ds_matched':
            g = comp['gate']
            for name, ar, mtp in (('gate', g['AR_us'], g['MTP_step_us']), ('matched', comp['headline']['AR_us'],
                                                                           comp['headline']['MTP_step_us']),
                                  ('today', g['today_AR_us'], g['today_MTP_step_us'])):
                rows[name] = dict(AR_us=ar, AR_priced_us=round(ar + tot_us, 3), AR_delta_pct=round(100 * tot_us / ar, 2),
                                  MTP_step_us=mtp, MTP_step_priced_us=round(mtp + tot_us, 3),
                                  AR_tok_s_priced=round(1e6 / (ar + tot_us), 1),
                                  MTP_tok_s_priced=round(3.8879 * 1e6 / (mtp + tot_us), 1))
            rows['note'] = ('the MTP step carries the same die-level traversals as the AR walk (the P6 verify walk has '
                            'the AR node sequence; the draft is off-die-path); today-clock rows priced at 1.2 GHz wire '
                            'stages (conservative: their SM clock is lower)')
        else:
            ar = comp.get('AR_us')
            rows['inherited'] = dict(AR_us=ar, AR_priced_us=round(ar + tot_us, 3) if ar else None)
        comps[tag] = dict(source=rel, counts=n, terms=terms, added_us=tot_us, rows=rows)
    # ---- Qwen 8K: the W12 vehicle's own broadcast / tree depth is inside its measured cycles; price the die-level
    #      collective run (SU <-> endpoint <-> SerDes per crossing) and the first-access KV hop per layer
    qa = json.loads((ROOT / F.QWEN_ALL).read_text())
    qwen = {}
    for dn_, d in qa['designs'].items():
        add_cyc, det = 0, []
        for s_ in d['stages']:
            cr = s_.get('coll_crossings', 0)
            kv = 1 if s_['attribution_die0'].get('kv_wait', 0) > 0 else 0
            c = s_['count'] * (cr * (2 * S['link'] + S['su_coll'] + S['coll_su']) + kv * S['kv'])
            det.append(dict(stage=s_['stage'], count=s_['count'], crossings=cr, kv_first_access=kv,
                            added_cycles_per_stage=c // max(1, s_['count'])))
            add_cyc += c
        base = d['composed_cycles']
        qwen[dn_] = dict(composed_cycles=base, added_cycles=add_cyc, priced_cycles=base + add_cyc,
                         ar_tok_s=d['ar_tok_s'], ar_tok_s_priced=round(hz / (base + add_cyc), 1),
                         delta_pct=round(100 * add_cyc / base, 2), stages=det)
    qwen['scope'] = ('HA8 W12 vehicle mapped to this die\'s collective and stream-service geometry: per switch crossing '
                     'endpoint <-> farthest SerDes both ways, SU <-> endpoint once per collective, stream service -> '
                     'compute once per layer with a KV first access.  The W12 spine/tile tree (BD31, NWS/TWS) is '
                     'measured inside its cycles; the W12 tile die (1,536 tiles, 421.5 MiB SRAM residence, ~382 mm2 tile '
                     'core) is NOT this SM die and is not floorplanned here')
    return dict(one_way_cycles=S, compositions=comps, qwen_8k=qwen)


# ------------------------------------------------------------------------------------------------ Qwen tile die
Q_BASES = (('stages_430', 'BOUND: longest k16 bundle of each routed segment (every bit registered in time)'),
           ('stages_430_median_bundle', 'median bundle of each routed segment (GRT outlier detours excluded)'),
           ('stages_430_mean_bundle', 'mean bundle of each routed segment'),
           ('stages_430_manhattan', 'FLOOR: Manhattan length between the placed pins of each segment (no detour)'))


def _q_vehicle(rel):
    """The measured vehicle's own wire-stage parameters (bd, nws, tws, ord) from a stage's token_result.json."""
    d = json.loads((ROOT / rel).read_text())['design_point']
    return {k: d[k] for k in ('tp', 'bd', 'nws', 'tws', 'ord')}


def q_one_way(m, rp, key):
    """One-way die-level depths (cycles at 1.2 GHz) of the Qwen tile die for one basis.  Element-internal forwarding
    is fixed by construction: hop_stages per tile pitch (corridor and fill banks every <= 430.56 um)."""
    T = m['tile_element']
    hop = T['hop_stages']

    def mx(prefix):
        v = [(e[key], p) for p, e in rp.items() if p.startswith(prefix) and key in e]
        return max(v) if v else (0, None)
    bd, bdp = mx('bd_')
    tr, trp = mx('tree_')
    tw, twp = mx('tws_')
    fl, flp = mx('fill_')
    st, stp = mx('stat_')
    lk, lkp = mx('link_')
    return dict(
        bd=bd + 8 * hop, bd_worst=bdp, bd_die_net=bd, bd_element=8 * hop,
        tree=tr, tree_worst=trp,
        tws=tw + MESO_CYC, tws_worst=twp,
        coll=rp['coll_tx'][key] + rp['coll_rx'][key],
        link=lk, link_worst=lkp,
        fill=fl + F.QROWS * hop + MESO_CYC, fill_worst=flp, fill_element=F.QROWS * hop,
        stat=st, stat_worst=stp)


def _q_price(m, S_, key):
    hz = F.CLK_HZ
    me = json.loads((ROOT / F.Q_ME_OPS).read_text())['me_ops']
    qa = json.loads((ROOT / F.QWEN_ALL).read_text())
    ch = json.loads((ROOT / F.Q_CHAINS).read_text())
    out = {}
    veh_of_tp = {}

    def terms(veh, stages):
        """stages: [(name, count, decoder layer?, crossings, kv first access?)]"""
        me_ops = sum(c * (me['per_layer_pass'] if dec else me['per_head']) for _, c, dec, _, _ in stages)
        cr = sum(c * x for _, c, _, x, _ in stages)
        kv = sum(c * k for _, c, _, _, k in stages)
        t = dict(
            bd_delta=dict(count=me_ops, cycles_each=max(0, S_['bd'] - veh['bd']),
                          basis=f'x / instruction broadcast: floorplan {S_["bd"]} (head chain + entry + 8 tile hops) '
                                f'against the vehicle bd {veh["bd"]}, once per ME op (6 a layer, 1 the head)'),
            tree_delta=dict(count=me_ops, cycles_each=max(0, S_['tree'] - 4 * veh['nws']),
                            basis=f'in-block split tree, worst leaf -> root {S_["tree"]} against 4 levels x nws '
                                  f'{veh["nws"]}, once per ME op'),
            tws_delta=dict(count=me_ops, cycles_each=max(0, S_['tws'] - veh['tws']),
                           basis=f'block word -> port slice -> core tree top {S_["tws"]} (incl. meso 2) against the '
                                 f'vehicle tws {veh["tws"]}, once per ME op'),
            collective=dict(count=cr, cycles_each=S_['coll'] + 2 * S_['link'],
                            basis='core <-> collective block round trip + collective <-> farthest SerDes both ways, per '
                                  'switch crossing (the TP link budget LAT excludes the on-die run)'),
            kv_first_access=dict(count=kv, cycles_each=S_['fill'] + S_['stat'],
                                 basis='stream service -> farthest tile of its column (fill net + 16 element hops + '
                                       'async FIFO) + service -> core status counts, per layer whose KV segment the '
                                       'engine waits for (kv_wait > 0)'),
            stream_first_word=dict(count=1, cycles_each=S_['fill'] + S_['stat'],
                                   basis='the same depth once a token for the stream\'s first word (later words are '
                                         'prefetched behind it: a constant pipeline shift)'))
        for v in t.values():
            v['cycles'] = v['count'] * v['cycles_each']
        return t, me_ops
    for dn_, d in qa['designs'].items():
        veh = _q_vehicle(d['stages'][-1]['source'])
        veh_of_tp[veh['tp']] = veh
        st_ = [(s_['stage'], s_['count'], s_['stage'] != 'head', s_.get('coll_crossings', 0),
                1 if s_['attribution_die0'].get('kv_wait', 0) > 0 else 0) for s_ in d['stages']]
        t, me_ops = terms(veh, st_)
        add = sum(v['cycles'] for v in t.values())
        base = d['composed_cycles']
        out[dn_] = dict(composed_cycles=base, ar_tok_s=d['ar_tok_s'], vehicle_wire_stages=veh, me_ops=me_ops,
                        terms=t, added_cycles=add, priced_cycles=base + add,
                        ar_tok_s_priced=round(hz / (base + add), 1), delta_pct=round(100 * add / base, 2),
                        source=F.QWEN_ALL)
    for row, tp in (('a_AR_spread', 2), ('b_AR_spread', 4)):
        r_ = ch['rows'][row]
        st_ = []
        for cnt, term, cyc in r_['composition']:
            head = 'head' in term
            st_.append((term, cnt, not head, 1 if head else 2, 0 if head else 1))
        t, me_ops = terms(veh_of_tp[tp], st_)
        add = sum(v['cycles'] for v in t.values())
        base = r_['cycles']
        out[row] = dict(composed_cycles=base, ar_tok_s=r_['tok_s'], vehicle_wire_stages=veh_of_tp[tp], me_ops=me_ops,
                        terms=t, added_cycles=add, priced_cycles=base + add,
                        ar_tok_s_priced=round(hz / (base + add), 1), delta_pct=round(100 * add / base, 2),
                        source=F.Q_CHAINS, note='every layer streamed (spread): 2 crossings and a KV first access a '
                                                'layer, head 1 crossing')
    return out


def price_qwen(m, grt_work, out=None):
    grt_work = Path(grt_work)
    tp = F.q_tree_paths(m)
    m2 = dict(m, paths=dict(m['paths'], **{f'tree_{t}': ids for t, ids in tp.items()}))
    rp = routed_paths(m2, grt_work)
    rec = dict(schema='opentallas.hbm-accel-qwen-die.wire-stages.v1', grt_case=str(grt_work.name),
               stage_pitch_um=F.LINK_STAGE_UM, meso_crossing_cycles=MESO_CYC, clock_hz=F.CLK_HZ,
               tile_hop_stages=m['tile_element']['hop_stages'], bases={})
    for key, basis in Q_BASES:
        S_ = q_one_way(m2, rp, key)
        rows = _q_price(m, S_, key)
        rec['bases'][key] = dict(basis=basis, one_way_cycles=S_, rows=rows,
                                 summary={k: dict(ar_tok_s=v['ar_tok_s'], ar_tok_s_priced=v['ar_tok_s_priced'],
                                                  delta_pct=v['delta_pct'], added_cycles=v['added_cycles'])
                                          for k, v in rows.items()})
    b = rec['bases']['stages_430']
    rec.update(one_way_cycles=b['one_way_cycles'], qwen_8k=b['rows'])
    rec['paths'] = {p: v for p, v in rp.items() if not p.startswith('tree_')}
    tr = {p: v for p, v in rp.items() if p.startswith('tree_') and 'stages_430' in v}
    rec['tree_paths_summary'] = dict(paths=len(tr), max_stages_430=max(v['stages_430'] for v in tr.values()),
                                     max_stages_430_manhattan=max(v['stages_430_manhattan'] for v in tr.values()))
    rec['me_ops_source'] = F.Q_ME_OPS
    rec['scope'] = ('Qwen3-8B HBM accelerator tile die (the HA8 W12 vehicle\'s organisation): the vehicle cycles carry '
                    'its own bd / nws / tws stage parameters; the floorplan prices the excess of the routed depths '
                    'over them per ME op, plus the die-level collective run per crossing and the fill + status depth '
                    'per KV first access and once a token.  Deltas are clamped at 0 (a shorter floorplan path is not '
                    'credited).  Bounds from routed length, not die-level STA.')
    rec['tool_sha256'] = dict(fp=F.sha('tools/hbm_accel_die_fp.py'), price=F.sha('tools/hbm_accel_die_price.py'))
    out = Path(out) if out else ROOT / F.Q_OUT / 'wire_stages.json'
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: dict(one_way=v['one_way_cycles'], summary=v['summary']) for k, v in rec['bases'].items()},
                     indent=1, default=str)[:8000])
    return 0
