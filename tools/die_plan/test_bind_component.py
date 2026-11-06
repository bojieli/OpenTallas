import unittest
import bind_component as C


class ComponentTests(unittest.TestCase):
 def test_literal_native_interface_and_defaults(self):
    ports, defaults = C.interface("""module unit #(parameter [7:0] TAG=8'b01010010)
        (input wire clk, input wire [2:0] data, output wire rst_o_0);
        endmodule""", 'unit')
    assert ports['data'] == dict(direction='input', width=3)
    assert defaults['TAG']['value'] == 82
    with self.assertRaisesRegex(ValueError, 'literal parameters'):
        C.interface('module unit #(parameter TAG=OTHER)(input wire clk); endmodule', 'unit')


 def test_native_reset_graph_and_shortened_path_mutant(self):
    source = '''wire rst_n_t0;
wire rst_n_t1;
wire rst_n = rst_n_t0;
ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));
ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));
ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_root_n), .q(rst_n_t1));
ot_dp_rrelay u_rrl_out (.clk(clk), .d(rst_root_n), .q(rst_o_0));
leaf u_leaf (.clk(clk), .rst_n(rst_n));
'''
    metadata = dict(types=dict(unit=dict(entry='relayed', entry_stages=1, depth_K=1,
        release_after_pin=2,relays=2,outs=[['rst_o_0',0,0]],core_resets=[])))
    errors = []
    report = C._reset(source,'unit',metadata,errors,expected_taps=2)
    assert not errors
    assert report['outputs'] == dict(rst_o_0=2)
    errors = []
    C._reset(source.replace('.d(rst_root_n), .q(rst_n_t0)', '.d(arst_n), .q(rst_n_t0)'),
             'unit',metadata,errors,expected_taps=2)
    assert any('rst_n_t0' in error and 'expected 2' in error for error in errors)
