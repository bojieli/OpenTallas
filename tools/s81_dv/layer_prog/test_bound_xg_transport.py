import unittest
from layer_prog.bound_entry_transport import BufferSinks
from layer_prog.bound_xg_transport import NXF, RING, collect_ring, collect_xf, collect_xfin, summarise

SLS = ('u_s_0N', 'u_s_1N')


def xg(sl):
    return f'{sl}.u_sl.u_xg'


def xr(sl):
    return f'{sl}.u_sl.u_xr'


def vq(sl, k):
    return f'{sl}.u_sl.u_lf{k}.u_vq'


def xfin(sl):
    return f'{sl}.u_sl.u_xf'


class FakeDie:
    die_sha = 'x'

    def __init__(self, age=4, mutate=None, ring_age=3):
        self.units, ip, raw, net = {}, {}, {}, [1000]
        li = {}

        def inport(unit, port, w):
            bits = []
            for i in range(w):
                net[0] += 1; bits.append(net[0]); ip[str(net[0])] = [f'{unit}.{port}[{i}]']
            return dict(dir='input', bits=bits)

        def outport(w):
            net[0] += w
            return dict(dir='output', bits=list(range(net[0] - w, net[0])))

        vqm = dict(module='ot_s81sl_vq', kind='leaf', ports=dict(xf_v=dict(dir='output', width=1),
                   xf_s=dict(dir='output', width=1), xf=dict(dir='output', width=276)))
        xfp = {f'{s}_{f}': dict(dir=d, width=w) for s, d in (('wi', 'input'), ('ei', 'input'), ('eo', 'output'),
                                                          ('wo', 'output')) for f, w, _ in NXF}
        xfp.update(rb_v=dict(dir='output', width=1), rb_d=dict(dir='output', width=32))
        for n, sl in enumerate(SLS):
            g = xg(sl)
            ports = dict(xf_v=inport(g, 'xf_v', 5), xf_s=inport(g, 'xf_s', 5), xf=inport(g, 'xf', 1380),
                         nx_eo=inport(g, 'nx_eo', 173), nx_wo=inport(g, 'nx_wo', 173),
                         nx_wi=outport(173), nx_ei=outport(173))
            for inp, out, w in RING:
                ports[inp] = inport(g, inp, w); ports[out] = outport(w)
            self.units[g] = dict(master='ot_s81sl_xgt_xo', ports=ports)
            self.units[xr(sl)] = dict(master='ot_s81sl_xrt1', ports=dict(
                x_rbv=inport(xr(sl), 'x_rbv', 1), x_rbd=inport(xr(sl), 'x_rbd', 32)))
            self.units[sl] = dict(master='ot_s81sl_slice_c1x', ports=dict(sid=dict(dir='input', bits=['0'] * 4)))
            li[xfin(sl)] = dict(module='ot_s81dv_xfin', kind='leaf', ports=xfp)
            li[sl + '.u_sl.$7'] = dict(module='$buf', kind='glue', ports=dict(A=dict(dir='input', width=5),
                                                                              Y=dict(dir='output', width=5)))
            for k in range(5):
                li[vq(sl, k)] = vqm
                raw[f'{g}.xf_v[{k}]'] = ['pin', f'{sl}.u_sl.$7.Y[{k}]', 1, False]
                raw[f'{sl}.u_sl.$7.A[{k}]'] = ['pin', f'{vq(sl, k)}.xf_v[0]', age - 1, False]
                raw[f'{g}.xf_s[{k}]'] = ['pin', f'{vq(sl, k)}.xf_s[0]', age, False]
                for j in range(276):
                    raw[f'{g}.xf[{276*k+j}]'] = ['pin', f'{vq(sl, k)}.xf[{j}]', age, False]
            for f, w, lsb in NXF:
                for i in range(w):
                    for side, nx in (('wi', 'nx_wi'), ('ei', 'nx_ei')):
                        raw[f'{xfin(sl)}.{side}_{f}[{i}]'] = ['pin', f'{g}.{nx}[{lsb+i}]', 1, False]
                    for side, nx in (('eo', 'nx_eo'), ('wo', 'nx_wo')):
                        raw[f'{g}.{nx}[{lsb+i}]'] = ['pin', f'{xfin(sl)}.{side}_{f}[{i}]', 1, False]
            raw[f'{xr(sl)}.x_rbv[0]'] = ['pin', f'{xfin(sl)}.rb_v[0]', 2, False]
            for i in range(32):
                raw[f'{xr(sl)}.x_rbd[{i}]'] = ['pin', f'{xfin(sl)}.rb_d[{i}]', 2, False]
        # ring: s0.ro_e -> s1.ri_w, s1.ro_w -> s0.ri_e, s0.vo -> s1.vi; s0 ri_w and s1 ri_e/ s0 vi constant edges
        a, b = SLS
        for i in range(1104):
            raw[f'{xg(b)}.ri_w[{i}]'] = ['pin', f'{xg(a)}.ro_e[{i}]', ring_age, False]
            raw[f'{xg(a)}.ri_e[{i}]'] = ['pin', f'{xg(b)}.ro_w[{i}]', ring_age, False]
        for i in range(276):
            raw[f'{xg(b)}.vi[{i}]'] = ['pin', f'{xg(a)}.vo[{i}]', 1, False]
        for g, p, w in ((xg(a), 'ri_w', 1104), (xg(b), 'ri_e', 1104), (xg(a), 'vi', 276)):
            self.units[g]['ports'][p]['bits'] = ['0'] * w
        self.inventory = dict(leaf_interfaces=li, input_pins=ip, source_variants={}, source_asbuilt_sha256='y')
        if mutate:
            mutate(raw, self)
        self.sinks = BufferSinks(raw, li)
        self.entry = [dict(status='PASS', slice=sl, leaf=k, vp=f'{sl}.u_sl.u_lf{k}.u_vp', command_transport_edges=2)
                      for sl in SLS for k in range(5)]
        self.ret = [dict(status='PASS', slice=sl, leaf=k, leaf_instance=f'{sl}.u_sl.u_lf{k}', partial_return_edges=3)
                    for sl in SLS for k in range(5)]

    def slices(self):
        return {sl: dict(sid=n) for n, sl in enumerate(SLS)}


