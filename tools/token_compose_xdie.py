#!/usr/bin/env python3
"""Token composition with inter-die terms, every term graded (TOKEN-COMPOSE, 2026-10-18).

  T_token = sum_l n_l * C_die(l)  +  sum_l n_l * sum_x max(0, E_meas(x) - O_meas(l, x))      tok/s = f_clk / T_token

C_die(l)  critical-die cycles of layer l without its inter-die exchanges.
E(x)      cycles of inter-die exchange x (producer's last-word issue -> consumer's first-word land), PHY/switch included.
O(l, x)   cycles the static schedule overlaps x with independent work, READ from the schedule the die run uses (never
          assumed): HBM = the S2 compiler schedule records (time a COLL record shares with any non-COLL unit record);
          S81 = the token-path DAG solve (critical / slack); Qwen ROM = the die run's op-fetch window partition.

Every term carries one grade, a source record and the commit that holds it:
  measured-current-RTL  measured on the die RTL of record (10-18: d4g GEN2, S81 p4l, Qwen dv2f14 + kvs14c)
  measured-old-RTL      measured in RTL, but on an older RTL revision or vehicle (10-08 field phases, 10-13/14 layer runs)
  modelled-PHY          off-chip legs: PHY analog, FEC, switch, cable, package trace (cited constants)
  priced                analytic price (pricer / ledger), no RTL measurement of this term

A mixed exchange (current-RTL transport + modelled off-chip + priced on-die COLL stages) is split into one part per
grade; the exposed cycles max(0, E - O) are shared over the parts in proportion to E.

Higher-grade records override base terms by slot (see README "Override records").  By default EVERY record is found
by discovery (no path list): results/rtl/*_layer_tput_*/** (TOKEN-PASS / LAYERBENCH / LB2), results/rtl/xdie_*/**
(TOKEN-XDIE) and any committed results/**/*.json with a "token_compose" block.  Records without a block are listed in
index.json records_seen and ignored.  An exchange override must carry O_meas read from the compiler schedule / record
(O + O_source, or O_ref {record, pointer}); one without it is rejected (listed) and the base term kept.
--pass-records / --xdie-records replace discovery with exactly the given files (what-ifs, tests).

  python3 tools/token_compose_xdie.py --list-records         # show the discovered records

  python3 tools/token_compose_xdie.py                        # compose all designs from the pinned inputs, write outputs
  python3 tools/token_compose_xdie.py --check                # recompute and compare with the committed outputs
  python3 tools/token_compose_xdie.py --page-data DIR        # also patch the token page data in DIR (banner per design)
"""
import argparse
import glob
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/arch/token_path_1018'
INP = OUT / 'inputs'
F_CLK = 1.2e9
GRADES = ('measured-current-RTL', 'measured-old-RTL', 'modelled-PHY', 'priced')
SCHEMA = 'opentallas.token_compose_xdie.v1'

# ---------------------------------------------------------------- inputs (path in repo, where it was committed)
INPUTS = {
    'ds_dag_ar': ('results/arch/token_path_20261009/ds_rom.json', 'main'),
    'ds_dag_mtp': ('results/arch/token_path_20261009/ds_rom_mtp.json', 'main'),
    's81_1013': ('results/rtl/s81_layer_tput_1013/record.json', 'main'),
    's81_p4l_layers': ('results/arch/token_path_1018/inputs/s81_layer_price_p4l.json',
                       'snapshot of claude/tokpass-s81-1018 36e5c2683:results/rtl/s81_layer_tput_1018/layer_price_p4l.json'),
    's81_p4l_price': ('results/arch/s81_dv_1016/p4l/price_land.json', 'main (S81-DIE7/PRICE ec38691d6)'),
    's81_scand': ('results/arch/s81_scand_1018/scand.json',
                  'claude/s81-scand-1018 (S81-SCAND: option D, measured 1-stack reader, keys over k = 3 TP4 stages)'),
    'q_1013': ('results/rtl/qwen_layer_tput_1013/record.json', 'main'),
    'q_1013_terms': ('results/rtl/qwen_layer_tput_1013/die_terms.json', 'main'),
    'q_tp8_coll': ('results/rtl/qwen_layer_tput_1013/native_tp8_collective/positive/record.json', 'main'),
    'hbm_price5': ('results/arch/hbm_d4g_price_1017/price5/summary.json', 'main'),
    'hds_sched': ('results/arch/token_path_1018/inputs/hbm_ds_priced_layers_all.json',
                  'ot-epyc5 run 10-18 of claude/tokpass-hbmds-1018 tools/hbm_layer_vehicle/priced_layers.py '
                  '--layers 0,1,2,3,8,14,20,24,28,32,36,head (hgi_sim d4g_price5_1018 e680e506, reproduces 629,775.1 cycles)'),
    'xdie_hbm': ('results/arch/token_path_1018/inputs/xdie_hbm_record.json',
                 'snapshot of claude/xdie-hbm-1018 38149e70b:results/rtl/xdie_hbm_1018/record.json'),
    'hq_price': ('results/arch/token_path_1018/inputs/hbm_qwen_price_per_layer.json',
                 'snapshot of claude/tokpass-hbmq-1018 f5c3d8ba9:results/rtl/hbm_qwen_layer_tput_1018/price_per_layer.json'),
    'hq_sched': ('results/arch/token_path_1018/inputs/hbm_qwen_static_schedule.json',
                 'snapshot of claude/tokpass-hbmq-1018 f5c3d8ba9:results/rtl/hbm_qwen_layer_tput_1018/static_schedule.json'),
}
_cache, _seen = {}, {}


def git(*a):
    try:
        return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ''


def load(key):
    if key not in _cache:
        path, origin = INPUTS[key]
        p = ROOT / path
        raw = p.read_bytes()
        _cache[key] = json.loads(raw)
        _seen[key] = dict(path=path, origin=origin, sha256=hashlib.sha256(raw).hexdigest()[:16],
                          commit=git('log', '-1', '--format=%h', '--', path) or 'uncommitted')
    return _cache[key]


def src(key, pointer, note=None):
    load(key)
    s = dict(record=INPUTS[key][0], pointer=pointer, commit=_seen[key]['commit'], origin=INPUTS[key][1])
    if note:
        s['note'] = note
    return s


