`timescale 1ns/1ps
// Source-command caller -> ACTUAL installed STATE tap/cohort3 producers.
// No source mapping, HBM storage, software done or elapsed service authority.
// Map comes from Nash's held sector owner, never a static address reservation.
// Byte RPC metadata/payload are original source offers; W2/tap supply captures.
// State write payload port32B covers canonical r17 writes8/1/16; >32 refused.
module ot_gpu_qwen_kv_state_rpc_join #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable, local_reset, source_bound,
 input wire [33:0] state_base_rank0, state_base_rank1,
 input wire rpc_valid, output wire rpc_ready,
 input wire [63:0] rpc_identity, input wire rpc_rank, rpc_write,
 input wire [33:0] rpc_address, input wire [15:0] rpc_bytes,
 input wire [255:0] rpc_payload,
 output wire rpc_reply_valid, input wire rpc_reply_ready,
 output wire [63:0] rpc_reply_identity, output wire rpc_reply_rank,
 output wire [33:0] rpc_reply_address, output wire [15:0] rpc_reply_bytes,
 output wire root_accept, input wire root_admit,
 output wire [63:0] root_identity,
 output wire root_retire, input wire root_retire_ready,
 output wire [63:0] root_retire_identity,
 output wire sector_offer_valid, output wire sector_offer_rank, sector_offer_write,
 output wire [63:0] sector_offer_identity, output wire [33:0] sector_offer_source_addr,
 input wire map_valid, output wire map_ready,
 input wire map_rank, map_sector_granted,
 input wire [33:0] map_source_addr, map_physical_addr, input wire [45:0] map_owner,
 output wire tap_command_valid, input wire tap_command_ready,
 output wire tap_command_rank, tap_command_write, tap_command_sector_granted,
 output wire [63:0] tap_command_identity,
 output wire [33:0] tap_command_source_addr, tap_command_physical_addr,
 output wire [45:0] tap_command_owner,
 output reg [255:0] tap_command_new_data, output reg [31:0] tap_command_byte_mask,
 input wire tap_reply_valid, output wire tap_reply_ready,
 input wire [63:0] tap_reply_identity, input wire tap_reply_rank,
 input wire [45:0] tap_reply_owner, input wire [33:0] tap_reply_physical_addr,
 input wire [255:0] tap_reply_old_data,
 output wire sector_capture_valid, input wire sector_capture_ready,
 output wire [33:0] sector_capture_source_addr, output wire [255:0] sector_capture_old_data,
 output wire quiescent, output reg fault
);
 localparam IDLE=0,OFFER=1,CHILD=2,FINISH=3;
 reg [1:0] state; reg [63:0] identity; reg rank, write_command;
 reg [33:0] start_addr, current;reg [15:0] count;reg [34:0] ending;
 reg [255:0] payload;reg [45:0] child_owner;reg [33:0] child_address;
 wire active=ENABLE && por_n && run_enable && !local_reset && source_bound && !fault;
 wire [33:0] base=rpc_rank ? state_base_rank1 : state_base_rank0;
 wire bad_command=rpc_bytes==0 || (rpc_write && rpc_bytes>32) || base[4:0]!=0 ||
       rpc_address<base || {1'b0,rpc_address}+rpc_bytes>{1'b0,base}+35'd37504 ||
       {1'b0,base}+35'd37504>35'h400000000;
 assign rpc_ready=active && state==IDLE && root_admit;
 assign root_accept=rpc_valid && rpc_ready;
 assign root_identity=state==IDLE ? rpc_identity : identity;
 assign root_retire_identity=identity;
 assign root_retire=active && state==FINISH && rpc_reply_ready;
 assign rpc_reply_valid=active && state==FINISH && root_retire_ready;
 assign rpc_reply_identity=identity;assign rpc_reply_rank=rank;
 assign rpc_reply_address=start_addr;assign rpc_reply_bytes=count;
 assign quiescent=state==IDLE && !fault;
 assign sector_offer_valid=active && state==OFFER;
 assign sector_offer_identity=identity;assign sector_offer_rank=rank;
 assign sector_offer_source_addr=current;assign sector_offer_write=write_command;
 wire map_match=map_rank==rank && map_source_addr==current && map_physical_addr[4:0]==0 && map_owner[38:36]<6;
 assign tap_command_valid=sector_offer_valid && map_valid && map_match && map_sector_granted;
 assign map_ready=tap_command_valid && tap_command_ready;
 assign tap_command_rank=rank;assign tap_command_write=write_command;
 assign tap_command_sector_granted=map_sector_granted;
 assign tap_command_identity=identity;assign tap_command_source_addr=current;
 assign tap_command_physical_addr=map_physical_addr;assign tap_command_owner=map_owner;
 integer i, index;
 always @* begin
  tap_command_new_data=0;tap_command_byte_mask=0;index=0;
  for(i=0;i<32;i=i+1) begin
   if(write_command && {1'b0,current}+i>={1'b0,start_addr} && {1'b0,current}+i<ending) begin
    index=current+i-start_addr;
    if(index<32) begin tap_command_byte_mask[i]=1;tap_command_new_data[i*8+:8]=payload[index*8+:8];end
   end
  end
 end
 wire reply_match=tap_reply_identity==identity && tap_reply_rank==rank &&
       tap_reply_owner==child_owner && tap_reply_physical_addr==child_address;
 assign sector_capture_valid=active && state==CHILD && tap_reply_valid && reply_match;
 assign sector_capture_source_addr=current;assign sector_capture_old_data=tap_reply_old_data;
 assign tap_reply_ready=sector_capture_valid && sector_capture_ready;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin state<=IDLE;identity<=0;rank<=0;write_command<=0;start_addr<=0;
   count<=0;ending<=0;current<=0;payload<=0;child_owner<=0;child_address<=0;fault<=0;end
  else begin
   if(ENABLE && !source_bound && state!=IDLE) fault<=1;
   if(active) begin
    if(root_accept) begin
     state<=OFFER;identity<=rpc_identity;rank<=rpc_rank;write_command<=rpc_write;
     start_addr<=rpc_address;count<=rpc_bytes;ending<={1'b0,rpc_address}+rpc_bytes;
     current<={rpc_address[33:5],5'b0};payload<=rpc_payload;
     if(bad_command) fault<=1;
    end
    if(state==OFFER && map_valid && !map_match) fault<=1;
    if(map_ready) begin state<=CHILD;child_owner<=map_owner;child_address<=map_physical_addr;end
    if(tap_reply_valid && (state!=CHILD || !reply_match)) fault<=1;
    else if(tap_reply_ready) begin
     if({1'b0,current}+35'd32>=ending) state<=FINISH;
     else begin current<=current+34'd32;state<=OFFER;end
    end
    if(rpc_reply_valid && rpc_reply_ready) state<=IDLE;
   end
  end
 end
endmodule
