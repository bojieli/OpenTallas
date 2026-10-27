"""Pinned vendor physical functions in CDC elaboration; real tool cases run only on the fleet."""
import copy
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import gray_fifo_cdc_constraints as G
import lint_receipt as L
from test_gray_fifo_cdc_constraints import FIXTURE, REVIEWED, ROOT, spec

LIB = 'physical/asap7_stdcell_native_models/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib'
SHA = 'fa92e6ab1481810602811b1eea54bc016a341f11fb5188d7512c026599adf038'
CELL = 'AND2x2_ASAP7_75t_R'


def entry():
    return dict(path=LIB, sha256=SHA, cells=[CELL])


def declared():
    s = spec()
    s[G.EXTENSIONS] = dict(tech_cell_liberties=[entry()])
    return s


class Schema(unittest.TestCase):
    def test_actual_bytes_and_receipt_inputs(self):
        s = declared()
        self.assertEqual(G.tech_cell_libraries(s, ROOT), ((LIB, SHA, (CELL,)),))
        self.assertIn(LIB, L.input_files(s, ROOT))
        self.assertEqual(L.projection(s)[G.EXTENSIONS], s[G.EXTENSIONS])
        self.assertEqual(hashlib.sha256((ROOT / LIB).read_bytes()).hexdigest(), SHA)

    def test_gate_references_include_actual_liberty_bytes(self):
        import ref_tile as RT
        s = declared(); s.update(route={}, children=[], macros=[])
        self.assertIn(LIB, RT.referenced_paths(s, 'physical/ref_tile/gf_fix'))

    def test_undeclared_legacy_spec_keeps_original_elaboration_inputs(self):
        self.assertEqual(G.tech_cell_libraries(spec(), ROOT), ())
        self.assertNotIn(LIB, L.input_files(spec(), ROOT))

    def test_unknown_models_and_unsafe_or_duplicate_entries_refuse(self):
        for change in (dict(path='../outside.lib'), dict(path='/absolute.lib'), dict(sha256='0'*64),
                       dict(cells=['OR2x2_ASAP7_75t_R']), dict(cells=[CELL, CELL]), dict(extra=True)):
            s = declared()
            s[G.EXTENSIONS]['tech_cell_liberties'][0].update(change)
            with self.assertRaises(G.GrayFifoError):
                G.tech_cell_libraries(s, ROOT)
        for rows in ([], [entry(), entry()]):
            s = declared(); s[G.EXTENSIONS]['tech_cell_liberties'] = rows
            with self.assertRaises(G.GrayFifoError):
                G.tech_cell_libraries(s, ROOT)

    def test_mutated_real_function_refuses_even_with_updated_declared_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / LIB; target.parent.mkdir(parents=True)
            data = (ROOT / LIB).read_bytes()
            changed = data.replace(b'function : "(A * B)"', b'function : "(A + B)"', 1)
            self.assertNotEqual(data, changed)
            target.write_bytes(changed)
            s = declared()
            with self.assertRaisesRegex(G.GrayFifoError, 'bytes differ'):
                G.tech_cell_libraries(s, root)
            s[G.EXTENSIONS]['tech_cell_liberties'][0]['sha256'] = hashlib.sha256(changed).hexdigest()
            with self.assertRaisesRegex(G.GrayFifoError, 'not a reviewed actual library'):
                G.tech_cell_libraries(s, root)


@unittest.skipUnless(os.environ.get('OT_CDC_TECH_FLEET') == '1', 'actual Yosys cases require fleet admission')
class ActualCdc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        for path in REVIEWED + [LIB]:
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / path, target)
        # Real physical AND masks the actual FIFO read-valid with a same-family request. No FIFO source changes.
        self.rtl = FIXTURE.replace('wire pop = !empty;',
            'wire pop; ' + CELL + ' u_real_cell (.A(!empty), .B(c_wr), .Y(pop));')
        (self.root / 'gf_fix.sv').write_text(self.rtl)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_function_passes_and_is_source_bound(self):
        record = G.lint(declared(), self.root)
        self.assertEqual(record['tech_cell_liberties'], [entry()])
        self.assertIn('u_hc', {f['scope'] for f in record['fifos'].values()})

    def test_real_cell_without_declared_model_refuses(self):
        with self.assertRaisesRegex(G.GrayFifoError, 'elaboration failed'):
            G.lint(spec(), self.root)

    def test_other_vendor_master_remains_unknown(self):
        (self.root / 'gf_fix.sv').write_text(self.rtl.replace(CELL, 'OR2x2_ASAP7_75t_R'))
        with self.assertRaisesRegex(G.GrayFifoError, 'elaboration failed'):
            G.lint(declared(), self.root)

    def test_rtl_shadow_of_the_physical_master_refuses(self):
        (self.root / 'gf_fix.sv').write_text(self.rtl + '\nmodule ' + CELL +
            '(input A,B, output Y); assign Y=A|B; endmodule\n')
        with self.assertRaisesRegex(G.GrayFifoError, 'elaboration failed'):
            G.lint(declared(), self.root)

    def test_existing_cross_family_and_invalid_storage_mutants_still_refuse(self):
        for mutant in (2, 3):
            s = declared(); s['params']['MUT'] = mutant
            with self.assertRaises(G.GrayFifoError):
                G.lint(s, self.root)