# ---------------------------------------------------------------- terms
def term(slot, kind, n, cycles, grade, source, **kw):
    assert grade in GRADES, grade
    t = dict(slot=slot, kind=kind, n=n, cycles=round(cycles, 2), grade=grade, total=round(n * cycles, 2), source=source)
    t.update({k: v for k, v in kw.items() if v is not None})
    return t


def xdie(slot, n, parts, O, O_source, source, **kw):
    """parts: [(grade, E_part, note)]; exposed = max(0, E - O) shared over the parts in proportion to E."""
    E = sum(p[1] for p in parts)
    ex = max(0.0, E - O)
    out = []
    for g, e, note in parts:
        share = ex * (e / E) if E > 0 else 0.0
        out.append(term(slot, 'xdie', n, share, g, source, E=round(e, 2), E_total=round(E, 2), O=round(O, 2),
                        O_source=O_source, part=note, **kw))
    return out


def union_overlap(s, e, ivs):
    iv = sorted((max(s, a), min(e, b)) for a, b in ivs if min(e, b) > max(s, a))
    tot, cur = 0.0, None
    for a, b in iv:
        if cur is None or a > cur[1]:
            if cur:
                tot += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        tot += cur[1] - cur[0]
    return tot


# ---------------------------------------------------------------- DS ROM (S81 array)
GRADE_DAG = {'measured': 'measured-old-RTL', 'measured+vendor': 'modelled-PHY'}
SCAN_GROUP = 'S81.SCAN_STACKS_P4L'      # accepted-cost ledger group of the 1-stack scan correction


def ds_rom(wl):
    dag = load('ds_dag_ar' if wl == 'ar' else 'ds_dag_mtp')
    dk = 'ds_dag_ar' if wl == 'ar' else 'ds_dag_mtp'
    p4l = load('s81_p4l_layers')['workloads'][wl]['layers']
    rec = load('s81_p4l_price')['scenarios']['dv_base']['workloads'][wl]
    gk = {g['id']: g['kind'] for g in dag['groups']}

    def lkey(n):
        k = gk.get(n.get('group'))
        if k in ('head', 'embed', 'hops', 'draft', 'wave', 'accept'):
            return k
        L = n.get('layer')
        return f'L{L}' if isinstance(L, int) and L >= 0 else (k or 'other')

    die, terms, xd = {}, [], 0.0
    for n in dag['nodes']:
        L = lkey(n)
        g = GRADE_DAG.get((n.get('src') or {}).get('grade'), 'priced')
        if n.get('cls') in ('coll', 'hop'):
            crit = bool(n.get('critical'))
            E = float(n['cycles'])
            O = 0.0 if crit else E
            terms += xdie(f'{L}.xdie.{n["id"]}', 1, [(g, E, n.get('op'))], O,
                          'token-path DAG solve: critical (slack 0) -> O 0; off the critical path (slack %.1f) -> O = E'
                          % float(n.get('slack') or 0.0), src(dk, f'nodes[id={n["id"]}]', (n.get('src') or {}).get('record')),
                          layer=L, critical=crit, cls=n.get('cls'))
        elif n.get('critical'):
            die.setdefault(L, {}).setdefault(g, 0.0)
            die[L][g] += float(n['cycles'])
    old = load('s81_1013')['runs']['phier']['layers']
    ev = {o['layer']: dict(vehicle='tb_s81_die_layer (10-13/14 hub die control plane, NOT p4l)',
                           layer_path_measured=o['layer_path_hc_measured'], layer_path_at_price=o['layer_path_at_price'],
                           ratio=o['layer_ratio_hc'], record=INPUTS['s81_1013'][0] + ' runs.phier.layers',
                           behavioural=o['not_covered']) for o in old}
    for L, by in die.items():
        for g, c in sorted(by.items()):
            terms.append(term(f'{L}.die', 'layer', 1, c, g, src(dk, f'nodes[layer={L}, critical, cls not coll/hop]'),
                              layer=L, evidence=ev.get(L)))
    # current die (p4l, landed, half-cycle hops): per-layer DV deltas on the critical nodes (priced)
    dsum = 0.0
    for L, r in p4l.items():
        if r is None:
            continue
        d = r['dv_crit'] - r['hub_crit']
        if abs(d) > 1e-9:
            dsum += d
            terms.append(term(f'{L}.dv_p4l', 'layer', 1, d, 'priced',
                              src('s81_p4l_layers', f'workloads.{wl}.layers.{L}.dv_crit - hub_crit'), layer=L,
                              note='p4l DV die deltas (landing, half-cycle hops, pin registers) on the critical nodes'))
    mtp = wl == 'mtp'
    tau = dag['totals'].get('tau') if mtp else None
    T_rec = F_CLK / rec['dv_tok_s'] * (tau if mtp else 1.0)
    rest = T_rec - sum(t['total'] for t in terms)
    terms.append(term('price_of_record_residual', 'adjust', 1, rest, 'priced',
                      src('s81_p4l_price', f'scenarios.dv_base.workloads.{wl}.dv_tok_s = hop_only x (1 - (ledger_kept + dv_dag_loss)/100)'),
                      note='hop-only basis + accepted-cost ledger rows + DAG re-solve: the part of the S81 price of record '
                           'that is not a per-node term'))
    # MU.S81.SCANCHK (10-18): the DAG's idx.score nodes and so the price of record charge the 10-04 reader on FOUR
    # HBM3E stacks a rank die; p4l has ONE (plan.json: one phy block, NPC 32).  Charge the 1-stack scan here until
    # dv_price carries the ledger row (then price_land.json lists the group and the residual already holds it).
    # S81-SCAND (10-18, coordinator 0iq: option D adopted): the full-scan layers' keys are spread over k = 3 adjacent
    # TP4 stages; the reader term is the MEASURED 1-stack reader at the per-die key count (scand.json, measured-old-RTL:
    # the W11 reader is not bound on p4l), the q fan-out legs + wider final merge are priced; re-index gathers keep the
    # SCANCHK 1-stack price.  Charged here until dv_price carries the ledger row (then the residual already holds it).
    sd = load('s81_scand')
    led_rows = {r['group'] for r in load('s81_p4l_price')['scenarios']['dv_base'].get('ledger_rows', [])}
    sc_add = 0.0
    if SCAN_GROUP not in led_rows:
        k = str(sd['adopted_k'])
        st = sd['by_k'][k]
        for L, d in st['idx_score_delta_cycles'].items():
            pl = st['per_layer'].get(L)
            parts = ([('measured-old-RTL', pl['reader_1stack'] - pl['reader_4stack_basis'], 'reader'),
                      ('priced', pl['legs_and_merge'], 'legs_merge')] if pl else [('priced', d, 'reindex')])
            for g, c, nm in parts:
                if abs(c) > 1e-9:
                    terms.append(term(f'{L}.scan_d_{nm}', 'layer', 1, c, g,
                                      src('s81_scand', f'by_k.{k}.per_layer.{L}' if pl else f'by_k.{k}.idx_score_delta_cycles.{L}'),
                                      layer=L, note='option D k=%s: index scan at 1 HBM stack a p4l die, keys over %d dies (%s)'
                                      % (k, st['dies'], nm)))
                    sc_add += c
        wave = st['dag_1009'][wl]['added_cycles'] - sum(st['idx_score_delta_cycles'].values())
        if abs(wave) > 1e-9:
            terms.append(term('wave.scan_d', 'layer', 1, wave, 'priced', src('s81_scand', f'by_k.{k}.dag_1009.{wl}'),
                              layer='wave', note='MTP wavefront: the slowest verify stage after option D, +delta per position'))
            sc_add += wave
    T_por = T_rec + sc_add
    por = dict(tok_s=round(F_CLK * (tau if mtp else 1.0) / T_por, 1), cycles=round(T_por, 1),
               source=INPUTS['s81_p4l_price'][0] + f' dv_base.{wl}' + (' + S81-SCAND option D 1-stack scan (ledger %s, '
                                                                     'not yet in dv_price)' % SCAN_GROUP if sc_add else ''))
    if sc_add:
        por.update(uncorrected_tok_s=rec['dv_tok_s'], scan_stacks_correction_cycles=round(sc_add, 1))
    return dict(terms=terms, tau=tau, price_of_record=por,
                title='DeepSeek-V4.1 ROM, S81 array (p4l DV die), 1M context, ' + ('MTP (DSpark, tau %.3f)' % tau if mtp else 'AR'),
                o_rule='O from the token-path DAG solve (critical / slack); no S81 die-run compiler schedule exists yet (TOKEN-PASS-S81 BLOCKED)')


