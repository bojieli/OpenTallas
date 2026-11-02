"""Independent controls for parameter/body selection and frozen cache identity.

Synthetic metadata exercises packaging guards; it claims no native child compile.
The actual 86-child cache has a separate read-only positive replay receipt.
"""
from pathlib import Path
import os
import tempfile
import unittest

import link_generated_hier_top as link


class LinkGeneratedHierTop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.obj = self.root/'obj'
        self.wrapper = self.obj/'Vchild_dpi'/'child_dpi.sv'
        self.wrapper.parent.mkdir(parents=True)
        self.wrapper.write_text('// Wrapper module for DPI protected library\n'
                                'module child_dpi(input wire a, output wire y); endmodule\n')
        self.child_args = self.obj/'Vchild_dpi__hierMkArgs.f'
        self.child_args.write_text('-GP=1\n')
        self.child = ('module child #(parameter integer P=1)(input wire a, output wire y);\n'
                      'assign y=a;\nendmodule\n')
        self.top = 'module top(input wire a, output wire y);\n child u (.a(a),.y(y));\nendmodule\n'
        self.args = 'Vchild_dpi/child_dpi.sv\n--hierarchical-block child,child_dpi\n'
        self.source = self.root/'selected_preprocessed.sv'
        self.source.write_text(self.child+self.top)
        self.metadata = self.wrapper.parent/'Vchild_dpi__verFiles.dat'
        self.freeze_metadata()

    def freeze_metadata(self):
        def row(kind, path):
            return f'{kind} '+ ' '.join(map(str,link.file_identity(path))) + f' "" "{path.resolve()}"\n'
        self.metadata.write_text(row('S',self.source)+row('T',self.wrapper)+
                                 f'C "-f {self.child_args}"\n')

    def run_prepare(self, *, source=None):
        return link.prepare(self.source.read_text(),self.top,self.args,self.obj,self.root/'out',
                            source_path=self.source if source is None else source)

    def change_top(self, body):
        self.top='module top(input wire a, output wire y);\n'+body+'\nendmodule\n'
        self.source.write_text(self.child+self.top)
        self.freeze_metadata()

    def test_fixed_integer_positive(self):
        result=self.run_prepare()
        self.assertEqual((result['instance_count'],result['used_dpi_modules']),(1,1))
        self.assertEqual(result['instances'][0]['effective_parameters']['P']['bits'],1)

    def test_unconnected_named_port_is_preserved(self):
        self.change_top(' child u (.a(a),.y());')
        self.run_prepare()
        self.assertIn('.y()', (self.root/'out/linked_top.sv').read_text())

    def test_string_data_cannot_change_under_whitespace_normalization(self):
        self.change_top(' child u (.a("a b"),.y(y));')
        # Keep the frozen PP/cache metadata untouched; only the separately
        # supplied raw parent changes its connection's literal value.
        self.top=self.top.replace('"a b"','"ab"')
        with self.assertRaises(ValueError):
            self.run_prepare()

    def test_escaped_identifier_delimiter_cannot_be_normalized_away(self):
        self.change_top(' child u (.a(\\a [0]),.y(y));')
        self.top=self.top.replace('\\a [0]','\\a[0] ')
        with self.assertRaises(ValueError):
            self.run_prepare()

    def test_untyped_width_changing_relation_is_rejected(self):
        self.child="module child #(parameter P=1'b1)(input wire a, output wire y); assign y=($bits(P)==1)?a:~a; endmodule\n"
        self.change_top(" child #(.P(32'd1)) u (.a(a),.y(y));")
        with self.assertRaisesRegex(ValueError,'formal type|untyped'):
            self.run_prepare()

    def test_inherited_fixed_type_and_signed_literal_semantics(self):
        p=link.defaults('module c #(parameter integer A=0, B=0)(); endmodule')
        link.apply_override(p,'A',"8'shff")
        link.apply_override(p,'B',"8'hff")
        self.assertEqual(p['A']['type'],p['B']['type'])
        self.assertEqual(p['A']['bits'],0xffffffff)
        self.assertEqual(p['B']['bits'],255)

    def test_sized_literal_truncation_precedes_formal_coercion(self):
        p=link.defaults('module c #(parameter integer P=0)(); endmodule')
        link.apply_override(p,'P',"1'b10")
        self.assertEqual(p['P']['bits'],0)

    def test_multiple_instances_cannot_skip_second_port_inventory(self):
        self.change_top(' child u0 (.a(a),.y(y)), u1 (.a(a));')
        with self.assertRaisesRegex(ValueError,'one instance'):
            self.run_prepare()

    def test_missing_duplicate_or_wrong_ports(self):
        for call in ['.a(a)', '.a(a),.a(a),.y(y)', '.mutant_a(a),.y(y)']:
            with self.subTest(call=call):
                self.change_top(' child u ('+call+');')
                with self.assertRaisesRegex(ValueError,'port inventory|unique named'):
                    self.run_prepare()

    def test_unsupported_top_behavior_is_rejected(self):
        for body in [' wire extra=a;\n child u (.a(a),.y(y));',
                     ' child u (.a(a),.y(y));\n defparam u.P=2;',
                     ' if (1) begin:g\n child u (.a(a),.y(y));\n end']:
            with self.subTest(body=body):
                self.change_top(body)
                with self.assertRaisesRegex(ValueError,'pure connectivity|initializers'):
                    self.run_prepare()

    def test_duplicate_wrapper_name_has_no_last_file_fallback(self):
        self.args='Vchild_dpi/child_dpi.sv\n'+self.args
        with self.assertRaisesRegex(ValueError,'duplicate generated DPI'):
            self.run_prepare()

    def test_changed_child_body_with_same_top_and_ports_is_rejected(self):
        self.source.write_text(self.source.read_text().replace('assign y=a;','assign y=~a;'))
        with self.assertRaisesRegex(ValueError,'source epoch differs'):
            self.run_prepare()

    def test_identical_bytes_at_another_source_path_are_not_cache_authority(self):
        other=self.root/'different_epoch.sv'
        other.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValueError,'source epoch differs'):
            self.run_prepare(source=other)

    def test_changed_wrapper_same_ports_is_rejected(self):
        self.wrapper.write_text(self.wrapper.read_text()+'\n// changed generated body\n')
        with self.assertRaisesRegex(ValueError,'wrapper changed after frontend'):
            self.run_prepare()

    def test_cached_child_arguments_must_match_selected_variant(self):
        self.child_args.write_text('-GP=2\n')
        self.freeze_metadata() # isolate signature check from argument-age check
        with self.assertRaisesRegex(ValueError,'cached child arguments'):
            self.run_prepare()

    def test_arguments_changed_after_frontend_are_rejected(self):
        self.child_args.write_text('-GP=1\n# altered argument file\n')
        # Make chronological order explicit; several synthetic writes may share
        # one filesystem timestamp tick during this sub-millisecond fixture.
        later=self.metadata.stat().st_mtime_ns+1_000_000_000
        os.utime(self.child_args,ns=(later,later))
        with self.assertRaisesRegex(ValueError,'arguments changed after frontend'):
            self.run_prepare()


if __name__ == '__main__':
    unittest.main()
