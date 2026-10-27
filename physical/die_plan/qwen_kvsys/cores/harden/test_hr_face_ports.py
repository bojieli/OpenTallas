"""Adversarial controls for zero-cycle boundary register recutting."""
import copy
import unittest
import tempfile
from pathlib import Path
import gen_core_kit_kv as G
import hr_face_ports as H


def pair(second_clear):
    def flop(q, clear):
        return dict(type='$dffsr', parameters=dict(WIDTH='1', CLK_POLARITY='1', SET_POLARITY='1', CLR_POLARITY='1'),
                    attributes={}, port_directions=dict(D='input', Q='output', CLK='input', SET='input', CLR='input'),
                    connections=dict(D=[2], Q=[q], CLK=[3], SET=['0'], CLR=[clear]))
    return dict(modules=dict(top=dict(ports=dict(d=dict(direction='input', bits=[2]),
                ck=dict(direction='input', bits=[3])), netnames=dict(d=dict(bits=[2], attributes={}),
                ck=dict(bits=[3], attributes={})), cells=dict(a=flop(4,5),b=flop(6,second_clear)))))


class BoundaryControls(unittest.TestCase):
    def test_different_async_clear_must_not_merge(self):
        _, r = H.transform(pair(7), 'top')
        self.assertEqual(r['merged_in'], [])
        self.assertEqual(r['n_multi_in'], 1)

    def test_identical_async_clear_can_merge(self):
        _, r = H.transform(pair(5), 'top')
        self.assertEqual(len(r['merged_in']), 1)
        self.assertEqual(r['n_multi_in'], 0)

    def test_existing_equal_private_outputs_are_preserved(self):
        j = pair(5)
        m = j['modules']['top']
        del m['ports']['d']
        for port, bit in [('qa',4),('qb',6)]:
            m['ports'][port] = dict(direction='output',bits=[bit])
            m['netnames'][port] = dict(bits=[bit],attributes={})
        out, r = H.transform(j, 'top')
        self.assertEqual(r['added_ff_bits'],0)
        for port, cell in [('qa','a'),('qb','b')]:
            self.assertEqual(out['modules']['top']['cells'][cell]['attributes']['keep'],H.ONE)
            self.assertEqual(out['modules']['top']['netnames'][port]['attributes']['keep'],H.ONE)

    def test_different_initial_states_must_not_merge(self):
        j = pair(5)
        j['modules']['top']['netnames'].update(
            qa=dict(bits=[4], attributes=dict(init='0')),
            qb=dict(bits=[6], attributes=dict(init='1')))
        _, r = H.transform(j, 'top')
        self.assertEqual(r['merged_in'], [])

    def test_private_output_preserves_both_initial_states(self):
        j = pair(5)
        m = j['modules']['top']
        m['ports']['q'] = dict(direction='output', bits=[4])
        m['netnames']['q'] = dict(bits=[4], attributes=dict(init='1'))
        m['cells']['feedback'] = dict(type='$not', parameters={}, attributes={},
            port_directions=dict(A='input', Y='output'), connections=dict(A=[4], Y=[8]))
        out, r = H.transform(j, 'top')
        m = out['modules']['top']
        private = m['ports']['q']['bits'][0]
        self.assertNotEqual(private, 4)
        self.assertEqual(m['netnames']['q']['attributes']['init'], '1')
        self.assertTrue(any(n['bits'] == [4] and n.get('attributes', {}).get('init') == '1'
                            for n in m['netnames'].values()))

    def test_escaped_macro_instance_keeps_reached_master(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'core.v'
            f.write_text('module top;\n  ot_sram_example \\u_slice.g_grp[0].u_rb ( .CK(ck) );\nendmodule\n')
            self.assertIn('ot_sram_example', G.reached_modules([f], 'top').split())

    def test_reset_pins_are_not_data_landing_candidates(self):
        for n in ('rrst_n','wrst_n','u_rx__rrst_n','u_tx__wrst_n'):
            self.assertIsNotNone(H.CLKRST.search(n))


if __name__ == '__main__':
    unittest.main()


class KeptFace(unittest.TestCase):
    """KV-KITS-7: --kept-face moves each face register bit into a keep_hierarchy 1-bit cell (constant-D output and
    dead input captures survive synthesis; core_tx shared299/dropped215)."""
    def j(self):
        def ff(d, q):
            return dict(type="$adff", parameters=dict(WIDTH="00000000000000000000000000000010", CLK_POLARITY="1",
                        ARST_POLARITY="0", ARST_VALUE="00"), attributes={},
                        port_directions=dict(D="input", Q="output", CLK="input", ARST="input"),
                        connections=dict(D=d, Q=q, CLK=[3], ARST=[4]))
        return dict(modules=dict(top=dict(ports=dict(ck=dict(direction="input", bits=[3]),
                    rst_n=dict(direction="input", bits=[4]), a=dict(direction="input", bits=[5, 6]),
                    c=dict(direction="output", bits=[7, 8])),
                    netnames=dict(ck=dict(bits=[3], attributes={}), rst_n=dict(bits=[4], attributes={}),
                                  a=dict(bits=[5, 6], attributes={}), c=dict(bits=[7, 8], attributes={}),
                                  q=dict(bits=[9, 10], attributes={})),
                    cells=dict(cap=ff([5, 6], [9, 10]), cst=ff(["0", "0"], [7, 8])))))

    def test_every_face_bit_wrapped_same_flop(self):
        out, r = H.transform(self.j(), "top")
        out, k = H.kept_face(out, "top")
        self.assertEqual(k["kept_face_bits"], 4)
        mods = [m for m in out["modules"] if m.startswith(H.KFF_PREFIX)]
        self.assertEqual(len(mods), 1)                       # same signature -> one 1-bit module
        mm = out["modules"][mods[0]]
        self.assertEqual(mm["attributes"]["keep_hierarchy"], H.ONE)
        self.assertEqual(mm["cells"]["ff"]["type"], "$adff")
        self.assertEqual(mm["cells"]["ff"]["parameters"]["ARST_VALUE"], "0")
        top = out["modules"]["top"]["cells"]
        inst = [c for n, c in top.items() if c["type"] == mods[0]]
        self.assertEqual(sorted(tuple(c["connections"]["Q"]) for c in inst), [(7,), (8,), (9,), (10,)])
        self.assertEqual(sorted((str(c["connections"]["D"]) for c in inst)), sorted(str(x) for x in [["0"], ["0"], [5], [6]]))
        for n in ("cap", "cst"):                               # originals no longer drive any face / internal net
            self.assertFalse(set(top[n]["connections"]["Q"]) & {7, 8, 9, 10})