# ---------------------------------------------------------------- Qwen ROM (TP8 compute dies + KV die + D2D)
def qwen_rom():
    r, dt = load('q_1013'), load('q_1013_terms')
    cls = {c['cls']: c for c in r['classes']}
    win = {w['op']: w for w in r['windows']}
    kv = r['unmeasured_per_layer']['kv_die_attention']
    qc = dt['terms']['issue_plus_die']
    still = dt['composed_production_layer']['still_priced']
    vmx = {i['item']: i for i in r['end_to_end']['items']}['VM bit-plane x read + 10 edges (latency probe)']
    tp8 = load('q_tp8_coll')
    tp8c = {c['name']: c['cycles'] for c in tp8['cases']}
    terms = []
    win_src = lambda p: src('q_1013', p)
    xd_on = (cls['link']['measured'])           # attn_tail (all-reduce #1 beats) + allreduce2 windows
    for L, n, veh, st, vx in (('L0', 1, r['layer']['all_layers']['L0']['measured'], qc['l0']['delta'], vmx['l0']),
                              ('Lc', 35, r['layer']['all_layers']['L1']['measured'], qc['measured_delta'], vmx['per_layer'])):
        att = cls['attention']['measured']
        on = veh - att - xd_on
        terms.append(term(f'{L}.die.vehicle', 'layer', n, on, 'measured-old-RTL',
                          win_src(f'layer.all_layers.{"L0" if L == "L0" else "L1"}.measured - classes[attention,link].measured'),
                          layer=L, die='compute', note='TP4 cycle-reference core (bd6e82288+30b6440b5), su/me windows + lead;'
                          ' NOT the hardened qfd_* tiles / dv2f14 die' + (' (L0 windows not broken out: chained-layer attention'
                                                                         ' and link windows subtracted)' if L == 'L0' else '')))
        terms.append(term(f'{L}.die.stations', 'layer', n, st, 'measured-old-RTL',
                          src('q_1013_terms', 'terms.issue_plus_die.' + ('l0.delta' if L == 'L0' else 'measured_delta')),
                          layer=L, die='compute', note='qC run: r22k issue relays + r21 die relay stages at the priced counts'))
        terms.append(term(f'{L}.die.vm_xread', 'layer', n, vx, 'measured-old-RTL',
                          win_src('end_to_end.items[VM bit-plane x read].' + ('l0' if L == 'L0' else 'per_layer')), layer=L, die='compute'))
        terms.append(term(f'{L}.die.kv_attention', 'layer', n, kv['service_cycles_T8192'], 'measured-old-RTL',
                          win_src('unmeasured_per_layer.kv_die_attention.service_cycles_T8192'), layer=L, die='KV',
                          note=f'KV-die static w16 attention service, {kv["record"]} @{kv["source"]} (static_kv RTL, not kvs14c)'))
        terms.append(term(f'{L}.die.still_priced', 'layer', n, still, 'priced',
                          src('q_1013_terms', 'composed_production_layer.still_priced'), layer=L, die='compute',
                          note=dt['composed_production_layer']['still_priced_items']))
        terms += xdie(f'{L}.xdie.d2d_attention', n, [('measured-old-RTL', kv['link_cycles'], 'compute <-> KV die D2D link stages')],
                      0.0, 'die run window partition: attention is serial on the controller (allreduce1 window = END-b barrier '
                      'waiting on the posted attention) -> O 0', win_src('unmeasured_per_layer.kv_die_attention.link_cycles'), layer=L)
        terms += xdie(f'{L}.xdie.tp_allreduce', n, [('measured-old-RTL', win['attn_tail']['measured'], 'all-reduce #1 (in attn_tail window)'),
                                                    ('measured-old-RTL', win['allreduce2']['measured'], 'all-reduce #2')],
                      0.0, 'die run op-fetch windows holding "link": the controller is stalled on the collective for the whole '
                      'window (ME work inside it is the posted write-back of the same layer) -> O 0',
                      win_src('windows[attn_tail, allreduce2].measured'), layer=L,
                      evidence=dict(tp8_unit_bench_2x256w=tp8c.get('qwen_layer_2x256w'), record=INPUTS['q_tp8_coll'][0],
                                    note='TP8 collective unit bench (8 ranks, 2 all-reduces) 862 cycles vs the TP4 vehicle windows; '
                                         'not substituted: no TP8 layer vehicle'))
    h = r['head']
    terms.append(term('head.die', 'layer', 1, h['measured'], 'measured-old-RTL', win_src('head.measured'), layer='head',
                      note='LM head + argmax on the stationed TP4 core (argmax collective inside)'))
    terms += xdie('embed.xdie.kv_embedding', 1, [('priced', 272.0, 'embedding row fetched through the KV die')], 0.0,
                  'serial (token start)', win_src('unmeasured_per_layer.embed'), layer='embed')
    base = r['end_to_end']
    return dict(terms=terms, tau=None, price_of_record=dict(tok_s=base['tok_s_price'], cycles=base['base_cycles'],
                                                            source=INPUTS['q_1013'][0] + ' end_to_end.base_cycles (6,835-cycle production layer)'),
                title='Qwen3-8B ROM (compute dies + KV die + D2D), 8K context, AR',
                o_rule='O from the 10-13 die run op-fetch window partition (TP4 reference vehicle); no dv2f14+kvs14c co-sim yet')


