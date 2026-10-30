module tb;
reg clk=0;always #5 clk=~clk;
reg raw=0,d=0;wire baseline,face0,face1;reg previous=0;reg [31:0] r=32'h8c392ef1;
ot_dp_landing_relay ref0(clk,raw,d,baseline);
wire copy_d = MUTANT==1 ? baseline : d;
wire copy_raw = MUTANT==2 ? 1'b1 : raw;
ot_dp_landing_relay copy0(clk,copy_raw,copy_d,face0);
ot_dp_landing_relay copy1(clk,raw,d,face1);
integer checks=0;parameter MUTANT=0;
initial begin
 for(integer i=0;i<4096;i=i+1)begin
  @(negedge clk);r=r^(r<<13);r=r^(r>>17);r=r^(r<<5);
  raw=(i>3)&&(i%37>2);d=r[0];
  @(posedge clk);#1;
  if(face0!==baseline||face1!==baseline)begin
   $display("MUTANT_CAUGHT %0d edge=%0d",MUTANT,i);$finish_and_return(86);
  end
  checks=checks+2;
 end
 $display("PASS checks=%0d added_cycles=0",checks);$finish;
end
endmodule
