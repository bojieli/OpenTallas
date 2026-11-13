import json, re, sys
dump, out = sys.argv[1:3]
pts = {}
for ln in open(dump):
    if not ln.startswith('C\t'): continue
    p = ln.rstrip('\n').split('\t')
    n = re.sub(r'\$_[A-Za-z0-9_]*$', '', p[8].replace('\\', '')); n = re.sub(r'^u_bound[./]', '', n)
    m = re.match(r'(u_bin_bc_i\w+?)/q\[(\d+)\]$|(u_u_fab_u_x_\d_\d)\.u_st\.(b_d|tap_d)\[(\d+)\]$|(u_d\d+_u_fab_u_x_\d_\d_a_d)\.(?:r\[(\d+)\]|q)\[(\d+)\]$|(u_pc_nk_u_t_\d_\d_tap)\.q\[(\d+)\]$', n)
    if not m: continue
    bit = int(next(g for g in (m.group(2), m.group(5), m.group(8), m.group(10)) if g is not None))
    if bit % 8: continue
    if m.group(1): k = m.group(1)
    elif m.group(3): k = m.group(3) + ('#B' if m.group(4) == 'b_d' else '#T')
    elif m.group(6): k = m.group(6) + '#' + (m.group(7) if m.group(7) is not None else 'q')
    else: k = m.group(9)
    x0, y0, x1, y1 = map(float, p[4:8])
    pts.setdefault(k, []).append([round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)])
json.dump(pts, open(out, 'w'))
