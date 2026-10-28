"""Adversarial controls for zero-cycle boundary register recutting."""
import copy
import random
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


def _cell(typ, conns, dirs, **params):
    return dict(type=typ, parameters={k: str(v) for k, v in params.items()}, attributes={},
                port_directions=dirs, connections=conns)


def abort_core(second_flop=False):
    """core_tx shape: abort_q <= wrap_clear ? 0 : package_abort  (pin -> $not/$and cone -> one $adff D)."""
    I, O = 'input', 'output'
    cells = dict(
        inv=_cell('$not', dict(A=[5], Y=[6]), dict(A=I, Y=O), A_WIDTH=1, Y_WIDTH=1),
        andc=_cell('$and', dict(A=[2], B=[6], Y=[7]), dict(A=I, B=I, Y=O), A_WIDTH=1, B_WIDTH=1, Y_WIDTH=1),
        f=_cell('$adff', dict(CLK=[3], ARST=[9], D=[7], Q=[8]), dict(CLK=I, ARST=I, D=I, Q=O),
                WIDTH=1, CLK_POLARITY=1, ARST_POLARITY=0, ARST_VALUE='0'),
        use=_cell('$xor', dict(A=[8], B=[5], Y=[10]), dict(A=I, B=I, Y=O), A_WIDTH=1, B_WIDTH=1, Y_WIDTH=1))
    if second_flop:
        cells['f2'] = _cell('$adff', dict(CLK=[3], ARST=[9], D=[7], Q=[11]), dict(CLK=I, ARST=I, D=I, Q=O),
                            WIDTH=1, CLK_POLARITY=1, ARST_POLARITY=0, ARST_VALUE='0')
    ports = dict(u_ctrl__package_abort=dict(direction=I, bits=[2]), ck=dict(direction=I, bits=[3]),
                 clr=dict(direction=I, bits=[5]), u_ctrl__rst_n=dict(direction=I, bits=[9]), o=dict(direction=O, bits=[10]))
    nn = {k: dict(bits=list(v['bits']), attributes={}) for k, v in ports.items()}
    nn['abort_q'] = dict(bits=[8], attributes={})
    return dict(modules=dict(top=dict(ports=ports, netnames=nn, cells=cells)))


def simulate(j, stim):
    """1-bit cycle simulation of the JSON (cells used by abort_core + the retime); returns the o trace."""
    m = j['modules']['top']
    st = {cn: (c['parameters'].get('ARST_VALUE', '0')[-1] == '1') for cn, c in m['cells'].items() if c['type'] == '$adff'}
    trace = []
    for vec in stim:
        v = {}
        for pn, bit in (('u_ctrl__package_abort', 2), ('clr', 5), ('u_ctrl__rst_n', 9)):
            v[m['ports'][pn]['bits'][0]] = vec[pn]
        for cn, c in m['cells'].items():
            if c['type'] == '$adff':
                v[c['connections']['Q'][0]] = st[cn]
        val = lambda b: (b == '1') if isinstance(b, str) else v[b]
        for _ in range(len(m['cells'])):
            for cn, c in m['cells'].items():
                k = c['connections']
                try:
                    if c['type'] == '$not': v[k['Y'][0]] = not val(k['A'][0])
                    elif c['type'] == '$and': v[k['Y'][0]] = val(k['A'][0]) and val(k['B'][0])
                    elif c['type'] == '$xor': v[k['Y'][0]] = val(k['A'][0]) != val(k['B'][0])
                    elif c['type'] == '$mux': v[k['Y'][0]] = val(k['B'][0]) if val(k['S'][0]) else val(k['A'][0])
                except KeyError:
                    pass
        trace.append(v[m['ports']['o']['bits'][0]])
        for cn, c in m['cells'].items():
            if c['type'] == '$adff':
                k = c['connections']
                st[cn] = (c['parameters']['ARST_VALUE'][-1] == '1') if not val(k['ARST'][0]) else val(k['D'][0])
    return trace


