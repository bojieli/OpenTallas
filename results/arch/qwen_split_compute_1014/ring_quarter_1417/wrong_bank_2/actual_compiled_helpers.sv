(* keep_hierarchy = 1 *) module ot_coll_local_ring_quarter #(parameter integer OFF=55,W=128,ID=0)(
 input wire ctl_ck,input wire[1:0]mem_ck,input wire rs_n,input wire[W-1:0]wd,output wire[W-1:0]rd);
 localparam integer B=(OFF<=32)?1:2,AW=5+$clog2(B);
 initial if(OFF<2||OFF>64||W<1||W>128)$error("local quarter ring: OFF2..64,W1..128");
 reg[AW-1:0]wa;
 always @(posedge ctl_ck or negedge rs_n)if(!rs_n)wa<=0;else wa<=wa+1'b1;
 wire[AW-1:0]ra=wa-AW'(OFF-1);
 wire[127:0]wdata={{(128-W){1'b0}},wd};wire[128*B-1:0]rdata;
 genvar b;
 generate for(b=0;b<B;b=b+1)begin:g_bank
  wire we;
  if(B==1)begin:g_one assign we=1'b1;end else begin:g_two assign we=wa[5]==b;end
  ot_sram_1r1w_32x128_m1 u_m(.clk(mem_ck[b]),.r_ce_in(1'b1),.r_addr_in(ra[4:0]),.rd_out(rdata[128*b +:128]),
   .w_ce_in(we),.w_addr_in(wa[4:0]),.wd_in(wdata),.w_mask_in({128{1'b1}}));
 end
 if(B==1)begin:g_one assign rd=rdata[0 +:W];end else begin:g_two
  // Two private one-hot copies bound fanout to64bits per bank. They have the
  // same unreset registered read-bank timing as the legacy546-bit ring.
  wire[1:0]sel0,sel1;
  ot_coll_local_rep_reg #(.W(2),.ID(128+ID*2),.RST(0)) u_sel0(.clk(ctl_ck),.rst_n(1'b1),.d(ra[5]?2'b01:2'b10),.q(sel0));
  ot_coll_local_rep_reg #(.W(2),.ID(129+ID*2),.RST(0)) u_sel1(.clk(ctl_ck),.rst_n(1'b1),.d(ra[5]?2'b01:2'b10),.q(sel1));
  for(genvar k=0;k<W;k=k+1)begin:g_bit
   wire[1:0]sel=(k<64)?sel0:sel1;
   assign rd[k]=(rdata[k]&sel[0])|(rdata[128+k]&sel[1]);
  end
 end endgenerate
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_rep_reg #(parameter integer W = 1, ID = 0, RST = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output reg [W-1:0] q);
    generate if (RST) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule
module ot_coll_static_ring #(parameter integer OFF = 20) (
    input  wire         clk,
    input wire [3:0] mem_ck,
    input  wire         rs_n,
    input  wire [545:0] wd,
    output wire [545:0] rd
);
    localparam integer B  = (OFF <= 32) ? 1 : (OFF <= 64) ? 2 : 4;
    localparam integer AW = 5 + $clog2(B);
    initial if (OFF < 2 || OFF > 128) $error("ot_coll_static_ring: 2 <= OFF <= 128");
    reg [AW-1:0] wa;
    always @(posedge clk or negedge rs_n) if (!rs_n) wa <= 0; else wa <= wa + 1'b1;
    wire [AW-1:0] ra = wa - AW'(OFF - 1);      // read issued OFF - 1 cycles after the write, data one edge later
    wire [546*B-1:0] rdb;
    genvar b;
    generate for (b = 0; b < B; b = b + 1) begin : g_b
        ot_sram_1r1w_32x546_m1 u_m (.clk(mem_ck[b]), .r_ce_in(1'b1), .r_addr_in(ra[4:0]), .rd_out(rdb[b*546 +: 546]),
            .w_ce_in((B == 1) ? 1'b1 : (wa[AW-1:5] == b)), .w_addr_in(wa[4:0]), .wd_in(wd), .w_mask_in({546{1'b1}}));
    end endgenerate
    generate if (B == 1) begin : g_one
        assign rd = rdb;
    end else begin : g_sel
        // decoded bank select (one-hot AND-OR, constant-index slices: no wide runtime part-select); the registered
        // one-hot is replicated per <= 110-bit group (s4: one rbs drove 1,604 loads)
        localparam integer NG = 5, GW = 110;
        reg [545:0] rsel;
        wire [B*NG-1:0] boh;
        genvar gg;
        for (gg = 0; gg < NG; gg = gg + 1) begin : g_g
            wire [B-1:0] oh_d;
            for (genvar kd = 0; kd < B; kd = kd + 1) begin : g_d
                assign oh_d[kd] = (ra[AW-1:5] == kd);
            end
            ot_coll_rep_reg #(.W(B), .ID(64 + OFF*8 + gg), .RST(0)) u_oh (.clk(clk), .rst_n(1'b1), .d(oh_d), .q(boh[gg*B +: B]));
        end
        integer kb, kbit;
        always @(*) begin
            rsel = 546'd0;
            for (kbit = 0; kbit < 546; kbit = kbit + 1)
                for (kb = 0; kb < B; kb = kb + 1)
                    rsel[kbit] = rsel[kbit] | (rdb[kb*546 + kbit] & boh[(kbit / GW)*B + kb]);
        end
        assign rd = rsel;
    end endgenerate
endmodule
(* keep_hierarchy = 1 *) module ot_coll_rep_reg #(parameter integer W = 1, ID = 0, RST = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output reg [W-1:0] q);
    generate if (RST) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule
