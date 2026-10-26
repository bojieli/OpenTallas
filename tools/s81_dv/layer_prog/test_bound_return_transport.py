import unittest
from layer_prog.bound_entry_transport import BufferSinks
from layer_prog.bound_return_transport import collect_return

SL = 'u_s_0N'
XR = SL + '.u_sl.u_xr'


def vnb(k):
    return f'{SL}.u_sl.u_lf{k}.u_vn.u_b'


class FakeDie:
    die_sha = 'x'

    def __init__(self, age=3, mutate=None):
        ports = dict(p_v=dict(dir='input', bits=list(range(100, 105))),
                     p_d=dict(dir='input', bits=list(range(200, 360))))
        self.units = {XR: dict(master='ot_s81sl_xrt1', ports=ports)}
        vmeta = dict(module='ot_s81sl_vn_b', kind='leaf', ports=dict(
            p_v=dict(dir='output', width=1), p_d=dict(dir='output', width=32),
            rb_v=dict(dir='input', width=1), rb_d=dict(dir='input', width=32)))
        li = {vnb(k): vmeta for k in range(5)}
        li[SL + '.u_sl.$7'] = dict(module='$buf', kind='glue', ports=dict(A=dict(dir='input', width=5), Y=dict(dir='output', width=5)))
        ip = {str(100 + k): [f'{XR}.p_v[{k}]'] for k in range(5)}
        ip.update({str(200 + b): [f'{XR}.p_d[{b}]'] for b in range(160)})
        self.inventory = dict(leaf_interfaces=li, input_pins=ip, source_variants={}, source_asbuilt_sha256='y')
        raw = {}
        for k in range(5):
            # p_v through a source $buf (age split 1 + age-1), p_d direct
            raw[f'{XR}.p_v[{k}]'] = ['pin', f'{SL}.u_sl.$7.Y[{k}]', 1, False]
            raw[f'{SL}.u_sl.$7.A[{k}]'] = ['pin', f'{vnb(k)}.p_v[0]', age - 1, False]
            for j in range(32):
                raw[f'{XR}.p_d[{32*k+j}]'] = ['pin', f'{vnb(k)}.p_d[{j}]', age, False]
            raw[f'{vnb(k)}.rb_v[0]'] = ['pin', f'{XR}.rb_v[0]', 2, False]
            for j in range(32):
                raw[f'{vnb(k)}.rb_d[{j}]'] = ['pin', f'{XR}.rb_d[{j}]', 2, False]
        if mutate:
            mutate(raw)
        self.sinks = BufferSinks(raw, li)
        self.entry = [dict(status='PASS', slice=SL, leaf=k, vp=f'{SL}.u_sl.u_lf{k}.u_vp', command_transport_edges=2)
                      for k in range(5)]

    def slices(self):
        return {SL: {}}


def run(**kw):
    d = FakeDie(**kw)
    return collect_return(d, d.entry)['leaves']


class ReturnTransportTest(unittest.TestCase):
    def test_exact_return_sums_buffer_stages(self):
        rows = run(age=5)
        self.assertTrue(all(r['status'] == 'PASS' for r in rows), rows)
        self.assertEqual({r['partial_return_edges'] for r in rows}, {5})
        self.assertEqual(rows[3]['vn_b'], vnb(3))
        self.assertEqual(rows[0]['rb_broadcast_edges'], 2)

    def test_swapped_payload_bit_blocks(self):
        def m(raw):
            raw[f'{XR}.p_d[33]'] = ['pin', f'{vnb(1)}.p_d[0]', 3, False]
        rows = run(mutate=m)
        self.assertEqual(rows[1]['status'], 'BLOCKED')
        self.assertIn('expected', rows[1]['reason'])

    def test_incoherent_valid_payload_age_blocks(self):
        def m(raw):
            raw[f'{XR}.p_d[70]'] = ['pin', f'{vnb(2)}.p_d[6]', 4, False]
        self.assertIn('incoherent', run(mutate=m)[2]['reason'])

    def test_return_from_other_leaf_than_command_blocks(self):
        def m(raw):
            raw[f'{SL}.u_sl.$7.A[0]'] = ['pin', f'{vnb(1)}.p_v[0]', 2, False]
        rows = run(mutate=m)
        self.assertEqual(rows[0]['status'], 'BLOCKED')

    def test_non_vnb_driver_blocks(self):
        def m(raw):
            raw[f'{SL}.u_sl.$7.A[4]'] = ['pin', f'{SL}.u_sl.u_lf4.u_vn.u_a.c_v[0]', 2, False]
        self.assertIn('not an actual VN_b', run(mutate=m)[4]['reason'])

    def test_rb_wrong_source_blocks(self):
        def m(raw):
            raw[f'{vnb(2)}.rb_d[5]'] = ['pin', f'{XR}.rb_d[6]', 2, False]
        self.assertEqual(run(mutate=m)[2]['status'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
