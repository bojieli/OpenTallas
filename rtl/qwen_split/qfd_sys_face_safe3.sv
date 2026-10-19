`timescale 1ns/1ps
// QW-SYSFACE3 (10-19): structural depth successor of the qfd_sys_face record port leaves, selected only by
// qfd_sys_face_record_port #(.SAFE3(1)) (default 0 keeps qfd_host_native_context_rx / qkd_program_commit, whose
// files stay byte-identical for every other user).  Zero added state edges; two-state next-state identical.
//
// qfd_sys_face_context_rx_s3 = qfd_host_native_context_rx with
//  * the bc2l TT -57.9 ps / 28-level cone (rx_payload[142] reserved-zero test -> nine-term structure_ok AND chain
//    -> five serial bad-receive ORs -> six serial fault ORs -> fault D) rebuilt as ONE balanced 16-predicate
//    bad-receive reduction plus a balanced 6-cause sticky fault reduction (Candidate A 76277b2cb lineage,
//    17 abstract levels), and
//  * every next state written as explicit dataflow (no procedural `if` on a possibly-unknown condition and no case
//    equality operators): the four a1e934503 source/native X counterexamples (receive_slot / rx_v = X or Z made the
//    source fault 1 through `!==` while the native netlist gives X) are fixed in source -- source and native now
//    propagate the unknown identically.  Binary behaviour is unchanged.
// qfd_sys_face_program_commit_s3 = qkd_program_commit with bad_write's 11-bit subtract/compare chain
//  (count-11'd1024 ripple ALU, 21 generic levels into the FSM) replaced by exact bit-field tests on count
//  (count in [0,2047]: count>=1024 <=> count[10]; count-1024 == dw_addr <=> count[10] & count[9:3]==0 & count[2:0]==dw_addr).
module qfd_sys_face_context_rx_s3(
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
 // sixteen raw invalid predicates (nine structure, four image, three receive/activity/BEGIN), one balanced OR
 wire[15:0]bad_p={
  program_begin_v,                         // BEGIN in the receive slot
  native_active,                           // receive while native execution is active
  ~rx_v,                                   // receive slot without rx_v
  rx_record[61]!=installed_fusedcap,
  rx_record[141:78]!=program_digest,
  rx_record[77:62]!=program_epoch,
  ~program_ready,
  rx_record[532:517]!=tag[58:43],
  ~(tag[36:19]<18'd151936),
  |tag[5:0],
  |tag[42:37],
  |rx_record[511:142],                     // reserved-zero field (the bc2l critical cone)
  |rx_record[516:512],
  rx_record[538:533]!=6'd63,
  rx_record[542:539]!=4'd12,
  |rx_record[547:543]};
 wire[7:0]b1={bad_p[15]|bad_p[14],bad_p[13]|bad_p[12],bad_p[11]|bad_p[10],bad_p[9]|bad_p[8],
              bad_p[7]|bad_p[6],bad_p[5]|bad_p[4],bad_p[3]|bad_p[2],bad_p[1]|bad_p[0]};
 wire[3:0]b2={b1[7]|b1[6],b1[5]|b1[4],b1[3]|b1[2],b1[1]|b1[0]};
 wire bad_receive=(b2[3]|b2[2])|(b2[1]|b2[0]);
 wire mismatch=rx_v^receive_slot;
 wire accept=receive_slot&~bad_receive&~fault;
 wire changed_image=host_epoch_valid&(~program_ready|(program_epoch!=host_image_epoch)|
                    (program_digest!=host_image_digest)|(installed_fusedcap^host_fusedcap));
 wire bad_head=head_context_v&(head_stage>=6'd1)&(head_stage<=6'd36)&
               (~host_epoch_valid|~host_fusedcap|(head_token!=host_tag[36:19])|(head_position>=18'd8192)|
                (head_position[12:0]!=host_tag[18:6]));
 // original priority: BEGIN / rx-slot mismatch / bad receive clear, an accepted receive sets, a late retained-image
 // change clears last (it reads the PRESENT image registers)
 wire hev_next=~changed_image&(accept|(host_epoch_valid&~receive_slot&~program_begin_v&~mismatch));
 wire[5:0]cause={bad_head,changed_image&native_active,receive_slot&bad_receive,mismatch,program_begin_v&native_active,fault};
 wire fault_next=((cause[5]|cause[4])|(cause[3]|cause[2]))|(cause[1]|cause[0]);
 assign host_epoch=host_tag[58:43];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin accepted_v<=0;host_epoch_valid<=0;host_tag<=0;host_gen<=0;host_fusedcap<=0;host_image_epoch<=0;host_image_digest<=0;fault<=0;end
  else begin
   accepted_v<=accept;
   host_epoch_valid<=hev_next;
   fault<=fault_next;
   host_tag<=accept?tag:host_tag;
   host_gen<=accept?rx_record[60:59]:host_gen;
   host_fusedcap<=accept?rx_record[61]:host_fusedcap;
   host_image_epoch<=accept?rx_record[77:62]:host_image_epoch;
   host_image_digest<=accept?rx_record[141:78]:host_image_digest;
  end
 end
endmodule

module qfd_sys_face_program_commit_s3(
 input wire ck,rst_n,execution_active,control_stores_ready,
 input wire begin_v,input wire[15:0]begin_epoch,
 input wire[10:0]expected_pw,input wire[3:0]expected_dw,
 input wire auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,input wire pw_full_word,
 input wire dw_v,input wire[2:0]dw_addr,input wire[63:0]dw_data,input wire dw_full_word,
 output reg commit_v,ready,fault,installed_fusedcap,output reg[15:0]commit_epoch,
 output reg[63:0]commit_digest);
 localparam IDLE=0,WAIT_AUTH=1,WRITES=2,VERIFIED=3,READY=4;
 reg[2:0]state;reg footer_cap;reg[10:0]count;reg[15:0]epoch;
 reg[63:0]digest,authorized_digest;
 wire event_desc=dw_v;
 wire[9:0]event_addr=dw_v?{7'd0,dw_addr}:pw_addr;
 wire[63:0]event_data=dw_v?dw_data:pw_data;
 wire[63:0]next_digest={digest[56:0],digest[63:57]}^event_data^{53'd0,event_desc,event_addr};
 wire pw_bad=~pw_full_word|count[10]|(pw_addr!=count[9:0]);
 wire dw_bad=~dw_full_word|~count[10]|(|count[9:3])|(count[2:0]!=dw_addr);
 wire bad_write=(pw_v&dw_v)|(pw_v&pw_bad)|(dw_v&dw_bad);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;count<=0;epoch<=0;digest<=0;authorized_digest<=0;
   commit_v<=0;ready<=0;fault<=0;installed_fusedcap<=0;footer_cap<=0;commit_epoch<=0;commit_digest<=0;end
  else begin
   commit_v<=0;
   if(!fault)begin
    if(begin_v)begin
     ready<=0;installed_fusedcap<=0;footer_cap<=0;
     if(execution_active||state==WAIT_AUTH||state==WRITES||state==VERIFIED||auth_v||pw_v||dw_v||expected_pw!=1024||expected_dw!=8)begin fault<=1;installed_fusedcap<=0;state<=IDLE;end
     else begin state<=WAIT_AUTH;epoch<=begin_epoch;count<=0;digest<=64'h51484f5354505247;end
    end else if(auth_v)begin
     if(execution_active||state!=WAIT_AUTH||auth_epoch!=epoch||pw_v||dw_v)begin fault<=1;installed_fusedcap<=0;ready<=0;state<=IDLE;end
     else begin authorized_digest<=auth_digest;state<=WRITES;end
    end else if(pw_v||dw_v)begin
     if(execution_active||state!=WRITES||bad_write)begin fault<=1;installed_fusedcap<=0;ready<=0;state<=IDLE;end
     else begin
      count<=count+1'b1;digest<=next_digest;
      if(pw_v&&pw_addr==1023)footer_cap<=pw_data[63:32]==32'h58504631&&pw_data[1:0]==2&&pw_data[31:13]==0&&pw_data[5:2]>=1&&pw_data[5:2]<=4&&pw_data[12];
      if(count==1031)begin
       if(next_digest!=authorized_digest)begin fault<=1;installed_fusedcap<=0;ready<=0;state<=IDLE;end
       else begin commit_epoch<=epoch;commit_digest<=next_digest;state<=VERIFIED;end
      end
     end
    end
   end else ready<=0;
   if(!fault&&state==VERIFIED&&!begin_v&&!auth_v&&!pw_v&&!dw_v)begin
    if(control_stores_ready)begin commit_v<=1;ready<=1;installed_fusedcap<=footer_cap;state<=READY;end
   end
   if(fault)installed_fusedcap<=0;
  end
 end
endmodule
