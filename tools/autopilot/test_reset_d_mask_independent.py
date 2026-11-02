"""Independent physical-only controls: mapped proof and native receipt stay fixed."""
import copy
import json
from pathlib import Path
import unittest

import reset_d_mask as r

FIXTURE = Path(__file__).resolve().parents[2] / 'results/r2_reset_capture_1101/native_fixture.json'


class IndependentPhysicalControls(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text())
        self.cells = self.fixture['cells']
        self.rows = r.qualify_cones(self.cells)['candidates']
        self.dump = self.fixture['physical_dump']
        self.typed = self.fixture['typed_physical']

    def join(self, dump=None, typed=None):
        return r.physical_join(self.cells, self.dump if dump is None else dump,
                               self.rows, self.typed if typed is None else typed)

    def test_native_receipt_positive(self):
        self.assertEqual(self.join()['actual_capture_edges'], 9)

    def test_untyped_functional_input_cannot_hide_behind_native_receipt(self):
        mutant = self.dump + ('P\t99999\tfunctional_reset_data\tINPUT\tSIGNAL\tM5\t1\t1\n'
                              'N\tSIGNAL\tp99999\ti8790\n')
        with self.assertRaises(ValueError):
            self.join(dump=mutant)

    def test_extra_actual_capture_cannot_hide_behind_native_receipt(self):
        lines = []
        mask_changed = clock_changed = False
        for line in self.dump.splitlines():
            fields = line.split('\t')
            if fields[0] == 'N' and fields[2] == 'i4876':
                line += '\ti99998'
                mask_changed = True
            if fields[0] == 'N' and fields[2] == 'p1025':
                line += '\ti99998c'
                clock_changed = True
            lines.append(line)
        self.assertTrue(mask_changed and clock_changed)
        lines.append('C\t99998\tS\tDFFHQNx1_ASAP7_75t_R\t1\t1\t2\t2\textra_capture')
        with self.assertRaises(ValueError):
            self.join(dump='\n'.join(lines) + '\n')

    def test_reset_chain_typed_input_mutations(self):
        # A source-level EQ receipt cannot establish the actual D/assert/preset
        # connections. Independently alter each actual semantic pin.
        for pin in ('D', 'RESETN', 'SETN', 'CLK'):
            with self.subTest(pin=pin):
                typed = copy.deepcopy(self.typed)
                ports = typed['cells']['u_rst.rst_n$_DFF_PN0_']['ports']
                ports[pin]['net'] = typed['ports']['wce']['net']
                with self.assertRaisesRegex(ValueError, 'typed (reset D|RESETN|SETN|reset CLK)'):
                    self.join(typed=typed)

    def test_coherent_actual_reset_inputs_rewired_to_functional_data(self):
        name = 'u_rst.rst_n$_DFF_PN0_'
        cell_ids, port_ids = {}, {}
        for line in self.dump.splitlines():
            f = line.split('\t')
            if f[0] == 'C':
                cell_ids[r.norm(f[8])] = 'i' + f[1]
            elif f[0] == 'P':
                port_ids[r.norm(f[2])] = 'p' + f[1]

        def drivers(net):
            result = [port_ids[n] for n, p in self.typed['ports'].items()
                      if p['direction'] == 'INPUT' and p['net'] == net]
            result += [cell_ids[n] for n, cell in self.typed['cells'].items()
                       if any(p['direction'] == 'OUTPUT' and p['net'] == net
                              for p in cell['ports'].values())]
            self.assertEqual(len(result), 1, 'control requires one actual driver')
            return result[0]

        for pin in ('D', 'RESETN', 'SETN', 'CLK'):
            with self.subTest(pin=pin):
                typed = copy.deepcopy(self.typed)
                ports = typed['cells'][name]['ports']
                old_net = ports[pin]['net']
                new_net = typed['ports']['wce']['net']
                self.assertNotEqual(old_net, new_net)
                old_driver, new_driver = drivers(old_net), drivers(new_net)
                target = cell_ids[name] + ('c' if pin == 'CLK' else '')
                ports[pin]['net'] = new_net
                retain_old = any(p['direction'] == 'INPUT' and p['net'] == old_net
                                 and (other == 'CLK') == (pin == 'CLK')
                                 for other, p in ports.items())
                lines, removed, added = [], False, False
                for line in self.dump.splitlines():
                    f = line.split('\t')
                    if f[0] == 'N' and f[2] == old_driver and target in f[3:]:
                        if not retain_old:
                            f = f[:3] + [q for q in f[3:] if q != target]
                        removed = True
                    if f[0] == 'N' and f[2] == new_driver:
                        if target not in f[3:]:
                            f.append(target)
                        added = True
                    lines.append('\t'.join(f))
                self.assertTrue(removed and added, 'control must update both actual net edges')
                with self.assertRaisesRegex(ValueError, 'typed (reset D|RESETN|SETN|reset CLK)'):
                    self.join(dump='\n'.join(lines) + '\n', typed=typed)


if __name__ == '__main__':
    unittest.main()
