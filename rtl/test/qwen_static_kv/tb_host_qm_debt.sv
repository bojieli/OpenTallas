`timescale 1ns/1ps
module tb_host_qm_debt;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,hv=0,tcr=0,ocr=0;reg[1:0]hc=0;reg[511:0]hd=0;
 wire[4:0]hcr;wire tv,ov,owe,fault,qh,qi,qc;wire[63:0]td;wire[31:0]oa;wire[255:0]od;
 qkd_host_native_qm_debt #(.QUIET_MUT(MUT),.QKV_EN(0),.ENG_TRIM(1))dut(.rst_n(rst_n),.clk_h(ck),.h_v(hv),.h_cls(hc),.h_d(hd),.h_crn(hcr),.t_v(tv),.t_d(td),.t_cr(tcr),.clk_i(ck),.clk_i_bank({ck,ck}),.clk_i_out(ck),.ck(ck),.o_v(ov),.o_we(owe),.o_addr(oa),.o_d(od),.o_cr(ocr),.i_rv(1'b0),.i_rd(256'd0),.fault(fault),.quiet_h(qh),.quiet_i(qi),.quiet_c(qc));
 integer words=0;reg waiting_payload=0;
 always @(posedge ck)if(rst_n)begin
  if(waiting_payload&&qi)$fatal(1,"PARTIAL_DESCRIPTOR_FALSE_QUIET");
  if(ov)begin
   if(!owe||oa!=32'(128+words)||od!=256'(words==0?123:456))$fatal(1,"RAW_EXACT");
   words=words+1;
  end
 end
 always @(negedge ck)begin ocr=ov;tcr=tv;end
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 initial begin
  tick(3);rst_n=1;tick(20);if(!qh||!qi||!qc)$fatal(1,"INITIAL_QUIET");
  hc=1;hd=0;hd[47:16]=128;hd[167:144]=2;hd[255:240]=1;hv=1;tick(1);hv=0;tick(25);
  waiting_payload=1;tick(20);waiting_payload=0;
  hc=2;hd={256'd456,256'd123};hv=1;tick(1);hv=0;tick(100);
  if(words!=2||fault||!qh||!qi||!qc)$fatal(1,"FINAL_DEBT w%0d f%0d q%0d%0d%0d",words,fault,qh,qi,qc);
  $display("PASS actual_QM partial_RAW_descriptor held nonquiet until two exact sectors emitted");$finish;
 end
 initial begin #50000;$fatal(1,"TIMEOUT");end
endmodule
