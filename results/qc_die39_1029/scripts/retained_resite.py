#!/usr/bin/env python3
"""DIE-QC-39: retained clock lower shapes = the re-sited clock-cell stacks (stair shapes) + clock-cell vias of a prebuild
run (diag_shapes.pkl), M1..M7 only, replacing the pre-resite clock_seed.json as the provider access reservation."""
import pickle, json, sys
d = pickle.load(open(sys.argv[1], 'rb')); S = d['shapes']; n1, n2, n3 = d['n']
keep = ('M1','M2','M3','M4','M5','M6','M7')
out = [list(s) for s in S[:n1] + S[n2:n3] if s[1] in keep]
json.dump(out, open(sys.argv[2], 'w')); print('RETAINED', len(out))
