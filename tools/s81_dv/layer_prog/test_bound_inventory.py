"""Real hierarchy alias and default-off controls for the compiler inventory."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_inventory as I
E = I.E


def design():
    return {'modules': {
        'top': {'ports': {'a': {'direction': 'input', 'bits': [2]}, 'z': {'direction': 'output', 'bits': [3]}},
                'netnames': {'a': {'bits': [2]}, 'z': {'bits': [3]}},
                'cells': {'u_s_0S': {'type': '$paramodP', 'parameters': {},
                                    'connections': {'x': [2], 'y': [3]}}}},
        '$paramodP': {'attributes': {'hdlname': 'slice'}, 'parameter_default_values': {'W': '00000100'},
                     'ports': {'x': {'direction': 'input', 'bits': [10]}, 'y': {'direction': 'output', 'bits': [10]}},
                     'netnames': {'alias': {'bits': [10]}},
                     'cells': {'u_q': {'type': 'reg', 'parameters': {}, 'connections': {'d': [10], 'q': [10]},
                                       'port_directions': {'d': 'input', 'q': 'output'}}}},
        'reg': {'attributes': {'blackbox': 1}, 'ports': {'d': {'direction': 'input', 'bits': [2]},
                 'q': {'direction': 'output', 'bits': [3]}}}}}


class InventoryTests(unittest.TestCase):
    def test_aliases_params_and_real_endpoints(self):
        rec = I.extract(design(), {'top': 'top'}, ['u_s_0S'], asbuilt_sha256='a'*64, top_sha256='b'*64)
        u = rec['units']['u_s_0S']
        self.assertEqual(u['master'], 'slice')
        self.assertEqual(u['params']['W'], "8'b00000100")
        self.assertEqual(u['ports']['x']['bits'], u['ports']['y']['bits'])
        net = str(u['ports']['x']['bits'][0])
        self.assertEqual(set(rec['drivers'][net]), {'$top.a[0]', 'u_s_0S.u_q.q[0]'})
        self.assertIn('u_s_0S.u_q.d[0]', rec['input_pins'][net])
        self.assertEqual(rec['source_asbuilt_sha256'], 'a'*64)
        self.assertEqual(rec['source_top_sha256'], 'b'*64)

    def test_default_graph_unchanged(self):
        old = E.flatten(design(), 'top')
        enabled = E.flatten(design(), 'top', retain_hierarchy_ports=['u_s_0S'])
        self.assertFalse(hasattr(old, 'instances'))
        self.assertEqual(old.top_ports, enabled.top_ports)
        self.assertEqual([(c.path, c.params, c.ports) for c in old.cells],
                         [(c.path, c.params, c.ports) for c in enabled.cells])
        self.assertEqual(old.parent, enabled.parent)

    def test_wrong_logical_unit_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, 'absent from actual source'):
            I.extract(design(), {'top': 'top'}, ['u_s_0N'], asbuilt_sha256='a'*64, top_sha256='b'*64)


if __name__ == '__main__':
    unittest.main()
