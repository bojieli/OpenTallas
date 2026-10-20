import json, sys
d = json.load(open(sys.argv[1])); a = json.load(open(sys.argv[2]))
C = {  # op -> (class, compiler-bubble part per instance (AR), note)
 'attn.wo_a': ('S+H', 1329, '12 BF16 phases/frame run SERIALLY (8x354+4x348); pipelined at the BF floor P231 = 11x231+354'),
 'attn.wq_b': ('S+H', 1372, '15 epochs at P224 serial calendar; P126 pipelined calendar measured 1,987 bit-exact (WQBP)'),
 'attn.wo_b': ('S+H', 570, '4 FP8 phases/frame serial (4x316); old DAG had 1 phase'),
 'ffn.experts_gu': ('H/M', 0, 'already back-to-back at min period P145 (23x145+345); p4l puts 6 experts x w1/w3 = 24 phases on one frame in EVERY layer'),
 'ffn.down': ('H/M', 0, 'already back-to-back at P130 (20x130+289); 21 phases/frame on p4l'),
 'ffn.router': ('H', 0, '5 BF phases at P231 floor: at <=230 return words alias the next segment index (RTL tag width)'),
 'attn.idx.topk_local': ('H', 0, 'p4l index reader HBM-bound 8,702 cyc / 43,691 keys (record D 3,724) + serial select; L2/L8/L14 span 14.2k'),
 'attn.idx.topk_final': ('H', 0, 'release rung-ingress-bound final 6.5k vs price 178 (INDEXED13 1,033 / TAIL_FINAL 276 not in release)'),
 'attn.idx.score': ('H', 0, 're-index scorer L24..36, 5,829 each, HBM-bound reader'),
 'attn.window_load': ('S', 0, 'HBM-latency-bound 532 vs 178; issued serially, not prefetched (W_SLACK 560 assumes latency<=56)'),
 'attn.scores': ('H', 0, 'svc GO->last fold score 289 vs 52.6 at 1M context'),
 'attn.idx.q_field': ('M', 0, 'indexer wq_b rows: field projection missing from the price (new DAG node)'),
 'ffn.norm.scale': ('D', 0, '16-slice neighbour exchange (247) replaces the star hub reduction'),
 'attn.q_quant': ('D', 0, 'same 16-slice exchange'), 'attn.quant': ('D', 0, 'same 16-slice exchange'),
}
for wl in ('ar', 'mtp'):
    w = d['workloads'][wl]; wa = a['workloads'][wl]
    pa = {o['op']: o for o in wa['per_op']}
    price = w['price_of_record']['cycles']; T = w['T_cycles']; gap = T - price
    print(f'## {wl}: price {price} T {T} gap {gap:.0f}')
    rows = sorted(w['per_op'], key=lambda o: -abs(o['cycles'] - o['old_cycles']))
    other_d = other_old = other_new = 0
    for o in rows:
        dlt = o['cycles'] - o['old_cycles']
        if o['op'] in C or abs(dlt) >= 3000:
            cl, b, note = C.get(o['op'], ('G' if dlt < 0 else '?', 0, ''))
            n = o['n_crit']
            p37 = pa.get(o['op'], {}).get('cycles', 0)
            print(f"| {o['op']} | {n} | {o['old_cycles']/n:,.0f} | {o['cycles']/n:,.0f} | {o['old_cycles']:,.0f} | {p37:,.0f} | {o['cycles']:,.0f} | {dlt:+,.0f} | {100*dlt/gap:+.1f} % | {cl} | {note} |")
        else:
            other_d += dlt; other_old += o['old_cycles']; other_new += o['cycles']
    print(f'| other on-die ops | | | | {other_old:,.0f} | | {other_new:,.0f} | {other_d:+,.0f} | {100*other_d/gap:+.1f} % |')
    sp = sum(o['cycles'] for o in w['per_op']); spo = sum(o['old_cycles'] for o in w['per_op'])
    ex = sum(e['cycles'] for e in w['extra_terms']); exb = sum(e['base_cycles'] for e in w['extra_terms'])
    xd = w['T_cycles_fixed'] - sp - ex
    xp = price - spo - exb
    print('xdie price', xp, 'xdie now', xd, 'd', xd - xp, 100*(xd-xp)/gap)
    print('extra', exb, ex, ex - exb, 'solved', T - w['T_cycles_fixed'])
