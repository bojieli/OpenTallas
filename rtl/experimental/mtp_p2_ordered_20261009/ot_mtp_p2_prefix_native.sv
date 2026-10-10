`timescale 1ns/1ps
`default_nettype none
// Converts the actual protected accumulator code into the native FP32 stream.
// One-flight decoder; duplicate held data/control detect mutable-state faults.
// mtp-lead 2026-10-09: BREG=1 gates healthy with a registered duplicate-state compare (default 0: original).
module ot_mtp_p2_prefix_native #(parameter integer ENABLE=0, BREG=0)(
 input wire clk,rst_n,abort,input wire in_v,output wire in_r,
 input wire [575:0] in_secded,input wire [73:0] in_identity,
 input wire [6:0] in_word,input wire in_last,
 output wire out_v,input wire out_r,output wire [511:0] out_data,
 output wire [73:0] out_identity,output wire [6:0] out_word,
 output wire out_last,output wire fault,corrected
);
 generate if(!ENABLE)begin: disabled
 assign in_r=0;assign out_v=0;assign out_data=0;assign out_identity=0;
 assign out_word=0;assign out_last=0;assign fault=0;assign corrected=0;
 end else begin: enabled
 reg [1:0] state,state_copy;
 reg [511:0] held,held_copy;
 reg [73:0] identity,identity_copy;
 reg [6:0] word,word_copy;reg last,last_copy,fault_q,corrected_q;
 wire bad=(state!=state_copy)||(held!=held_copy)||(identity!=identity_copy)||
 (word!=word_copy)||(last!=last_copy);
 reg bad_q;
 wire healthy=!fault_q&&!(BREG?bad_q:bad)&&!abort;
 wire [511:0] decoded;wire [7:0] dv,ce,ue;
 assign in_r=healthy&&state==0;assign out_v=healthy&&state==2;
 assign out_data=held;assign out_identity=identity;assign out_word=word;
 assign out_last=last;assign fault=fault_q||bad;assign corrected=corrected_q;
 for(genvar s=0;s<8;s=s+1)begin: codecs
 ot_secded_dec #(.K(64),.R(8)) d(.clk(clk),.rst_n(rst_n),.v(in_v&&in_r),
 .w(in_secded[72*s+:72]),.ov(dv[s]),.d(decoded[64*s+:64]),
 .ce(ce[s]),.ue(ue[s]),.n_ce(),.n_ue());
 end
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin state<=0;state_copy<=0;held<=0;held_copy<=0;
 identity<=0;identity_copy<=0;word<=0;word_copy<=0;last<=0;last_copy<=0;
 fault_q<=0;corrected_q<=0;bad_q<=0;end
 else begin bad_q<=bad;
 if(bad||abort)fault_q<=1;
 if(healthy)case(state)
 0:if(in_v&&in_r)begin identity<=in_identity;identity_copy<=in_identity;
 word<=in_word;word_copy<=in_word;last<=in_last;last_copy<=in_last;
 state<=1;state_copy<=1;end
 1:if(&dv)begin if(|ue)fault_q<=1;
 else begin held<=decoded;held_copy<=decoded;if(|ce)corrected_q<=1;state<=2;state_copy<=2;end end
 2:if(out_v&&out_r)begin state<=0;state_copy<=0;end
 default:fault_q<=1;
 endcase end end
 end endgenerate
endmodule
`default_nettype wire
