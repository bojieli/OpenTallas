`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,p_v=0;reg [543:0] raw=0;wire [543:0] face;wire face_v;
ot_pl_pad #(.W(544),.N(1)) u_face_p_d(.ck(clk),.d(raw),.q(face));
ot_pl_pad #(.W(1),.N(1)) u_face_p_v(.ck(clk),.d(p_v),.q(face_v));
wire [8:0] parts;ot_s81_kp4_am_face3 u_parts(.clk(clk),.p_d(raw),.parts(parts));
wire ck_syn=clk;
wire [8:0] face_am_parts=parts;wire face_p_v=face_v;wire [543:0] face_p_d=face;
`ifdef OT_S81_RCK_RELAY4
`ifndef OT_S81_KP4_AM_FACE3
initial $error("RCK relay4 requires the joint AM face3 source option");
`endif
// A whole cohort, one word/edge. The reset root takes the SAME four edges.
wire [543:0] rck_p_d;
wire rck_p_v;
wire [8:0] rck_am_parts;
wire rck_reset_calendar;
ot_pl_pad #(.W(554), .N(4)) u_rck_transport4 (.ck(ck_syn),
    .d({face_am_parts, face_p_v, face_p_d}), .q({rck_am_parts, rck_p_v, rck_p_d}));
ot_pl_pad #(.W(1), .N(3)) u_rck_reset4 (.ck(ck_syn), .d(rst_n), .q(rck_reset_calendar));
`endif

reg [1716:0] history [0:3];integer h;
always @(posedge clk) begin history[0]<=a;for(h=1;h<4;h=h+1)history[h]<=history[h-1];end
wire [1716:0] expected=history[3];

wire [1716:0] a,b;wire al,bl;wire [31:0] an,bn;
am_old u_old(.clk(clk),.rst_n(rst_n),.p_v(face_v),.p_d(face),.state(a),.lock(al),.n_relock(an));
am_new u_new(.clk(clk),.rst_n(rck_reset_calendar),.p_v(rck_p_v),.p_d(rck_p_d),.am_face3(rck_am_parts),.state(b),.lock(bl),.n_relock(bn));
integer cycle,j,locked=0,resets=0;reg prior=0;
initial begin
for(cycle=0;cycle<20000;cycle=cycle+1) begin
 @(negedge clk);
 for(j=0;j<17;j=j+1) raw[32*j+:32]=$urandom;
 if(cycle>=12 && cycle<4108) raw[543:532]=cycle-12;
 else raw[543:532]=(cycle%10==0)?12'hA5C:12'hFFF;
 p_v=(cycle<10000)?1:($urandom%5!=0);
 rst_n=(cycle>=12 && !(cycle>=6000 && cycle<6010) && !(cycle>=12000 && cycle<12009) && !(cycle>=16000 && cycle<16011));
 if(!rst_n) resets=resets+1;
 @(posedge clk);#0.1;
 if(cycle>24 && expected!==b) begin $display("DIFF cycle=%0d am=%b/%b pv=%b/%b lock=%b/%b state_x=%b",cycle,u_old.am_ok,u_new.am_ok,u_old.pv,u_new.pv,al,bl,((^a)===1'bx || (^b)===1'bx));$fatal(1,"literal relay4 cohort/reset/calendar mismatch");end
 if(al&&!prior) locked=locked+1;prior=al;
end
if(locked<2)$fatal(1,"missing native lock acquisition coverage");
$display("PASS cycles=20000 exhaustive_headers=4096 lock_acquisitions=%0d reset_edges=%0d state_bits=1717 added_ff=2229 added_full_cycles=4",locked,resets);
$finish;
end
endmodule
