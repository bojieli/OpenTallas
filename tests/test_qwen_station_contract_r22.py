"""Contract gates: a representative timing arc must never clear signoff."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qwen_die_etm_map import view_eligibility, require_interface_complete
from uarch_model_qwen_station_r22 import model


class StationContract(unittest.TestCase):
    def test_routed_bit_zero_still_blocks_final(self):
        views = view_eligibility(['qfd_cdc', 'qfd_cst_n', 'qfd_port_tiles_0'],
                                 ['qfd_port_tiles_0'], ['qfd_cst_n'])
        self.assertTrue(views['qfd_cdc']['interface_complete'])
        self.assertEqual(views['qfd_cst_n']['classification'], 'representative_by_direction')
        self.assertFalse(views['qfd_port_tiles_0']['final_die_signoff_eligible'])
        with self.assertRaisesRegex(ValueError, 'qfd_cst_n'):
            require_interface_complete(views)
        require_interface_complete({'qfd_cdc': views['qfd_cdc']})

    def test_external_and_assumed_require_audit(self):
        views = view_eligibility(['qfd_tile', 'ot_hbm3e_phy'], [], [])
        self.assertEqual(views['qfd_tile']['classification'], 'assumed_constant')
        with self.assertRaises(ValueError):
            require_interface_complete(views)

    def test_bus_contract_no_overlap_or_missing_payload(self):
        m = model(path_hops=12)
        for name, expected in [('corridor', 574), ('tap', 511)]:
            used = []
            for field in m['proposed_bundle_map'][name]:
                used.extend(range(field['lo'], field['lo'] + field['width']))
            self.assertEqual(sorted(used), list(range(expected)))
        self.assertEqual(sum(x['width'] for x in m['payload_map']), 508)
        self.assertIsNone(m['selected_tile']['ready_port'])
        self.assertEqual(m['latency']['fault_path_cycles'], 24)
        self.assertFalse(m['latency']['headline_adoption'])
        self.assertEqual(m['state']['FIFO_storage_bits'], 0)
        self.assertEqual(m['boundaries']['extra_bits_per_boundary'], 186)
        self.assertTrue(m['geometry']['geometric_pin_fit'])


if __name__ == '__main__':
    unittest.main()
