import sys, json
N, plan, tn, kind = sys.argv[1:5]
sys.path[:0] = [N + '/tools/die_plan']
import street_rule as S
orig = S.analyze; cap = []
def an(*a, **k):
    V, c = orig(*a, **k); cap.extend(V); return V, c
S.analyze = an
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    S.main(['check', plan, '--die', 's81_head', '--types', tn, '--repo', N, '--out', '/dev/null'])
for v in cap:
    if v['kind'] == kind: print(json.dumps({a: (b[-34:] if isinstance(b, str) else b) for a, b in v.items()})[:260])
