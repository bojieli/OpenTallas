import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from kv_gen_safety import bits, clock_pins, export, free_rectangles


class GenSafetyTests(unittest.TestCase):
    def fixture(self, root):
        (root / 'die.v').write_text('''module die;
  wire [0:0] n_clk_core_c;
  wire [0:0] n_clk_core_W;
  wire [1:0] data;
  src a (.ck(n_clk_core_c[0]), .b(data));
  dst b (.ck(n_clk_core_W[0]), .a(data));
endmodule
''')
        lines = []
        for mst, direction, port in [('src', 'OUTPUT', 'b'), ('dst', 'INPUT', 'a')]:
            lines.extend([f'MACRO {mst}', '  SIZE 10 BY 10 ;'])
            for name, dr, use, xy in [('ck', 'INPUT', 'CLOCK', (5, 5)),
                                      (port+'[0]', direction, 'SIGNAL', (0, 1)),
                                      (port+'[1]', direction, 'SIGNAL', (9, 9))]:
                x, y = xy
                lines.extend([f'  PIN {name}', f'    DIRECTION {dr} ;', f'    USE {use} ;',
                              '    PORT', '      LAYER M3 ;', f'      RECT {x} {y} {x+.1} {y+.1} ;',
                              '    END', f'  END {name}'])
            lines.append(f'END {mst}')
        (root / 'elements.lef').write_text('\n'.join(lines))
        (root / 'place.tcl').write_text('ot_mts::place [$_blk findInst a] 0 0 R0\n'
                                       'ot_mts::place [$_blk findInst b] 500 0 MY\n')
        (root / 'manifest.json').write_text(json.dumps(dict(die_um=[520, 20])))

    def test_constants_keep_bit_positions(self):
        self.assertEqual(bits("{v[1:0], 2'b00}", {}), [None, None, 'v[0]', 'v[1]'])
        with self.assertRaises(ValueError):
            bits('a & b', {})

    def test_real_pin_span_and_unlanded_crossing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            f = export(root)
            self.assertEqual(f['coverage']['driver_load_bit_pairs'], 2)
            self.assertAlmostEqual(f['wires'][0]['max_um'], 509.9)
            self.assertEqual(f['wires'][0]['witness_bits'], [0, 0])
            self.assertIsNone(f['crossings'][0]['landing'])
            self.assertEqual(len(f['regions']), 2)

    def test_missing_direction_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            lef = root / 'elements.lef'
            lef.write_text(lef.read_text().replace('DIRECTION INPUT ;', ''))
            with self.assertRaisesRegex(ValueError, 'missing LEF direction'):
                export(root)

    def test_unknown_multiroot_is_not_a_clock_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            p = root / 'die.v'
            p.write_text(p.read_text().replace('.ck(n_clk_core_c[0]),',
                                               '.ck(n_clk_core_c[0]), .clk_aux(n_clk_core_W[0]),'))
            # Add a real auxiliary clock pin; no arbitrary pin-to-root guess.
            lef = root / 'elements.lef'
            lef.write_text(lef.read_text().replace('END src', '  PIN clk_aux\n DIRECTION INPUT ;\n USE CLOCK ;\n PORT\n LAYER M3 ;\n RECT 5 5 5.1 5.1 ;\n END\n END clk_aux\nEND src'))
            f = export(root)
            self.assertEqual(f['regions']['None']['root'], None)

    def test_channels_exclude_macro_wall(self):
        rs = free_rectangles([100, 100], [[40, 0, 60, 100]])
        self.assertEqual(rs, [[0.0, 0.0, 40, 100], [60, 0.0, 100, 100]])

    def test_actual_liberty_clock_arc_disambiguates_regions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            p = root / 'die.v'
            p.write_text(p.read_text().replace('.ck(n_clk_core_c[0]),',
                                               '.ck(n_clk_core_c[0]), .clk_aux(n_clk_core_W[0]),'))
            lef = root / 'elements.lef'
            lef.write_text(lef.read_text().replace('END src', '  PIN clk_aux\n DIRECTION INPUT ;\n USE CLOCK ;\n PORT\n LAYER M3 ;\n RECT 5 5 5.1 5.1 ;\n END\n END clk_aux\nEND src'))
            lib = root / 'fixture_tt.lib'
            lib.write_text('''library(x) { cell(src) {
              pin("b[0]") { timing() { related_pin : "ck"; timing_type : rising_edge; } }
              pin("b[1]") { timing() { related_pin : "clk_aux"; timing_type : rising_edge; } }
            } }''')
            mapping, hashes = clock_pins(root)
            self.assertEqual(mapping[('src', 'b[0]')], {'ck'})
            self.assertEqual(len(hashes['fixture_tt.lib']), 64)
            f = export(root, libs=root)
            self.assertNotIn('None', f['regions'])
            self.assertEqual(len(f['crossings']), 1)

    def test_geometric_inout_needs_actual_source_direction(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            lef = root/'elements.lef'
            lef.write_text(lef.read_text().replace('DIRECTION OUTPUT', 'DIRECTION INOUT'))
            with self.assertRaisesRegex(ValueError, 'missing LEF direction on connected net'):
                export(root)
            source = root/'source_ports.json'
            source.write_text(json.dumps(dict(die_sha256=hashlib.sha256((root/'die.v').read_bytes()).hexdigest(),
                masters={'src': dict(ports={'b': ['OUTPUT']*2}), 'dst': dict(ports={'a': ['INPUT']*2})})))
            f = export(root, source_ports=source)
            self.assertEqual(f['coverage']['driver_load_bit_pairs'], 2)

    def test_actual_source_and_definite_lef_conflict_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            source = root/'source_ports.json'
            source.write_text(json.dumps(dict(die_sha256=hashlib.sha256((root/'die.v').read_bytes()).hexdigest(),
                masters={'src': dict(ports={'b': ['INPUT']*2}), 'dst': dict(ports={'a': ['INPUT']*2})})))
            with self.assertRaisesRegex(ValueError, 'LEF/source direction conflict'):
                export(root, source_ports=source)


if __name__ == '__main__':
    unittest.main()
