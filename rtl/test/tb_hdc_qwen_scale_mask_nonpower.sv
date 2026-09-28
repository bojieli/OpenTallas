`timescale 1ns/1ps
// Six groups stand in for shipped G6144. S4 leaves a G%S tail, and nout=2
// makes only group 0's first slot useful. Inactive scale data is poison.
module tb_hdc_qwen_scale_mask_nonpower;
    reg clk=0, rst_n=0, go=0;
    always #5 clk=~clk;
    wire ready, idle, scale_re, ov, fault, am_any;
    wire [5:0] scale_gre, o_we;
    wire [143:0] scale_addr;
    reg [191:0] scale_q={12{16'h7fc0}};
    wire [11:0] o_mask;
    wire [383:0] o_data;
    wire [15:0] am_idx;
    wire [31:0] am_val;
    integer requests=0, group_reads=0, writes=0, g;
    ot_hdc_matvec #(.G(6),.W(2),.IL(8),.INT8_WEIGHT(1)) dut (
        .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),
        .i_nout(16'd2),.i_tiles(16'd1),.i_k(16'd1),
        .i_wsrc(1'b0),.i_wbase(24'd100),.i_ts(24'd0),.i_ks(24'd0),.i_js(24'd0),
        .i_xbase(24'd0),.i_xks(24'd0),.i_xjs(24'd0),.i_xcs(24'd0),
        .i_jsh(3'd0),.i_split(4'd2),.i_wcs(24'd0),.i_round(1'b1),
        .i_obase(24'd0),.i_ots(24'd8),.i_ojs(24'd1),
        .i_mmode(1'b0),.i_oen(1'b1),.i_amax(1'b1),
        .i_rmax(1'b0),.i_mbase(24'd0),
        .wrom_q({12{8'h01}}),.scale_re(scale_re),.scale_gre(scale_gre),
        .scale_addr(scale_addr),.scale_q(scale_q),
        .kv_q(384'd0),.x_q({6{32'h3f800000}}),
        .ov(ov),.o_we(o_we),.o_mask(o_mask),.o_data(o_data),
        .am_idx(am_idx),.am_val(am_val),.am_any(am_any),.fault(fault));
    always @(posedge clk) begin
        if (scale_re) begin
            if (scale_gre !== 6'b000001)
                $fatal(1,"inactive group read mask=%b",scale_gre);
            for (g=0;g<6;g=g+1)
                if (scale_addr[g*24 +:24] !== 24'd100)
                    $fatal(1,"inactive group address overreach g=%0d addr=%0d",g,scale_addr[g*24 +:24]);
            scale_q <= {{10{16'h7fc0}},16'h4040,16'h4000};
            requests <= requests+1;
            group_reads <= group_reads+1;
        end
        if (o_we[0]) begin
            if (writes==0 && (o_mask[1:0]!==2'b11 ||
                o_data[31:0]!==32'h41000000 || o_data[63:32]!==32'h41400000))
                $fatal(1,"active output changed: mask=%b data=%h",o_mask,o_data[63:0]);
            writes <= writes+1;
        end
    end
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        @(negedge clk); go=1;
        @(negedge clk); go=0;
        wait(idle);
        @(negedge clk);
        if (fault || requests!=1 || group_reads!=1 || writes!=8 ||
            !am_any || am_idx!=1 || am_val!==32'h41400000)
            $fatal(1,"scale mask failed fault=%b req=%0d groups=%0d writes=%0d argmax=%b/%0d/%h",
                   fault,requests,group_reads,writes,am_any,am_idx,am_val);
        $display("PASS Qwen scale mask: G6/S4, 1 active of 6 groups, poison inactive, no overreach/fault");
        $finish;
    end
    initial begin #20000; $fatal(1,"scale mask timeout"); end
endmodule
