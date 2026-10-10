`timescale 1ps/1fs
`default_nettype none
// Atomic four-tap join behind the existing native 16-lane score boundary.
// 128 credits per tap reserve every in-flight word, independent of tap skew.
// MEM=1 (FILL-9 2026-10-10, root cause of the flop build: 4 x 128 x 153 b = 78 kbit of flops behind four 128:1
// read muxes): each tap queue is an ot_fifo_sram_fwft on one ot_sram_1r1w_128x256_m1_r2c2 macro with a 2-entry
// registered head buffer (macro rd_out captured directly); the overflow check uses a per-tap occupancy counter.
module hfd_idx_t4_join #(parameter integer AW=7, CRED=128, MEM=0) (
 input wire ck, rst,
 input wire [615:0] taps,
 output reg [3:0] tap_credit,
 output wire [609:0] s,
 input wire sc,
 output reg fault
);
 reg rs1, rs2;
 always @(posedge ck or negedge rst)
   if (!rst) {rs2,rs1} <= 2'b00; else {rs2,rs1} <= {rs1,1'b1};
 wire rn=rs2;
 wire [3:0] ne;
 wire [152:0] head [0:3];
 wire [AW:0] occupancy [0:3];
 reg [8:0] credits;
 reg scq;
 reg sv;
 reg [608:0] sd;
 wire last_ok=(head[0][0]==head[1][0]) &&
              (head[0][0]==head[2][0]) && (head[0][0]==head[3][0]);
 wire fire=(&ne) && credits!=0 && !fault && last_ok;
 genvar t;
 generate for(t=0;t<4;t=t+1) begin: gt
   if (MEM == 0) begin : fl
     hfd_idx_fifo #(.W(153),.AW(AW)) queue (
       .ck(ck),.rst_n(rn),.we(taps[t*154]),.wd(taps[t*154+1 +:153]),
       .re(fire),.rd(head[t]),.ne(ne[t]),.cnt(occupancy[t]));
   end else begin : sr
     wire ovf_, hv_; wire [152:0] hd_;
     reg [AW:0] occ;
     wire [AW:0] occ_n = occ + {{AW{1'b0}}, taps[t*154]} - {{AW{1'b0}}, fire};
     ot_fifo_sram_fwft #(.W(153),.DEPTH(1<<AW),.MACRO(2)) queue (
       .clk(ck),.rst_n(rn),.push(taps[t*154]),.wdata(taps[t*154+1 +:153]),
       .pop(fire),.hv(hv_),.head(hd_),.ovf(ovf_));
     assign ne[t]=hv_; assign head[t]=hd_;
     always @(posedge ck or negedge rn)
       if(!rn) occ<={(AW+1){1'b0}}; else occ<=occ_n;
     assign occupancy[t]=occ;
   end
 end endgenerate
 always @(posedge ck or negedge rn) begin
   if(!rn) begin
     credits<=9'(CRED); scq<=0; sv<=0; tap_credit<=0; fault<=0;
   end else begin
     scq<=sc;
     sv<=fire;
     tap_credit<={4{fire}};
     case({fire,scq})
       2'b10: credits<=credits-1'b1;
       2'b01: begin
         if(credits>=CRED) fault<=1;
         else credits<=credits+1'b1;
       end
     endcase
     if((&ne) && !last_ok) fault<=1;
     for(integer u=0;u<4;u=u+1)
       if(taps[u*154] && occupancy[u]==(1<<AW) && !fire) fault<=1;
   end
 end
 always @(posedge ck) if(fire) begin
   sd[0]<=head[0][0];
   for(integer v=0;v<4;v=v+1) begin
     sd[1+4*v +:4]<=head[v][1 +:4];
     sd[17+4*v +:4]<=head[v][5 +:4];
     sd[33+64*v +:64]<=head[v][9 +:64];
     sd[289+80*v +:80]<=head[v][73 +:80];
   end
 end
 assign s={sd,sv};
endmodule
`default_nettype wire
