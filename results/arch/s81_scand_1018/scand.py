#!/usr/bin/env python3
"""S81-SCAND (10-18): option D (coordinator 0iq) with the MEASURED 1-stack reader.

Inputs
  reader_1stack.json  (this dir; scand_bench.py on ot-epyc5, Verilator 5.050): one p4l die (1 HBM3E stack, NPC 32)
                      scanning M keys, M = ceil(K_rank / k); the slower of two ring placements is charged.
  10-04 4-stack reader (results/rtl/dsrom_1m_measured_20261004/reader.json): the basis the token-path DAG's
                      *.attn.idx.score nodes carry (L20 5,821, L2 2,835 reader cycles of 5,937 / 2,951).
  S81 cross-die leg 729 cycles (MU.S81.SCANCHK, results/rtl/xdie_s81_1018 idx_topk_merge exchange, measured) and the
                      10-04 final select 178 cycles for 4 x 512 local selections (measured), grown linearly with the
                      number of local selections (modelled, as scan_stacks.py).
  Re-index gathers L24-L36 are not full scans: D does not touch them; their 1-stack delta stays the SCANCHK price.

Per full-scan layer at k stages:  delta = reader_1stack(M) - reader_4stack + 2 ceil((k-1)/2) x 729 + 178 (k-1).
Token solve = the SCANCHK one (tools/throughput/accepted_cost.solve on the 10-09 DAG + the MTP wavefront rule).
No MTP read sharing (S81-BALANCE B3): the index scorer has one query store and is not on p4l (README).

Writes scand.json next to this file.  Run from the repo root.
"""
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('accepted_cost', ROOT / 'tools/throughput/accepted_cost.py')
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)

F = 1.2e9
LEG, FINAL = 729.0, 178.0
FULL = {2: ('L2', 'csa2_full_L2_clk833'), 8: ('L2', 'csa2_full_L2_clk833'), 14: ('L2', 'csa2_full_L2_clk833'),
        20: ('L20', 'csa1_full_L20_clk833')}
REINDEX = (24, 28, 32, 36)


def jl(p):
    return json.loads((ROOT / p).read_text())


meas = jl('results/arch/s81_scand_1018/reader_1stack.json')
assert meas['status'] == 'pass' and 'v5.050' in meas['simulator'], meas['simulator']
by_m = {}
for r in meas['runs']:
    assert r['checked_keys'] == r['keys']
    by_m.setdefault(r['die_keys'], []).append(r)
reader4 = {r['name']: r for r in jl('results/rtl/dsrom_1m_measured_20261004/reader.json')['runs']}
sc = jl('results/arch/s81_scanchk_1018/scan_stacks.json')
REIDX_D = sc['per_stack_count']['1']['idx_score_delta_cycles']['L24']      # SCANCHK price, unchanged by D


def reader1(M):
    rs = by_m[M]
    w = max(rs, key=lambda r: r['cycles'])
    return w['cycles'], {r['name']: r['cycles'] for r in rs}


def solve(doc, dl):
    delta = {}
    for n in doc['nodes']:
        if n.get('op') == 'attn.idx.score' and n.get('layer') in dl:
            delta[n['id']] = dl[n['layer']]
    assert len(delta) == len(dl), (len(delta), dl)
    nodes, edges = doc['nodes'], doc['edges']
    base, _ = ac.solve(nodes, edges)
    wave = [n['id'] for n in nodes if n.get('op') == 'wave.busy']
    wadd = 0.0
    if wave:
        byid = {n['id']: n for n in nodes}
        stages = [g for g in doc.get('groups', []) if g.get('kind') in ('stage', 'layer', 'embed')]
        cyc = {g['id']: g['cycles'] + sum(v for k, v in delta.items() if byid[k].get('group') == g['id']) for g in stages}
        worst0 = max(stages, key=lambda g: g['cycles'])['id']
        worst = max(cyc, key=cyc.get)
        wadd = cyc[worst] - {g['id']: g['cycles'] for g in stages}[worst0]
        delta = dict(delta)
        for i in wave:
            delta[i] = delta.get(i, 0.0) + wadd
    new, _ = ac.solve(nodes, edges, delta)
    return dict(base_cycles=round(base, 1), cycles=round(new, 1), added_cycles=round(new - base, 1),
                wave_positions=len(wave), wave_added_cycles_per_position=round(wadd, 1),
                e2e_loss_pct=round(ac.loss_pct(base, new), 3))


