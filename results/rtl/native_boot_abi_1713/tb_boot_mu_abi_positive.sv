`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[142:0]pr=0;reg[3:0]target=1;reg ready=0;reg[63:0]words[0:326];reg[63:0]muwords[0:470];
 wire[1:0]fault;wire[7:0]code[0:1];integer i;
 genvar g;generate for(g=0;g<2;g=g+1)begin:G
 qkd_static_kv_boot_dispatch_mu_nc32 #(.MU(g),.SRQ(2),.DSTG(1)) dut(.ck(ck),.rst_n(rst_n),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),.boot_image_fault(1'b0),.boot_image_epoch(16'h0b0b),.boot_image_digest(64'h0),.execution_active(1'b0),.sink_applied({160{1'b1}}),.local_configured(3'b111),.sink_fault(1'b0),.diecfg_sealed(1'b1),.diecfg_fault(1'b0),.fault(fault[g]),.fault_code(code[g]));
 end endgenerate
 initial begin
 $readmemh("target1.hex",words);$readmemh("target1_mu.hex",muwords);repeat(5)@(negedge ck);rst_n=1;repeat(4)@(negedge ck);
 for(i=0;i<327;i=i+1)begin pr=0;pr[74]=1;pr[73:64]=10'(i);pr[63:0]=words[i];@(negedge ck);end
 pr=0;repeat(4)@(negedge ck);ready=1;repeat(5)@(negedge ck);
 $display("SU327 fault=%b code=%h installed=%h next=%0d",fault[0],code[0],G[0].dut.u_disp.installed,G[0].dut.u_disp.next_word);
 $display("NATIVE_MU327 fault=%b code=%h installed=%h next=%0d gap=%0d",fault[1],code[1],G[1].dut.u_disp.installed,G[1].dut.u_disp.next_word,G[1].dut.g_mu.gcnt);
 if(fault[0]||!G[0].dut.u_disp.installed[0])$fatal(1,"SU_IMAGE_NOT_VALID");
 if(!fault[1]||code[1]!=8'h80||G[1].dut.u_disp.installed[0])$fatal(1,"MU_MISMATCH_NOT_REPRODUCED");
 $display("ACTUAL_MU_IMAGE_ABI_CAUSE_REPRODUCED");
 rst_n=0;ready=0;pr=0;repeat(6)@(negedge ck);rst_n=1;repeat(6)@(negedge ck);
 for(i=0;i<471;i=i+1)begin pr=0;pr[74]=1;pr[73:64]=10'(i);pr[63:0]=muwords[i];@(negedge ck);end
 pr=0;repeat(4)@(negedge ck);ready=1;repeat(5)@(negedge ck);
 $display("NATIVE_MU471 fault=%b code=%h installed=%h next=%0d",fault[1],code[1],G[1].dut.u_disp.installed,G[1].dut.u_disp.next_word);
 if(fault[1]||!G[1].dut.u_disp.installed[0])$fatal(1,"REAL_COMPILER_MU_IMAGE_REJECTED");
 $display("ACTUAL_NATIVE_MU471_IMAGE_PASS");$finish;
 end
endmodule
