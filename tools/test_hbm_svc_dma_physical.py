import unittest
from hbm_svc_dma_physical import edge_ports, validate_pins, relay_path, HEIGHT


class PhysicalPlanTests(unittest.TestCase):
    def test_smallest_tile_two_layer_edge_allocation(self):
        ports = edge_ports(400.032)
        counts = validate_pins(ports, 400.032)
        self.assertEqual(counts['W/M4'], 1110)
        self.assertEqual(counts['E/M6'], 1110)
        # An illegal rectangle must fail the pin-fit gate.
        ports['lane_W']['pins'][0][5] = HEIGHT + 1
        with self.assertRaises(AssertionError):
            validate_pins(ports, 400.032)

    def test_seam_has_two_captures_and_bounded_wire(self):
        path = relay_path([(0,120),(1100,120)], [400,800])
        roles = [s['role'] for s in path['stages']]
        self.assertEqual(roles.count('seam_output_pin'), 2)
        self.assertEqual(roles.count('seam_input_pin'), 2)
        self.assertLessEqual(path['max_wire_hop_um'], 380)
        self.assertEqual(path['manhattan_um'], 1100)

    def test_east_stack_data_flow_reverses(self):
        p = edge_ports(400.032, reverse=True)
        self.assertEqual(p['lane_W']['direction'], 'output')
        self.assertEqual(p['credit_W']['direction'], 'input')
        self.assertEqual(p['lane_E']['direction'], 'input')


if __name__ == '__main__':
    unittest.main()
