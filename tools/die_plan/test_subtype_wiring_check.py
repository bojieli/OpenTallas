"""BIND-SUBTYPE 11-11: subtype_wiring_check passes the declared substitution and fails a one-bit change."""
import subtype_wiring_check as W

RULE = dict(native="NAT", top="GLUE", rename={"sfu_y": "lane_y"}, share={"sfu_clk": "map_clk"})
OLD = """module t (input wire clk, input wire [1:0] a, output wire [1:0] y);
    // as-built q.cut_lane0
    NAT u_l (.map_clk(clk), .a(a[1:0]), .lane_y(y[1:0]));
    X u_x (.o(y[0]));
endmodule
"""
NEW = OLD.replace("NAT u_l (.map_clk(clk), .a(a[1:0]), .lane_y(y[1:0]));",
                  "GLUE u_l (.map_clk(clk), .sfu_clk(clk), .a(a[1:0]), .sfu_y(y[1:0]));")


def test_pass():
    errs, n = W.check(OLD, NEW, RULE)
    assert errs == [] and n == 1


def test_negative_one_bit_swap():
    errs, n = W.check(OLD, NEW.replace(".a(a[1:0])", ".a({a[0], a[1]})"), RULE)
    assert errs and "NEW" in errs[0]


def test_negative_other_instance_changed():
    errs, _ = W.check(OLD, NEW.replace(".o(y[0])", ".o(y[1])"), RULE)
    assert errs
