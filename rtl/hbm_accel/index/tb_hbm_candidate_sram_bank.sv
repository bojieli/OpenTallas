`timescale 1ps/1fs
module tb_hbm_candidate_sram_bank #(parameter integer MUT_PAYLOAD=0);
 reg clk=0;always #416.5 clk=~clk;
 reg por_n=0,req_v=0,req_write=0,rsp_r=0;reg[6:0]address=0;reg[511:0]data=0;
 wire req_r,rsp_v,rsp_write,ce,poison,fault;wire[511:0]answer;
 // Structural transport mutant modifies the actual bank input after golden
 // generation, not the checker. SRAM and its SECDED decoder are unchanged.
 ot_hbm_candidate_sram_bank #(.ENABLE(1)) dut(.clk(clk),.por_n(por_n),.req_v(req_v),.req_r(req_r),.req_write(req_write),
 .req_address(address),.req_data(data^(MUT_PAYLOAD?512'd1:512'd0)),
 .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_data(answer),.rsp_write(rsp_write),.rsp_ce(ce),.rsp_poison(poison),.fault(fault));
 function automatic[511:0]word(input integer a);
 for(integer k=0;k<8;k++)word[k*64+:64]={16'(a),16'(k),32'h75a39f01^32'(a*137+k*911)};
 endfunction
 task tick;begin @(negedge clk);end endtask
 task request(input integer a,wr);
 begin
 while(!req_r)tick;address=7'(a);req_write=wr;data=word(a);req_v=1;tick;req_v=0;
 while(!rsp_v&&!fault)tick;
 if(fault||poison||rsp_write!=wr||(!wr&&answer!==word(a)))$fatal(1,"BANK_MISMATCH address=%0d write=%0d",a,wr);
 repeat(3)begin tick;if(!rsp_v||(!wr&&answer!==word(a)))$fatal(1,"BANK_MISMATCH unstable response");end
 rsp_r=1;tick;rsp_r=0;
 end endtask
 initial begin
 repeat(3)tick;por_n=1;tick;
 for(integer a=0;a<128;a++)request(a,1);
 for(integer a=0;a<128;a++)request(a,0);
 // The boundary values and all three macro seats participate in every read.
 $display("BANK_PASS writes=128 reads=128 payload_bits=512 macros=3");$finish;
 end
endmodule
