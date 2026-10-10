`timescale 1ps/1fs
`default_nettype none
// Atomic four-tap join behind the existing native 16-lane score boundary.
// 128 credits per tap reserve every in-flight word, independent of tap skew.
module hfd_idx_t4_join #(parameter integer AW=7, CRED=128) (
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
 generate for(genvar t=0;t<4;t=t+1) begin: gt
   hfd_idx_fifo #(.W(153),.AW(AW)) queue (
     .ck(ck),.rst_n(rn),.we(taps[t*154]),.wd(taps[t*154+1 +:153]),
     .re(fire),.rd(head[t]),.ne(ne[t]),.cnt(occupancy[t]));
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
     for(integer t=0;t<4;t=t+1)
       if(taps[t*154] && occupancy[t]==(1<<AW) && !fire) fault<=1;
   end
 end
 always @(posedge ck) if(fire) begin
   sd[0]<=head[0][0];
   for(integer t=0;t<4;t=t+1) begin
     sd[1+4*t +:4]<=head[t][1 +:4];
     sd[17+4*t +:4]<=head[t][5 +:4];
     sd[33+64*t +:64]<=head[t][9 +:64];
     sd[289+80*t +:80]<=head[t][73 +:80];
   end
 end
 assign s={sd,sv};
endmodule
`default_nettype wire
