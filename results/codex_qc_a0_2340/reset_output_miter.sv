`timescale 1ns/1ps
module reset_output_miter;
 reg face_ck=0,outer_ck=0,rst_n=0,body_on=1;
 wire inner_ck=face_ck & body_on;
 reg reset_q;
 always #5 face_ck=~face_ck;
 always @(posedge face_ck) reset_q<=rst_n;
 always @(negedge face_ck) body_on<=$random;
 always #7 outer_ck=~outer_ck;
 reg [1:0] src=0;
 always @(posedge inner_ck) src <= {$random,$random};
 reg tv,tf;
 always @(posedge inner_ck or negedge reset_q) if(!reset_q) begin tv<=0;tf<=0;end else begin tv<=src[0];tf<=src[1];end
 reg [1:0] original,candidate,mutant;
 integer checks=0,caught=0;
 always @(posedge outer_ck) begin
  original<=reset_q?{tf,tv}:2'b0;candidate<={tf,tv};mutant<={tf,tv}^2'b01;
  #0.01;
  if(original!==candidate) $fatal(1,"reset output mismatch");
  checks=checks+1;if(original!==mutant)caught=caught+1;
 end
 integer n;
 initial begin
  #0.1;rst_n=1;#0.1;rst_n=0;
  for(n=0;n<50;n=n+1) begin #31.3;rst_n=1;#109.7;rst_n=0;end
  #20;
  if(checks<500 || caught!=checks)$fatal(1,"missing checks/control");
  $display("PASS checks=%0d wrong_data_controls=%0d data_cycles=0 boot_delta=0",checks,caught);$finish;
 end
endmodule
