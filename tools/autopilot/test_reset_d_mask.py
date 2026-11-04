import copy
import json
from pathlib import Path
import tempfile
import unittest

import reset_d_mask as r

FIXTURE = Path(__file__).resolve().parents[2] / 'results/r2_reset_capture_1101'


class ResetDMaskTest(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((FIXTURE / 'native_fixture.json').read_text())
        self.cells = copy.deepcopy(self.fixture['cells'])
        self.rows = r.qualify_cones(self.cells)['candidates']
        self.gate = self.rows[0]['mask']
        self.capture = self.rows[0]['capture']

    def reject(self):
        with self.assertRaises(ValueError):
            r.qualify_cones(self.cells)

    def test_actual_native_positive_and_physical_join(self):
        r.proof_gate(self.fixture['lec'], self.fixture['provenance'], FIXTURE)
        self.assertEqual(len(self.rows), 9)
        result = r.physical_join(self.cells, self.fixture['physical_dump'], self.rows, self.fixture['typed_physical'])
        self.assertEqual(result['actual_capture_edges'], 9)

    def test_functional_mask_operand(self):
        self.cells[self.gate]['ports']['A'] = 'r_a[0]'
        self.reject()

    def test_or_is_not_reset_d_mask(self):
        self.cells[self.gate]['master'] = 'OR2x2_ASAP7_75t_R'
        self.reject()

    def test_extra_enable_or_capture(self):
        self.cells['extra'] = copy.deepcopy(self.cells[self.capture])
        self.reject()

    def test_added_functional_enable(self):
        old_output = self.cells[self.gate]['ports']['Y']
        self.cells['extra_enable'] = {'master': 'AND2x2_ASAP7_75t_R', 'ports': {'A': old_output, 'B': 'r_a[0]', 'Y': 'enabled'}}
        self.cells[self.capture]['ports']['D'] = 'enabled'
        self.reject()

    def test_actual_physical_or_mask(self):
        dump = self.fixture['physical_dump']
        lines = []
        for line in dump.splitlines():
            f = line.split('\t')
            if f[0] == 'C' and r.norm(f[8]) == self.gate:
                f[3] = 'OR2x2_ASAP7_75t_R'
            lines.append('\t'.join(f))
        with self.assertRaises(ValueError):
            r.physical_join(self.cells, '\n'.join(lines), self.rows, self.fixture['typed_physical'])

    def test_actual_physical_reset_cell_is_not_async(self):
        dump = self.fixture['physical_dump']
        lines = []
        for line in dump.splitlines():
            f = line.split('\t')
            if f[0] == 'C' and r.norm(f[8]) == 'u_rst.rst_n$_DFF_PN0_':
                f[3] = 'DFFHQNx1_ASAP7_75t_R'
            lines.append('\t'.join(f))
        with self.assertRaises(ValueError):
            r.physical_join(self.cells, '\n'.join(lines), self.rows, self.fixture['typed_physical'])

    def test_wrong_capture_clock(self):
        self.cells[self.capture]['ports']['CLK'] = 'clk'
        self.reject()

    def test_functional_reset_release_data(self):
        self.cells['u_rst.sync_q[0]$_DFF_PN0_']['ports']['D'] = 'wce'
        self.reject()

    def test_wrong_reset_assertion(self):
        self.cells['u_rst.rst_n$_DFF_PN0_']['ports']['RESETN'] = 'r_a[0]'
        self.reject()

    def test_wrong_reset_polarity(self):
        g = r.Graph(self.cells)
        name, _ = g.driver('u_rst.relay_q[0][0]')
        self.cells[name]['master'] = 'BUFx2_ASAP7_75t_R'
        self.reject()

    def test_shared_input_use(self):
        self.cells['other'] = {'master': 'AND2x2_ASAP7_75t_R',
                               'ports': {'A': 'wce', 'B': 'r_a[0]', 'Y': 'outside'}}
        self.reject()

    def test_old_reset64_proof_rejected(self):
        lec = copy.deepcopy(self.fixture['lec'])
        lec['reset_contract']['used'] = 64
        with self.assertRaises(ValueError):
            r.proof_gate(lec, self.fixture['provenance'], FIXTURE)

    def test_missing_keep_proof_rejected(self):
        lec = copy.deepcopy(self.fixture['lec'])
        lec['kept_registers']['missing']['n'] = 1
        with self.assertRaises(ValueError):
            r.proof_gate(lec, self.fixture['provenance'], FIXTURE)

    def test_changed_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for name in r.SOURCE_SHA:
                (d / name).write_bytes((FIXTURE / name).read_bytes())
            (d / 'ot_hgi_sm_xload_bfqg.sv').write_text('wrong source')
            with self.assertRaises(ValueError):
                r.proof_gate(self.fixture['lec'], self.fixture['provenance'], d)

    def test_actual_placement_capture_edge_missing(self):
        dump = self.fixture['physical_dump']
        # A renamed actual mask breaks the source/placement join, even with valid EQ.
        dump = dump.replace('\t' + self.gate + '\n', '\twrong_mask\n')
        with self.assertRaises(ValueError):
            r.physical_join(self.cells, dump, self.rows, self.fixture['typed_physical'])


if __name__ == '__main__':
    unittest.main()
