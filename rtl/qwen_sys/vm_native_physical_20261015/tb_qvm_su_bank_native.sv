`timescale 1ns/1ps
module tb_qvm_su_bank_native #(parameter integer MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,re=0,we=0;reg[9:0]ra=0,wl=0;reg[15:0]wm=0;reg[511:0]wd=0;
 wire[511:0]q,refq;
 qvm_su_bank_native #(.MUT(MUT))dut(.ck_ctrl(clk),.ck_in_lo(clk),.ck_in_hi(clk),.ck_mem_lo(clk),.ck_mem_hi(clk),.ck_cap_lo(clk),.ck_cap_hi(clk),.ck_out_lo(clk),.ck_out_hi(clk),.rst_n(rst_n),.re(re),.we(we),.ra(ra),.wl(wl),.wm(wm),.wd(wd),.q(q));
 ot_qfd_vm_su_t #(.NSB(1),.DEPTHS(695),.LAWS(10),.USE_MACRO(1))reference(.clk(clk),.rst_n(rst_n),.sre(re),.swe(we),.sra(ra),.swl(wl),.swm(wm),.swd(wd),.q(refq));
 integer i,j;reg[31:0]rng=32'h6ab95328;
 task cycle;
 begin @(posedge clk);#1;if(q!==refq)$fatal(1,"BANK_MISMATCH cycle=%0d",i);@(negedge clk);end
 endtask
 initial begin
 repeat(3)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 // Initialize all legal rows through actual masked macro writes.
 for(i=0;i<695;i=i+1)begin we=1;wl=10'(i);wm=16'hffff;for(j=0;j<16;j=j+1)wd[j*32+:32]=32'(i*17+j);cycle();end
 we=0;repeat(6)cycle();
 for(i=0;i<4096;i=i+1)begin
 rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
 re=1;we=rng[0];ra=10'((rng>>1)%695);wl=10'((rng>>9)%695);wm=rng[31:16];
 if(i%17==0)wl=ra; // Read/write same address: preserve macro read-before-write.
 for(j=0;j<16;j=j+1)wd[j*32+:32]=rng^32'(i*1024+j);
 cycle();
 end
 we=0;re=0;repeat(6)cycle();
 // Reset releases controls without clearing mutable SRAM payload.
 rst_n=0;repeat(3)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 for(i=0;i<695;i=i+1)begin re=1;ra=10'(i);cycle();end
 repeat(6)cycle();$display("PASS qvm_su_bank_native rows695 random4096 RBW reset-preserve full512");$finish;
 end
endmodule
