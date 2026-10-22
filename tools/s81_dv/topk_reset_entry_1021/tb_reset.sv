`timescale 1ns/1ps
`ifndef RESET_MUT
`define RESET_MUT 0
`endif
module tb_topk_reset_entry;
 reg ck=0, raw=0;
 always #5 ck=~ck;
 wire local_reset;
 wire [275:0] vo,dl;
 wire fault;
 wire [4:0] tx_reset;
 dsdv_topk_reset_entry #(.MUT(`RESET_MUT)) u_entry(.ck(ck),.rst_n(raw),.q(local_reset));
 dsdv_idx_vmux_n32 u_vm(.ck(ck),.rst(local_reset),.i_r(276'b0),.i_s(276'b0),.i_a(276'b0),.i_b(276'b0),.o(vo),.fault(fault));
 dsdv_idx_vdly u_dl(.ck(ck),.rst(local_reset),.i(276'b0),.o(dl));
 // Exact TX source primitive and parameters; this test does not claim full TX data-path qualification.
 ot_rst_relay #(.REGIONS(5),.SYNC_STAGES(2),.TREE_STAGES(1)) u_tx_reset(.clk(ck),.rst_n_in(local_reset),.rst_n(tx_reset));
 integer age=0,errors=0,epochs=0,checks=0,async_checks=0;
 always @(negedge raw) age=0;
 always @(posedge ck) begin
  if(raw) age=age+1;else age=0;
  #1;
  checks++;
  if(local_reset !== (age>=1) || u_vm.rnk !== {3{age>=3}} || u_dl.rn !== {2{age>=3}} || tx_reset !== {5{age>=4}})begin
   errors++;
   if(errors<=8)$display("TOPK_RESET_AGE_MISMATCH epoch=%0d age=%0d entry=%b vm=%b dl=%b tx=%b expected=1,3,3,4",epochs,age,local_reset,u_vm.rnk,u_dl.rn,tx_reset);
  end
 end
 task automatic assert_reset;
  raw=0;#1;async_checks++;
  if(local_reset !== 0 || u_vm.rnk !== 0 || u_dl.rn !== 0 || tx_reset !== 0)begin
   errors++;$display("TOPK_RESET_ASYNC_MISMATCH epoch=%0d",epochs);
  end
 endtask
 initial begin
  // Start with a real falling edge, then check long, short and non-clock-aligned assertions.
  #1;raw=1;#1;assert_reset();#11;
  for(integer k=0;k<12;k++)begin
   epochs++;raw=1;
   repeat(8)@(negedge ck);
   #2;assert_reset();
   if(k%2==0)#1;else #16;
  end
  raw=1;repeat(8)@(negedge ck);#2;
  $display("TOPK_RESET_AGE epochs=%0d checks=%0d async_checks=%0d errors=%0d VMUX=3 VDLY=3 TX=4 extra_boot_edges=1",epochs,checks,async_checks,errors);
  if(errors!=0)begin $display("TOPK_RESET_ENTRY_CAUGHT");$fatal(1,"release age mismatch");end
  $display("TOPK_RESET_ENTRY_PASS");$finish;
 end
endmodule
