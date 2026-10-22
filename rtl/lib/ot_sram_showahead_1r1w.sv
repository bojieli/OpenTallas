`timescale 1ns/1ps
// Registered continuous SRAM read, NEW on a current logical same-address write.
// WREG=1 registers macro write pins; its previous logical write also forwards.
// Caller supplies ra = NEXT head and independent same-depth resets per16-bit slice.
// No reset/storage ECC is added to the SRAM. Two unconditional payload registers
// avoid a W-bit hit-enable cone; reset-distinct kept flags each select <=16 bits.
module ot_sram_showahead_1r1w #(
 parameter integer W=553, AW=3, WREG=1, NS=(W+15)/16, MUT=0
)(input wire clk, input wire [NS-1:0] rst_n,
 input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
 input wire [AW-1:0] ra, output wire [W-1:0] q);
 localparam integer NB=(W+127)/128;
 reg wv; reg [AW-1:0] waddr; reg [W-1:0] wdata, prevdata;
 always @(posedge clk or negedge rst_n[0]) if(!rst_n[0]) wv<=1'b0; else wv<=we;
 always @(posedge clk) begin waddr<=wa; wdata<=wd; prevdata<=wdata; end
 wire current_hit=we && wa==ra;
 wire previous_hit=(WREG!=0) && wv && waddr==ra;
 wire mw=(WREG!=0) ? wv : we;
 wire [AW-1:0] mwa=(WREG!=0) ? waddr : wa;
 wire [W-1:0] mwd=(WREG!=0) ? wdata : wd;
 wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},mwd}, raw;
 genvar b,s;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
`ifdef OT_SHOWAHEAD_FLOP
  // flop variant: storage lives in g_fs below (raw driven there)
`elsif OT_SRAM_P192
  // pitch-192 pin-limited 32x128 (51.408x39.960, W/E 4.98/4.95 pins/um); same ports/timing contract
  ot_sram_1r1w_32x128_m1_p192_rc u_m(.clk(clk),.r_ce_in(1'b1),.r_addr_in(5'(ra)),
   .rd_out(raw[b*128+:128]),.w_ce_in(mw),.w_addr_in(5'(mwa)),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
`else
  ot_sram_1r1w_32x128_m1 u_m(.clk(clk),.r_ce_in(1'b1),.r_addr_in(5'(ra)),
   .rd_out(raw[b*128+:128]),.w_ce_in(mw),.w_addr_in(5'(mwa)),
   .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
`endif
 end
`ifdef OT_SHOWAHEAD_FLOP
 // STW-S81c-COLLA 10-22 (TOPK control h NEEDS_RTL: SRAM clk->q -> queue head -> packet done, TT -111): opt-in flop
 // storage per 16-bit slice.  The macro read is registered (old word); here the read ADDRESS is registered (kept copy
 // per slice, same edge) and the word is read combinationally after the edge.  They differ only when the landing write
 // (wv/waddr) hits the read address on that edge, and exactly then previous_hit selects prevdata (= that write's data),
 // so q is identical.  Write enables decode from per-slice kept copies of wv / waddr (same D, same edge, same reset).
 wire [(1<<AW)-1:0] woh_d, roh_d;
 for(s=0;s<(1<<AW);s=s+1) begin:g_wd
  assign woh_d[s] = we && wa == AW'(s);
  assign roh_d[s] = ra == AW'(s);
 end
 for(s=0;s<NS;s=s+1) begin:g_fs
  localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16;
  // per-slice copies live in keep_hierarchy instances (plain keep regs were merged by synthesis: 1432 loads).
  // Write and read addresses are decoded ONCE (woh_d / roh_d, one line per word) and each slice registers its own
  // one-hot copies, so no address bit fans into every slice's decoder / mux tree (control i/j census: read-address
  // copy bit 64 loads per 16-bit slice, rp/wp 46-49 loads with per-8-bit copies).  Each one-hot line drives one
  // slice's 16 bits (enables / AND-OR read); each decoded line drives NS (<= 32) copies.
  wire [(1<<AW)-1:0] woh_s, roh_s;
  ot_sa_ohcopy #(.W(1<<AW),.ID(s)) u_wc (.clk(clk),.rst_n(rst_n[s]),.d(woh_d),.q(woh_s));
  ot_sa_copy #(.W(1<<AW),.ID(s)) u_ac (.clk(clk),.d(roh_d),.q(roh_s));
  reg [SW-1:0] mfs [0:(1<<AW)-1];
  integer k;
  always @(posedge clk) for(k=0;k<(1<<AW);k=k+1) if(woh_s[k]) mfs[k]<=wdata[LO+:SW];
  reg [SW-1:0] rd_s;
  integer kr;
  always @* begin rd_s='0; for(kr=0;kr<(1<<AW);kr=kr+1) rd_s=rd_s|({SW{roh_s[kr]}}&mfs[kr]); end
  assign raw[LO+:SW]=rd_s;
 end
`endif
 for(s=0;s<NS;s=s+1) begin:g_slice
  localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16;
  (* keep="true" *) reg cur_q, prev_q;
  always @(posedge clk or negedge rst_n[s])
   if(!rst_n[s]) begin cur_q<=1'b0; prev_q<=1'b0; end
   else begin cur_q<=(MUT==1)?1'b0:current_hit; prev_q<=(MUT==2)?1'b0:previous_hit; end
  assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
 end endgenerate
`ifndef SYNTHESIS
 initial begin
  if(AW>5 || AW<1 || W<1 || NS!=(W+15)/16) $fatal(1,"ot_sram_showahead_1r1w invalid shape");
 end
`endif
endmodule

`ifdef OT_SHOWAHEAD_FLOP
// distinct-ID same-D copies behind module boundaries (synthesis may not merge them)
(* keep_hierarchy="yes" *)
module ot_sa_copy #(parameter integer W=1, ID=0)(input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
 (* keep *) reg [W-1:0] r; always @(posedge clk) r<=d; assign q=r;
endmodule
(* keep_hierarchy="yes" *)
module ot_sa_ohcopy #(parameter integer W=1, ID=0)(input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
 (* keep *) reg [W-1:0] r; always @(posedge clk or negedge rst_n) if(!rst_n) r<='0; else r<=d; assign q=r;
endmodule
(* keep_hierarchy="yes" *)
module ot_sa_rcopy #(parameter integer ID=0)(input wire clk, rst_n, d, output wire q);
 (* keep *) reg r; always @(posedge clk or negedge rst_n) if(!rst_n) r<=1'b0; else r<=d; assign q=r;
endmodule
`endif
