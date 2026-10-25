import sys, json, os
H='/srv/opentallas-scratch2/claude/wt/path-hbm-q3-1025/physical/die_plan/hbm/cores/harden'
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, '..', '..', 'pins_cut'))
import netcut, split_conn as sc
n = netcut.Netlist(sys.argv[1])
ex = ['u_body.u_ring', 'u_body.u_reduce', 'u_body.g_link[0].u_link', 'u_body.g_link[1].u_link', 'u_body.g_link[2].u_link',
      'u_body.g_q3.t192.u_arg', 'u_body.u_vmasm', 'u_body.u_writer']
m = n.resolve('ot_hfd_coll_q3_hard_v8x_s')
names = [i for i, t in n.children(m)]
ex = [e for e in names if any(e == x or e.replace('\\', '') == x for x in ex)] or ex
print('excluded', ex)
u = sc.top_port_use(n, 'ot_hfd_coll_q3_hard_v8x_s', [''], ex)
W = {p[0]: p[2] for p in n.mods[m].ports}
out = {k: v for k, v in u.items() if len(v) < W[k] and k in ('vm_rr', 'clk_reduce')}
json.dump(out, open(sys.argv[2], 'w')); print({k: len(v) for k, v in out.items()}, out.get('clk_reduce'))
