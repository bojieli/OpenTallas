"""max per-bit Manhattan hop of the bc column chains in a placed dump (before) and in the relay_sites delta (after)."""
import json, re, sys
dump, spine_json, delta_json, tn = sys.argv[1:5]
sp = json.load(open(spine_json)); dl = json.load(open(delta_json))['changes'][tn]['relay_sites']
pos = {}
for ln in open(dump):
    if not ln.startswith('C\t'): continue
    p = ln.rstrip('\n').split('\t')
    n = re.sub(r'\$_[A-Za-z0-9_]*$', '', p[8].replace('\\', '')); n = re.sub(r'^u_bound[./]', '', n)
    if re.search(r'u_bin_bc|u_u_fab_u_x_|_u_fab_u_x_\d_\d_a_d|u_pc_nk_u_t_\d_\d_tap\.q|u_bout_bc', n):
        x0, y0, x1, y1 = map(float, p[4:8]); pos[n] = ((x0 + x1) / 2, (y0 + y1) / 2)
def chainpairs(bus, chain):
    out = []
    for k in range(516):
        seq = [f'u_bin_{bus}/q[{k}]']
        for i, s in enumerate(chain):
            seq.append(f'{s}.u_st.b_d[{k}]')
            if i + 1 < len(chain):
                m = [g['group'] for g in col['groups'] if g['group'].startswith('u_d') and s[2:] in g['group']]
                D = int(re.match(r'u_d(\d+)_', m[0]).group(1)) if m else 6
                dn = f'u_d{D}_{s[2:]}_a_d'
                seq += [f'{dn}.r[{j}][{k}]' for j in range(D - 1)] + [f'{dn}.q[{k}]']
        out.append(seq)
    return out
for col in sp['columns']:
    bus = col['bus']; chain = [s['st'] for s in col['stations']]
    for name, P in (('before', pos), ('after', {k: tuple(v) for k, v in dl.items()})):
        mx = 0; arg = None; over = 0; n = 0
        for seq in chainpairs(bus, chain):
            for a, b in zip(seq, seq[1:]):
                if a in P and b in P:
                    d = abs(P[a][0] - P[b][0]) + abs(P[a][1] - P[b][1]); n += 1
                    over += d > 405
                    if d > mx: mx, arg = d, (a, b)
        # t_q (tap_d[k<380]) from the station input
        for i, s in enumerate(chain):
            for k in range(380):
                a = f'{s}.u_st.tap_d[{k}]'
                b = f'u_pc_nk_u_t_{s[-3]}_{s[-1]}_tap.q[{k}]'
                if a in P and b in pos:
                    d = abs(P[a][0] - pos[b][0]) + abs(P[a][1] - pos[b][1]); n += 1; over += d > 405
                    if d > mx: mx, arg = d, (a, b)
        print(f'{tn}\t{bus}\t{name}\tmax_hop {mx:.0f}\tpairs {n}\tover405 {over}\t{arg}')