# ---------------------------------------------------------------- HBM d4g (DeepSeek and Qwen)
DS_ROWS = [  # schedule tag regex -> xdie_hbm row (train = the records of one layer that form one row instance)
    (r'^x_projections_gather\.', None),          # resolved per layer by record count / layer (below)
    (r'^o-group tree reduce', 'o-group reduce-mcast (8 contributors)'),
    (r'^(attn_out_gather\.y|ffn_out_gather\.yf)$', 'attn_out y / ffn_out yf'),
    (r'^router_gather\.gsc$', 'router gsc'),
    (r'^expert_intermediate_gather\.', 'MoE expert_intermediate s0..s6 7-record train (dispatch/combine)'),
    (r'^indexer\.q_gather\.iq$', 'indexer q iq'),
    (r'^96 x 512 index merge$', '96x512 index TOPK_MERGE'),
    (r'^argmax merge$', 'argmax / LM head'),
]
SINGLE = {'attn_out y / ffn_out yf'}               # each record is one instance


def _xproj_row(L, k):
    if k == 2:
        return 'x_proj qa+kvraw 2-record train'
    if L == 20:
        return 'x_proj 4-record train L20'
    return 'x_proj 3-record train L24-36' if k == 3 else 'x_proj 4-record train L2/8/14'


def _offchip(model, k, row):
    # off-chip legs inside E_link (xdie_hbm record 'modelled'): DS switch 250 + cable 27.6 ns = 333 cycles a crossing;
    # Qwen in-package trace 4 words a crossing (hypercube: 6 dependent crossings)
    if model == 'DS':
        return 333.0 * k
    return 4.0 * (6 if 'hypercube' in row['collective'] else k)


def _split(row, model):
    k = row.get('crossings') or 6
    el = row.get('E_link_meas_cycles')
    trans = k * el if el is not None else sum(row['E_link_steps'])
    off = _offchip(model, k, row)
    return [('measured-current-RTL', trans - off, 'COLL rail + relays + hfd_ep_static + ot_pdie_serdes (GEN2 7c124deae), '
             + row['grade'].split(' transport')[0]),
            ('modelled-PHY', off, 'switch + cable' if model == 'DS' else 'in-package trace'),
            ('priced', row['C_on_die'], 'on-die COLL stages (VM rd/wr, COLL_VM, ring, quadrant adder)')]


def _sched_layer(recs, Lkey, rows_by_name, model, layer_label, n, tag_src):
    """C_die + xdie terms of one scheduled layer (records of one segment)."""
    other = [(x['start'], x['end']) for x in recs if x['unit'] != 'COLL']
    coll = [x for x in recs if x['unit'] == 'COLL']
    groups = {}
    xp = [x for x in coll if x['tag'].startswith('x_projections_gather.')]
    for x in coll:
        name = None
        for rx, nm in DS_ROWS if model == 'DS' else ((r'^all_reduce_(o|down)$', 'Q_AR'), (r'^argmax_merge$', 'argmax / LM head')):
            if re.search(rx, x['tag']):
                name = nm or _xproj_row(int(layer_label[1:]) if layer_label[1:].isdigit() else -1, len(xp))
                break
        key = (name or 'priced:' + x['tag']) + (('#' + x['tag']) if name in SINGLE or name == 'Q_AR' or name is None else '')
        groups.setdefault(key, (name, []))[1].append(x)
    terms, xd_priced = [], 0.0
    for key, (name, xs) in groups.items():
        Ep = sum(max(0.0, x['end'] - x['start']) for x in xs)
        O = sum(union_overlap(x['start'], x['end'], other) for x in xs)
        xd_priced += max(0.0, Ep - O)
        slot = f'{layer_label}.xdie.{key}'
        Osrc = 'S2 compiler schedule: cycles the COLL record(s) share with any non-COLL unit record of the layer'
        row = rows_by_name.get(name) if name else None
        if row is None:
            terms += xdie(slot, n, [('priced', Ep, 'no transport measurement for this exchange (' + ', '.join(sorted({x['op'] for x in xs})) + ')')],
                          O, Osrc, tag_src, layer=layer_label, E_priced=round(Ep, 2))
        else:
            terms += xdie(slot, n, _split(row, model), O, Osrc,
                          src('xdie_hbm', f'rows[collective={row["collective"]}]'), layer=layer_label, E_priced=round(Ep, 2),
                          schedule_records=[x['tag'] for x in xs])
    return terms, xd_priced


