"""DIE-LAYOUT-HBM ladder EQ statement: a lane is a registered pipe; the ladder only re-routes its middle (bank FT slots,
ports between banks).  Per lane, compare what the RTL/bind sees: the launch end (first port src part.bus), the capture
end (last port dst part.bus), width, and the end-to-end cycles of the latency table (= natural + fixed_cycles + group
pad).  Also the lane set, latency_groups and every non-bank type byte-for-byte."""
import json, sys, hashlib
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
def lanes(p):
    pm = {q['id']: q for q in p['ports']}
    out = {}
    for ln in p['lanes']:
        h = [pm[q] for q in ln['ports']]
        out[ln['id']] = (h[0]['src']['part'], h[0]['src']['bus'], h[-1]['dst']['part'], h[-1]['dst']['bus'], h[0]['width'],
                         p['latency']['lanes'][ln['id']]['cycles'])
    return out
A, B = lanes(a), lanes(b)
print('lanes', len(A), len(B), 'missing', sorted(set(A) - set(B)), 'extra', sorted(set(B) - set(A)))
ends = [l for l in A if l in B and A[l][:5] != B[l][:5]]
cyc = [(l, A[l][5], B[l][5]) for l in A if l in B and A[l][5] != B[l][5]]
print('end/width changed', len(ends), ends[:20])
print('cycles changed', len(cyc), cyc)
h = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()[:12]
print('latency_groups same', h(a.get('latency_groups')) == h(b.get('latency_groups')))
bank_types = {p['type'] for p in b['partitions'] if '_b0' in p['name']}
tch = [t for t in a['partition_types'] if t not in bank_types and h(a['partition_types'][t]) != h(b['partition_types'].get(t))]
print('non-bank types changed', len(tch), tch)
pa = {p['name']: p for p in a['partitions']}; pb = {p['name']: p for p in b['partitions']}
print('partitions moved/changed (non-bank)', [n for n in pa if '_b0' not in n and h(pa[n]) != h(pb.get(n))])
