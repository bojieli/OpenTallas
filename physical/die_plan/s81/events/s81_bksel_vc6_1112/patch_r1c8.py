from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='''        always @(posedge clk) q <= (i0_lane[LO +: SW] & {SW{rpb_l}}) | (mem_rdata[LO +: SW] & {SW{memb_l}});'''
new='''`ifdef OT_BKQ_R1C8
        // Same-cycle H2 control copies: each kept pair owns at most eight payload bits.
        // The original rpb/memb pair still owns the sign sideband (rpb_v/memb_v).
        // Every copy samples the identical rpd/mbd edge and retains the launch-side HLAT.
        for (genvar rs = 0; rs < (SW+7)/8; rs = rs + 1) begin : g_cp8
            localparam integer RL = rs*8;
            localparam integer RW = (SW-RL < 8) ? SW-RL : 8;
            (* keep = "true" *) reg rp8, mb8;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin rp8 <= 1'b0; mb8 <= 1'b1; end
                else begin
`ifdef OT_BKQ_R1C8_MUT
                    rp8 <= (gg == 5 && rs == 2) ? !rpd : rpd;
`else
                    rp8 <= rpd;
`endif
                    mb8 <= (MUT == 1 && gg == 7) ? 1'b0 : mbd;
                end
            wire rp8_l, mb8_l;
            ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rp8, mb8}), .q({rp8_l, mb8_l}));
            always @(posedge clk) q[RL +: RW] <= (i0_lane[LO+RL +: RW] & {RW{rp8_l}}) | (mem_rdata[LO+RL +: RW] & {RW{mb8_l}});
        end
`else
'''+old+'''
`endif'''
assert s.count(old)==1
p.write_text(s.replace(old,new))
