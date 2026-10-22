"""DENSE2 probe specs: expert-only (X: no a_proj on a split map) slope probes + dense A / B half intercepts per class."""
import json, sys
R = int(sys.argv[1]); out = sys.argv[2]
sp = [dict(id=f'exp_n{n}', experts=n, dense_layer=None, dense_split2='X') for n in (1, 2, 3, 64)]
for L in (0, 1, 2, 14, 20, 24):
    for h in 'AB':
        sp.append(dict(id=f'dense_L{L}{h}_n0', experts=0, dense_layer=L, dense_split2=h, dense_split2_rows=R))
open(out, 'w').write(json.dumps(sp, indent=1) + '\n')
