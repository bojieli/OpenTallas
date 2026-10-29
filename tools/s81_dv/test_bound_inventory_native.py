"""Current-plan hierarchy discovery must refuse guessed or ambiguous atoms."""
from pathlib import Path
import tempfile
import unittest

from layer_prog.bound_inventory import native_control_units, native_vp_units


class NativeUnits(unittest.TestCase):
    def test_repeated_source_copies_and_selected_parent(self):
        root = {'cells': {f'u_s_{col}{tier}': {'type': 'slice'}
                         for col in range(8) for tier in ('S', 'N')}}
        graph = {'modules': {'top': root,
                 'slice': {'cells': {f'leaf{k}': {'type': 'vp'} for k in range(5)}},
                 'vp': {'attributes': {'hdlname': 'ot_s81sl_vp'}}}}
        self.assertEqual(len(native_vp_units(graph, {'top': 'top'})), 80)
        graph['modules']['bad_slice'] = {'attributes': {'hdlname': 'bad_slice'},
                                        'cells': {'only': {'type': 'vp'}}}
        with self.assertRaisesRegex(ValueError, 'u_s_5S: actual source needs five'):
            native_vp_units(graph, {'top': 'top', 'substitute_parent': [
                {'inst': 'u_s_5S', 'module': 'bad_slice'}]})

    def test_actual_wrappers_and_missing_ambiguity(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / 'part.sv'
            paths = [f'u_s_{col}{tier}.u_{"sl" if col in (0, 7) else "lp"}.{atom}'
                     for col in range(8) for tier in ('S', 'N') for atom in ('u_xg', 'u_xr')]
            file.write_text(''.join(f' // as-built {p}\n' for p in paths))
            units = native_control_units(root)
            self.assertEqual(len(units), 50)
            self.assertIn('u_s_0S.u_sl.u_xg', units)
            self.assertIn('u_s_4N.u_lp.u_xr', units)
            self.assertNotIn('u_s_0S.u_xg', units)
            file.write_text(''.join(f' // as-built {p}\n' for p in paths[1:]))
            with self.assertRaisesRegex(ValueError, 'one exact u_xg'):
                native_control_units(root)
            file.write_text(''.join(f' // as-built {p}\n' for p in paths + ['u_s_0S.other.u_xg']))
            with self.assertRaisesRegex(ValueError, 'one exact u_xg'):
                native_control_units(root)


if __name__ == '__main__':
    unittest.main()
