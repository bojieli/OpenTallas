import json, sys
sys.path.insert(0, sys.argv[1]); import opsarest_lib as L
PD = sys.argv[2]; P = json.load(open(PD + '/die_plan.json'))
C = L.Ctx(PD, P, L.rd(PD, 'core_conns.json'), json.load(open(sys.argv[3])), L.rd(PD, L.OLD_TABLE), json.load(open(sys.argv[4])))
g0, g1 = 'u_sfucore_Q_opstore_a__g0', 'u_sfucore_Q_opstore_a__g1'
others = [b for k, b in C.boxes.items() if k != L.RI]
def ovl(b):
    return any(b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3] for o in others)
res = []
for o in ('R0', 'MX', 'MY', 'R180'):
    for kx in range(0, 120):
        x0 = round(1080 + 4.32 * kx, 2)
        if x0 + 250.56 > 1840.32 + 1e-6: break
        for ky in range(0, 6):
            y0 = round(941.76 + 4.32 * ky, 2)
            if y0 + 64.8 > 1028.16 + 1e-6: break
            box = (x0, y0, x0 + 250.56, y0 + 64.8)
            pp = L.place(C.new_table, o, x0, y0, *L.NEW_WH)
            ib = C.in_box(box)
            real = {k: v for k, v in ib.items() if k[0] == 'u_sfucore_Q_ctl__rest'}
            real[('g0.flt', 'gf01[0]')] = L.man(C.tab(g0)['flt'], pp['group_fault_01[0]'])
            real[('g1.flt', 'gf01[1]')] = L.man(C.tab(g1)['flt'], pp['group_fault_01[1]'])
            ob = C.out_box(pp)
            real.update({('out',) + k: v for k, v in ob.items()})
            w = max(real.values())
            res.append((w, o, x0, y0, sorted(real.items(), key=lambda kv: -kv[1])[:4]))
res.sort(key=lambda r: r[0])
for r in res[:12]: print('%.1f %s %.2f %.2f' % r[:4], [(k, round(v, 1)) for k, v in r[4]])
