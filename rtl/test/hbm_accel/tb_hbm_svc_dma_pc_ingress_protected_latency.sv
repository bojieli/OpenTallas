`timescale 1ns/1ps
module tb_hbm_svc_dma_pc_ingress_protected_latency;
 reg clk=0;always #5 clk=~clk;reg rst=1;
 reg reserve_take=0;wire reserve_ready;reg[1:0]reserve_bank=0;reg[3:0]reserve_len=1;
 reg in_v=0;reg[1:0]in_bank=0;reg[5:0]in_slot=37;reg[7:0]in_idx=19;reg[255:0]in_data=0;reg in_fault=0,in_epoch=1;
 reg[3:0]write_ready=15;wire out_v;wire[1:0]out_bank;wire[5:0]out_slot;wire[7:0]out_idx;wire[255:0]out_data;wire out_fault,out_epoch,control_fault;
 integer edge_count=0,native_edge=-1,write_edge=-1;
 ot_hbm_svc_dma_pc_ingress_protected #(.ENABLE(1))dut(.*);
 always @(posedge clk)begin
 edge_count=edge_count+1;
 if(!rst&&in_v)native_edge=edge_count;
 if(!rst&&out_v)begin
 if(out_slot!==in_slot||out_idx!==in_idx||out_data!==in_data||out_fault||!out_epoch||out_bank!=0||control_fault)$fatal(1,"latency vehicle identity slot=%d idx=%d data=%h fault=%b epoch=%b bank=%d cf=%b expecteddata=%h",out_slot,out_idx,out_data,out_fault,out_epoch,out_bank,control_fault,in_data);
 write_edge=edge_count;
 end
 end
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
 repeat(3)tick();@(negedge clk);rst=0;reserve_take=1;#1;if(!reserve_ready)$fatal(1,"reserve");tick();
 @(negedge clk);reserve_take=0;in_data=0;in_v=1;tick();@(negedge clk);in_v=0;
 while(write_edge<0)begin tick();if(edge_count>20)$fatal(1,"latency flow stalled");end
 if(write_edge-native_edge!=5)$fatal(1,"model latency mismatch measured=%0d priced=5",write_edge-native_edge);
 $display("PASS LATENCY native_edge=%0d write_edge=%0d native_to_write_cycles=%0d real_encoder_cycles=1 real_decoder_cycles=2 finite_publication_slots=4",native_edge,write_edge,write_edge-native_edge);$finish;
 end
endmodule
