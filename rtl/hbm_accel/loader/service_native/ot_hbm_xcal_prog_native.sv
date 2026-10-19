`timescale 1ns/1ps
`default_nettype none
// Opt-in native programme/RELOC tile. The clk port is the actual programme root.
module ot_hbm_xcal_prog_native #(parameter integer MUT=0, PAW=11, PREL=1)(
 input wire clk,rst_n,
 input wire cfg_we,input wire [PAW-1:0] cfg_addr,input wire [255:0] cfg_data,
 input wire start_v,input wire [PAW-1:0] start_base,input wire [PAW:0] start_limit,
 input wire [15:0] start_loops,input wire [4:0] start_ctx,
 output wire [108:0] cmd_ext,output wire [63:0] kv_desc,
 output wire active,done,fault
);
 (* keep = 1 *) reg [1:0] reset_landing;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)reset_landing<=0;else reset_landing<={reset_landing[0],1'b1};
 wire rst_q=reset_landing[1];
 reg cw,sv;reg [PAW-1:0] ca,sb;reg [255:0] cd;reg [PAW:0] sl;reg [15:0] sn;reg [4:0] sx;
 always @(posedge clk)begin ca<=cfg_addr;cd<=cfg_data;sb<=start_base;sl<=start_limit;sn<=start_loops;sx<=start_ctx;end
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin cw<=0;sv<=0;end else begin cw<=cfg_we;sv<=start_v;end
 wire [172:0] word0;wire [4:0] wctx;wire [31:0] word_ord;wire cal_v;
 ot_smh_calendar_static_x #(.W(173),.AW(PAW),.XW(5)) u_cal(
  .clk(clk),.rst_n(rst_q),.cfg_we(cw),.cfg_addr(ca),.cfg_data(cd),
  .start_v(sv),.start_base(sb),.start_limit(sl),.start_loops(sn),.start_ctx(sx),
  .calendar(word0),.calendar_ctx(wctx),.calendar_iter(),.calendar_lastit(),
  .calendar_v(cal_v),.ordinal(word_ord),.active(active),.done(done),.fault(fault));
    // RELOC mirror of the svg feed: R stage (+1 edge) = the svg cache-read edge, C stage (+2) = the svg command edge.
    // mrel: the SM mode [183:181] (cmd_ext [100:98]) of every magic word comes from the descriptor (P2: one programme for
    // FP8 / FP4 / BF16 bodies of a shape); fl: the format-launch edge (R edge of the programme's first word) carries
    // {magic, mode} as the svg carries {format_launch, mode[1:0]}.  PREL=0: one stage (absolute words, old envelope).
    localparam [7:0] MAGIC = 8'ha2;
    reg [172:0] word_r, word_c;
    always @(posedge clk) begin
        word_r <= word0;
        if (PREL != 0 && cal_v && wctx[1] && word0[108:101] == MAGIC) word_r[100:98] <= wctx[4:2];
        word_c <= word_r;
        if (PREL != 0 && cal_v && word_ord == 0 && wctx[0]) begin word_c[108:101] <= MAGIC; word_c[100:98] <= wctx[4:2]; end
    end
    wire [172:0] word = (MUT == 4) ? word0 : (PREL != 0) ? word_c : word_r;
    assign cmd_ext = (MUT == 2) ? word[172:64] : word[108:0];
    assign kv_desc = (MUT == 2) ? word[63:0] : word[172:109];
endmodule
`default_nettype wire
