"""per lane: crossings with entry/exit pins, slot stations (die), hop list. usage: TOOLS PLAN LANE..."""
import sys, json
sys.path.insert(0, sys.argv[1])
import schema as S, check as C
P = S.Plan(json.load(open(sys.argv[2])))
for lid in sys.argv[3:]:
    pts, regs, xs = C.lane_geometry(P, lid)
    hops = C.lane_pin_hops(P, lid, regs)
    print('LANE', lid, 'fixed', P.lanes[lid].get('fixed_cycles'), 'nregs', len(regs), 'max hop', round(max(hops), 1))
    i = 1; h = 0
    for (part, slot, a, b), x in zip(P.lane_crossings(lid), xs):
        pa, pb = P.port_point(a), P.port_point(b)
        k = x['stations']
        st = regs[i:i + k]
        hh = hops[h:h + k]
        s = P.slot(part, slot) or {}
        print(f"  {part}.{slot} type {P.parts[part]['type']} k {k} in {s.get('in_face')} {tuple(round(v,1) for v in pa)} out {s.get('out_face')} {tuple(round(v,1) for v in pb)} len {x['len_um']}")
        print('     st', [tuple(round(v, 1) for v in p) for p in st])
        print('     hops-into', [round(v, 1) for v in hh])
        i += k; h += k
    print('   final hop', round(hops[-1], 1))
