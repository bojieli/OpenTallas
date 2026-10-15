import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_rom_fulldie import Master
from qwen_split import native_graph_bind as N


class AssignedOrientation(unittest.TestCase):
    def assign(self, orient, peer):
        inst = SimpleNamespace(name='dut', master='leaf', x=1000., y=2000.,
                               w=777.576, h=518.376, orient=orient)
        ports = {'data': (8, 'input'), 'ck': (1, 'input')}
        masters = {}
        peers = {('dut', 'data'): [SimpleNamespace(x=peer[0], y=peer[1], w=0., h=0.)]}
        with patch.object(N, 'rtl_ports', return_value=ports):
            N.assign_pins(masters, {}, Master, inst, 'leaf', 'unused.sv', peers, None)
        q = masters['leaf']
        result = {}
        for port in ports:
            _, _, face, layer, positions, _ = q.ports[port]
            points = []
            for z in positions:
                x, y = {'N': (z, q.h), 'S': (z, 0), 'W': (0, z), 'E': (q.w, z)}[face]
                if orient in ('MY', 'R180'):
                    x = q.w-x
                if orient in ('MX', 'R180'):
                    y = q.h-y
                points.append((round(inst.x+x, 4), round(inst.y+y, 4)))
            result[port] = (layer, points)
        return result

    def test_every_bit_and_clock_stay_toward_same_global_peer(self):
        # Mirrors used for the adopted band0/1 train must retain the global
        # peer-facing pin and numeric bus order, including fallback clock pins.
        for peer in ((1300., 1000.), (1300., 4000.), (0., 2300.), (3000., 2300.)):
            expected = self.assign('R0', peer)
            for orient in ('MX', 'MY', 'R180'):
                with self.subTest(peer=peer, orient=orient):
                    self.assertEqual(self.assign(orient, peer), expected)

    def test_actual_mx_band_rq_uses_local_north_for_global_south(self):
        data = self.assign('MX', (1300., 1000.))['data'][1]
        self.assertTrue(all(y == 2000. for x, y in data))
        self.assertLess(data[0][0], data[-1][0])

    def test_unsupported_rotated_axis_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'unsupported pin-assignment orientation'):
            self.assign('R90', (1300., 1000.))

    def test_shared_master_with_incompatible_orientation_requires_clone(self):
        a = SimpleNamespace(name='a', master='leaf', w=777.576, h=518.376, orient='MX')
        b = SimpleNamespace(name='b', master='leaf', w=777.576, h=518.376, orient='R0')
        with self.assertRaisesRegex(ValueError, 'clone physical masters'):
            N.assign_pins({}, {'insts': [a, b]}, Master, a, 'leaf', 'unused.sv', {}, None)


if __name__ == '__main__':
    unittest.main()
