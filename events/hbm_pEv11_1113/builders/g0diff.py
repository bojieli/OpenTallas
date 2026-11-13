"""G0 diff by exact (level, check, msg): usage g0diff.py BASE_REPORT NEW_REPORT"""
import json, sys, collections
def load(f):
    d = json.load(open(f)); it = d.get('findings') if isinstance(d, dict) else d
    if it is None:
        it = next(v for v in d.values() if isinstance(v, list))
    return [(i.get('level'), i.get('check'), i.get('msg')) for i in it]
a, b = load(sys.argv[1]), load(sys.argv[2])
ca, cb = collections.Counter(x for x in a if x[0] == 'ERROR'), collections.Counter(x for x in b if x[0] == 'ERROR')
new = cb - ca; gone = ca - cb
print('ERROR base', sum(ca.values()), 'new', sum(cb.values()), 'new msgs', sum(new.values()), 'gone', sum(gone.values()))
for k in list(new)[:40]: print('  NEW', k)
for k in list(gone)[:40]: print('  GONE', k)
