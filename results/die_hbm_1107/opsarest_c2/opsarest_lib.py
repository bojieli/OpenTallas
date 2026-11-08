"""DIE-HBM-90-OPSA 11-07: geometry helpers for the opsa_rest compact PART event (plan-tool models, check.py formulas)."""
import gzip, json, os, re
RI = 'u_sfucore_Q_opstore_a__r'
OLD_TABLE = 'cores/ot_hgi_sfu_opsa_rest__760.32x86.4__d44v_split.json'
SLOT = dict(origin=(1080.0, 941.76), outline=(760.32, 86.4), orient='MX')
NEW_WH = (250.56, 64.8)
REACH = 405.0          # tools/die_plan/schema.py SIGNAL_REACH_UM / budgets.ft_station_max_um (check.py R3-INTERNAL limit)
G0C = 0.9 * REACH      # reach.py MARGIN x reach (lane hops)
PS_PER_UM = 0.76       # reach.py planning constant (REACH-M89 calibration basis); measured one-cycle reach 452.5 um TT @ 833 ps


def rd(plan_dir, rel):
    p = os.path.join(plan_dir, rel)
    if os.path.exists(p):
        return json.load(open(p))
    return json.load(gzip.open(p + '.gz'))


def orient(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def place(pins, o, x0, y0, w, h):
    out = {}
    for q in pins:
        tx, ty = orient(o, w, h, q['x'], q['y'])
        out[q['name']] = (x0 + tx, y0 + ty)
    return out


def boxd(p, b):
    return max(b[0] - p[0], 0, p[0] - b[2]) + max(b[1] - p[1], 0, p[1] - b[3])


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def bus(n):
    return re.sub(r'\[\d+\]$', '', n)


def hc_box(h):
    dx, dy = h.get('track_offset_um', [0.0, 0.0])
    x0, y0 = h['origin_um'][0] + dx, h['origin_um'][1] + dy
    return (x0, y0, x0 + h['outline_um'][0], y0 + h['outline_um'][1])


def hc_pins(plan_dir, h):
    doc = rd(plan_dir, h['pins_file'])
    L = doc if isinstance(doc, list) else doc['pins']
    return place(L, h.get('orient') or 'R0', h['origin_um'][0], h['origin_um'][1], h['outline_um'][0], h['outline_um'][1])


class Ctx:
    def __init__(self, plan_dir, plan, core_conns, opsa_conn, por_table, new_table, tn='q_b113'):
        self.T = plan['partition_types'][tn]
        self.HC = {h['inst']: h for h in self.T['hard_cores']}
        self.boxes = {k: hc_box(h) for k, h in self.HC.items()}
        self.conns = core_conns[tn]
        self.por_table, self.new_table = por_table, new_table
        self.por = place(por_table, SLOT['orient'], SLOT['origin'][0], SLOT['origin'][1], *SLOT['outline'])
        self.PB = (SLOT['origin'][0], SLOT['origin'][1], SLOT['origin'][0] + SLOT['outline'][0], SLOT['origin'][1] + SLOT['outline'][1])
        self.plan_dir = plan_dir
        self._tab = {}
        # station-covered inbound bundles (capture = rest box)
        self.st_in = {(e['launch'].split('.')[0], e['launch'].split('.', 1)[1]) for e in self.T['internal_stations'] if e.get('capture') == RI}
        self.inbound = []
        for ci, ports in self.conns.items():
            if ci == RI or ci not in self.HC: continue
            for p, tg in ports.items():
                if 'core:' + RI in tg:
                    self.inbound.append((ci, p, [v for n, v in self.tab(ci).items() if bus(n) == p]))
        # exact sibling pin pairs inside opstore_a (shared opstore_a top net / internal net), from the split conn map
        subs = {s['inst'].split('.')[-1]: s for s in opsa_conn['subs']}
        inst = {'u_g0': 'u_sfucore_Q_opstore_a__g0', 'u_g1': 'u_sfucore_Q_opstore_a__g1'}
        by = {}
        for k, s in subs.items():
            for b, v in s['bits'].items():
                if b == 'clk' or b.startswith('rst_n'): continue
                for t in v['top']: by.setdefault(t, []).append((k, b))
        self.pairs = []
        for mem in by.values():
            for r in [b for k, b in mem if k == 'u_r']:
                for k, b in mem:
                    if k != 'u_r': self.pairs.append((r, inst[k], b))
        for k in ('u_g0', 'u_g1'):
            rb = sorted(b for b, v in subs['u_r']['bits'].items() if not v['top'] and v['peer'] == ['u_fcore.u_core.' + k])
            pb = sorted(b for b, v in subs[k]['bits'].items() if not v['top'] and 'u_fcore.u_core.u_r' in v['peer'])
            assert len(rb) == len(pb), (k, rb, pb)
            self.pairs += [(r, inst[k], b) for r, b in zip(rb, pb)]

    def tab(self, ci):
        if ci not in self._tab: self._tab[ci] = hc_pins(self.plan_dir, self.HC[ci])
        return self._tab[ci]

    def out_box(self, pp):
        """check.py R3-INTERNAL core bundle, rest side: per rest port and named partner core, worst pin -> partner box"""
        w = {}
        for n, p in pp.items():
            for tg in self.conns[RI].get(bus(n), []):
                k, _, nm = tg.partition(':')
                if k != 'core' or nm not in self.boxes: continue
                key = (bus(n), nm); w[key] = max(w.get(key, 0.0), boxd(p, self.boxes[nm]))
        return w

    def in_box(self, box):
        """partner side: per partner port naming rest (no station chain), worst partner pin -> rest box"""
        return {(ci, p): max(boxd(v, box) for v in xs) for ci, p, xs in self.inbound if (ci, p) not in self.st_in}

    def sib(self, pp):
        """exact pin-to-pin, rest bit <-> sibling (g0/g1) bit on the same net"""
        w = {}
        for r, ci, b in self.pairs:
            key = (bus(r), ci); w[key] = max(w.get(key, 0.0), man(pp[r], self.tab(ci)[b]))
        return w


def lattice(v, step=4.32):
    return round(round(v / step) * step, 3)

# capture-side rest buses per launching partner port (opstore_a.conn.json top nets: operand_2/3 u_group rq/sw_v/rd/flt,
# u_output sr_addr/sr_v/flt, operand_2 u_group sw_addr -> meta_78); g0/g1 of opsb both listed (plan net membership is per bus)
CAPMAP = {
    'rq': ('u_core_u_engine_u_memory_g_operand_2_req', 'u_core_u_engine_u_memory_g_operand_3_req'),
    'sw_v': ('u_core_u_engine_u_memory_g_operand_2_sw', 'u_core_u_engine_u_memory_g_operand_3_sw'),
    'rd': ('u_core_u_engine_u_memory_g_operand_2_data', 'u_core_u_engine_u_memory_g_operand_3_data'),
    'flt': ('u_core_u_engine_u_memory_group_fault',),
    'sw_addr': tuple('u_core_u_vm_g_lg_%d_meta_78' % k for k in range(4)),
    'sr_addr': ('u_core_io_r',), 'sr_v': ('u_core_io_r',),
}
MEASURED_REACH = 452.5    # reach.py MEASURED M4-M7 (REACH-M89, TT 833 ps, unc 60 + skew 90)
