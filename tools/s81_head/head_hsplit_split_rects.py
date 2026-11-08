import json, sys
r = json.load(open(sys.argv[1])); out = sys.argv[2]
rects = r['rects_um']; X = 648.0
w = [q for q in rects if q[2] <= X]; e = [[round(q[0] - X, 4), q[1], round(q[2] - X, 4), q[3]] for q in rects if q[0] >= X]
assert len(w) + len(e) == len(rects), 'a macro rect straddles the seam'
for tag, v in (('hd_host_w', w), ('hd_host_e', e)):
    json.dump(dict(r, rects_um=v, note=f'DIE-HEAD-84 HSPLIT: {tag} half of macro_rects_hd_host.json (E shifted -648)'), open(f'{out}/macro_rects_{tag}.json', 'w'), indent=1)
print(len(rects), len(w), len(e), list(r))
