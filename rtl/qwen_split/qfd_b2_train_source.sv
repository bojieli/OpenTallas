`timescale 1ns/1ps
// NEW point-to-point train command producer pins. Exactly50 independent FF.
// Source IB is on ck_head, result tags on ck_tree; physical clock phase remains assigned externally.
// Adds one edge to each observed source signal, no change to controller execution.
module qfd_b2_train_source(
 input wire ck_head,ck_tree,rst_n,
 input wire[379:0]ib,input wire[340:0]tc2,
 output reg me_go,output reg[17:0]me_tiles,output reg[23:0]me_ts,
 output reg[3:0]me_split,output reg me_oen,output reg tag_v,tag_last);
 always @(posedge ck_head or negedge rst_n)
 if(!rst_n)begin me_go<=0;me_tiles<=0;me_ts<=0;me_split<=0;me_oen<=0;end
 else begin
 me_go<=ib[0];me_tiles<=ib[36:19];me_ts<=ib[103:80];me_split<=ib[254:251];me_oen<=ib[353];
 end
 always @(posedge ck_tree or negedge rst_n)
 if(!rst_n)begin tag_v<=0;tag_last<=0;end
 else begin tag_v<=tc2[26];tag_last<=tc2[139];end
endmodule
