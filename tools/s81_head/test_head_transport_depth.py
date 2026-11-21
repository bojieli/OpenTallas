import importlib.util
import pathlib
import unittest

_P = pathlib.Path(__file__).with_name("head_transport_depth.py")
_S = importlib.util.spec_from_file_location("head_transport_depth", _P)
M = importlib.util.module_from_spec(_S)
_S.loader.exec_module(M)

NON_ANSI_TOP = """module s81_head_top (rst_n, start, clk_region_a, lk_x_pma_rck, pst_a, lk_x_pma_rx, lk_x_pma_tx);
    input  wire rst_n;
    input  wire start;
    input  wire [0:0] clk_region_a;
    input  wire [0:0] lk_x_pma_rck;
    input  wire [0:0] pst_a;
    input  wire [543:0] lk_x_pma_rx;
    output wire [543:0] lk_x_pma_tx;
endmodule
"""


class NonAnsiPorts(unittest.TestCase):
    def test_ports_connected_and_driven(self):
        tb = M.tb_text({}, NON_ANSI_TOP, 1700, 64)
        for n in ("rst_n", "start", "clk_region_a", "lk_x_pma_rck", "pst_a", "lk_x_pma_rx", "lk_x_pma_tx"):
            self.assertIn(".%s(%s)" % (n, n), tb)
        self.assertIn("rst_n = (cyc >= 40)", tb)
        self.assertIn("start = (cyc >= 400)", tb)
        self.assertIn("pst_a = (cyc >= 400)", tb)
        self.assertIn("clk_region_a = clk", tb)


if __name__ == "__main__":
    unittest.main()
