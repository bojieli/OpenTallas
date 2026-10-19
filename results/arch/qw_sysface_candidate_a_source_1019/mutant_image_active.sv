`timescale 1ns/1ps
module qfd_host_native_context_rx_candidate_a(
 input wire ck,rst_n,receive_slot,rx_v,input wire[547:0]rx_record,
 input wire program_begin_v,program_ready,installed_fusedcap,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,input wire native_active,
 output reg accepted_v,output reg host_epoch_valid,output wire[15:0]host_epoch,
 output reg[58:0]host_tag,output reg[1:0]host_gen,
 output reg host_fusedcap,output reg[15:0]host_image_epoch,output reg[63:0]host_image_digest,
 output reg fault
);
 wire[58:0]tag=rx_record[58:0];
 // PRIVATE source candidate: raw four-state predicates; no new state or edge.
 wire [15:0] bad_predicate;
 assign bad_predicate[0]=!(rx_record[547:543]==0);
 assign bad_predicate[1]=!(rx_record[542:539]==12);
 assign bad_predicate[2]=!(rx_record[538:533]==63);
 assign bad_predicate[3]=!(rx_record[516:512]==0);
 assign bad_predicate[4]=!(rx_record[511:142]==0);
 assign bad_predicate[5]=!(tag[42:37]==0);
 assign bad_predicate[6]=!(tag[5:0]==0);
 assign bad_predicate[7]=!(tag[36:19]<151936);
 assign bad_predicate[8]=!(rx_record[532:517]==tag[58:43]);
 assign bad_predicate[9]=!(program_ready);
 assign bad_predicate[10]=!(rx_record[77:62]==program_epoch);
 assign bad_predicate[11]=!(rx_record[141:78]==program_digest);
 assign bad_predicate[12]=!(rx_record[61]==installed_fusedcap);
 assign bad_predicate[13]=!(rx_v);
 assign bad_predicate[14]=!(!native_active);
 assign bad_predicate[15]=!(!program_begin_v);
 wire [7:0] bad_l1; wire [3:0] bad_l2; wire [1:0] bad_l3;
 assign bad_l1[0]=bad_predicate[0]|bad_predicate[1];
 assign bad_l1[1]=bad_predicate[2]|bad_predicate[3];
 assign bad_l1[2]=bad_predicate[4]|bad_predicate[5];
 assign bad_l1[3]=bad_predicate[6]|bad_predicate[7];
 assign bad_l1[4]=bad_predicate[8]|bad_predicate[9];
 assign bad_l1[5]=bad_predicate[10]|bad_predicate[11];
 assign bad_l1[6]=bad_predicate[12]|bad_predicate[13];
 assign bad_l1[7]=bad_predicate[14]|bad_predicate[15];
 assign bad_l2[0]=bad_l1[0]|bad_l1[1];
 assign bad_l2[1]=bad_l1[2]|bad_l1[3];
 assign bad_l2[2]=bad_l1[4]|bad_l1[5];
 assign bad_l2[3]=bad_l1[6]|bad_l1[7];
 assign bad_l3[0]=bad_l2[0]|bad_l2[1];
 assign bad_l3[1]=bad_l2[2]|bad_l2[3];
 wire bad_receive=(bad_l3[0]|bad_l3[1]) !== 1'b0;
 wire changed_image=host_epoch_valid&&(!program_ready||program_epoch!=host_image_epoch||program_digest!=host_image_digest||installed_fusedcap!=host_fusedcap);
 wire bad_head=head_context_v&&head_stage>=1&&head_stage<=36&&(!host_epoch_valid||!host_fusedcap||head_token!=host_tag[36:19]||head_position>=8192||head_position[12:0]!=host_tag[18:6]);
 wire [5:0] fault_cause={bad_head,1'b0,receive_slot&&bad_receive,(rx_v!==receive_slot),program_begin_v&&native_active,fault};
 wire [2:0] fault_l1={fault_cause[5]|fault_cause[4],fault_cause[3]|fault_cause[2],fault_cause[1]|fault_cause[0]};
 wire next_fault=(fault_l1[0]|fault_l1[1])|fault_l1[2];
 assign host_epoch=host_tag[58:43];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin accepted_v<=0;host_epoch_valid<=0;host_tag<=0;host_gen<=0;host_fusedcap<=0;host_image_epoch<=0;host_image_digest<=0;fault<=0;end
  else begin
   accepted_v<=0;
   if(program_begin_v)begin host_epoch_valid<=0;end
   if(rx_v!==receive_slot)begin host_epoch_valid<=0;end
   if(receive_slot)begin
    if(bad_receive||fault)begin host_epoch_valid<=0;end
    else begin accepted_v<=1;host_epoch_valid<=1;host_tag<=tag;host_gen<=rx_record[60:59];host_fusedcap<=rx_record[61];host_image_epoch<=rx_record[77:62];host_image_digest<=rx_record[141:78];end
   end
   if(host_epoch_valid&&(!program_ready||program_epoch!=host_image_epoch||program_digest!=host_image_digest||installed_fusedcap!=host_fusedcap))begin host_epoch_valid<=0;end
   if(next_fault)fault<=1;
  end
 end
endmodule
