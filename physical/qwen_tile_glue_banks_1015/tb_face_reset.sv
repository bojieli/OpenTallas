`timescale 1ns/1ps
module tb_face_reset;
`ifndef MUT
`define MUT 0
`endif
reg clk=0,rst_n=0;
wire [95:0] resets;
reg [2:0] reference=0;
wire [513:0] q;
reg [513:0] d={257{2'b10}};
integer n,checks=0,errors=0;
wire [507:0] tq;
wire [513:0] aq,bq,yq;
ot_qwen_tile_native_face_reset #(.RMUT(`MUT)) dut(.ck_reset({9{clk}}),.ck_face({5{clk}}),.rst_n(rst_n),.tap_d(d[507:0]),.na_d(d),.nb_d(d),.to_d(d),.ny_d(d),.tap_q(tq),.na_q(aq),.nb_q(bq),.to_q(q),.ny_q(yq),.reset_targets(resets));
task step;
begin
 #4;clk=1;reference={reference[1:0],rst_n};#1;
 checks=checks+96;
 if(resets !== {96{reference[2]}})errors=errors+1;
 clk=0;
end
endtask
initial begin
 // All constant-reset masters initialize while capturing the asserted reset.
 for(n=0;n<16;n=n+1)begin #4;clk=1;#1;clk=0;end
 reference=0;
 if(resets!==96'd0 || {tq,aq,bq,q,yq}!==2564'd0)errors=errors+1;
 rst_n=1;
 for(n=1;n<=8;n=n+1)begin
  step();checks=checks+2564;
  if(n<7 ? {tq,aq,bq,q,yq}!==2564'd0 : {tq,aq,bq,q,yq}!=={d[507:0],d,d,d,d})errors=errors+1;
 end
 for(n=0;n<512;n=n+1)begin
  rst_n=((n%11)>3);step();
 end
 rst_n=0;
 for(n=0;n<16;n=n+1)step();
 if({tq,aq,bq,q,yq}!==2564'd0)errors=errors+1;
 if(errors)begin $display("FAIL native_full_face_reset checks=%0d errors=%0d",checks,errors);$fatal;end
 $display("PASS native_full_face_reset checks=%0d fixed_reset_edges=3 first_data_edge=7",checks);$finish;
end
endmodule
