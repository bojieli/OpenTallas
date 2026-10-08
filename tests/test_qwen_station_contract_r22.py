"""Contract gates: a representative timing arc must never clear signoff."""
import sys
from pathlib import Path
import unittest
import tempfile
import types
import json
import hashlib
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qwen_die_etm_map import view_eligibility, require_interface_complete, main
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

    def test_mapper_records_actual_representative_pin_and_refuses_signoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for part in ['etm', 'station/cst', 'station/chead', 'assumed']:
                (root/part).mkdir(parents=True)
            pin_bodies = {'clk': ' direction : input;', 'a_d[0]': ' direction : input;',
                          'b_d[0]': ' direction : output;'}
            cell = '  cell ("mock") {\n' + ''.join('    pin("%s") {%s}\n' % x for x in pin_bodies.items()) + '  }\n'
            for corner in ['ss', 'ff']:
                text = 'library (mock) {\n' + cell + '}\n'
                for rel in [f'etm/ot_qwen_stream4_cdc_pc_{corner}.lib',
                            f'etm/ot_qwen_slab_port_group_{corner}.lib',
                            f'station/cst/ot_qwen_die_station_cst_{corner}.lib',
                            f'station/chead/ot_qwen_die_station_chead_{corner}.lib',
                            f'assumed/qfd_elements_{corner}.lib']:
                    (root/rel).write_text(text)
            (root/'elements.lef').write_text('MACRO qfd_cdc\n PIN clk\nEND qfd_cdc\n'
                'MACRO qfd_cst_n\n PIN ck[0]\n PIN a[0]\n PIN b[0]\nEND qfd_cst_n\n')
            (root/'stubs.sv').write_text('module qfd_cst_n (\n input wire [0:0] ck,\n'
                ' input wire [0:0] a,\n output wire [0:0] b\n);\nendmodule\n')
            lint = types.SimpleNamespace(real_blocks=lambda _: {'qfd_cdc': {'binding': {'clk': ['clk']}}})
            argv = ['--etm', str(root/'etm'), '--lef', str(root/'elements.lef'),
                    '--assumed', str(root/'assumed'), '--station-etm', str(root/'station'),
                    '--stubs', str(root/'stubs.sv'), '--out', str(root/'out')]
            with patch.dict(sys.modules, {'die_top_lint': lint}):
                main(argv)
                with self.assertRaisesRegex(ValueError, 'qfd_cst_n'):
                    main(argv + ['--require-final-signoff'])
            record = json.loads((root/'out/views.json').read_text())
            pin = record['source_pin_bindings']['ss']['qfd_cst_n']['b[0]']
            self.assertEqual(pin['pin'], 'b_d[0]')
            self.assertEqual(pin['source_pin_sha256'], hashlib.sha256(pin_bodies['b_d[0]'].encode()).hexdigest())
            self.assertFalse(record['final_die_signoff_eligible'])
            self.assertTrue(record['pathfinding_only'])

    def test_bus_contract_no_overlap_or_missing_payload(self):
        m = model(path_hops=12)
        for name, expected in [('corridor', 509), ('tap', 509)]:
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
