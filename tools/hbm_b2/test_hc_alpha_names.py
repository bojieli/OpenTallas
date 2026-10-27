import hashlib
import unittest
from hc_alpha_names import normalize_names, placement_name


class AlphaNames(unittest.TestCase):
    def test_nested_emitted_types_and_instances(self):
        src = r'''module top(input clk, input a, output y);
  \child$site.path  #(.P(1+(2))) \u.x[0]  (.clk(clk),.a(a),.y(y));
endmodule
module \child$site.path  #(parameter P=3)(input clk,a,output reg y);
 always @(posedge clk) y<=a;
endmodule
'''
        text, r = normalize_names(src, 'top')
        self.assertNotIn(r'\child$site.path', text)
        self.assertNotIn(r'\u.x[0]', text)
        self.assertEqual(r['replacements'], 3)
        self.assertEqual(r['added_cycles'], 0)
        self.assertIn('always @(posedge clk) y<=a;', text)

    def test_native_ports_and_signal_identifiers_unchanged(self):
        src = r'''module top(input \physical.pin[0] , output \data.net );
 wire \another.signal ;
 \child.type  \u.deep[1]  (.a(\physical.pin[0] ),.y(\data.net ));
endmodule
module \child.type (input a,output y); assign y=a; endmodule
'''
        text, _ = normalize_names(src, 'top')
        for name in [r'\physical.pin[0]', r'\data.net', r'\another.signal']:
            self.assertEqual(text.count(name), src.count(name))

    def test_external_macro_placement_follows_flat_name(self):
        src = r'module top(input clk); ot_sram_1r1w_128x256_m1_r2c2 \u_c.u_b.g_x[0].u_m  (.CLK(clk)); endmodule'
        _, r = normalize_names(src, 'top')
        self.assertEqual(placement_name(r'u_c.u_b.g_x\[0\].u_m', r), r['instance_names']['u_c.u_b.g_x[0].u_m'])
        self.assertEqual(placement_name('unchanged', r), 'unchanged')

    def test_comments_and_strings_are_not_identifiers(self):
        src = r'''// module \fake.name \fake.inst (
module top; initial $display("\\not.an.id "); endmodule
'''
        text, r = normalize_names(src, 'top')
        self.assertEqual(src, text)
        self.assertEqual(r['replacements'], 0)

    def test_existing_identifier_collision_fails_closed(self):
        name = r'\child.foo'
        safe = 'hc_a_' + hashlib.sha256(name.encode()).hexdigest()[:16]
        src = f'module top; wire {safe}; {name} u(); endmodule\nmodule {name} (); endmodule\n'
        with self.assertRaisesRegex(ValueError, 'collision'):
            normalize_names(src, 'top')

    def test_unsupported_module_reference_fails_closed(self):
        src = r'module top; wire \child.foo ; endmodule module \child.foo (); endmodule'
        with self.assertRaisesRegex(ValueError, 'unclassified'):
            normalize_names(src, 'top')


if __name__ == '__main__':
    unittest.main()
