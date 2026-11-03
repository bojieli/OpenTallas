"""SAFE-STATION-1 11-03 (OWNER TWO-STRIKES): relay-bay station form = registered relay at every <=300-um hop"""
import json, os, re, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relay_bay as RB

BOUND = """module t_bound(input clk, input rst_n, input [4:0] fa_i, input [4:0] fb_i, output [4:0] fa_o, output [4:0] fb_o);
    wire [4:0] cland_fa_i;
    wire [4:0] fa_o_s0;
    wire [4:0] fa_o_s1;
    wire [4:0] fb_o_s0;
    wire [4:0] fb_o_s1;
    ot_dp_landing_collect u_cland_fa (.clk(clk), .d(fa_i), .q(cland_fa_i));
    ot_dp_st #(.W(4)) u_ft_fa_o_0 (.clk(clk), .rst_n(rst_n), .d(cland_fa_i[3:0]), .ea(cland_fa_i[4]), .q(fa_o_s0[3:0]), .eq(fa_o_s0[4]));
    ot_dp_st #(.W(4)) u_ft_fa_o_1 (.clk(clk), .rst_n(rst_n), .d(fa_o_s0[3:0]), .ea(fa_o_s0[4]), .q(fa_o_s1[3:0]), .eq(fa_o_s1[4]));
    ot_dp_st #(.W(4)) u_ft_fa_o_2 (.clk(clk), .rst_n(rst_n), .d(fa_o_s1[3:0]), .ea(fa_o_s1[4]), .q(fa_o[3:0]), .eq(fa_o[4]));
    ot_dp_st #(.W(4)) u_ft_fb_o_0 (.clk(clk), .rst_n(rst_n), .d(fb_i[3:0]), .ea(fb_i[4]), .q(fb_o_s0[3:0]), .eq(fb_o_s0[4]));
    ot_dp_st #(.W(4)) u_ft_fb_o_1 (.clk(clk), .rst_n(rst_n), .d(fb_o_s0[3:0]), .ea(fb_o_s0[4]), .q(fb_o_s1[3:0]), .eq(fb_o_s1[4]));
    ot_dp_st #(.W(4)) u_ft_fb_o_2 (.clk(clk), .rst_n(rst_n), .d(fb_o_s1[3:0]), .ea(fb_o_s1[4]), .q(fb_o[3:0]), .eq(fb_o[4]));
endmodule
"""


def mkkit(d, L=1200.0, fb_sites=""):
    K = os.path.join(d, "t"); os.makedirs(K + "/rtl")
    with open(K + "/io.tcl", "w") as f:
        for b in range(5):
            f.write(f"place_pin -pin_name fa_i[{b}] -layer M5 -location {{100.0 {L}}}\n")
            f.write(f"place_pin -pin_name fa_o[{b}] -layer M5 -location {{100.0 0.0}}\n")
            f.write(f"place_pin -pin_name fb_i[{b}] -layer M5 -location {{200.0 0.0}}\n")
            f.write(f"place_pin -pin_name fb_o[{b}] -layer M5 -location {{200.0 {L}}}\n")
    open(K + "/ft_stations.txt", "w").write(f"# slot stations in_face out_face [x y ...]\nfa 3 N S\nfb 3 S N {fb_sites}\n")
    open(K + "/rtl/t_bound.sv", "w").write(BOUND)
    open(K + "/config.mk", "w").write("export X = 1\nexport OT_MAXWIRE_UM = 100\n")
    return K


class RelayBay(unittest.TestCase):
    def test_form_applied(self):
        with tempfile.TemporaryDirectory() as d:
            K = mkkit(d)
            self.assertEqual(RB.main([K]), 0)
            dc = json.load(open(K + "/declared_cycles.json"))
            # landed fa: ceil(1200/300)=4 stations (+1 cycle); plain fb: ceil(1200/300)+1=5 (+2 cycles)
            self.assertEqual((dc["lanes"]["fa"]["stations_new"], dc["lanes"]["fa"]["extra_cycles"]), (4, 1))
            self.assertEqual((dc["lanes"]["fb"]["stations_new"], dc["lanes"]["fb"]["extra_cycles"]), (5, 2))
            rtl = open(K + "/rtl/t_bound.sv").read()
            self.assertEqual(len(re.findall(r"u_ft_fa_o_\d", rtl)), 4)
            self.assertEqual(len(re.findall(r"u_ft_fb_o_\d", rtl)), 5)
            self.assertIn(".q(fa_o[3:0]), .eq(fa_o[4]));", rtl.split("u_ft_fa_o_3")[1].split("\n")[0])
            self.assertIn("wire [4:0] fb_o_s3;", rtl)
            self.assertNotIn("DLL", rtl)
            ft = {l.split()[0]: l.split() for l in open(K + "/ft_stations.txt") if l.strip() and not l.startswith("#")}
            self.assertEqual(len(ft["fa"]), 4 + 2 * 4)
            self.assertEqual(ft["fb"][-1], "1200.0000")                    # plain: last station = out-face register
            tab = open(K + "/relay_bay_table.tsv").read()
            hops = [l.split("\t") for l in tab.splitlines()[2:] if l.split("\t")[-1] == "PASS"]
            self.assertEqual(len(hops), 4 + 4)
            self.assertTrue(all(float(h[3]) <= 300.0 and float(h[7]) >= 83.3 and float(h[8]) >= 83.3 for h in hops))
            self.assertRegex(open(K + "/config.mk").read(), r"OT_MAXWIRE_UM = (50|62|75|100)\n")
            # idempotent: a second run re-checks only
            self.assertEqual(RB.main([K]), 0)
            self.assertEqual(len(re.findall(r"u_ft_fb_o_\d", open(K + "/rtl/t_bound.sv").read())), 5)
            self.assertEqual(json.load(open(K + "/declared_cycles.json"))["lanes"]["fb"]["extra_cycles"], 2)

    def test_check_is_dry(self):
        with tempfile.TemporaryDirectory() as d:
            K = mkkit(d)
            self.assertEqual(RB.main([K, "--check"]), 0)
            self.assertEqual(open(K + "/rtl/t_bound.sv").read(), BOUND)
            self.assertFalse(os.path.exists(K + "/declared_cycles.json"))

    def test_short_hops_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            K = mkkit(d, L=150.0)                                          # 3 stations over 150 um: 50-75 um hops
            self.assertEqual(RB.main([K]), 2)
            self.assertEqual(open(K + "/rtl/t_bound.sv").read(), BOUND)

    def test_plan_sites_kept_when_short_enough(self):
        with tempfile.TemporaryDirectory() as d:
            K = mkkit(d, L=500.0, fb_sites="200 0 200 250 200 500")
            self.assertEqual(RB.main([K]), 0)
            fb = [l for l in open(K + "/ft_stations.txt") if l.startswith("fb ")][0].split()
            self.assertEqual(fb[1], "3")
            self.assertTrue(json.load(open(K + "/declared_cycles.json"))["lanes"]["fb"]["sites_kept"])


if __name__ == "__main__":
    unittest.main()
