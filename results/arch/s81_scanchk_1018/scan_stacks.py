#!/usr/bin/env python3
"""MU.S81.SCANCHK (10-18): the S81 index scan at p4l's real HBM stack count.

Facts read from the repo (no simulation):
  * p4l has ONE HBM3E stack a die: results/arch/s81_dv_1016/p4l/plan.json holds one `phy` block
    (ot_hbm3e_phy_v41x_aw30_e8p5, 8,500 x 1,177 um, NPC 32 = one stack's 32 pseudo-channels, 10 mm2 a stack per its
    abstract) served by 16 dsfd_ctrl_rg2 x 2 PCs (SPEC.md 0b-p4g).  Every S81 layer die is the one p4l die type.
  * The composition's index-scan nodes (results/arch/token_path_20261009/ds_rom{,_mtp}.json *.attn.idx.score) are the
    10-04 reader run (results/rtl/dsrom_1m_measured_20261004/reader.json): "W11 quarter-per-stack", i.e. FOUR HBM3E
    stacks a rank die (peak 4 x 32 PCs x 32 B / 1,024 ps = 4 TB/s a rank), and, for the re-index layers, the 4-stack
    candidate-block gather (results/rtl/dsrom_reindex_candidates_20261004/gather.json, bound in
    results/rtl/dsrom_idxkey_layout_20261004/gather.json).

Model at s stacks a die (grade: priced = analytic scaling of a measured 4-stack rate):
  full scans (L2/L8/L14 ratio 2, L20 ratio 1): the per-stack reader is independent and per-PC bound (91.9-94.4 % of
    peak measured), a rank's keys are fixed, so reader cycles scale by 4 / s:  delta = (4/s - 1) * reader_cycles.
  re-index gathers (L24/L28/L32/L36): only the bank-group bound part scales:  delta = (4/s - 1) * bound_cycles.
  The +72 array settle/latency and the +44 die-tile adders are per scan, unchanged.
AR / MTP: the same longest-path solve the ledger and dv_price use (tools/throughput/accepted_cost.solve + the MTP
wavefront rule: the slowest verify stage's added cycles are paid once more per wave.busy node).

Writes scan_stacks.json next to this file.  Run from the repo root:  python3 results/arch/s81_scanchk_1018/scan_stacks.py
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
BASIS_STACKS = 4
P_STACKS = 1
FULL = {2: 'csa2_full_L2_clk833', 8: 'csa2_full_L2_clk833', 14: 'csa2_full_L2_clk833', 20: 'csa1_full_L20_clk833'}
REINDEX = (24, 28, 32, 36)


def jl(p):
    return json.loads((ROOT / p).read_text())


plan = jl('results/arch/s81_dv_1016/p4l/plan.json')
phys = [b for b in plan['blocks'] if b.get('kind') == 'phy']
phy_abs = jl('physical/asap7_memory_macros/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5.json')
NPC = phy_abs['interface']['parameters']['NPC']
assert len(phys) == 1 and phys[0]['master'] == 'ot_hbm3e_phy_v41x_aw30_e8p5' and NPC == 32, (phys, NPC)

reader = {r['name']: r for r in jl('results/rtl/dsrom_1m_measured_20261004/reader.json')['runs']}
g_used = jl('results/rtl/dsrom_reindex_candidates_20261004/gather.json')['worst_rank']
g_bound = jl('results/rtl/dsrom_idxkey_layout_20261004/gather.json')['worst_rank']
assert g_used['sectors'] == g_bound['sectors']
BOUND = g_bound['bound']['bound_cycles']


def deltas(s):
    """node id suffix 'L<L>.attn.idx.score' -> added cycles at s stacks a die"""
    f = BASIS_STACKS / s - 1.0
    d = {L: f * reader[FULL[L]]['cycles'] for L in FULL}
    d.update({L: f * BOUND for L in REINDEX})
    return d


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
        stages = [g for g in doc.get('groups', []) if g.get('kind') in ('stage', 'layer', 'embed')]
        # the slowest verify stage AFTER the change (the scan stage only grows, so it stays the slowest)
        cyc = {g['id']: g['cycles'] + sum(v for k, v in delta.items() if by[k].get('group') == g['id']) for g in stages
               for by in [{n['id']: n for n in nodes}]}
        worst0 = max(stages, key=lambda g: g['cycles'])['id']
        worst = max(cyc, key=cyc.get)
        wadd = cyc[worst] - dict((g['id'], g['cycles']) for g in stages)[worst0]
        delta = dict(delta)
        for i in wave:
            delta[i] = delta.get(i, 0.0) + wadd
    new, _ = ac.solve(nodes, edges, delta)
    return dict(base_cycles=round(base, 1), cycles=round(new, 1), added_cycles=round(new - base, 1),
                scan_nodes=len(dl), wave_positions=len(wave), wave_added_cycles_per_position=round(wadd, 1),
                e2e_loss_pct=round(ac.loss_pct(base, new), 3))


ar_doc = jl('results/arch/token_path_20261009/ds_rom.json')
mtp_doc = jl('results/arch/token_path_20261009/ds_rom_mtp.json')
tau = mtp_doc['totals']['tau']
comp = {wl: jl('results/arch/token_path_1018/ds_rom.json')['workloads'][wl] for wl in ('ar', 'mtp')}

out = dict(
    schema='opentallas.s81_scanchk.v1', lane='MU.S81.SCANCHK', date='2026-10-18',
    facts=dict(
        p4l_phy_blocks=[dict(name=b['name'], master=b['master'], w_um=b['w'], h_um=b['h']) for b in phys],
        phy_pseudo_channels=NPC, stacks_per_die=P_STACKS,
        phy_area_mm2_per_stack=phy_abs['footprint']['area_basis']['value_mm2'],
        phy_area_grade=phy_abs['footprint']['area_basis']['grade'],
        source=['results/arch/s81_dv_1016/p4l/plan.json blocks[kind=phy]',
                'results/arch/s81_dv_1016/SPEC.md 0b-p4g (16 dsfd_ctrl_rg2 x 2 PCs = 32 PCs on the one PHY)',
                'physical/asap7_memory_macros/ot_hbm3e_phy_v41x_aw30_e8p5/*.json interface.parameters.NPC'],
        composition_basis_stacks_per_die=BASIS_STACKS,
        composition_basis_source='results/rtl/dsrom_1m_measured_20261004/reader.json (peak_TBps 4.0 = 4 stacks x 32 PCs '
                                 'x 32 B / 1,024 ps; tools/dsrom_1m_measure.py "W11 quarter-per-stack")'),
    measured_4stack=dict(
        L20_reader=dict((k, reader[FULL[20]][k]) for k in ('keys', 'cycles', 'sectors', 'fraction_of_peak')),
        L2_reader=dict((k, reader[FULL[2]][k]) for k in ('keys', 'cycles', 'sectors', 'fraction_of_peak')),
        reindex_gather=dict(cycles=g_used['cycles'], sectors=g_used['sectors'], bound_cycles=BOUND,
                            bound_note=g_bound['bound'])),
    per_stack_count={})

for s in (1, 2, 4):
    dl = deltas(s)
    ar = solve(ar_doc, dl)
    mtp = solve(mtp_doc, dl)
    row = dict(idx_score_delta_cycles={f'L{L}': round(v, 1) for L, v in dl.items()},
               L20_idx_score_cycles=round(5937.0 + dl[20], 1), L2_idx_score_cycles=round(2951.0 + dl[2], 1),
               dag_1009=dict(ar=ar, mtp=mtp))
    c = {}
    for wl, r in (('ar', ar), ('mtp', mtp)):
        T = comp[wl]['T_token_cycles'] + r['added_cycles']
        per = T / tau if wl == 'mtp' else T
        c[wl] = dict(T_cycles=round(T, 1), tok_s=round(F / per, 1), vs_composed_pct=round(100 * (comp[wl]['T_token_cycles'] / T - 1), 2))
    row['composition_1018'] = c
    out['per_stack_count'][str(s)] = row

# ---- option D (modelled): spread a full-scan layer's index keys over k adjacent TP4 stages (4k dies, 4k stacks); every
# p4l die carries the scan service, so this needs only key placement + q fan-out + candidate return + a 4k-way merge.
# Leg = the measured S81 cross-die idx_topk_merge exchange (729 cycles, results/rtl/xdie_s81_1018/record.json); the
# farthest stage is ceil((k-1)/2) stages away; q out and candidates back are serial legs; merge grows with the
# number of local selections (10-09 topk_final 178 cycles for 4 x 512 -> linear in k, modelled).
LEG = 729.0
opt_d = {}
for k in (2, 3, 4):
    dist = math.ceil((k - 1) / 2)
    dl = {}
    for L, name in FULL.items():
        r = reader[name]['cycles']
        scan = r * BASIS_STACKS / k        # a rank's keys over k dies, 1 stack each
        dl[L] = max(0.0, scan - r) + 2 * dist * LEG + 178.0 * (k - 1)
    dl.update({L: (BASIS_STACKS / P_STACKS - 1.0) * BOUND for L in REINDEX})
    ar, mtp = solve(ar_doc, dl), solve(mtp_doc, dl)
    opt_d[str(k)] = dict(stages=k, dies=4 * k, farthest_stage=dist, idx_score_delta_cycles={f'L{L}': round(v, 1) for L, v in dl.items()},
                         ar=dict(added=ar['added_cycles'], tok_s=round(F / (comp['ar']['T_token_cycles'] + ar['added_cycles']), 1)),
                         mtp=dict(added=mtp['added_cycles'],
                                  tok_s=round(F * tau / (comp['mtp']['T_token_cycles'] + mtp['added_cycles']), 1)))
out['option_D_spread_keys_over_k_stages'] = dict(grade='modelled', leg_cycles=LEG, by_k=opt_d)

# ---- CKV selected-row gather sensitivity (not charged): 22,995 sectors a token over 16 die-stacks at 4 stacks a die;
# at 1 stack a die each die's owned rows sit on 32 PCs, not 128.  The measured arrival window (732 - 298 = 434 cycles)
# is far above the 4-stack data time, so it is bound by the attention engine's row ingest, not HBM; the 1-stack data
# time is below that window.
ck = jl('results/rtl/dsrom_1m_measured_20261004/ckv_lat259.json')
ck_r = ck['results'][0] if isinstance(ck.get('results'), list) else None
out['ckv_gather_sensitivity'] = dict(
    sectors_per_token=22995, die_stacks_basis=16, sectors_per_pc_4stack=round(22995 / 16 / 32, 1),
    sectors_per_pc_1stack=round(22995 / 4 / 32, 1), data_cycles_1stack=round(22995 / 4 / 32 * 1.024e-9 * F, 1),
    measured_arrival_window_cycles=732 - 298,
    verdict='not charged: the 1-stack per-PC data time (~221 cycles) stays inside the measured 434-cycle arrival window '
            '(engine-ingest bound); upper bound if it were exposed: 38 gather layers x ~165 = ~6.3k cycles (-0.6 % AR)')

(HERE / 'scan_stacks.json').write_text(json.dumps(out, indent=1) + '\n')
for s, r in out['per_stack_count'].items():
    print(s, 'stacks', r['idx_score_delta_cycles'], 'AR', r['composition_1018']['ar'], 'MTP', r['composition_1018']['mtp'],
          'dag ar', r['dag_1009']['ar']['e2e_loss_pct'], 'mtp', r['dag_1009']['mtp']['e2e_loss_pct'],
          'wave/pos', r['dag_1009']['mtp']['wave_added_cycles_per_position'])
for k, r in opt_d.items():
    print('D k', k, r['idx_score_delta_cycles'], r['ar'], r['mtp'])
