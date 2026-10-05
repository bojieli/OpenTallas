import sys
sys.path.insert(0, '/tmp/claude-dshbm-wt/tools')
import uarch_model as U, arch_budget_v41 as A, inspect
arch, b = U.arch_graph(1048576); g=b.g; path=g.path(b.sink)
for x in path:
    if g.nodes[x]['kind'] in ('op','join'): print(x, g.nodes[x]['kind'], g.nodes[x].get('desc'), round(sum(g.contrib[x].values())*1e9,1))
print(inspect.signature(A.price))
# shared_gu sm time
d=U.hbm_gpu_design('v41'); clk=d['clock_hz']
for k in ['L5.ffn.shared_gu','L5.ffn.experts_gu','L5.ffn.down','L5.ffn.shared_down']:
    if k in g.nodes:
        nd=g.nodes[k]; key=U.node_key(k)
        if nd['sweep'] and key in U.NODE_K:
            rows=nd['sweep']['macs']/U.NODE_K[key]/U.V41_HBM_DIES
            print(k, key, rows, U.sm_op_cycles(rows,U.NODE_K[key],U.NODE_FMT[key],d['drain_cycles'],True), 'cyc', nd['deps'])
print([x for x in g.nodes if x.startswith('L5.ffn')])
