"""rtl_cmp.py A_DIR B_DIR [FILE]: bound RTL files equal after yosys renumbering / src-path normalization?"""
import collections, json, os, re, sys
A, B = sys.argv[1:3]
def nz(t):
    t = re.sub(r'/[^\s"|:]*/', '', t)
    t = re.sub(r'\$\d+', '$N', t)
    return re.sub(r'__[0-9a-f]{8}\b', '__H', re.sub(r'_\d{4,}(?=_|\b)', '_N', t)) if os.environ.get('LOOSE') else t
out, ex = {}, {}
for f in sorted(os.listdir(A)):
    pa, pb = os.path.join(A, f), os.path.join(B, f)
    if os.path.isdir(pa) or not f.endswith('.sv') or (len(sys.argv) > 3 and f != sys.argv[3]):
        continue
    if not os.path.exists(pb):
        out[f] = 'MISSING_IN_B'; continue
    a, b = open(pa).read(), open(pb).read()
    if a == b:
        out[f] = 'IDENTICAL'; continue
    ca, cb = collections.Counter(nz(a).splitlines()), collections.Counter(nz(b).splitlines())
    if ca == cb:
        out[f] = 'SAME_AFTER_RENUMBER'
    else:
        out[f] = 'DIFF %d/%d' % (sum((ca - cb).values()), sum((cb - ca).values()))
        ex[f] = ([l[:160] for l in list((ca - cb).elements())[:3]], [l[:160] for l in list((cb - ca).elements())[:3]])
print(json.dumps(collections.Counter(v.split()[0] for v in out.values())))
for k, v in out.items():
    if v.startswith('DIFF') or v.startswith('MISS'):
        print(k, v, json.dumps(ex.get(k)) if len(sys.argv) > 3 else '')