def live_loads(j, port):
    """loads of a port bit after dead-logic removal (cells without a live output and not keep are dropped)."""
    m = j['modules']['top']
    cells = dict(m['cells'])
    outs = {b for p in m['ports'].values() if p['direction'] == 'output' for b in p['bits']}
    while True:
        used = set(outs)
        for c in cells.values():
            for p, bits in c['connections'].items():
                if c['port_directions'][p] == 'input':
                    used.update(b for b in bits if isinstance(b, int))
        dead = [cn for cn, c in cells.items() if not c['attributes'].get('keep') and not any(
            b in used for p, bits in c['connections'].items() if c['port_directions'][p] == 'output' for b in bits)]
        if not dead:
            break
        for cn in dead:
            del cells[cn]
    b = m['ports'][port]['bits'][0]
    return [(c['type'], p) for c in cells.values() for p, bits in c['connections'].items()
            if c['port_directions'][p] == 'input' and b in bits]


class RetimeInput(unittest.TestCase):
    """DIE-KV-3/CORETX 10-27: --retime-in gives an input with a cone into one flop a face capture flop, 0 cycles."""
    STIM = None

    @classmethod
    def setUpClass(cls):
        rng = random.Random(1027)
        cls.STIM = [dict(u_ctrl__package_abort=rng.random() < .5, clr=rng.random() < .3,
                         u_ctrl__rst_n=k not in (0, 1, 40)) for k in range(200)]

    def test_default_unchanged(self):
        out, r = H.transform(abort_core(), 'top')
        self.assertEqual(out, H.transform(abort_core(), 'top')[0])
        self.assertNotIn('retimed_in', r)
        self.assertEqual(r['n_logic_in'], 1)        # pin -> $and listed, nothing changed
        self.assertEqual(live_loads(out, 'u_ctrl__package_abort'), [('$and', 'A')])

    def test_retime_face_flop_zero_cycles(self):
        out, r = H.transform(abort_core(), 'top', retime_in=['u_ctrl__package_abort[0]'])
        self.assertEqual(r['n_logic_in'], 0)
        self.assertEqual(r['retimed_in'][0]['cycles'], 0)
        self.assertEqual(r['added_cycles'], 0)
        self.assertEqual(live_loads(out, 'u_ctrl__package_abort'), [('$adff', 'D')])
        self.assertEqual(simulate(out, self.STIM), simulate(abort_core(), self.STIM))

    def test_retime_mutant_is_caught(self):
        out, _ = H.transform(abort_core(), 'top', mutant=True, retime_in=['u_ctrl__package_abort[0]'])
        self.assertNotEqual(simulate(out, self.STIM), simulate(abort_core(), self.STIM))

    def test_retime_refuses_two_sink_flops(self):
        with self.assertRaises(SystemExit):
            H.transform(abort_core(second_flop=True), 'top', retime_in=['u_ctrl__package_abort[0]'])

    def test_retime_refuses_unknown_pin(self):
        with self.assertRaises(SystemExit):
            H.transform(abort_core(), 'top', retime_in=['u_ctrl__nope[0]'])


class ExtraResets(unittest.TestCase):
    CJ = dict(pin_class={'ck[0]': 'clk', 'u_ctrl__rst_n[0]': 'in', 'u_ctrl__por_n[0]': 'in', 'q[0]': 'out'})

    def test_default_none(self):
        self.assertEqual(G.extra_resets(self.CJ, ''), [])

    def test_por_n_declared(self):
        self.assertEqual(G.extra_resets(self.CJ, 'u_ctrl__por_n', ['u_ctrl__rst_n']), ['u_ctrl__por_n'])
        self.assertEqual(G.extra_resets(self.CJ, 'u_ctrl__rst_n', ['u_ctrl__rst_n']), [])

    def test_typo_or_output_refused(self):
        for n in ('u_ctrl__porn', 'q', 'ck'):
            with self.assertRaises(SystemExit):
                G.extra_resets(self.CJ, n)


if __name__ == '__main__':
    unittest.main()
