import sys, json, collections
sys.path.insert(0, '/tmp/claude-dshbm-wt/tools')
import uarch_model as U
arch, b = U.arch_graph(1048576)
g = b.g; path = g.path(b.sink)
kinds = collections.Counter(); bnd = collections.Counter(); ex = {}
for x in path:
    nd = g.nodes[x]; k = nd['kind']; kinds[k]+=1
    if k == "matvec" or x.endswith((".attn.scores", ".idx.topk_final")) or x == "argmax":
        key = U.node_key(x) if k=="matvec" else x.split('.')[-1] if '.' in x else x
        key2 = (k, key)
        bnd[key2]+=1; ex.setdefault(key2, x)
print(len(path), dict(kinds))
for k,v in sorted(bnd.items(), key=lambda t:-t[1]): print(v, k, ex[k])
print(sum(bnd.values()))
# what precedes/follows each boundary: collectives?
coll=[x for x in path if g.nodes[x]['kind'] in ('collective','hop')]
print('collectives/hops on path', len(coll), collections.Counter(g.nodes[x]['kind'] for x in coll))
print(coll[:10])
print('----L5 sequence')
for x in path:
    if x.startswith('L5.') or x.startswith('L2.attn.idx'):
        nd=g.nodes[x]; print(x, nd['kind'], round(sum(g.contrib[x].values())*1e9,1),'ns')
for x in path[-12:]:
    nd=g.nodes[x]; print(x, nd['kind'], round(sum(g.contrib[x].values())*1e9,1),'ns')
