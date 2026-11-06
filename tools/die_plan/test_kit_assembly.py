import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

try:
    from . import kit_assembly as A
except ImportError:
    import kit_assembly as A


class KitAssembly(unittest.TestCase):
    def fixture(self, root, native=True):
        source = root / 'source.sv'
        source.write_text(('module leaf #(parameter P=0)(input [7:0] a,output [7:0] y); assign y=a+P; endmodule\n' if native else '') +
                          'module top(input [7:0] a,output [7:0] yh,ys);\n'
                          'leaf #(.P(0)) u_hard(a,yh);\n' +
                          ('leaf #(.P(4)) u_soft(a,ys);\n' if native else 'assign ys=a;\n') + 'endmodule\n')
        (root / 'leaf_bb.v').write_text('(* blackbox *) module leaf(input [7:0] a,output [7:0] y); endmodule\n')
        children = [dict(master='leaf', inst='u_hard')]
        contracts = [dict(master='leaf', instance='u_hard', child_params=dict(P=0),
                          binding_sha256=hashlib.sha256(source.read_bytes()).hexdigest())]
        return source, children, contracts

    def test_selected_sealed_call_only_and_real_hierarchy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, children, contracts = self.fixture(root)
            result = A.assemble_fixed_children(root, children, contracts, root/'assembly.json')
            self.assertIn('leaf u_hard', source.read_text())
            self.assertIn('leaf__soft #(.P(4)) u_soft', source.read_text())
            self.assertEqual(result['cycles_changed'], 0)
            if not shutil.which('yosys'):
                self.skipTest('Yosys required for actual hierarchy evidence')
            target = root/'hierarchy.json'
            command = f'read_verilog -sv {source} {root}/leaf_bb.v; hierarchy -check -top top; proc; write_json {target}'
            run = subprocess.run(['yosys', '-Q', '-T', '-p', command], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout[-3000:] + run.stderr[-1000:])
            design = json.loads(target.read_text())
            evidence = A.hierarchy_inventory(design, 'top', children)
            self.assertEqual(evidence['problems'], [])
            self.assertEqual(evidence['matched'], 1)
            self.assertEqual(design['modules']['top']['cells']['u_hard']['type'], 'leaf')
            soft = design['modules']['top']['cells']['u_soft']['type']
            self.assertIn('leaf__soft', soft)
            # Mutant: a dropped selected macro cannot pass the inventory.
            del design['modules']['top']['cells']['u_hard']
            self.assertTrue(A.hierarchy_inventory(design, 'top', children)['problems'])

    def test_changed_source_is_rejected_before_any_output_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, children, contracts = self.fixture(root)
            source.write_text(source.read_text().replace('.P(0)', '.P(1)'))
            before = source.read_bytes()
            with self.assertRaisesRegex(ValueError, 'sealed bytes'):
                A.assemble_fixed_children(root, children, contracts)
            self.assertEqual(source.read_bytes(), before)

    def test_wrong_sealed_literal_parameter_cannot_be_stripped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, children, contracts = self.fixture(root)
            before = source.read_bytes()
            contracts[0]['child_params']['P'] = 1
            with self.assertRaisesRegex(ValueError, 'differs from sealed child'):
                A.assemble_fixed_children(root, children, contracts)
            self.assertEqual(source.read_bytes(), before)

    def test_effective_parent_recipe_override_cannot_select_wrong_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, children, contracts = self.fixture(root)
            contracts[0]['parent_params'] = dict(D=8192)
            before = source.read_bytes()
            with self.assertRaisesRegex(ValueError, 'effective parent parameter D'):
                A.assemble_fixed_children(root, children, contracts,
                                         parent_profile=dict(top='top', parameters=dict(D=4096)))
            self.assertEqual(source.read_bytes(), before)

    def test_existing_frontend_emits_flat_kit_inventory_without_second_frontend(self):
        if not shutil.which('yosys'):
            self.skipTest('Yosys required for actual flat-kit frontend')
        try:
            from . import rtl_lint as lint
        except ImportError:
            import rtl_lint as lint
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rtl = root/'rtl'
            rtl.mkdir()
            source, children, contracts = self.fixture(rtl)
            (root/'config.mk').write_text('export DESIGN_NAME = top\nexport VERILOG_FILES = ' +
                                         ' '.join(str(p) for p in sorted(rtl.iterdir())) + '\n')
            self.assertNotIn('kit_assembly_elaborated', lint.script(root, mount=str(root)))
            A.assemble_fixed_children(rtl, children, contracts, root/'kit_assembly.json')
            self.assertTrue((root/'kit_assembly.py').is_file())
            original_script = lint.script
            with mock.patch.object(lint, 'script', lambda kit, flatten=None:
                                   original_script(kit, mount=str(kit), flatten=flatten)):
                self.assertEqual(lint.run(root), 0)
            record = json.loads((root/'rtl_lint.json').read_text())
            self.assertEqual(record['kit_assembly']['matched'], 1)
            self.assertEqual(record['kit_assembly']['problems'], [])
            # The staged helper loads under isolated Python without repository imports.
            bindings = root/'contracts.json'
            bindings.write_text(json.dumps(dict(children=children, parameter_contracts=contracts)))
            run = subprocess.run(['python3', '-I', str(root/'kit_assembly.py'), 'inventory',
                                  '--yosys-json', str(root/'kit_assembly_elaborated.json'), '--top', 'top',
                                  '--contracts', str(bindings), '--receipt', str(root/'isolated.json')],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads((root/'isolated.json').read_text())['matched'], 1)

    def test_already_fixed_parent_keeps_physical_blackbox(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, children, contracts = self.fixture(root, native=False)
            before = (root/'leaf_bb.v').read_bytes()
            A.assemble_fixed_children(root, children, contracts)
            self.assertIn('leaf u_hard', source.read_text())
            self.assertEqual((root/'leaf_bb.v').read_bytes(), before)

    def test_unplanned_hard_sibling_is_reported(self):
        design = dict(modules=dict(top=dict(cells=dict(u_hard=dict(type='leaf'), u_soft=dict(type='leaf'))),
                                   leaf=dict(attributes=dict(blackbox='1'))))
        evidence = A.hierarchy_inventory(design, 'top', [dict(master='leaf', inst='u_hard')])
        self.assertEqual(evidence['problems'], ['unplanned hard instance u_soft (leaf)'])

    def test_native_instead_of_fixed_child_is_reported(self):
        design = dict(modules=dict(top=dict(cells=dict(u_hard=dict(type='leaf__soft'))), leaf__soft=dict(cells={})))
        evidence = A.hierarchy_inventory(design, 'top', [dict(master='leaf', inst='u_hard')])
        self.assertIn('expected fixed leaf', evidence['problems'][0])
        wrong = A.hierarchy_inventory(design, 'top', [dict(master='leaf', inst='u_hard')],
                                      parent_profile=dict(top='unrelated_native_parent'))
        self.assertIn('differs from selected profile', wrong['problems'][0])

    def test_disjoint_filename_alias_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root/'a', root/'b'
            a.mkdir(); b.mkdir()
            (a/'prefix.sv').write_text('module one; endmodule\n')
            (b/'prefix.sv').write_text('module two; endmodule\n')
            files = A.dedupe_sources([a/'prefix.sv', b/'prefix.sv'], root/'aliases')
            self.assertEqual(len(files), 2)
            self.assertEqual(files[1].read_bytes(), (b/'prefix.sv').read_bytes())
            self.assertNotEqual(files[0].name, files[1].name)
            files = A.dedupe_sources([a/'prefix.sv', b/'prefix.sv', b/'prefix.sv'], root/'aliases')
            self.assertEqual(len(files), 2)
            c = root/'c'
            c.mkdir()
            (c/'prefix.sv').write_text('module two; wire different; endmodule\n')
            with self.assertRaisesRegex(ValueError, 'different source files'):
                A.dedupe_sources([a/'prefix.sv', b/'prefix.sv', c/'prefix.sv'], root/'aliases')

    def test_overlapping_module_or_include_collision_stays_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root/'a', root/'b'
            a.mkdir(); b.mkdir()
            (a/'prefix.sv').write_text('module same; endmodule\n')
            for text in ('module same; wire x; endmodule\n', '`include "relative.svh"\nmodule other; endmodule\n'):
                (b/'prefix.sv').write_text(text)
                with self.assertRaisesRegex(ValueError, 'different source files'):
                    A.dedupe_sources([a/'prefix.sv', b/'prefix.sv'], root/'aliases')


if __name__ == '__main__':
    unittest.main()
