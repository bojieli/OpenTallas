import hashlib
import unittest
import romq_parent_adapter as A


def fixture(expression='P_INSTANCE', nb='2', mtp='1'):
    source = ('module parent #(parameter P_INSTANCE="type.default") ();\n'
              f'{A.MASTER} #(.INSTANCE({expression}), .NB({nb}), .MTP({mtp}), .CGR(0)) selected (.clk(c), .fault(f));\n'
              f'{A.MASTER} #(.NB(3)) soft_sibling (.clk(c));\n'
              '// ' + A.MASTER + ' selected is mentioned in a comment\nendmodule\n')
    old = dict(INSTANCE=expression, NB=nb, MTP=mtp, CGR='0')
    selected = {k:v for k,v in old.items() if k != 'NB'}
    selected.update(A.SELECTED)
    contract = dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                    native_instance='selected', original_master=A.MASTER,
                    selected_shell=A.SHELL, original_params=old, selected_params=selected)
    return source, contract


class ParentAdapterTests(unittest.TestCase):
    def test_preserve_identity_connections_and_unselected_sibling(self):
        for expression in ['P_INSTANCE', '"literal.with,.NB(3)"', '$sformatf("%s.parent", P_INSTANCE)']:
            with self.subTest(expression=expression):
                source, contract = fixture(expression)
                output, receipt = A.adapt(source, [contract])
                self.assertIn('.INSTANCE(' + expression + ')', output)
                self.assertNotIn('.NB(2)', output)
                self.assertIn('.IOREG(1), .OUTPUT_NEG(1), .OLAT(1), .IFN(1)', output)
                self.assertEqual(output.split('selected ', 1)[1], source.split('selected ', 1)[1])
                self.assertIn(A.MASTER + ' #(.NB(3)) soft_sibling', output)
                self.assertEqual(receipt['instances'][0]['retained_instance_expression'], expression)
                self.assertEqual((receipt['added_interface_cycles'], receipt['added_child_reset_edges']), (2, 1))
                self.assertEqual(receipt['physical_status'], 'PREPARATION_ONLY')

    def test_staged_profile_seal_and_cycle_prices(self):
        source, contract = fixture()
        contract.update(input_stages=3, output_stages=2)
        contract['selected_params'].update(INPUT_STAGES='3', OUTPUT_STAGES='2')
        output, receipt = A.adapt(source, [contract])
        self.assertIn('.INPUT_STAGES(3), .OUTPUT_STAGES(2)', output)
        self.assertEqual((receipt['added_interface_cycles'], receipt['added_child_reset_edges']), (5, 3))
        contract['output_stages'] = 1
        with self.assertRaisesRegex(ValueError, 'capture-stage profile'):
            A.adapt(source, [contract])
        contract['output_stages'] = 2
        contract['selected_params']['OUTPUT_STAGES'] = '1'
        with self.assertRaisesRegex(ValueError, 'selected form'):
            A.adapt(source, [contract])

    def test_conservative_complete_input_pair_profile(self):
        source, contract = fixture()
        contract.update(input_stages=4, output_stages=2, input_pair=1)
        contract['selected_params'].update(INPUT_STAGES='4', OUTPUT_STAGES='2', INPUT_PAIR='1')
        output, receipt = A.adapt(source, [contract])
        self.assertIn('.INPUT_PAIR(1)', output)
        self.assertEqual((receipt['added_interface_cycles'], receipt['added_child_reset_edges']), (6, 4))
        self.assertEqual(receipt['physical_FF_per_ROMQ'], 3287)
        contract['input_pair'] = 2
        with self.assertRaisesRegex(ValueError, 'capture-stage profile'):
            A.adapt(source, [contract])

    def test_foreign_half_configuration_rejected(self):
        for nb, mtp in [('3', '1'), ('NB_VALUE', '1'), ('2', '0')]:
            with self.subTest(nb=nb, mtp=mtp):
                source, contract = fixture(nb=nb, mtp=mtp)
                with self.assertRaises(ValueError):
                    A.adapt(source, [contract])

    def test_source_and_instance_seals_reject_drift(self):
        source, contract = fixture()
        with self.assertRaisesRegex(ValueError, 'source hash'):
            A.adapt(source + '\n', [contract])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            A.adapt(source, [contract, contract])

    def test_duplicate_overrides_rejected(self):
        source, contract = fixture()
        source = source.replace('.NB(2)', '.NB(2), .NB(2)')
        contract['source_sha256'] = hashlib.sha256(source.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            A.adapt(source, [contract])


if __name__ == '__main__':
    unittest.main()
