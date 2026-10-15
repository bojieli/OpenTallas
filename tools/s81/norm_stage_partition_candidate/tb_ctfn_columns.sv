`timescale 1ns/1ps
module tb;
reg clk=0,rst=0;reg [6:0] fv_in=0;reg[2919:0] fd_in=0;
reg[3:0] ci=0,co=0;wire[3:0] resets={4{rst}};
wire[2919:0] refd,newd;wire[6:0] refv,newv;wire refr,newr;
integer mutant=0,cycle,j,checks=0;reg[2919:0] stimulus;reg[31:0] rng=32'h7ecfa129;
ot_s81_hc_ctfn old(.clk(clk),.rst_in(rst),.fv_in(fv_in),.fd_in(fd_in),.rst_c(refr),.fvm(refv),.fdm(refd));
ot_s81_hc_ctfn_columns_candidate dut(.clk_input(ci),.clk_output(co),.rst_in(resets),.fv_in(fv_in),.fd_in(fd_in),.rst_c(newr),.fvm(newv),.fdm(newd));
initial begin
 if($value$plusargs("MUTANT=%d",mutant)) begin end
 for(cycle=0;cycle<2048;cycle=cycle+1) begin
  clk=0;ci=0;co=0;
  // Exercise reset entry, long assertion, release, and low/high reset pulses between clock edges.
  rst= !((cycle<5)||(cycle>=517&&cycle<522)||(cycle>=1031&&cycle<1035)||(cycle>=1541&&cycle<1547));
  for(j=0;j<2920;j=j+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);stimulus[j]=rng[0];end
  fd_in=stimulus;
  fv_in=rng[6:0];
  #4;
  if(cycle==721||cycle==1703)begin rst=0;#1;rst=1;end else #1;
  clk=1;ci=4'b1111;co=4'b1111;
  if(cycle==99&&mutant>=1&&mutant<=4)ci[mutant-1]=0;
  if(cycle==99&&mutant>=5&&mutant<=8)co[mutant-5]=0;
  #1;
  if(cycle>8) begin
   if({refd,refv,refr} !== {newd,newv,newr})begin $display("OBSERVED_MISMATCH mutant=%0d cycle=%0d data=%0d fv=%0d rst=%0d",mutant,cycle,refd!==newd,refv!==newv,refr!==newr);$fatal(1,"lockstep mismatch");end
   checks=checks+2928;
  end
  #4;
 end
 $display("LOCKSTEP_PASS cycles=2048 checks=%0d mutant=%0d",checks,mutant);$finish;
end
endmodule
