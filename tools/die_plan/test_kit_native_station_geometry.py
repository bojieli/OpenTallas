"""Native station placement survives kit-rtl wrapping; no synthesis needed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind


class NativeGeometry(unittest.TestCase):
    RTL = 'module bound;\n ot_dp_st #(.W(1)) u_ist_o_0 (.clk(clk), .d(d), .q(q));\nendmodule\n'

    def test_sidecar_is_carried_next_to_first_wrapper_rtl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'native_internal_stations' / 't__v1'
            source.mkdir(parents=True)
            text = 'is_place {*u_ist_o_0[./]*} 100 200 ist:o\n'
            (source / 'istations.tcl').write_text(text)
            receipt = dict(entries=[dict(stations=['u_ist_o_0'])])
            (source / 'receipt.json').write_text(json.dumps(receipt))
            (source / 'plan.json').write_text(json.dumps(dict(partition_types={})))
            kit = root / 'kit'; kit.mkdir()
            result = bind.kit_native_station_geometry(root, 't__v1', self.RTL, kit)
            self.assertEqual((kit / 'istations.tcl').read_text(), text)
            self.assertEqual(json.loads((kit / 'native_station_receipt.json').read_text()), receipt)
            self.assertEqual(result['rtl_cycles_changed'], 0)
            self.assertEqual(result['stations'], 1)
            self.assertEqual(result['plan'], 'native_station_plan.json')
            self.assertTrue((kit / result['plan']).is_file())
            # This is the same lookup gen_phys uses on rtl_files[:1].
            self.assertTrue(((kit / 'wrapper.sv').parent / 'istations.tcl').is_file())

    def test_native_rtl_cannot_silently_lose_missing_or_partial_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); kit = root / 'kit'; kit.mkdir()
            with self.assertRaisesRegex(bind.BindError, 'requires'):
                bind.kit_native_station_geometry(root, 't', self.RTL, kit)
            source = root / 'native_internal_stations' / 't'; source.mkdir(parents=True)
            (source / 'istations.tcl').write_text('is_place {*u_ist_o_0[./]*} 100 200 ist:o\n')
            for names in ([], ['u_ist_o_0', 'u_ist_o_1'], ['u_ist_o_0', 'u_ist_o_0']):
                (source / 'receipt.json').write_text(json.dumps(dict(entries=[dict(stations=names)])))
                with self.assertRaisesRegex(bind.BindError, 'mismatch'):
                    bind.kit_native_station_geometry(root, 't', self.RTL, kit)
            (source / 'receipt.json').write_text(json.dumps(dict(entries=[dict(stations=['u_ist_o_0'])])))
            (source / 'istations.tcl').write_text('# u_ist_o_0: no placement operation\n')
            with self.assertRaisesRegex(bind.BindError, 'sites missing'):
                bind.kit_native_station_geometry(root, 't', self.RTL, kit)

    def test_non_native_kit_stays_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(bind.kit_native_station_geometry(root, 't', 'module bound; endmodule', root))
            self.assertEqual(list(root.iterdir()), [])

if __name__ == '__main__':
    unittest.main()
