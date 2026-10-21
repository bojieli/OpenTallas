`timescale 1ns/1ps
`default_nettype none
module tb_vm_fault_l16;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg [143:0] bank_status[0:3];reg[2:0] hub_status[0:3];reg[15:0] legacy[0:3];
 wire[18:0] vmstat[0:3];wire[3:0] leaf_fault,a_fault;
 wire die_fault,block_ready,program_active,program_fault,irq;wire[3:0]cause;
 integer checked=0;integer cause_bit[0:3];integer sync_bit[0:3];
 ot_vms_status_static status_SW(.clk(clk),.rst_n(rst_n),.bank_status(bank_status[0]),.hub_status(hub_status[0]),.ring_fault(1'b0),.vmstat(vmstat[0]));
 wire[13:0] leaf_in_SW={(MUT==1?3'd0:vmstat[0][18:16]),legacy[0][10:0]};
 ot_hbm_fault_leaf #(.N(14),.SYNC_MASK(64'h120),.MUT(MUT==2?3:0)) fr_SW(.clk(clk),.rst_n(rst_n),.in(leaf_in_SW),.fault(leaf_fault[0]));
 assign a_fault[0]=leaf_fault[0];
 initial begin cause_bit[0]=0;sync_bit[0]=5;end
 ot_vms_status_static status_SE(.clk(clk),.rst_n(rst_n),.bank_status(bank_status[1]),.hub_status(hub_status[1]),.ring_fault(1'b0),.vmstat(vmstat[1]));
 wire[12:0] leaf_in_SE={(MUT==1?3'd0:vmstat[1][18:16]),legacy[1][9:0]};
 ot_hbm_fault_leaf #(.N(13),.SYNC_MASK(64'h30),.MUT(MUT==2?3:0)) fr_SE(.clk(clk),.rst_n(rst_n),.in(leaf_in_SE),.fault(leaf_fault[1]));
 assign a_fault[1]=leaf_fault[1];
 initial begin cause_bit[1]=1;sync_bit[1]=4;end
 ot_vms_status_static status_NW(.clk(clk),.rst_n(rst_n),.bank_status(bank_status[2]),.hub_status(hub_status[2]),.ring_fault(1'b0),.vmstat(vmstat[2]));
 wire[12:0] leaf_in_NW={(MUT==1?3'd0:vmstat[2][18:16]),legacy[2][9:0]};
 ot_hbm_fault_leaf #(.N(13),.SYNC_MASK(64'h50),.MUT(MUT==2?3:0)) fr_NW(.clk(clk),.rst_n(rst_n),.in(leaf_in_NW),.fault(leaf_fault[2]));
 assign a_fault[3]=leaf_fault[2];
 initial begin cause_bit[2]=3;sync_bit[2]=4;end
 ot_vms_status_static status_NE(.clk(clk),.rst_n(rst_n),.bank_status(bank_status[3]),.hub_status(hub_status[3]),.ring_fault(1'b0),.vmstat(vmstat[3]));
 wire[13:0] leaf_in_NE={(MUT==1?3'd0:vmstat[3][18:16]),legacy[3][10:0]};
 ot_hbm_fault_leaf #(.N(14),.SYNC_MASK(64'h50),.MUT(MUT==2?3:0)) fr_NE(.clk(clk),.rst_n(rst_n),.in(leaf_in_NE),.fault(leaf_fault[3]));
 assign a_fault[2]=leaf_fault[3];
 initial begin cause_bit[3]=2;sync_bit[3]=4;end
 ot_hbm_status_join_fa #(.NT(1),.NF(1),.NH(1),.TGTS(8'd0),.NA(4),.FCLR(125),.RRELAY(1)) host_status(
 .clk(clk),.rst_n(rst_n),.cfg_v(1'b0),.desc_v(1'b0),.launch_v(1'b0),.cfg_target(8'd0),
 .t_ready(1'b1),.t_active(1'b0),.t_fault(1'b0),.h_fault(1'b0),.a_fault(a_fault),
 .block_ready(block_ready),.program_active(program_active),.program_fault(program_fault),.irq(irq),.die_fault(die_fault),.a_cause(cause));
 task tick;begin @(posedge clk);#1;end endtask
 task reset_case;begin
 @(negedge clk);rst_n=0;
 for(integer q=0;q<4;q=q+1)begin bank_status[q]=0;hub_status[q]=0;legacy[q]=0;end
 repeat(5)tick();@(negedge clk);rst_n=1;repeat(32)tick();
 if(die_fault||cause!=0||!block_ready)$fatal(1,"VM_FAULT_FAIL reset/admission");
 end endtask
 // kind0 bank UE,1 bank protocol,2 hub status,3 preexisting serial source,4 CEcount only.
 task run_case(input integer q,input integer kind,input integer item);
 integer latency;reg expected_fault;reg[3:0] expected_cause;
 begin
 reset_case();latency=(kind==3)?6:8;expected_fault=(kind!=4);expected_cause=4'b1<<cause_bit[q];
 @(negedge clk);
 case(kind)
 0:bank_status[q][item*18+16]=1;
 1:bank_status[q][item*18+17]=1;
 2:hub_status[q][item]=1;
 3:legacy[q][sync_bit[q]]=1;
 4:bank_status[q][item*18]=1;
 endcase
 for(integer age=1;age<=latency+12;age=age+1)begin
  tick();
  if(expected_fault)begin
   if(age<latency && die_fault)$fatal(1,"VM_FAULT_FAIL early q=%0d kind=%0d item=%0d age=%0d",q,kind,item,age);
   if(age>=latency && (!die_fault||block_ready||cause!==expected_cause))
    $fatal(1,"VM_FAULT_FAIL missing/wrong-cause q=%0d kind=%0d item=%0d age=%0d fault=%0b cause=%h",q,kind,item,age,die_fault,cause);
  end else if(die_fault||cause!=0||!block_ready)$fatal(1,"VM_FAULT_FAIL CEcount became fatal q=%0d",q);
  if(age==1)begin @(negedge clk);bank_status[q]=0;hub_status[q]=0;legacy[q]=0;end
 end
 checked=checked+1;
 end endtask
 initial begin
 for(integer q=0;q<4;q=q+1)begin
  for(integer b=0;b<8;b=b+1)begin run_case(q,0,b);run_case(q,1,b);end
  for(integer h=0;h<3;h=h+1)run_case(q,2,h);
 end
 for(integer q=0;q<4;q=q+1)run_case(q,3,0);
 for(integer q=0;q<4;q=q+1)run_case(q,4,0);
 $display("VM_FAULT_PASS cases=%0d all32banksUE/protocol all12hubflags serialsync-preserved CEcount-nonfatal",checked);
 $finish;
 end
endmodule
`default_nettype wire
