`timescale 1ps/1fs
module tb_preload;
reg clk=0,rst=0;always #1 clk=~clk;
reg[31:0]row_v=0,col_v=0;reg[95:0]row_op=0;
wire[31:0]rv[0:3];wire[8191:0]rd[0:3];
ot_hbm3e_phy_rc_e8p5 phy_SW(.clk(clk),.rst_n(rst),.row_v(row_v),.row_op(row_op),.row_bank(160'd0),.row_row(608'd0),.col_v(col_v),.col_we(32'd0),.col_bank(160'd0),.col_col(160'd0),.col_data(8192'd0),.col_strb(1024'd0),.dram_rvalid(rv[0]),.dram_rdata(rd[0]));
ot_hbm3e_phy_rc_e8p5 phy_SE(.clk(clk),.rst_n(rst),.row_v(row_v),.row_op(row_op),.row_bank(160'd0),.row_row(608'd0),.col_v(col_v),.col_we(32'd0),.col_bank(160'd0),.col_col(160'd0),.col_data(8192'd0),.col_strb(1024'd0),.dram_rvalid(rv[1]),.dram_rdata(rd[1]));
ot_hbm3e_phy_rc_e8p5 phy_NW(.clk(clk),.rst_n(rst),.row_v(row_v),.row_op(row_op),.row_bank(160'd0),.row_row(608'd0),.col_v(col_v),.col_we(32'd0),.col_bank(160'd0),.col_col(160'd0),.col_data(8192'd0),.col_strb(1024'd0),.dram_rvalid(rv[2]),.dram_rdata(rd[2]));
ot_hbm3e_phy_rc_e8p5 phy_NE(.clk(clk),.rst_n(rst),.row_v(row_v),.row_op(row_op),.row_bank(160'd0),.row_row(608'd0),.col_v(col_v),.col_we(32'd0),.col_bank(160'd0),.col_col(160'd0),.col_data(8192'd0),.col_strb(1024'd0),.dram_rvalid(rv[3]),.dram_rdata(rd[3]));
integer checks=0;
always @(posedge clk)begin #0.1;
if(rv[0][0])begin if(rd[0][0+:256]!==256'h0000000100000001000000010000000100000001000000010000000100000001)$fatal(1,"PRELOAD_READBACK q0 pc0 actual%h",rd[0][0+:256]);checks=checks+1;end
if(rv[0][1])begin if(rd[0][256+:256]!==256'h0000000100000002000000010000000200000001000000020000000100000002)$fatal(1,"PRELOAD_READBACK q0 pc1 actual%h",rd[0][256+:256]);checks=checks+1;end
if(rv[1][0])begin if(rd[1][0+:256]!==256'h0000000200000001000000020000000100000002000000010000000200000001)$fatal(1,"PRELOAD_READBACK q1 pc0 actual%h",rd[1][0+:256]);checks=checks+1;end
if(rv[1][1])begin if(rd[1][256+:256]!==256'h0000000200000002000000020000000200000002000000020000000200000002)$fatal(1,"PRELOAD_READBACK q1 pc1 actual%h",rd[1][256+:256]);checks=checks+1;end
if(rv[2][0])begin if(rd[2][0+:256]!==256'h0000000300000001000000030000000100000003000000010000000300000001)$fatal(1,"PRELOAD_READBACK q2 pc0 actual%h",rd[2][0+:256]);checks=checks+1;end
if(rv[2][1])begin if(rd[2][256+:256]!==256'h0000000300000002000000030000000200000003000000020000000300000002)$fatal(1,"PRELOAD_READBACK q2 pc1 actual%h",rd[2][256+:256]);checks=checks+1;end
if(rv[3][0])begin if(rd[3][0+:256]!==256'h0000000400000001000000040000000100000004000000010000000400000001)$fatal(1,"PRELOAD_READBACK q3 pc0 actual%h",rd[3][0+:256]);checks=checks+1;end
if(rv[3][1])begin if(rd[3][256+:256]!==256'h0000000400000002000000040000000200000004000000020000000400000002)$fatal(1,"PRELOAD_READBACK q3 pc1 actual%h",rd[3][256+:256]);checks=checks+1;end
end
initial begin repeat(4)@(negedge clk);rst=1;row_v=3;row_op[0+:3]=1;row_op[3+:3]=1;@(negedge clk);row_v=0;repeat(20)@(negedge clk);col_v=3;@(negedge clk);col_v=0;repeat(30)@(negedge clk);if(checks!=8)$fatal(1,"PRELOAD_MISSING checks%0d",checks);$display("PRELOAD_FOUR_INSTANCE_READBACK_PASS instances4 sectors8 checks%0d",checks);$finish;end
endmodule
