"""Real loader regression and lexical controls for the legacy shared header API."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
load = importlib.util.spec_from_file_location('s81_header_bind', ROOT/'tools/s81_ftok/die_port_bind.py')
B = importlib.util.module_from_spec(load); load.loader.exec_module(B)


class HeaderParsing(unittest.TestCase):
    def test_actual_loader_comment_terminator(self):
        source = (ROOT/'rtl/hbm_accel/generic/loader/ot_hfd_loader_hgi.sv').read_text()
        self.assertIn('svc_dma_hc_sizing_20261010.json);', source)
        params, ports = B.header(source, 'ot_hfd_loader_hgi')
        self.assertEqual(len(ports), 97)
        self.assertEqual(params['KP_RB'], '64')
        self.assertEqual(ports['clk'][0], 'input')
        self.assertEqual(ports['h_awvalid'][0], 'output')
        self.assertEqual(B.evalw(ports['h_dma_araddr'][1], params), 64)
        self.assertNotIn('invented_port', ports)

    def test_nested_parameter_comments_and_string_delimiters(self):
        source = r'''
// module fake(input wire injected); endmodule
module actual #(
 parameter string LABEL="// /* ); module actual(input injected); endmodule, \\\"",
 parameter integer N=(2+(3*2)), W=$clog2((N+1))
 /* ); module actual(input phantom); endmodule */
)(input wire ck, input logic [W-1:0] a,b, output wire [(N*2)-1:0] q);
 initial $display("module actual(input body_injected); endmodule // /*");
endmodule
'''
        params, ports = B.header(source, 'actual')
        self.assertEqual(set(ports), {'ck', 'a', 'b', 'q'})
        self.assertTrue(params['LABEL'].startswith('"// /* );'))
        self.assertEqual(B.evalw(ports['b'][1], params), 4)
        self.assertEqual(B.evalw(ports['q'][1], params), 16)
        self.assertEqual(B.header(source, 'fake'), (None, None))

    def test_non_ansi_and_packed_dimensions(self):
        source = '''module old #(parameter integer N=(2+2)) (ck,a,q);
        input ck; input wire [N-1:0] a; output reg [7:0] q;
        always @(posedge ck) q <= a;
        endmodule'''
        params, ports = B.header(source, 'old')
        self.assertEqual(set(ports), {'ck','a','q'})
        self.assertEqual(B.evalw(ports['a'][1],params),4)
        self.assertEqual(B.evalw(ports['q'][1],params),8)
        params, ports = B.header('module packed(input logic [1:0][3:0] data); endmodule', 'packed')
        self.assertEqual(B.evalw(ports['data'][1],params),8)

    def test_unknown_ports_and_invalid_headers_fail_closed(self):
        for source in [
            'module m(input custom_type unknown); endmodule',
            'module m(ck,unresolved); input ck; endmodule',
            'module m(input ck); endmodule module m(input other); endmodule',
            'module m #(parameter N=(2+3) (input ck); endmodule',
            'module m(input ck); /* unterminated endmodule',
            'module m(input ck); initial $display("unterminated); endmodule',
        ]:
            with self.subTest(source=source):
                self.assertEqual(B.header(source,'m'),(None,None))


if __name__ == '__main__': unittest.main()
