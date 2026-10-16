"""Generated pin maps must survive the peer motion used for spread registers."""
import copy
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


class SpreadLoadPins(unittest.TestCase):
    def fixture(self, orient='R0'):
        load = G.Inst('load', 'test_hub', 100, 100, 200, 300, orient, kind='hub')
        peer = G.Inst('peer', 'dsfd_hstnh_8', 80, 150, 17.256, 17.28, kind='hstn')
        near = G.Inst('near', 'dsfd_hstnh_8', 80, 167, 17.256, 17.28, kind='hstn')
        ports = {'inp': ('input', 8), 'neighbor': ('input', 8)}
        model = dict(insts=[load, peer, near], buses=[
            ('a', 'hub', 8, [('peer', 'dq'), ('load', 'inp')]),
            ('b', 'hub', 8, [('near', 'dq'), ('load', 'neighbor')])], pdir={
                'test_hub': ports,
                'dsfd_hstnh_8': {'di': ('input', 8), 'dq': ('output', 8), 'ck': ('input', 1)}})
        original = G.masters_r8(model)['test_hub']
        model['spread_load_pin_maps'] = {'test_hub': dict(
            outline=[original.w, original.h], ports=copy.deepcopy(original.ports),
            order=list(original.order), port_signature=dict(ports))}
        return model, original, load, peer, near

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('REAL_FILES', {}), ('ASSIGNED_PINS_DIR', None),
                            ('PEER_PIN_POS', True), ('CK_RULE', False)]:
            self.stack.enter_context(patch.object(G, name, value))
        self.stack.enter_context(patch.object(G, '_init_real'))

    def test_reemission_preserves_all_pins_after_peer_relocation(self):
        for orient in ('R0', 'MY', 'MX'):
            with self.subTest(orient=orient):
                model, original, _, peer, near = self.fixture(orient)
                peer.y += 40
                peer.h += 80
                near.y -= 30
                restored = G.masters_r8(model)['test_hub']
                expected = G.Q.lef_text(original, 1, {})
                self.assertEqual(expected, G.Q.lef_text(restored, 1, {}))
                # Emission cannot mutate the retained access rectangles.
                restored.ports.clear()
                self.assertEqual(expected, G.Q.lef_text(G.masters_r8(model)['test_hub'], 1, {}))
                # Negative control reproduces the old peer-driven pin drift.
                del model['spread_load_pin_maps']
                self.assertNotEqual(original.ports, G.masters_r8(model)['test_hub'].ports)

    def test_current_assigned_pins_remain_authoritative(self):
        model, original, *_ = self.fixture()
        def assign(master, _ports):
            if master.name == 'test_hub':
                master.ports['inp'] = ('face', 8, 'W', 'M4', 20.0, 1)
        with patch.object(G, '_assigned_physical_pins', side_effect=assign):
            actual = G.masters_r8(model)['test_hub']
        self.assertEqual(actual.ports['inp'][4], 20.0)
        self.assertEqual(original.ports['neighbor'], actual.ports['neighbor'])

    def test_changed_outline_refuses_stale_map(self):
        model, _, load, *_ = self.fixture()
        load.h += 2.16
        with self.assertRaisesRegex(AssertionError, 'outline changed'):
            G.masters_r8(model)

    def test_changed_port_width_refuses_stale_map(self):
        model, *_ = self.fixture()
        model['pdir']['test_hub']['inp'] = ('input', 9)
        with self.assertRaisesRegex(AssertionError, 'port signature changed'):
            G.masters_r8(model)

    def test_actual_spread_adoption_retains_assessed_rectangles(self):
        load = G.Inst('load', 'test_hub', 120, 0, 40, 170, kind='hub')
        terminal = G.Inst('terminal', 'dsfd_hstnh_128', 100, 50, 17.28, 17.28, kind='hstn')
        previous = G.Inst('previous', 'dsfd_hstnh_128', 0, 50, 17.28, 17.28, kind='hstn')
        model = dict(insts=[load, terminal, previous], buses=[
            ('in', 'hub', 128, [('previous', 'dq'), ('terminal', 'di')]),
            ('out', 'hub', 128, [('terminal', 'dq'), ('load', 'inp')])], pdir={
                'test_hub': {'inp': ('input', 128)},
                'dsfd_hstnh_128': {'di': ('input', 128), 'dq': ('output', 128), 'ck': ('input', 1)}})
        original_faces = G._faces_r8
        ys = [10 + i * .048 for i in range(64)] + [100 + i * .048 for i in range(64)]

        def moving_load_pins(m, master, inst, ports):
            if master.name != 'test_hub':
                return original_faces(m, master, inst, ports)
            # Model the generated hub's feedback from the resized spread peer.
            shift = 33 if m.get('spread_stations') else 0
            master.ports['inp'] = ('rects', [
                (f'inp[{i}]', 'M4', (0, y + shift - .012, .192, y + shift + .012))
                for i, y in enumerate(ys)])
            master.order.append('inp')

        def texts(m):
            return [G.lef_text(master, 1, {})[0] for master in G.masters_r8(m).values()]

        with patch.object(G, 'real_ports', return_value={}), patch.object(G, 'ALIGN_EXT', [True]), \
                patch.object(G, '_faces_r8', side_effect=moving_load_pins), \
                patch.object(G, 'die_lef_texts', side_effect=texts):
            G.align_station_jogs(model)
            self.assertIn(terminal.master, model['spread_stations'])
            fixed = G.masters_r8(model)['test_hub']
            self.assertEqual([round((r[2][1] + r[2][3]) / 2, 6) for r in fixed.ports['inp'][1]],
                             [round(y, 6) for y in ys])
            self.assertEqual(G.lef_text(fixed, 1, {}),
                             G.lef_text(G.masters_r8(model)['test_hub'], 1, {}))
            del model['spread_load_pin_maps']
            self.assertNotEqual(fixed.ports, G.masters_r8(model)['test_hub'].ports)


if __name__ == '__main__':
    unittest.main()