def hbm_ds(wl):
    if wl == 'mtp':
        p5 = load('hbm_price5')['rows']['d4g_2ring_qbg']
        return dict(terms=[term('mtp_step.priced', 'adjust', 1, F_CLK / p5['ds_mtp_tok_s'], 'priced',
                                src('hbm_price5', 'rows.d4g_2ring_qbg.ds_mtp_tok_s'),
                                note='owner 10-16/18: HBM MTP parked (recorded, not blocking); no per-layer MTP schedule')],
                    tau=None, per_accepted=True, price_of_record=dict(tok_s=p5['ds_mtp_tok_s'], cycles=round(F_CLK / p5['ds_mtp_tok_s'], 1),
                                                                     source=INPUTS['hbm_price5'][0]),
                    title='HBM d4g GEN2 die, DeepSeek-V4.1, 1M context, MTP (priced only)', o_rule='n/a (priced only)')
    S = load('hds_sched')
    segs, per = S['segments'], S['per_segment']
    rows = {r['collective']: r for r in load('xdie_hbm')['rows'] if r['model'] == 'DS'}
    by_cyc = {}
    for k, s in segs.items():
        by_cyc.setdefault(round(s['cycles'], 1), k)
    terms, pre = [], S['ar_cycles'] - sum(per.values())
    for L, cyc in per.items():
        rep = L if L in segs else by_cyc.get(round(cyc, 1))
        if rep is None:
            raise SystemExit(f'hbm_ds: layer {L} ({cyc}) has no exported schedule with the same cycles; rerun priced_layers.py with it')
        label = 'head' if L == 'head' else f'L{L}'
        ts, xp = _sched_layer(segs[rep]['records'], L, rows, 'DS', label, 1,
                              src('hds_sched', f'segments.{rep}.records[unit=COLL]'))
        terms.append(term(f'{label}.die', 'layer', 1, cyc - xp, 'priced', src('hds_sched', f'per_segment.{L} - exposed COLL (segments.{rep})'),
                          layer=label, note='d4g price of record layer segment (unit benches exist, no layer RTL run yet)',
                          schedule_from=f'segment {rep}' + ('' if rep == L else ' (identical cycles)')))
        terms += ts
    if abs(pre) > 0.05:
        terms.append(term('preamble', 'layer', 1, pre, 'priced', src('hds_sched', 'ar_cycles - sum(per_segment)')))
    return dict(terms=terms, tau=None, price_of_record=dict(tok_s=S['ar_tok_s'], cycles=S['ar_cycles'], source=INPUTS['hds_sched'][0]),
                title='HBM d4g GEN2 die, DeepSeek-V4.1 (TP96 x quadrants), 1M context, AR',
                o_rule='O from the S2 compiler schedule of record (priced_layers.py: the HBMDS vehicle\'s schedule contract)')


def hbm_qwen():
    P = load('hq_price')['results']['base']['record']['token']
    Sd = load('hq_sched')['schedule']['base']['record']
    rows = {('Q_AR' if r['kind'] == 'ALL_REDUCE_SUM' else r['collective']): r for r in load('xdie_hbm')['rows']
            if r['model'] == 'Qwen' and (r['kind'] != 'ALL_REDUCE_SUM' or 'hypercube' in r['collective'])}
    terms = []
    lay = {s['L']: s['cycles'] for s in P['segments']}
    for L, cyc in lay.items():
        if L == 'head':
            recs, label = Sd['head'], 'head'
        elif L == 0:
            recs, label = Sd['L0'], 'L0'
        else:
            recs, label = [x for x in Sd['chain'] if x['L'] == 1], f'L{L}'
        ts, xp = _sched_layer(recs, L, rows, 'Qwen', label, 1, src('hq_sched', f'schedule.base.record.{"head" if L == "head" else ("L0" if L == 0 else "chain[L=1]")}'))
        terms.append(term(f'{label}.die', 'layer', 1, cyc - xp, 'priced', src('hq_price', f'results.base.record.token.segments[L={L}] - exposed COLL'),
                          layer=label, note='d4g price of record (TP-4 r25 programme under the TP-8 split transform)'))
        terms += ts
    pre = P['token_cycles'] - sum(lay.values())
    terms.append(term('preamble', 'layer', 1, pre, 'priced', src('hq_price', 'results.base.record.token.preamble_end')))
    return dict(terms=terms, tau=None, price_of_record=dict(tok_s=P['tok_s'], cycles=P['token_cycles'], source=INPUTS['hq_price'][0] + ' base.record'),
                title='HBM d4g GEN2 die, Qwen3-8B (TP8, 8 dies in package), 8K context, AR',
                o_rule='O from the S2 compiler schedule (static_schedule.json base.record); AR = realisable hypercube form (5 die links)',
                evidence=dict(d4g8_native_landed_tok_s=load('hq_price')['summary'].get('landed.d4g8', {}).get('tok_s'),
                              note='TOKEN-PASS-HBMQ proposes re-basing on the compiled D4G8 programme (coordinator decision)'))


# ---------------------------------------------------------------- record discovery (ROOT-TOKTOOL 10-18)
# Every TOKEN-PASS / LAYERBENCH / LB2 (per-layer layer-bench) record and every TOKEN-XDIE record is found by discovery,
# never by a hand-kept path list:
#   (1) the record families on disk, at any depth: results/rtl/*_layer_tput_*/**/*.json (TOKEN-PASS, LAYERBENCH, LB2 write
#       their records there) and results/rtl/xdie_*/**/*.json (TOKEN-XDIE, incl. xdie_qwen_1018/pair_r1);
#   (2) every committed results/**/*.json that carries a "token_compose" block (git grep), wherever a lane put it.
# A family's top-level record.json is always listed in records_seen (used false when it has no block yet); a deeper file
# is listed only when it carries a block (the 75 xdie_qtp8 case records, fixtures, calendars ... are not records of the
# composition).
FAMILIES = {'pass': 'results/rtl/*_layer_tput_*', 'xdie': 'results/rtl/xdie_*'}
TC_KEY = b'"token_compose"'


def _has_block(p):
    try:
        raw = Path(p).read_bytes()
        return TC_KEY in raw and bool(json.loads(raw).get('token_compose'))
    except Exception:
        return False


def _family(rel):
    for f, pat in FAMILIES.items():
        if re.match(pat.replace('*', '[^/]*') + '/', rel):
            return f
    return 'other'


