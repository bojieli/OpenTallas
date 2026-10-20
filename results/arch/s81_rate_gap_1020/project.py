"""Projection (NOT a price): re-run the committed composer with per-instance savings of proposed fixes applied to the
measured node cycles; report conservative (max fixed, solved) cycles and tok/s.  Savings are estimates from measured
laws (see README); nothing here is admitted evidence."""
import sys, json, importlib.util
WT = sys.argv[1]
spec = importlib.util.spec_from_file_location('tc', WT + '/tools/toksim_s81_compose.py')
tc = importlib.util.module_from_spec(spec); spec.loader.exec_module(tc)
orig_nc = tc.node_cycles
# per-instance saving functions: op -> f(node, measured_cycles) -> saving (>=0)
FIX = {
 'F1': {'attn.wq_b': lambda n, c: 3359 - 1987},                                 # WQBP P126 calendar (measured bit-exact)
 'F2': {'attn.wo_a': lambda n, c: (8*354 + 4*348) - (11*231 + 354)},           # 12 BF phases pipelined at BF floor P231
 'F3': {'attn.wo_b': lambda n, c: 4*316 - (3*126 + 316)},                       # 4 FP8 phases pipelined at P126
 'F4': {'ffn.router': lambda n, c: (4*231 + 345) - (4*145 + 345)},             # wider segment tag: BF period 231 -> 145
 'F5': {'attn.idx.topk_final': lambda n, c: max(0.0, c - 276 - 178) if c > 1000 else 0.0},  # RATEFIX TAIL_FINAL 276
 'F6': {'attn.idx.topk_local': lambda n, c: (8702 - 3724) if c > 10000 else 0.0,  # index reader split (record-D rate)
        'attn.idx.score': lambda n, c: max(0.0, c - float(n['cycles']))},       # re-index reader back to its price
 'F7': {'attn.idx.topk_local': lambda n, c: 4000 if c > 10000 else 0.0},       # tournament top-k streams under the reader
 'F2b': {'attn.wo_a': lambda n, c: 11*(231-145)},                       # BF tag widened: wo_a phases at P145
 'F10': {'ffn.experts_gu': lambda n, c: 3680 - (11*145 + 345), 'ffn.down': lambda n, c: 2889 - (10*130 + 289)},  # experts dealt over 2 frames/slice
 'F8': {'attn.window_load': lambda n, c: max(0.0, c - float(n['cycles']))},    # HBM window prefetch scheduled ahead
}
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
out = {}
SETS = {'measured': [], 'A near-term (F1 F3 F5)': ['F1','F3','F5'], 'B schedule+topk (F1 F2 F3 F5 F8)': ['F1','F2','F3','F5','F8'],
 'C = B + F4 router tag': ['F1','F2','F3','F4','F5','F8'], 'D = C + index F6 F7': ['F1','F2','F3','F4','F5','F6','F7','F8'],
 'E = D + F2b': ['F1','F2','F2b','F3','F4','F5','F6','F7','F8'], 'F = E + F10 placement': ['F1','F2','F2b','F3','F4','F5','F6','F7','F8','F10'],
 'F2b alone': ['F2b'], 'F10 alone': ['F10'], 'F8 alone':['F8'], 'F5 alone':['F5'], 'F6 alone':['F6'], 'F7 alone':['F7'], 'F4 alone':['F4'], 'F1 alone':['F1'], 'F2 alone':['F2'], 'F3 alone':['F3']}
for k, v in SETS.items(): out[k] = run(v)
for k, v in out.items():
    print('%-36s AR %10.0f cyc %7.1f tok/s | MTP %10.0f cyc %7.1f tok/s' % (k, v['ar'][0], v['ar'][1], v['mtp'][0], v['mtp'][1]))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
