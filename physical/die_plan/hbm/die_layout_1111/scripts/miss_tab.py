import json, sys
d = json.load(open(sys.argv[1])); out = open(sys.argv[2], 'w')
out.write('type\ta\tb\tbits\tdist_um\tclass\towner\tplan_change\tcycles\n')
n = {}
for t, v in sorted(d.items()):
    for m in v.get('missing', []):
        if not m.get('unbudgeted'): continue
        a, b = m['plan_a'], m['plan_b']
        if t.startswith('q_hub'):
            c, o, p, cy = 'M1/M2 hub', 'HBM-HUB-ARCH-2 (A5 co-location / op_Q stations in VM_RT_EXTRA pad)', 'hub interior, not this lane', 'A5: 0 / M2 priced'
        elif t == 'NW_io':
            c, o, p, cy = 'F1 regression', 'DIE-LAYOUT-HBM F1 (this event)', 'u_host_ep back to y 1468.80 beside u_ep_N0 (pins face N<->S, 134-um gap, centre 397 um)', '0'
        elif t == 'q_b113' or t == 'q_b113__physical_v1':
            c, o, p, cy = 'M3 q_b113', 'q_b113 option B / REDESIGN (die transits 7681 b out of q_b113 first)', 'centre ctl between sfup_q1 and opstore_a/b, lanes14/15 beside opstore; needs the 17 ft slots out of the type', '0 if co-located'
        elif t.startswith('q_su20'):
            c, o, p, cy = 'M5', 'DIE-HBM-100 (COORD 04:51 approved option 1)', 'move k=3/4/5 of the D=39 pd stages onto lane->pretree links as stations', '0 (pd39 -> pd(39-k))'
        elif t == 'root':
            c, o, p, cy = 'M4 root', 'ROOT REDESIGN (3x22 htile)', 'selector__q0 abut hb_idx__link E edge in the ROOTPACK root', '0'
        else:
            c, o, p, cy = 'M6 hcol h0->h1', {'q_b001': 'CPL-HBM-B1 A3', 'q_b010': 'q_b010 REDESIGN (cell cap)', 'q_b102': 'CPL-HBM-3 q_b10x', 'q_b103': 'CPL-HBM-3 q_b10x'}.get(t.split('__')[0], '?'), 'h0/h1 adjacent (<=405 centre) in the S2 layout, else +1 station', '0 adjacent / +1'
        n[c] = n.get(c, 0) + 1
        out.write('\t'.join(map(str, [t, a, b, m['bits'], m['dist_um'], c, o, p, cy])) + '\n')
print(n, sum(n.values()))
