"""S81-ROMCAP projection (NOT a price): the S81-RATE composer re-run (results/arch/s81_rate_gap_1020/project.py on
claude/s81-rate-gap-1020 540f0a0d4, FIX table copied verbatim) plus the contents-only placement levers of this lane.
Savings are per instance from measured laws: P145 (gu), P130 (down), P126 (wq_b); estimates, not evidence.
    python3 project.py <worktree> <out.json>"""
import sys, json, importlib.util
WT = sys.argv[1]
spec = importlib.util.spec_from_file_location('tc', WT + '/tools/toksim_s81_compose.py')
tc = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc)
orig_nc = tc.node_cycles
FIX = {   # S81-RATE 540f0a0d4 (verbatim)
 'F1': {'attn.wq_b': lambda n, c: 3359 - 1987},
 'F2': {'attn.wo_a': lambda n, c: (8*354 + 4*348) - (11*231 + 354)},
 'F3': {'attn.wo_b': lambda n, c: 4*316 - (3*126 + 316)},
 'F4': {'ffn.router': lambda n, c: (4*231 + 345) - (4*145 + 345)},
 'F5': {'attn.idx.topk_final': lambda n, c: max(0.0, c - 276 - 178) if c > 1000 else 0.0},
 'F6': {'attn.idx.topk_local': lambda n, c: (8702 - 3724) if c > 10000 else 0.0,
        'attn.idx.score': lambda n, c: max(0.0, c - float(n['cycles']))},
 'F7': {'attn.idx.topk_local': lambda n, c: 4000 if c > 10000 else 0.0},
 'F2b': {'attn.wo_a': lambda n, c: 11*(231-145)},
 'F10': {'ffn.experts_gu': lambda n, c: 3680 - (11*145 + 345), 'ffn.down': lambda n, c: 2889 - (10*130 + 289)},
 'F8': {'attn.window_load': lambda n, c: max(0.0, c - float(n['cycles']))},
}
# S81-ROMCAP levers (contents only: ROM images, cfg7 rows, xs streams; same physical views)
FIX.update({
 'O1': {'ffn.experts_gu': lambda n, c: 6*145},                                   # GU_MERGE: 24 -> 18 phases at P145
 'O2': {'attn.wq_b': lambda n, c: 3*126},                                        # 12 q pairs: wq_b R 6 -> 8, 11 -> 8 phases (P126, after F1)
 'O3k2': {'ffn.experts_gu': lambda n, c: 12*145, 'ffn.down': lambda n, c: 7*130},  # 2 classes/element: gu 24 -> 12, down 21 -> 14
 'O3k3': {'ffn.experts_gu': lambda n, c: 18*145, 'ffn.down': lambda n, c: 14*130}, # 3 classes/element: gu 24 -> 6, down 21 -> 7
})
def run(active):
    table = {}
    for k in active:
        for op, f in FIX[k].items():
            table.setdefault(op, []).append(f)
    def nc(n, ov):
        c, how = orig_nc(n, ov)
        if c is not None and n.get('op') in table:
            c = c - sum(f(n, c) for f in table[n['op']])
        return c, how
    tc.node_cycles = nc
    r = tc.build(tc.OUT / 'elements')
    tc.node_cycles = orig_nc
    return {wl: (w['T_cycles'], w['tok_s']) for wl, w in r['workloads'].items()}
C = ['F1', 'F2', 'F3', 'F4', 'F5', 'F8']
E = C + ['F6', 'F7', 'F2b']
SETS = {'measured': [], 'O1 alone': ['O1'], 'C (owner MTP set)': C, 'C + O1': C + ['O1'], 'C + O1 + O2': C + ['O1', 'O2'],
        'E': E, 'E + O1': E + ['O1'], 'E + O1 + O2': E + ['O1', 'O2'], 'E + F10 (S81-RATE F)': E + ['F10'],
        'E + O2 + O3k2': E + ['O2', 'O3k2'], 'E + O2 + O3k3': E + ['O2', 'O3k3'], 'C + O2 + O3k2': C + ['O2', 'O3k2']}
out = {k: run(v) for k, v in SETS.items()}
for k, v in out.items():
    print('%-24s AR %10.0f cyc %7.1f tok/s | MTP %10.0f cyc %7.1f tok/s' % (k, v['ar'][0], v['ar'][1], v['mtp'][0], v['mtp'][1]))
json.dump(dict(sets=SETS, result=out), open(sys.argv[2], 'w'), indent=1)
