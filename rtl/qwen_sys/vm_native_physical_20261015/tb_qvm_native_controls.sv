`timescale 1ns/1ps
module tb_qvm_native_controls #(parameter integer OBS=0,MUT=0);
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,re=0,we=0; reg [7:0] ra=0,wl=0; reg [15:0] wm=0;
 wire rtg,m_re,m_we;wire[7:0]m_ra,m_wl;wire[15:0]m_wm;
 wire cv;wire[7:0]cl;wire[15:0]cm;
 generate if(!OBS)begin
 ot_qfd_vm_bctl_nx #(.LAW(8),.NRI(2),.MUT(MUT?3:0)) dut(.clk(clk),.rst_n(rst_n),.re(re),.ra(ra),.we(we),.wl(wl),.wm(wm),.rtg(rtg),.m_re(m_re),.m_ra(m_ra),.m_we(m_we),.m_wl(m_wl),.m_wm(m_wm));
 end else begin
 qfd_vm_qcommit #(.LAW(8))dut(.ck(clk),.rst_n(rst_n),.bank_rst_n(rst_n),.we(we),.wl(wl^(MUT?8'h01:8'h00)),.wm(wm),.cv(cv),.cl(cl),.cm(cm));
 end endgenerate
 reg [33:0] d1=0,d2=0;integer i;reg[31:0]rng=32'h8a376125;
 initial begin
 repeat(3)@(negedge clk);rst_n=1;
 repeat(8)@(negedge clk);
 for(i=0;i<2048;i=i+1)begin
 rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
 re=rng[0];we=rng[1];ra=rng[9:2];wl=rng[17:10];wm=rng[31:16];
 @(posedge clk);d2=d1;d1={re,we,ra,wl,wm};#1;
 if(i>1)begin
 if(!OBS)begin
 if({m_re,m_we,m_ra,m_wl,m_wm}!==d2 || rtg!==1'b1)$fatal(1,"BCTL_MISMATCH cycle=%0d",i);
 end else begin
 if(cv!==d2[32] || cl!==d2[23:16] || cm!==(d2[32]?d2[15:0]:16'd0))$fatal(1,"OBSERVER_MISMATCH cycle=%0d",i);
 end
 end
 @(negedge clk);
 end
 rst_n=0;#1;if(OBS && (cv!==0||cl!==0||cm!==0))$fatal(1,"OBSERVER_RESET");
 $display("PASS qvm_native_controls OBS=%0d checks=2046",OBS);$finish;
 end
endmodule
