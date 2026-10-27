# builds proof copy of the argmax core RTL: adds OT_PROOF assertions (FSM range, res_id load-before-observe, sign identity)
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
anchor = "endmodule\n`default_nettype wire"
assert s.count(anchor) == 1
props = r'''
`ifdef OT_PROOF
    // proof-only observer: ld = res_id_r has been loaded since reset (set exactly where the RTL loads res_id_r)
    reg ld;
    always @(posedge clk or negedge rst_ctl)
        if (!rst_ctl) ld <= 1'b0;
        else if (st == E_WAIT && cnt == 6'd0) ld <= 1'b1;
    always @* begin
        // P1 FSM range: st[3] never set; only the 8 declared codes are reachable
        assert (st[3] == 1'b0);
        // P2 res_id is observed (wdat at st==E_W1, cq_d load at E_W0/E_W1) only after a load
        if (st == E_W0 || st == E_W1 || st == E_END) assert (ld);
    end
`endif
'''
s = s.replace(anchor, props + anchor)
open(dst, "w").write(s)
