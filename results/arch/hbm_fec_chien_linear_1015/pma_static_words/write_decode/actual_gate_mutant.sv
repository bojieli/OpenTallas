`timescale 1ns/1fs
`default_nettype none
// Fixed-clock, fixed-start four-bank gearbox. No ready or data-driven issue.
// Starts are compiler epochs, not pulses derived from valid. Once started each
// side transfers every edge. Require WI*NI == WO*NO and matched block periods.
// Completion toggles observe ownership only: failures latch, never delay issue.
// Registers are actual storage; implementation must place/clock/route this cost.
module ot_hbm_pma_block_gearbox_static_words #(
 parameter integer WI=544,NI=16,WO=512,NO=17,MUT=0
)(input wire wclk,rclk,rst_n,w_start,r_start,
 input wire [WI-1:0] d, input wire observed_v,
 output reg [WO-1:0] q,output reg q_v,
 output reg w_fault,r_fault,
 input wire [3:0] wclk_bank);
 localparam integer B=WI*NI;
 reg [B-1:0] bank[0:3];
 reg [3:0] done,consumed,done_s1,done_s2,cons_s1,cons_s2;
 reg wa,ra;
 reg [1:0] wb,rb;
 integer wi,ri;
 // Each word is actual fixed wiring/storage. No variable full-bank shift.
 wire [NI-1:0] write_word_sel;
 wire [NO-1:0] read_word_sel;
 localparam integer READ_LEAVES=1 << $clog2(NO);
 wire [WO-1:0] bank_read[0:3];
 wire [WO-1:0] selected_read;
 wire [WO-1:0] read_valid_data;
 reg [WO-1:0] selected_bank;
 genvar g,w,r,t;
 generate for(w=0;w<NI;w=w+1)begin:write_decode
  assign write_word_sel[w]=(wi==((w==0)?1:w));
 end
 for(r=0;r<NO;r=r+1)begin:read_decode
  assign read_word_sel[r]=(ri==r);
 end
 for(g=0;g<4;g=g+1)begin:storage
  // All fixed slices keep the same one actual bank clock root.
  for(w=0;w<NI;w=w+1)begin:word
   always @(posedge wclk_bank[g])
    if(rst_n && (w_start || wa) && wb==g && write_word_sel[w])
     bank[g][w*WI+:WI]<=d;
  end
  wire [WO-1:0] tree[0:2*READ_LEAVES-2];
  for(r=0;r<READ_LEAVES;r=r+1)begin:read_leaf
   if(r<NO)assign tree[READ_LEAVES-1+r]=bank[g][r*WO+:WO] & {WO{read_word_sel[r]}};
   else assign tree[READ_LEAVES-1+r]={WO{1'b0}};
  end
  for(t=0;t<READ_LEAVES-1;t=t+1)begin:read_or
   assign tree[t]=tree[2*t+1] | tree[2*t+2];
  end
  assign bank_read[g]=tree[0];
 end endgenerate
 // Preserve four-state behavior for an unknown bank or invalid read index.
 always @* begin
  selected_bank={WO{1'bx}};
  case(rb)
   2'd0:selected_bank=bank_read[0];
   2'd1:selected_bank=bank_read[1];
   2'd2:selected_bank=bank_read[2];
   2'd3:selected_bank=bank_read[3];
  endcase
 end
 assign selected_read=selected_bank;
 assign read_valid_data=(ri>=0 && ri<NO) ? selected_read : {WO{1'bx}};
 initial if(B!=WO*NO)$fatal(1,"nonintegral gearbox block");
 always @(posedge wclk or negedge rst_n)
 if(!rst_n)begin wa<=0;wb<=0;wi<=0;done<=0;cons_s1<=0;cons_s2<=0;w_fault<=0;end
 else begin
  cons_s1<=consumed;cons_s2<=cons_s1;
  if(w_start && wa)w_fault<=1;
  if(w_start || wa)begin
   wa<=1;
   if(!observed_v)w_fault<=1;
   if(wi==0 && done[wb]!=cons_s2[wb])w_fault<=1;

   if(wi==NI-1)begin wi<=0;wb<=wb+1'b1;done[wb]<=~done[wb];end
   else wi<=wi+1;
  end
 end
 always @(posedge rclk or negedge rst_n)
 if(!rst_n)begin ra<=0;rb<=0;ri<=0;consumed<=0;done_s1<=0;done_s2<=0;r_fault<=0;q_v<=0;q<=0;end
 else begin
  done_s1<=done;done_s2<=done_s1;q_v<=0;
  if(r_start && ra)r_fault<=1;
  if(r_start || ra)begin
   ra<=1;q_v<=1;
   if(ri==0 && done_s2[rb]==consumed[rb])r_fault<=1;
   q<=read_valid_data ^ ((MUT==1 && ri==NO-1)? {{(WO-1){1'b0}},1'b1}: {WO{1'b0}});
   if(ri==NO-1)begin ri<=0;rb<=rb+1'b1;consumed[rb]<=done_s2[rb];end
   else ri<=ri+1;
  end
 end
endmodule
`default_nettype wire
