`timescale 1ns/1ps
// Enumerate every physical 7-bit pointer state in the production W25/D123 RF.
// Only the initial pointer is injected; memories/data are the actual DUT logic.
module tb_idx_meta_rf_powerup;
 parameter integer MUT=0;
 reg clk=0, rst_n=0;
 reg [24:0] d=0;
 wire [24:0] q[0:127];
 for(genvar s=0;s<128;s=s+1)begin : states
  localparam [6:0] INITIAL=s;
  ot_hdc_delay_rf #(.W(25),.D(MUT==1?122:123)) dut(.clk(clk),.rst_n(rst_n),.d(d),.q(q[s]));
  initial begin
   // Override simulation-only initial-zero after it has executed. Release
   // before the first active edge, so all subsequent state is real RTL.
   #0.1; force dut.wptr=INITIAL;
   #0.1; release dut.wptr;
   #0.1; if(dut.wptr !== INITIAL)$fatal(1,"initial pointer injection failed state=%0d",INITIAL);
  end
 end
 reg [24:0] samples[0:1023];
 reg [31:0] random_state=32'hba7239e1;
 integer checks=0, errors=0, invalid_checks=0;
 integer n,s;
 initial begin
  for(n=0;n<1024;n=n+1)begin
   random_state=random_state^(random_state<<13);
   random_state=random_state^(random_state>>17);
   random_state=random_state^(random_state<<5);
   d=random_state[24:0];samples[n]=d;
   // Reset is intentionally irrelevant for RESET=0, including after fill.
   rst_n=!(n<4 || (n>=300 && n<305) || n==500 || n==777);
   #5;clk=1;#1;
   // D edges means sample at edge 0 appears immediately after edge D-1.
   // There is no extra allowance for out-of-range initial pointers 121..127.
   if(n>=122)begin
    for(s=0;s<128;s=s+1)begin
     checks=checks+1;
     if(s>=121)invalid_checks=invalid_checks+1;
     if(q[s]!==samples[n-122])begin
      if(errors<12)$display("mismatch state=%0d edge=%0d expected=%h actual=%h",s,n,samples[n-122],q[s]);
      errors=errors+1;
     end
    end
   end
   #4;clk=0;
  end
  $display("IDX_META_RF_POWERUP states=128 invalid_states=7 cycles=1024 first_checked_edge=122 checks=%0d invalid_checks=%0d errors=%0d MUT=%0d",checks,invalid_checks,errors,MUT);
  if(errors!=0)$fatal(1,"RF metadata delay is not D123 from every physical pointer state");
  $finish;
 end
endmodule
