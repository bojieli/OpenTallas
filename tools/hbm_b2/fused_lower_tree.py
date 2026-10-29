#!/usr/bin/env python3
"""HBM native top: the actual lower FUSED csum tree under the two hub n4 nodes (HBM-BIND-6, opt-in).

The released native top composes only the root (ot_hnx_fused_hub_n4ext, levels 4/5 split, t5 inside) and the two
level-4 nodes u_mu_fused_n4_{nw,ne}; their ua/ub were native_required__ top ports, so the 2 x (16 hnx_fused_lane +
14 lower ot_hnx_fused_tnode) plan MU cores had no as-built cells.  This module builds that lower tree with the
existing RTL (ot_hnx_fused_lane, ot_hnx_fused_tnode) wired exactly as the reference integration
ot_hnx_fused_tree_top (rtl/hbm_next/fused/tb, N4EXT = 1; snapshot results/hbm_n4_native_1027/source_snapshot.tar.gz):
  hub side s (nw = 0 -> global lanes 0..15, ne = 1 -> 16..31; reference quadrant Q = 2 s + h), hub quadrant h:
    n1_q{h}_{g}: a = lane 8h + 2g, b = lane 8h + 2g + 1          (lane up = {v, t, x, fin, fin, flt, d})
    n2L_q{h}:    a = n1_q{h}_0, b = n1_q{h}_1;  n2R_q{h}: a = n1_q{h}_2, b = n1_q{h}_3
    n3_q{h}:     a = n2L_q{h}, b = n2R_q{h};    n4: a = n3_q0, b = n3_q1  (down: da -> a child, db -> b child)
  lane lid = 16 s + L (5-bit ID strap; the n4 lane-map assertion tools/die_plan/hbm_n4_lanemap.py).
Instance names = the plan's hub-local core names + '_<side>' (same rule as u_mu_fused_n4_<side>), so map.parts
'<plan name>_<side>' -> [<SIDE>_hub, <plan name>] binds them.
Not composed (left explicit native_required__ obligations, never tied or invented):
  * every lane/node rst_n (die-delivered reset endpoint; the bind's wavefront core reset replaces it);
  * pad_k / pad_b of all 28 lower nodes (depend on the realised die link latencies = plan stations; die binder strap);
  * lane rr_v / rr_d (VM bank read return: no native VM bank port is wired to a FUSED lane in the current source;
    ot_hnx_fused_vm_native_adapter is the zero-cycle bridge once the calendar assigns the bank port).
  Lane rq_* / wq_* outputs stay unconsumed native outputs for the same reason.
The relay links of the reference are die stations (plan internal_stations mu_tree:*), not as-built cells.
"""
SIDES = ('nw', 'ne')
UW, DW = 271, 173
LANE_PARAMS = '.D(5120), .KX(4), .RR(10)'
NODE_PARAMS = '.LA(6), .UW(271), .DW(173), .DELIVERED_RESET(1)'
LANE_OUT = dict(rq_v=1, rq_s=16, wq_v=1, wq_s=16, wq_d=256, up_v=1, up_t=1, up_x=10, up_d=256, fin=1, flt=1)
RESET_REASON = 'Current die-delivered reset endpoint/offset is not bound; original POR is provenance only'
PAD_REASON = 'Lower FUSED tree pad strap depends on the realised die link latencies (plan mu_tree stations); die binder strap unbound'
VM_REASON = 'FUSED lane VM bank read return: no native VM bank port feeds a FUSED lane in the current source (calendar bank-port assignment pending)'


def lane(side, L):
    return f'u_mu_fused_{L}_{side}'


def node_plan_names():
    names = []
    for h in (0, 1):
        names += [f'u_mu_fused_n1_q{h}_{g}' for g in range(4)] + [f'u_mu_fused_n2L_q{h}', f'u_mu_fused_n2R_q{h}', f'u_mu_fused_n3_q{h}']
    return names


def plan_map(side):
    """as-built instance -> [partition, plan core name] for one hub side."""
    part = side.upper() + '_hub'
    m = {lane(side, L): [part, f'u_mu_fused_{L}'] for L in range(16)}
    m.update({f'{n}_{side}': [part, n] for n in node_plan_names()})
    return m


