`timescale 1ns/1ps
// Observe real accepted state-sector writes and their protected ACK+reverse.
// Data/old-data come from actual sector capture/RMW, never a requested RPC flag.
// Source r17: bitmap36864B, 36x16B records, tagcounter at37440, total37504B.
// Physical owner46/address must be the actual mapper's accepted W2 tuple.
module ot_gpu_qwen_kv_state_observer #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable, source_bound,
 input wire [33:0] state_base_rank0, state_base_rank1,
 input wire observe_valid, output wire observe_ready,
 input wire observe_rank, input wire [33:0] observe_source_addr, observe_physical_addr,
 input wire [45:0] observe_owner, input wire [255:0] observe_old_data, observe_new_data,
 input wire observe_old_captured,
 input wire writer_retained, input wire [63:0] writer_identity,
 input wire [19:0] writer_key, input wire [10:0] writer_PC,
 input wire ACK_valid, output wire ACK_ready,
 input wire [45:0] ACK_owner, input wire [33:0] ACK_physical_addr,
 input wire ACK_visible, ACK_reverse,
 output wire event_valid, input wire event_ready,
 output reg [2:0] event_kind, //0 bitmap,1 producer,2 acquire,3 SCORES record,4 PV record
 output reg [63:0] event_identity, event_producer,
 output reg [19:0] event_key, output reg [10:0] event_PC,
 output reg fault, output wire drained
);
 reg pending, visible, reversed;
 reg [45:0] owner; reg [33:0] physical_addr;
 wire active=ENABLE && por_n && run_enable && !fault;
 wire [33:0] base=observe_rank ? state_base_rank1 : state_base_rank0;
 wire [34:0] offset={1'b0,observe_source_addr}-{1'b0,base};
 assign observe_ready=active && source_bound && !pending;
 assign ACK_ready=active && pending;
 assign event_valid=active && pending && visible && reversed && event_kind!=7;
 assign drained=!pending;
 reg bad; reg [2:0] decoded_kind;
 reg [63:0] decoded_identity, decoded_producer;
 reg [19:0] decoded_key; reg [10:0] decoded_PC;
 reg [127:0] old_record, new_record;
 reg [255:0] changed;
 integer b, changed_bits, changed_bit, half, changed_halves, layer, position;
 always @* begin
  bad=0; decoded_kind=7; decoded_identity=0; decoded_producer=0; decoded_key=0; decoded_PC=0;
  old_record=0; new_record=0; changed=observe_old_data^observe_new_data;
  changed_bits=0; changed_bit=0; changed_halves=0; layer=0; position=0;
  if(observe_source_addr<base || base[4:0]!=0 || {1'b0,base}+35'd37504>35'h400000000 ||
     observe_source_addr[4:0]!=0 || observe_physical_addr[4:0]!=0 || offset+32>37504) bad=1;
  else if(offset<36864) begin
   // A source publication writes exactly one previously-clear bitmap bit.
   for(b=0;b<256;b=b+1) if(changed[b]) begin changed_bits=changed_bits+1; changed_bit=b; end
   position=(offset*8+changed_bit)&8191; layer=(offset*8+changed_bit)>>13;
   decoded_key={layer[5:0],observe_rank,position[12:0]};
   if(!observe_old_captured || changed_bits!=1 || !observe_new_data[changed_bit]
      || !writer_retained || writer_key!=decoded_key || layer>=36) bad=1;
   decoded_kind=0; decoded_identity=writer_identity; decoded_PC=writer_PC;
  end else if(offset<37440) begin
   for(half=0;half<2;half=half+1) if(observe_old_data[half*128+:128]!=observe_new_data[half*128+:128]) begin
     changed_halves=changed_halves+1;
     old_record=observe_old_data[half*128+:128]; new_record=observe_new_data[half*128+:128];
     layer=(offset-36864)/16+half;
   end
   decoded_key={layer[5:0],observe_rank,new_record[12:0]};
   decoded_identity=new_record[76:13]; decoded_PC=new_record[87:77];
   if(!observe_old_captured || changed_halves!=1 || layer>=36 || new_record[127:92]!=0 || decoded_PC>=1737) bad=1;
   else if(new_record[91:90]==1 && new_record[89:88]==0) begin
     decoded_kind=1;
     if(!writer_retained || writer_key!=decoded_key || writer_identity!=decoded_identity || writer_PC!=decoded_PC) bad=1;
   end else if(new_record[91:90]==2 && new_record[89:88]==0) begin
     decoded_kind=2; decoded_producer=old_record[76:13];
     if(old_record[91:90]!=1 || old_record[89:88]!=0 || old_record[12:0]!=new_record[12:0]
        || old_record[87:77]!=new_record[87:77]) bad=1;
   end else if(new_record[91:90]==2 && new_record[89:88]==1) begin
     decoded_kind=3;
     if(old_record[91:90]!=2 || old_record[89:88]!=0 || old_record[87:0]!=new_record[87:0]) bad=1;
   end else if(new_record[91:90]==3 && new_record[89:88]==3) begin
     decoded_kind=4;
     if(old_record[91:90]!=2 || old_record[89:88]!=1 || old_record[87:0]!=new_record[87:0]) bad=1;
   end else bad=1;
  end
  //37440..37503 is tag-counter/padding, not a publication/consumer event.
 end
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin pending<=0; visible<=0; reversed<=0; fault<=0;
   owner<=0; physical_addr<=0; event_kind<=7; event_identity<=0;
   event_producer<=0; event_key<=0; event_PC<=0; end
  else if(active) begin
   if(observe_valid && observe_ready) begin
    pending<=1; visible<=0; reversed<=0; owner<=observe_owner; physical_addr<=observe_physical_addr;
    event_kind<=decoded_kind; event_identity<=decoded_identity;
    event_producer<=decoded_producer; event_key<=decoded_key; event_PC<=decoded_PC;
    if(bad) fault<=1;
   end
   if(ACK_valid) begin
    if(!pending || ACK_owner!=owner || ACK_physical_addr!=physical_addr
       || (!ACK_visible && !ACK_reverse) || (ACK_visible && visible) || (ACK_reverse && reversed)
       || (ACK_reverse && !ACK_visible && !visible)) fault<=1;
    else begin if(ACK_visible) visible<=1; if(ACK_reverse) reversed<=1; end
   end
   if(pending && visible && reversed && (event_kind==7 || (event_valid && event_ready))) pending<=0;
  end
 end
endmodule