def xf_rows(**kw):
    d = FakeDie(**kw)
    return collect_xf(d, d.entry, d.ret)


class XfForwardTest(unittest.TestCase):
    def test_exact_forward_sums_buffer_stages(self):
        rows = xf_rows(age=6)
        self.assertTrue(all(r['status'] == 'PASS' for r in rows), rows[:1])
        self.assertEqual({r['xf_forward_edges'] for r in rows}, {6})
        self.assertEqual(rows[0]['bits_checked'], 278)
        self.assertTrue(rows[0]['xf_v_through_buffer'])

    def test_swapped_payload_bit_blocks(self):
        def m(raw, d):
            raw[f'{xg(SLS[0])}.xf[{276+5}]'] = ['pin', f'{vq(SLS[0], 1)}.xf[6]', 4, False]
        r = xf_rows(mutate=m)[1]
        self.assertEqual(r['status'], 'BLOCKED'); self.assertIn('expected', r['reason'])

    def test_strobe_age_incoherent_blocks(self):
        def m(raw, d):
            raw[f'{xg(SLS[0])}.xf_s[2]'] = ['pin', f'{vq(SLS[0], 2)}.xf_s[0]', 5, False]
        self.assertIn('incoherent', xf_rows(mutate=m)[2]['reason'])

    def test_leaf_mismatch_with_command_blocks(self):
        def m(raw, d):
            raw[f'{SLS[0]}.u_sl.$7.A[0]'] = ['pin', f'{vq(SLS[0], 1)}.xf_v[0]', 3, False]
        self.assertEqual(xf_rows(mutate=m)[0]['status'], 'BLOCKED')

    def test_constant_payload_blocks(self):
        def m(raw, d):
            d.units[xg(SLS[0])]['ports']['xf']['bits'][3] = '0'
        self.assertIn('constant', xf_rows(mutate=m)[0]['reason'])


class RingTest(unittest.TestCase):
    def test_neighbour_hops_and_edges(self):
        rows = collect_ring(FakeDie(ring_age=5))
        st = {(r['xg'], r['port']): r for r in rows}
        h = st[(xg(SLS[1]), 'ri_w')]
        self.assertEqual((h['status'], h['from_xg'], h['from_port'], h['age_edges']), ('PASS', xg(SLS[0]), 'ro_e', 5))
        self.assertEqual(st[(xg(SLS[0]), 'ri_w')]['status'], 'EDGE_CONSTANT')
        s = summarise([], rows, [])
        self.assertEqual(s['nx']['neighbour_hops'], 3)

    def test_misordered_ring_bit_blocks(self):
        def m(raw, d):
            raw[f'{xg(SLS[1])}.ri_w[7]'] = ['pin', f'{xg(SLS[0])}.ro_e[8]', 3, False]
        r = [r for r in collect_ring(FakeDie(mutate=m)) if r['xg'] == xg(SLS[1]) and r['port'] == 'ri_w'][0]
        self.assertIn('bit-exact', r['reason'])

    def test_mixed_age_blocks(self):
        def m(raw, d):
            raw[f'{xg(SLS[0])}.ri_e[0]'] = ['pin', f'{xg(SLS[1])}.ro_w[0]', 2, False]
        r = [r for r in collect_ring(FakeDie(mutate=m)) if r['xg'] == xg(SLS[0]) and r['port'] == 'ri_e'][0]
        self.assertIn('incoherent', r['reason'])

    def test_partial_constant_word_blocks(self):
        def m(raw, d):
            d.units[xg(SLS[1])]['ports']['vi']['bits'][9] = '1'
        r = [r for r in collect_ring(FakeDie(mutate=m)) if r['port'] == 'vi' and r['xg'] == xg(SLS[1])][0]
        self.assertEqual(r['status'], 'BLOCKED')


class XfinTest(unittest.TestCase):
    def test_endpoints_pass(self):
        rows = collect_xfin(FakeDie())
        self.assertTrue(all(r['status'] == 'PASS' for r in rows), rows)
        self.assertEqual(rows[0]['edges'], {'nx_wi->wi': 1, 'nx_ei->ei': 1, 'eo->nx_eo': 1, 'wo->nx_wo': 1,
                                            'rb->x_rb': 2})
        self.assertEqual(rows[0]['bits_checked'], 4 * 173 + 33)

    def test_wi_from_ei_blocks(self):
        def m(raw, d):
            raw[f'{xfin(SLS[0])}.wi_d[4]'] = ['pin', f'{xg(SLS[0])}.nx_ei[4]', 1, False]
        self.assertIn('expected', collect_xfin(FakeDie(mutate=m))[0]['reason'])

    def test_missing_xfin_record_blocks(self):
        def m(raw, d):
            del d.inventory['leaf_interfaces'][xfin(SLS[1])]
        self.assertIn('one actual XFIN', collect_xfin(FakeDie(mutate=m))[1]['reason'])


if __name__ == '__main__':
    unittest.main()
