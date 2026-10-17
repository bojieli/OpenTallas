#!/usr/bin/env python3
"""S81-DV price: per-user AR / MTP tok/s of the distributed-vector die vs the current hub die.

Method (same machinery as the ledger, tools/throughput/accepted_cost.py + tools/s81/mtp_ledger_1016.py):
  1. Token-path DAGs results/arch/token_path_20261009/ds_rom{,_mtp}.json; joint longest-path solve with per-node
     deltas (accepted_cost.solve); the MTP wavefront rule of accepted_cost.rom_loss (the slowest verify stage's
     added cycles are paid once more per wave.busy node).
  2. Ledger rows that are hub-implementation costs (VM.*, SU.*, HC.*, CAPT.CD_PINREG) are DROPPED: the units they
     price do not exist in DV.  Every other row (field return tree, cfg7, Engram lookup, MIX4, MTP p2) is KEPT.
  3. DV deltas, each from the node's own recorded composition + the DV plan geometry (dv_plan.py facts):
       hub-in/out:  SU nodes carrying 'hub in 33 / out 23'           -56 + PINREG
       hub-wired:   SU nodes carrying 'BCAST 22 / RET 15'            -37 + PINREG
       hub-slab:    SU 'r8 hub-slab stations' adders (3.333/0.833 ns) removed (-4 / -1)
       norm tree:   full-h RMS norms: hub RW 9 + BW 9 removed, + the mesh exchange of golden-subtree partial roots
                    (worst slice->slice, plan stages); q_lora norm over 4 adjacent slices; kv norm in <= 2 slices
       field wire:  'r8 die wire X cyc over N phases' scaled by DV phase path / DAG basis path (138 cyc)
       attention:   q heads slice -> PHY-side attention: + (DV worst - hub VM->svc) stages on attn.q_rope
       router:      scores slice -> G-unit tree on ffn.top6_order
       h transfer:  HC.H_XFER (246, dropped) replaced by ring-to-edge exit + entry on substage_hop0 / head.hop
     Collectives are left unchanged (conservative: ring end slices sit at the edge links, as far as the hub was).
  4. rate = hop_only(stages) * (1 - (kept ledger % + DV DAG loss %)/100), the mtp_ledger_1016 additive rule.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from throughput import accepted_cost as ac          # noqa: E402

TP = ROOT / 'results/arch/token_path_20261009'
LEDGER = ROOT / 'results/arch/accepted_cost_ledger_1013.json'
HOP = 1004 + 171 / 84
ANCHOR = {'ar': (1447.7, 1.0), 'mtp': (4238.4, 4.159)}
DROP = re.compile(r'^(VM|SU|HC)\.|^CAPT\.CD_PINREG$')
BASIS_PHASE = 138.0          # results/rtl/dsrom_field_reprice_r8_20261006 f183.60: farthest-frame round trip
HUB_VM_TO_SVC_STAGES = 50    # c26l sp_vm centre -> svc_SW centre ~20 mm at 405 um
# measured (tb_s81dv_xfin16, results/rtl/s81_dv_1016): last partial -> rstd 234 cycles with the sequenced dataflow finish
# vs 171 with the parallel tree the hub's price already contains -> +63 on every full-h norm (rstd precedes the matvec:
# norm-after-matvec is AGENTS level 6, excluded, so this latency is on the critical path)
FINISH_SEQ_EXTRA = 234 - 171


def hop_only(stages):
    add = (stages - 81) * HOP / 1200
    return {wl: t * 1e6 / (t * 1e6 / a + add) for wl, (a, t) in ANCHOR.items()}


def dv_deltas(doc, g, pinreg=8, su_scale=0.0, basis_scale=1.0):
    """per-node delta (cycles) and a per-rule audit"""
    st = lambda um: math.ceil(um / g['hop_um'])
    xchg = g['scalar_exchange_stages']
    rules = {}
    d = {}

    def add(nid, rule, v):
        d[nid] = d.get(nid, 0.0) + v
        r = rules.setdefault(rule, dict(nodes=0, cycles=0.0))
        r['nodes'] += 1; r['cycles'] += v
    r_phase = g['phase_path_stages'] / (BASIS_PHASE * basis_scale)
    for n in doc['nodes']:
        note = n.get('src', {}).get('note', '') or ''
        op, nid, cls = n.get('op', ''), n['id'], n.get('cls')
        if cls == 'su':
            if 'hub in 33 / out 23' in note:
                add(nid, 'hub_in_out', -56 + pinreg)
            if 'BCAST 22 / RET 15' in note:
                add(nid, 'hub_wired', -37 + pinreg)
            k = note.count('hub-slab stations 3.333 ns')
            if k:
                add(nid, 'hub_slab', -4 * k)
            k = note.count('hub-slab stations 0.833 ns')
            if k:
                add(nid, 'hub_slab', -1 * k)
            if op in ('attn.quant', 'ffn.norm.scale', 'eng.gate') or op.endswith('hc.sumsq'):
                add(nid, 'norm_tree_full', -18 + xchg)
                add(nid, 'norm_finish_seq', FINISH_SEQ_EXTRA)
            elif op == 'attn.q_quant':
                add(nid, 'norm_tree_q', -18 + st(3 * g['cluster_pitch_um']))
            elif op == 'attn.kv_rope_qdq':
                add(nid, 'norm_tree_kv', -18 + st(g['cluster_pitch_um']))
            if su_scale:
                add(nid, 'su_contingency', su_scale * n['cycles'])
        m = re.search(r'r8 die wire (\d+(?:\.\d+)?) cyc over (\d+) phase', note)
        if m and cls == 'field':
            add(nid, 'field_phase_wire', float(m.group(1)) * (r_phase - 1.0))
        if op == 'attn.q_rope':
            add(nid, 'attn_q_path', st(g['worst_slice_to_attention_um']) - HUB_VM_TO_SVC_STAGES)
        if op == 'ffn.top6_order':
            add(nid, 'router_tree', st(g['worst_slice_to_gunit_um']))
        if g.get('slice_leaves'):
            # p4: the slice is a cluster of `slice_leaves` leaves (one 64-lane beat each), ring stop + xfin in the
            # middle leaf; registered leaf-to-leaf hops: lm = middle <-> outer leaf, ld = outer <-> outer
            lh = g['leaf_um'][1]
            lm = st((g['slice_leaves'] - 1) / 2 * lh); ld = st((g['slice_leaves'] - 1) * lh)
            if m and cls == 'field':
                add(nid, 'intra_slice_leaf', int(m.group(2)) * (ld + 2 * lm))   # return to owner + x to/from ring stop
            if cls == 'su' and op in ('attn.quant', 'ffn.norm.scale', 'attn.q_quant', 'attn.kv_rope_qdq', 'eng.gate'):
                add(nid, 'intra_slice_leaf', 2 * lm)                            # partial to xfin leaf, rstd back
        if g.get('tier_w'):
            # p4c per-column tier exchange vs p4b end-column ring: the N tier needs the S tier's 40 beats; p4b moves
            # them over 2 x 1,104-b end links (~20 cycles of serialization each), p4c over 8 x tier_w-bit links
            # (5 x 1,104 / tier_w cycles per column); + up to 2 registered unit ring stops (+4) on the crossing
            cross = 5 * 1104 / g['tier_w'] - 20 + 4
            if m and cls == 'field':
                add(nid, 'tier_cross', int(m.group(2)) * max(0.0, cross))
            if cls == 'su' and op in ('attn.quant', 'ffn.norm.scale', 'eng.gate'):
                add(nid, 'tier_cross', 4 + math.ceil(173 / g['tier_w']) - 1)   # partial flit + unit stops
        if re.search(r'(substage_hop\d+|head\.hop)$', nid):
            add(nid, 'h_xfer_ring', 2 * st(g['worst_slice_to_edge_um']))
    return d, rules


def solve_with_wave(doc, delta):
    nodes, edges = doc['nodes'], doc['edges']
    base, _ = ac.solve(nodes, edges)
    delta = dict(delta)
    wave = [n['id'] for n in nodes if n.get('op') == 'wave.busy']
    if wave:
        stages = [x for x in doc.get('groups', []) if x.get('kind') in ('stage', 'layer', 'embed')]
        worst = max(stages, key=lambda x: x['cycles'])['id']
        wadd = sum(delta.get(n['id'], 0.0) for n in nodes if n.get('group') == worst)
        for i in wave:
            delta[i] = delta.get(i, 0.0) + wadd
    new, _ = ac.solve(nodes, edges, delta)
    return base, new


def ledger_split(path=LEDGER, drop=DROP):
    led = json.loads(Path(path).read_text())
    kept, dropped = {'ar': 0.0, 'mtp': 0.0}, {'ar': 0.0, 'mtp': 0.0}
    rows = []
    for r in led['rows']:
        if r['design'] != 's81' or r.get('status') not in ('accepted', 'proposed'):
            continue
        tgt = dropped if drop.search(r['group']) else kept
        for wl in ('ar', 'mtp'):
            tgt[wl] += (r.get('per_workload', {}).get(wl) or {}).get('e2e_loss_pct', 0.0) or 0.0
        rows.append(dict(group=r['group'], status=r['status'], dropped=bool(drop.search(r['group'])),
                         ar=(r.get('per_workload', {}).get('ar') or {}).get('e2e_loss_pct'),
                         mtp=(r.get('per_workload', {}).get('mtp') or {}).get('e2e_loss_pct')))
    return kept, dropped, rows


def price(g, stages=89, pinreg=8, su_scale=0.0, frames=128, drop=DROP, basis_scale=1.0):
    kept, dropped, rows = ledger_split(drop=drop)
    st_eff = stages * 128 / frames if frames != 128 else stages
    ho = hop_only(89)
    ho_dv = hop_only(math.ceil(st_eff))
    out = dict(stages=stages, dv_stages=math.ceil(st_eff), frames=frames, pinreg=pinreg, su_contingency=su_scale,
               ledger_kept_pct=kept, ledger_dropped_pct=dropped, workloads={})
    for wl, name in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')):
        doc = json.loads((TP / f'{name}.json').read_text())
        delta, rules = dv_deltas(doc, g, pinreg, su_scale, basis_scale)
        base, new = solve_with_wave(doc, delta)
        dv_loss = ac.loss_pct(base, new)
        cur = ho[wl] * (1 - (kept[wl] + dropped[wl]) / 100)
        dv = ho_dv[wl] * (1 - (kept[wl] + dv_loss) / 100)
        out['workloads'][wl] = dict(base_cycles=round(base, 1), dv_cycles=round(new, 1), dv_dag_loss_pct=round(dv_loss, 3),
                                    hop_only=round(ho[wl], 1), current_tok_s=round(cur, 1), dv_tok_s=round(dv, 1),
                                    change_vs_current_pct=round(100 * (dv / cur - 1), 2),
                                    rules={k: dict(nodes=v['nodes'], cycles=round(v['cycles'], 1)) for k, v in rules.items()})
    out['ledger_rows'] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True, help='dv_plan.py plan.json (facts)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    f = plan['facts']
    B = {b['name']: b for b in plan['blocks']}
    cen = lambda b: (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
    sl = [b for b in plan['blocks'] if b['kind'] == 'slice']
    man = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    g = dict(f, hop_um=f.get('hop_um', 405.0),
             worst_slice_to_gunit_um=max(man(cen(s), cen(B['gunit'])) for s in sl),
             worst_slice_to_edge_um=max(min(man(cen(s), cen(B[c])) for c in ('coll_WS', 'coll_WN', 'coll_ES', 'coll_EN')) for s in sl))
    # ROM capacity per die scales the stage count (owner-approved lever: fewer ROMs per die, more dies)
    st = math.ceil(89 * f.get('rom_slots_c26l', 1220) / f.get('rom_slots', 1220) - 1e-9)
    g['stages_from_slots'] = st
    res = dict(schema='opentallas.s81_dv.price.v1', geometry=g, status='COMPOSED_NOT_NATIVE',
               scenarios={
                   'dv_base': price(g, stages=st),
                   'dv_pinreg16': price(g, stages=st, pinreg=16),
                   'dv_su_plus10pct': price(g, stages=st, su_scale=0.10),
                   'dv_su_plus25pct_pinreg16': price(g, stages=st, pinreg=16, su_scale=0.25),
                   'pessimistic_keep_SU_HC_rows': price(g, stages=st, pinreg=16, drop=re.compile(r'^VM\.|^CAPT\.CD_PINREG$')),
                   'pessimistic_plus_su25': price(g, stages=st, pinreg=16, su_scale=0.25, drop=re.compile(r'^VM\.|^CAPT\.CD_PINREG$')),
               })
    if g['hop_um'] < 405:   # reach sensitivity: also price the hub basis on the same hop (today's die degrades too)
        res['scenarios']['dv_base_hub_basis_same_hop'] = price(g, stages=st, basis_scale=405.0 / g['hop_um'])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    for k, s in res['scenarios'].items():
        w = s['workloads']
        print(f"{k:28s} AR {w['ar']['current_tok_s']:7.1f} -> {w['ar']['dv_tok_s']:7.1f} ({w['ar']['change_vs_current_pct']:+.2f}%)   "
              f"MTP {w['mtp']['current_tok_s']:7.1f} -> {w['mtp']['dv_tok_s']:7.1f} ({w['mtp']['change_vs_current_pct']:+.2f}%)  "
              f"DAG {w['ar']['dv_dag_loss_pct']:+.2f}/{w['mtp']['dv_dag_loss_pct']:+.2f}")
    print(json.dumps(res['scenarios']['dv_base']['workloads']['ar']['rules'], indent=0))
    print(json.dumps(res['scenarios']['dv_base']['workloads']['mtp']['rules'], indent=0))
    print('kept', res['scenarios']['dv_base']['ledger_kept_pct'], 'dropped', res['scenarios']['dv_base']['ledger_dropped_pct'])


if __name__ == '__main__':
    main()