def discover_records(root=None):
    """-> sorted list of (repo-relative path, family); see the block comment above."""
    root = Path(root or ROOT)
    found = {}
    for fam, pat in FAMILIES.items():
        for d in sorted(glob.glob(str(root / pat))):
            top = Path(d) / 'record.json'
            if top.is_file():
                found[str(top.relative_to(root))] = fam
            for q in sorted(glob.glob(str(Path(d) / '**' / '*.json'), recursive=True)):
                rel = str(Path(q).relative_to(root))
                if rel not in found and _has_block(q):
                    found[rel] = fam
    try:
        out = subprocess.run(['git', '-C', str(root), 'grep', '-l', '-F', '"token_compose"', '--', 'results/*.json'],
                             capture_output=True, text=True).stdout.split()
    except Exception:
        out = []
    for rel in out:
        if rel not in found and (root / rel).is_file() and _has_block(root / rel):
            found[rel] = _family(rel)
    return sorted(found.items())


def missing_records(root=None):
    """Tracked record-family json files that are NOT on disk (sparse worktree: skip-worktree 'S', or deleted).
    Discovery reads the working tree, so a sparse checkout without e.g. results/rtl/xdie_qwen_1018 silently drops the
    pair_r2 override and recomputes Qwen ROM AR 4,767.1 instead of 4,766.5 (MU-S81-2/CHK 10-19).  Callers refuse."""
    root = Path(root or ROOT)
    try:
        ls = subprocess.run(['git', '-C', str(root), 'ls-files', '-t', '--', *[p + '/*.json' for p in FAMILIES.values()]],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    except Exception:
        return []
    return sorted(rel for tag, rel in (l.split(' ', 1) for l in ls if ' ' in l)
                  if tag == 'S' or not (root / rel).is_file())


def default_xdie_records():
    """compatibility: the discovered TOKEN-XDIE records (absolute paths)"""
    return [str(ROOT / r) for r, f in discover_records() if f == 'xdie']


# ---------------------------------------------------------------- overrides from higher-grade records
def _resolve(doc, pointer):
    cur = doc
    for k in pointer.split('.'):
        cur = cur[int(k)] if isinstance(cur, list) else cur[k]
    return cur


def _o_meas(o, rec_path, rec_doc):
    """O of an exchange override: from the record itself (O + O_source naming the compiler schedule / calendar it was read
    from) or from O_ref {record?, pointer} into a schedule/record file. Never assumed: no O or no O_source -> None."""
    ref = o.get('O_ref')
    if ref:
        tgt = rec_doc
        if ref.get('record'):
            rp = Path(ref['record'])
            rp = rp if rp.is_absolute() else ((ROOT / rp) if (ROOT / rp).exists() else Path(rec_path).parent / rp)
            tgt = json.loads(rp.read_text())
        v = _resolve(tgt, ref['pointer'])
        src_txt = o.get('O_source') or f'{ref.get("record", "this record")}:{ref["pointer"]}'
        return float(v), src_txt
    if isinstance(o.get('O'), (int, float)) and str(o.get('O_source') or '').strip():
        return float(o['O']), o['O_source']
    return None


def overrides(paths):
    seen, ov = [], []
    for p in paths:
        p = Path(p)
        rel = str(p.resolve().relative_to(ROOT)) if p.resolve().is_relative_to(ROOT) else str(p)
        try:
            d = json.loads(p.read_text())
        except Exception as e:
            seen.append(dict(record=rel, family=_family(rel), used=False, why=f'unreadable: {e}'))
            continue
        tc = d.get('token_compose') if isinstance(d, dict) else None
        ent = dict(record=rel, family=_family(rel), used=bool(tc and tc.get('terms')), n_terms=len((tc or {}).get('terms', [])),
                   why=None if tc and tc.get('terms') else ((tc or {}).get('note') or 'no token_compose block (record not yet in the override format)'),
                   rejected=[])
        commit = git('log', '-1', '--format=%h', '--', str(p)) or 'uncommitted'
        for i, o in enumerate((tc or {}).get('terms', [])):
            o = dict(o, _record=rel, _commit=commit, _i=i)
            if 'E' in o:
                try:
                    om = _o_meas(o, p, d)
                except Exception as e:
                    om, o['_why'] = None, f'O_ref unresolved: {e}'
                if om is None:
                    ent['rejected'].append(dict(i=i, slot=o.get('slot', o.get('slot_re')), why=o.get('_why') or
                                                'exchange override without O_meas (O + O_source from the compiler schedule, '
                                                'or O_ref): O is never assumed; base term kept'))
                    continue
                o['O'], o['O_source'] = om
            ov.append(o)
        if not ent['rejected']:
            ent.pop('rejected')
        elif not any(x['_record'] == rel for x in ov):
            ent['used'] = False
        seen.append(ent)
    return seen, ov


def apply_overrides(design, wl, terms, ov):
    used, owner = [], {}
    for o in ov:
        if o.get('design') != design or o.get('workload', wl) not in (wl, '*'):
            continue
        rx = re.compile(o['slot_re']) if 'slot_re' in o else None
        hit = [t for t in terms if (rx.search(t['slot']) if rx else t['slot'] == o['slot'])]
        slots = sorted({t['slot'] for t in hit}) or ([o['slot']] if 'slot' in o else [])
        terms[:] = [t for t in terms if t['slot'] not in slots]
        s = dict(record=o['_record'], pointer=o.get('pointer', ''), commit=o['_commit'], origin='override')
        for slot in slots:
            n = o.get('n', next((t['n'] for t in hit if t['slot'] == slot), 1))
            if 'E' in o:
                terms += xdie(slot, n, [(p['grade'], p['E'], p.get('note', '')) for p in o['E']], o['O'], o['O_source'], s)
            else:
                terms.append(term(slot, o.get('kind', 'layer'), n, o['cycles'], o['grade'], s, note=o.get('note')))
        conflicts = sorted({owner[sl] for sl in slots if sl in owner and owner[sl] != o['_record']})
        for sl in slots:
            owner[sl] = o['_record']
        used.append(dict(slots=slots, record=o['_record'], **({'replaces_override_from': conflicts} if conflicts else {})))
    return used


# ---------------------------------------------------------------- compose
DESIGNS = {  # page id -> (builder, workloads)
    'ds_rom': (ds_rom, ('ar', 'mtp')),
    'qwen_rom': (lambda wl: qwen_rom() if wl == 'ar' else None, ('ar', 'mtp')),
    'hbm_gen_ds': (hbm_ds, ('ar', 'mtp')),
    'hbm_gen_qwen': (lambda wl: hbm_qwen() if wl == 'ar' else None, ('ar', 'mtp')),
}
NO_MTP = {'qwen_rom': 'AR only (owner 2026-10-05 AR_MODE: DSpark measured below AR on the compute-balanced ROM)',
          'hbm_gen_qwen': 'not priced on d4g: owner 10-16/18 HBM MTP parked (recorded, not blocking)'}


def compose(design, wl, ov):
    b = DESIGNS[design][0](wl)
    if b is None:
        return dict(design=design, workload=wl, available=False, reason=NO_MTP.get(design, 'no workload'))
    terms = b['terms']
    used = apply_overrides(design, wl, terms, ov)
    T = sum(t['total'] for t in terms)
    by = {g: round(sum(t['total'] for t in terms if t['grade'] == g), 1) for g in GRADES}
    kinds = {k: round(sum(t['total'] for t in terms if t['kind'] == k), 1) for k in ('layer', 'xdie', 'adjust')}
    tau = b.get('tau')
    per_acc = T / tau if tau else T
    tok_s = F_CLK / per_acc
    cur = by['measured-current-RTL'] / T if T else 0.0
    old = by['measured-old-RTL'] / T if T else 0.0
    banner = (f'{100 * cur:.1f}% of token cycles measured on current RTL'
              f' ({100 * old:.1f}% on older RTL, {100 * by["modelled-PHY"] / T:.1f}% modelled PHY, {100 * by["priced"] / T:.1f}% priced)')
    xd = [t for t in terms if t['kind'] == 'xdie']
    xsum = {}
    for t in xd:
        k = re.sub(r'^(L\d+|Lc|head|embed|hops|draft|wave|accept)\.xdie\.', '', t['slot'])
        k = re.sub(r'#.*$', '', re.sub(r'^L\d+\.', '', k))
        k = re.sub(r'^(L\d+|head)\.', '', k)
        a = xsum.setdefault(k, dict(exposed=0.0, by_grade={}))
        a['exposed'] += t['total']
        a['by_grade'][t['grade']] = round(a['by_grade'].get(t['grade'], 0.0) + t['total'], 1)
    for a in xsum.values():
        a['exposed'] = round(a['exposed'], 1)
    lay = {}
    for t in terms:
        L = t.get('layer', t['slot'].split('.')[0])
        a = lay.setdefault(L, dict(n=t['n'], die=0.0, xdie=0.0, by_grade={}))
        a['die' if t['kind'] != 'xdie' else 'xdie'] += t['cycles']
        a['by_grade'][t['grade']] = round(a['by_grade'].get(t['grade'], 0.0) + t['cycles'], 1)
    for a in lay.values():
        a['die'], a['xdie'] = round(a['die'], 1), round(a['xdie'], 1)
    por = b['price_of_record']
    # the same terms with every exchange at its priced E (where the schedule gives one): must give the price of record
    at_price, done = sum(t['total'] for t in terms if t['kind'] != 'xdie'), set()
    for t in terms:
        if t['kind'] == 'xdie' and t['slot'] not in done:
            done.add(t['slot'])
            at_price += t['n'] * max(0.0, t.get('E_priced', t['E_total']) - t['O'])
    return dict(design=design, workload=wl, available=True, title=b['title'], clock_hz=F_CLK,
                T_token_cycles=round(T, 1), tau=tau, per_accepted_cycles=round(per_acc, 1), tok_s=round(tok_s, 1),
                price_of_record=por, vs_price_pct=round(100 * (tok_s / por['tok_s'] - 1), 2),
                T_at_price_cycles=round(at_price, 1),
                pct_measured_current_rtl=round(100 * cur, 2), banner=banner, by_grade=by,
                by_grade_share={g: round(v / T, 4) for g, v in by.items()}, by_kind=kinds, o_rule=b['o_rule'],
                xdie_summary=dict(sorted(xsum.items(), key=lambda kv: -kv[1]['exposed'])),
                layers=lay, overrides_used=used, evidence=b.get('evidence'), terms=terms)


# ---------------------------------------------------------------- multi-user (MU-S81, owner MU.DECIDE option A, 10-18)
MU_CAL = ROOT / 'results/arch/mu_s81_1018'


def multi_user_ds(wls):
    """S81 multi-user pricing: the latency user keeps the composed single-user rate (shift lemma, asserted by the
    calendar's brute-force check); the other users run the same schedule shifted by whole slots, so aggregate =
    users x composed per-user rate (+ AR fillers inside the MTP calendar at f_clk / step).  The user count is the
    compiled calendar's (tools/s81_dv/dv_mu_calendar.py: integer windows, A/B copy colouring, 0 collisions), not
    floor(T / II).  Grades: per-user = this composition's; users = modelled calendar (MU.TOK measures it)."""
    mu = {}
    for wl in ('ar', 'mtp'):
        f = MU_CAL / f'calendar_{wl}.json'
        w = wls.get(wl)
        if not f.exists() or not w or not w.get('available'):
            continue
        cal = json.loads(f.read_text())
        if cal['lemma']['brute_force']['result'] != 'PASS':
            mu[wl] = dict(available=False, reason=f'calendar lemma {cal["lemma"]["brute_force"]["result"]}')
            continue
        per = w['tok_s']
        fill = cal.get('fillers', 0) * (per / w['tau'] if wl == 'mtp' and w.get('tau') else 0.0)
        mu[wl] = dict(available=True, users=cal['users'], fillers=cal.get('fillers', 0), per_user_tok_s=round(per, 1),
                      aggregate_tok_s=round(cal['users'] * per + fill), slot_cycles=cal['slot'],
                      period_cycles=cal['period'], dies=cal['config']['dies'], stacks=cal['config']['stacks'],
                      total_mm2=cal['config']['total_mm2'], model_users=cal['config']['model_users'],
                      calendar_per_user_tok_s=cal['per_user_tok_s'],
                      record=str(f.relative_to(ROOT)), grade='per-user: this composition; users: modelled calendar')
    return mu


def run(pass_records=None, xdie_records=None):
    """records: None -> discovery (every TOKEN-PASS / LB2 / XDIE record); lists -> exactly those (tests, what-ifs)"""
    if pass_records is None and xdie_records is None:
        paths = [str(ROOT / r) for r, _ in discover_records()]
    else:
        paths = list(pass_records or []) + list(xdie_records or [])
    seen, ov = overrides(paths)
    out = {}
    for d, (_, wls) in DESIGNS.items():
        out[d] = {wl: compose(d, wl, ov) for wl in wls}
    return out, seen


def write(out, seen, page_dirs):
    OUT.mkdir(parents=True, exist_ok=True)
    head = git('rev-parse', '--short', 'HEAD')
    idx = dict(schema=SCHEMA + '.index', generated_from=head, tool='tools/token_compose_xdie.py', clock_hz=F_CLK,
               formula='T_token = sum_l n_l C_die(l) + sum_l n_l sum_x max(0, E_meas(x) - O_meas(l,x)); tok/s = f_clk / T '
                       '(MTP: per accepted token = step / tau)',
               grades=list(GRADES), inputs=_seen, records_seen=seen, designs={})
    for d, wls in out.items():
        doc = dict(schema=SCHEMA, design=d, workloads=wls)
        if d == 'ds_rom':
            doc['multi_user'] = multi_user_ds(wls)
            idx.setdefault('multi_user', {})[d] = doc['multi_user']
        (OUT / f'{d}.json').write_text(json.dumps(doc, indent=1) + '\n')
        idx['designs'][d] = {wl: ({k: w[k] for k in ('title', 'tok_s', 'T_token_cycles', 'per_accepted_cycles', 'tau',
                                                         'pct_measured_current_rtl', 'banner', 'by_grade', 'price_of_record',
                                                         'vs_price_pct')} if w['available'] else dict(available=False, reason=w['reason']))
                             for wl, w in wls.items()}
    (OUT / 'index.json').write_text(json.dumps(idx, indent=1) + '\n')
    for pd in page_dirs:
        patch_page(Path(pd), out)
    return idx


def page_block(w, d):
    if not w['available']:
        return dict(available=False, reason=w['reason'])
    return dict(available=True, banner=w['banner'], pct_measured_current_rtl=w['pct_measured_current_rtl'], tok_s=w['tok_s'],
                T_token_cycles=w['T_token_cycles'], per_accepted_cycles=w['per_accepted_cycles'], tau=w['tau'],
                by_grade=w['by_grade'], by_kind=w['by_kind'], price_of_record=w['price_of_record'], vs_price_pct=w['vs_price_pct'],
                o_rule=w['o_rule'], title=w['title'],
                xdie_top=[dict(x=k, **v) for k, v in list(w['xdie_summary'].items())[:8]],
                record=f'results/arch/token_path_1018/{d}.json', tool='tools/token_compose_xdie.py')


def patch_page(pd, out):
    """Add composition_1018 (banner + graded totals) to each design's page data and to index.json; nothing else changes."""
    ix = json.loads((pd / 'index.json').read_text())
    for e in ix['designs']:
        d = e['design']
        if d not in out:
            continue
        e['composition_1018'] = {wl: page_block(w, d) for wl, w in out[d].items()}
        files = [(e['file'], 'ar')] + ([(e['mtp']['file'], 'mtp')] if e.get('mtp', {}).get('available') and e['mtp'].get('file') else [])
        for f, wl in files:
            p = pd / f
            doc = json.loads(p.read_text())
            doc['composition_1018'] = page_block(out[d][wl], d)
            p.write_text(json.dumps(doc, separators=(',', ':')) + '\n')
    (pd / 'index.json').write_text(json.dumps(ix, indent=1) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pass-records', nargs='*', default=None, help='replace discovery with exactly these TOKEN-PASS records '
                    '(default: discovery, see discover_records)')
    ap.add_argument('--xdie-records', nargs='*', default=None, help='replace discovery with exactly these TOKEN-XDIE records')
    ap.add_argument('--list-records', action='store_true', help='print the discovered records and exit')
    ap.add_argument('--page-data', nargs='*', default=[], help='token page data dirs to patch (banner per design)')
    ap.add_argument('--check', action='store_true', help='recompute; fail if it differs from the committed outputs')
    a = ap.parse_args()
    if a.list_records:
        for r, f in discover_records():
            print(f'{f:5s} {"BLOCK" if _has_block(ROOT / r) else "-    "} {r}')
        return
    explicit = a.pass_records is not None or a.xdie_records is not None
    pr, xr = (a.pass_records, a.xdie_records) if explicit else (None, None)
    miss = [] if explicit else missing_records()
    if miss:
        dirs = sorted({'/'.join(m.split('/')[:3]) for m in miss})
        print(f'INCOMPLETE: {len(miss)} tracked record files are not on disk (sparse worktree?); discovery would drop '
              f'their overrides. Check out: {" ".join(dirs)}')
        sys.exit(2)
    out, seen = run(pr, xr)
    if a.check:
        bad = 0
        for d, wls in out.items():
            ref = json.loads((OUT / f'{d}.json').read_text())['workloads']
            for wl, w in wls.items():
                if w.get('tok_s') != ref[wl].get('tok_s') or w.get('by_grade') != ref[wl].get('by_grade'):
                    print(f'DIFF {d} {wl}: {w.get("tok_s")} vs committed {ref[wl].get("tok_s")}')
                    bad += 1
        print('CHECK', 'FAIL' if bad else 'PASS')
        sys.exit(1 if bad else 0)
    write(out, seen, a.page_data)
    for d, wls in out.items():
        for wl, w in wls.items():
            if not w['available']:
                print(f'{d:13s} {wl:3s}  n/a: {w["reason"]}')
                continue
            print(f'{d:13s} {wl:3s} {w["tok_s"]:9.1f} tok/s  T {w["T_token_cycles"]:12.1f}  record {w["price_of_record"]["tok_s"]:8.1f} '
                  f'({w["vs_price_pct"]:+.2f}%)  | {w["banner"]}')


if __name__ == '__main__':
    main()