ar_doc = jl('results/arch/token_path_20261009/ds_rom.json')
mtp_doc = jl('results/arch/token_path_20261009/ds_rom_mtp.json')
tau = mtp_doc['totals']['tau']
# composition basis without any scan correction (the 1018 composer's uncorrected T = T_token - SCANCHK correction)
comp = jl('results/arch/token_path_1018/ds_rom.json')['workloads']
T0 = {wl: comp[wl]['T_token_cycles'] - sum(t['total'] for t in comp[wl]['terms'] if 'scan_stacks_p4l' in t['slot'] or 'scan_d' in t['slot'])
      for wl in ('ar', 'mtp')}

out = dict(schema='opentallas.s81_scand.v1', lane='S81-SCAND', date='2026-10-18',
           grade=dict(reader='measured-old-RTL (W11 reader ot_hdc_v41x_idx_kstream_range + HBM model, 1 stack a die, '
                             'Verilator 5.050; this reader is NOT bound on the p4l die, see README)',
                      legs='measured (729-cycle S81 cross-die idx_topk_merge leg)',
                      merge='modelled (178 cycles a 4 x 512 final select, linear in k)',
                      reindex='priced (SCANCHK, unchanged by D)'),
           reader_1stack={str(M): dict(zip(('cycles_charged', 'by_placement'), reader1(M))) for M in sorted(by_m)},
           reader_4stack_basis={lay: reader4[n]['cycles'] for _, (lay, n) in FULL.items()},
           basis_T_cycles={wl: round(v, 1) for wl, v in T0.items()}, tau=tau, by_k={})
for k in (1, 2, 3, 4):
    dist = math.ceil((k - 1) / 2)
    dl, parts = {}, {}
    for L, (lay, n) in FULL.items():
        K = meas['rank_keys'][lay]
        M = math.ceil(K / k)
        r1, _ = reader1(M)
        xd = 2 * dist * LEG + FINAL * (k - 1)
        dl[L] = r1 - reader4[n]['cycles'] + xd
        parts[f'L{L}'] = dict(die_keys=M, reader_1stack=r1, reader_4stack_basis=reader4[n]['cycles'],
                              legs_and_merge=xd, idx_score_node_cycles=r1 + 116, delta=round(dl[L], 1))
    dl.update({L: REIDX_D for L in REINDEX})
    ar, mtp = solve(ar_doc, dl), solve(mtp_doc, dl)
    row = dict(stages=k, dies=4 * k, farthest_stage=dist, per_layer=parts,
               idx_score_delta_cycles={f'L{L}': round(v, 1) for L, v in dl.items()},
               dag_1009=dict(ar=ar, mtp=mtp))
    row['composition_1018'] = {
        'ar': dict(T_cycles=round(T0['ar'] + ar['added_cycles'], 1), tok_s=round(F / (T0['ar'] + ar['added_cycles']), 1)),
        'mtp': dict(T_cycles=round(T0['mtp'] + mtp['added_cycles'], 1),
                    tok_s=round(F * tau / (T0['mtp'] + mtp['added_cycles']), 1))}
    out['by_k'][str(k)] = row
best = min(out['by_k'].values(), key=lambda r: r['dag_1009']['mtp']['added_cycles'])
out['adopted_k'] = 3
out['best_k_by_mtp'] = best['stages']
(HERE / 'scand.json').write_text(json.dumps(out, indent=1) + '\n')
for k, r in out['by_k'].items():
    c = r['composition_1018']
    print(f"k={k} AR {c['ar']['tok_s']} (loss {r['dag_1009']['ar']['e2e_loss_pct']}%)  MTP {c['mtp']['tok_s']} "
          f"(loss {r['dag_1009']['mtp']['e2e_loss_pct']}%)  deltas {r['idx_score_delta_cycles']}")
