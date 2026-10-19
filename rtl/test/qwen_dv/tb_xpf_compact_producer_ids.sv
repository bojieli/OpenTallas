`timescale 1ns/1ps
module tb_xpf_compact_producer_ids;
  reg ck=0;always #5 ck=~ck;
  reg rst_n=0,cfg_v=0,cfg_clear=0,cfg_seal=0;
  reg[1:0]cfg_index=0;reg[187:0]cfg_data=0;reg[187:0]records[0:3];string file;
  wire ready,fault;
  ot_qfd_xpf_static_schedule #(.N(4)) dut(.clk(ck),.rst_n(rst_n),
    .cfg_v(cfg_v),.cfg_clear(cfg_clear),.cfg_seal(cfg_seal),.cfg_index(cfg_index),
    .cfg_data(cfg_data),.cfg_count(3'd4),.start(1'b0),.stop(1'b0),.stage(6'd1),
    .me_issue(1'b0),.me_pc(12'd0),.su_issue(1'b0),.su_pc(12'd0),.cp_issue(1'b0),.cp_pc(12'd0),
    .image_ready(ready),.xpf(),.fault(fault),.active(),.cycle());
  initial begin
    if(!$value$plusargs("RECORDS=%s",file))$fatal(1,"RECORDS");
    $readmemh(file,records);
    repeat(4)@(negedge ck);rst_n=1;cfg_clear=1;@(negedge ck);cfg_clear=0;
    for(integer i=0;i<4;i=i+1)begin cfg_v=1;cfg_index=i;cfg_data=records[i];@(negedge ck);end
    cfg_v=0;cfg_seal=1;@(negedge ck);cfg_seal=0;
    repeat(3)@(negedge ck);
    if(fault||!ready)$fatal(1,"XPF_PRODUCER_ID_INSTALL_REJECT");
    $display("XPF_PRODUCER_ID_INSTALL_PASS");$finish;
  end
endmodule
