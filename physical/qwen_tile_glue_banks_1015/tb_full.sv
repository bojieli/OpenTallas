`timescale 1ns/1ps
module tb_full;
`ifndef MUT
`define MUT 0
`endif
reg clk=0,rst=0;
reg manual=0;
reg [9:0] independent_ck=0;
wire [9:0] face_ck=manual ? independent_ck : {10{clk}};
reg [507:0] tap;
reg [513:0] na,nb,to_d,ny;
wire [507:0] tq;
wire [513:0] aq,bq,oq,yq;
reg [507:0] te;
reg [513:0] ae,be,oe,ye;
integer n,b,checks=0,errors=0;
reg [31:0] rng=32'h51ac3072;
ot_qwen_tile_face_banks_full #(.MUT(`MUT)) dut(.ck_face(face_ck[4:0]),.rst_face_n({5{rst}}),.tap_d(tap),.na_d(na),.nb_d(nb),.to_d(to_d),.ny_d(ny),.tap_q(tq),.na_q(aq),.nb_q(bq),.to_q(oq),.ny_q(yq));
task next_inputs;
begin
 for(b=0;b<514;b=b+1) begin
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  if(b<508)tap[b]=rng[0];na[b]=rng[1];nb[b]=rng[2];to_d[b]=rng[3];ny[b]=rng[4];
 end
end
endtask
task compare;
begin
 checks=checks+2564;
 if({tq,aq,bq,oq,yq} !== {te,ae,be,oe,ye})errors=errors+1;
end
endtask
initial begin
 next_inputs();
 for(n=0;n<8;n=n+1) begin #4;clk=1;#1;clk=0;end
 rst=1;
 // Reset release edge3, first data capture edge4, as actual leaf contract.
 for(n=0;n<4;n=n+1)begin #4;clk=1;#1;clk=0;end
 te=tap;ae=na;be=nb;oe=to_d;ye=ny;compare();
 for(n=0;n<4096;n=n+1)begin
  next_inputs();#1;compare(); // Missing-register mutants are observed before an edge.
  #3;clk=1;te=tap;ae=na;be=nb;oe=to_d;ye=ny;#1;compare();clk=0;
 end
 // Reassert/reset/release exercises the real local reset tree again.
 rst=0;#1;
 for(n=0;n<4;n=n+1)begin #4;clk=1;#1;clk=0;end
 rst=1;
 for(n=0;n<4;n=n+1)begin #4;clk=1;#1;clk=0;end
 te=tap;ae=na;be=nb;oe=to_d;ye=ny;compare();
 // Prove each of the five actual roots owns its declared bit slice.
 manual=1;
 for(n=0;n<5;n=n+1)begin
  next_inputs();#1;compare();
  #3;independent_ck[n]=1;
  case(n)
   0:te=tap;1:ae=na;2:be=nb;3:oe=to_d;4:ye=ny;
  endcase
  #1;compare();independent_ck[n]=0;
 end
 if(errors)begin $display("FAIL tile_native_full_face_banks checks=%0d errors=%0d",checks,errors);$fatal;end
 $display("PASS tile_native_full_face_banks checks=%0d",checks);$finish;
end
endmodule
