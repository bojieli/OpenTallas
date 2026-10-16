`timescale 1ns/1ps
// Force-only response-decoder/counter truth-table gate. Actual memory/ECC
// integration is separately exercised by tb_bank_wdecode_vs_allowners.
module tb_bank_ce_population;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;
ot_vms_bank_static_wdecode_vs #(.RG(7),.WG(3),.MUT(MUT)) dut(
.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),.rslot_v(1'b0),.rslot(3'd0),.wslot_v(1'b0),.wslot(3'd0),.rq(119'd0),.rr(),.wq(843'd0),.wq_done(),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status());
localparam [127:0] CE_OK=128'h00000016001616690116166916696996;
reg [55:0] syndromes=0;reg [15:0] seed=0;
integer expected,codewords,cases=0;
task check_count(input integer n,input bit uncorrectable);
begin
 // ft bank: the population is registered (ce_n_q) one edge before the saturating add
 @(negedge clk);
 force dut.d_syn=syndromes;
 force dut.d_v=1'b1;
 #1;
 if(dut.nce!==4'(n)||dut.nue!==uncorrectable)$fatal(1,"CE population decoder mismatch expected=%0d actual=%0d",n,dut.nce);
 @(posedge clk);#1;
 if(dut.ce_n_q!==4'(n)||dut.ce_v_q!==1'b1)$fatal(1,"CE population register mismatch");
 @(negedge clk);
 force dut.ce=seed;
 #1;
 release dut.ce;
 expected=int'(seed)+n;if(expected>65535)expected=65535;
 @(posedge clk);#1;
 if(dut.ce!==16'(expected))$fatal(1,"CE population saturation mismatch");
 cases=cases+1;
end
endtask
initial begin
 repeat(3)@(negedge clk);rst_n=1;repeat(3) @(negedge clk); /* bank reset relay release: initialization mode */
 for(integer mask=0;mask<256;mask=mask+1)begin
  syndromes=0;codewords=0;
  for(integer w=0;w<8;w=w+1)if((mask>>w)&1)begin syndromes[w*7+:7]=w<4?7'd1:7'd7;codewords=codewords+1;end
  for(integer state=0;state<4;state=state+1)begin
   case(state)0:seed=0;1:seed=15;2:seed=65527;3:seed=65535;endcase
   check_count(codewords,0);
  end
 end
 for(integer word_index=0;word_index<8;word_index=word_index+1)begin
  for(integer syndrome=0;syndrome<128;syndrome=syndrome+1)begin
   syndromes=0;syndromes[word_index*7+:7]=7'(syndrome);seed=16'h0ffe;
   check_count(CE_OK[syndrome]?1:0,syndrome!=0&&!CE_OK[syndrome]);
  end
 end
 release dut.d_v;release dut.d_syn;
 $display("CE_POPULATION PASS masks=256 seeds=4 syndrome_codes=128 positions=8 cases=%0d force_only_scope=1",cases);$finish;
end
endmodule
