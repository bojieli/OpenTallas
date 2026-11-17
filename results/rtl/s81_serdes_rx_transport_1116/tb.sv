`timescale 1ns/1ps

module tb #(parameter integer RN=4, parameter integer RRESET=4);
reg clk=0;always #5 clk=~clk;
reg rst_n=0,p_v=0;reg [543:0] raw=0;
wire [543:0] face;wire face_v;wire [8:0] parts;
ot_pl_pad #(.W(544),.N(1)) u_face_p_d(.ck(clk),.d(raw),.q(face));
ot_pl_pad #(.W(1),.N(1)) u_face_p_v(.ck(clk),.d(p_v),.q(face_v));
ot_s81_kp4_am_face3 u_parts(.clk(clk),.p_d(raw),.parts(parts));
wire [553:0] delayed;wire delayed_reset;
ot_pl_pad #(.W(554),.N(RN)) u_rck_transport4(.ck(clk),.d({parts,face_v,face}),.q(delayed));
ot_pl_pad #(.W(1),.N(RRESET)) u_rck_reset4(.ck(clk),.d(rst_n),.q(delayed_reset));
wire [1716:0] a,b;wire al,bl;wire [31:0] an,bn;
am_old u_old(.clk(clk),.rst_n(rst_n),.p_v(face_v),.p_d(face),.state(a),.lock(al),.n_relock(an));
am_new u_new(.clk(clk),.rst_n(delayed_reset),.p_v(delayed[544]),.p_d(delayed[543:0]),.am_face3(delayed[553:545]),.state(b),.lock(bl),.n_relock(bn));
reg [1716:0] history[0:3];
integer k;
always @(posedge clk) begin history[0]<=a;for(k=1;k<4;k=k+1)history[k]<=history[k-1];end
integer cycle,j,locked=0,resets=0,checks=0;reg prior=0;
initial begin
for(cycle=0;cycle<20000;cycle=cycle+1) begin
 @(negedge clk);
 for(j=0;j<17;j=j+1) raw[32*j+:32]=$urandom;
 if(cycle>=12 && cycle<4108) raw[543:532]=cycle-12;
 else raw[543:532]=(cycle%10==0)?12'hA5C:12'hFFF;
 p_v=(cycle<10000)?1:($urandom%5!=0);
 rst_n=(cycle>=12 && !(cycle>=6000 && cycle<6010) && !(cycle>=12000 && cycle<12009) && !(cycle>=16000 && cycle<16011));
 if(!rst_n)resets=resets+1;
 @(posedge clk);#0.1;
 if(cycle>20)begin
  checks=checks+1;
  if(history[3]!==b)begin
   $display("DIFF cycle=%0d RN=%0d RRESET=%0d state_x=%b",cycle,RN,RRESET,((^history[3])===1'bx || (^b)===1'bx));
   $fatal(1,"relay metadata/payload/valid/reset calendar mismatch");
  end
 end
 if(bl&&!prior)locked=locked+1;prior=bl;
end
if(locked<2)$fatal(1,"missing lock acquisitions");
$display("PASS cycles=20000 checks=%0d exhaustive_headers=4096 lock_acquisitions=%0d reset_edges=%0d state_bits=1717 cohort_bits=554 added_RX_edges=4 words_per_cycle=1",checks,locked,resets);
$finish;
end
endmodule