def compose_side(side, clock, required, output, mutant=None):
    """Instances of one hub side's lower tree; returns (instances, n4 ua/ub input specs).
    mutant (proof only): 'swap_2_4' swaps lanes 2 and 4 of hub quadrant 0 (reference MUT 8)."""
    s = SIDES.index(side)
    inp = lambda seg: dict(direction='input', segments=seg)
    N = lambda n: f'u_mu_fused_{n}_{side}'
    insts = {}

    def pos(h, i):
        L = 8 * h + i
        if mutant == 'swap_2_4' and h == 0 and i in (2, 4):
            L = 8 * h + (6 - i)
        return L

    def up_of(L):
        n = lane(side, L)
        return [('n', f'{n}__up_d', 0, 255), ('n', f'{n}__flt', 0, 0), ('n', f'{n}__fin', 0, 0), ('n', f'{n}__fin', 0, 0),
                ('n', f'{n}__up_x', 0, 9), ('n', f'{n}__up_t', 0, 0), ('n', f'{n}__up_v', 0, 0)]

    def node(name, ua, ub, dn):
        ports = dict(clk=inp(clock), rst_n=required(name, 'rst_n', 1, RESET_REASON),
                     pad_k=required(name, 'pad_k', 6, PAD_REASON), pad_b=required(name, 'pad_b', 1, PAD_REASON),
                     ua=inp(ua), ub=inp(ub))
        for p, w in dict(uo=UW).items():
            ports[p] = output(name, p, w)
        ports['dn'] = inp(dn)
        for p in ('da', 'db'):
            ports[p] = output(name, p, DW)
        insts[name] = dict(master='ot_hnx_fused_tnode', params=NODE_PARAMS, ports=ports, origin='native_FUSED_lower_tree')

    uo = lambda n: [('n', f'{n}__uo', 0, UW - 1)]
    dsel = lambda n, p: [('n', f'{n}__{p}', 0, DW - 1)]
    lane_dn = {}
    for h in (0, 1):
        n4slot = 'da' if h == 0 else 'db'
        n3, n2l, n2r = N(f'n3_q{h}'), N(f'n2L_q{h}'), N(f'n2R_q{h}')
        node(n3, uo(n2l), uo(n2r), dsel(f'u_mu_fused_n4_{side}', n4slot))
        node(n2l, uo(N(f'n1_q{h}_0')), uo(N(f'n1_q{h}_1')), dsel(n3, 'da'))
        node(n2r, uo(N(f'n1_q{h}_2')), uo(N(f'n1_q{h}_3')), dsel(n3, 'db'))
        for g in range(4):
            parent, slot = (n2l, 'da' if g == 0 else 'db') if g < 2 else (n2r, 'da' if g == 2 else 'db')
            n1 = N(f'n1_q{h}_{g}')
            a, b = pos(h, 2 * g), pos(h, 2 * g + 1)
            node(n1, up_of(a), up_of(b), dsel(parent, slot))
            lane_dn[a], lane_dn[b] = (n1, 'da'), (n1, 'db')
    for L in range(16):
        n = lane(side, L)
        src, p = lane_dn[L]
        d = f'{src}__{p}'
        ports = dict(clk=inp(clock), rst_n=required(n, 'rst_n', 1, RESET_REASON), lid=inp([('c', 5, 16 * s + L)]))
        ports['rr_v'] = required(n, 'rr_v', 1, VM_REASON)
        ports['rr_d'] = required(n, 'rr_d', 256, VM_REASON)
        ports.update(dn_v=inp([('n', d, 172, 172)]), dn_op=inp([('n', d, 169, 171)]), dn_x=inp([('n', d, 161, 168)]),
                     dn_d=inp([('n', d, 33, 160)]), r_v=inp([('n', d, 32, 32)]), r_d=inp([('n', d, 0, 31)]))
        for p, w in LANE_OUT.items():
            ports[p] = output(n, p, w)
        insts[n] = dict(master='ot_hnx_fused_lane', params=LANE_PARAMS, ports=ports, origin='native_FUSED_lower_tree')
    n4_inputs = dict(ua=inp(uo(N('n3_q0'))), ub=inp(uo(N('n3_q1'))))
    return insts, n4_inputs
