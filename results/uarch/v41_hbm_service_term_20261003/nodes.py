import sys, json
sys.path.insert(0, '/tmp/claude-dshbm-wt/tools')
import uarch_model as U
arch, b = U.arch_graph(1048576)
g=b.g
for x in ['L5.attn.scores','L5.attn.pv','L2.attn.idx.score','L2.attn.idx.topk_final','L5.attn.wq_b','L5.attn.a_allgather','L5.ffn.experts_gu']:
    nd=g.nodes[x]; print(x, {k:(v if not isinstance(v,(dict,list)) else str(v)[:300]) for k,v in nd.items()}, g.contrib[x])
