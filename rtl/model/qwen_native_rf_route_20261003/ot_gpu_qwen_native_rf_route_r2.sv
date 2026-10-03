`timescale 1ps/1ps
// Existing collector/counter observations select physical RF banks. This router
// creates no grant, numerical result, visibility, terminal or reverse event.
module ot_gpu_qwen_native_rf_route_r2 #(parameter bit ENABLE=0)(
 input wire clk,input wire [63:0] por_n,warm_reset,
 input wire [63:0] bank_port_owned,
 input wire [63:0] actor_busy,actor_fault,authority_valid,
 input wire [15295:0] authority_tuple,input wire [3519:0] authority_owner,
 input wire [63:0] read_route_valid,write_route_valid,
 input wire [383:0] read_bank,write_bank,
 input wire [575:0] read_slot,write_slot,
 input wire [2943:0] read_owner,write_owner,
 input wire [63:0] actor_rd_valid,actor_wr_valid,
 input wire [575:0] actor_a,actor_b,actor_dst,
 input wire [262143:0] actor_wdata,input wire [2943:0] actor_wowner,
 input wire [63:0] actor_rsp_ready,actor_ack_ready,
 output reg [63:0] actor_rd_ready,actor_wr_ready,actor_rsp_valid,actor_ack_valid,
 output reg [262143:0] actor_rsp_a,actor_rsp_b,
 output reg [575:0] actor_ack_slot,output reg [2943:0] actor_ack_owner,
 output reg [63:0] actor_routes_drained,
 output wire [63:0] bank_routes_drained,route_fault,
 output wire [63:0] bank_pending_read,bank_pending_write,
 output wire [575:0] bank_saved_read_slot,output wire [2943:0] bank_saved_read_owner,
 output reg [63:0] bank_rd_valid,bank_wr_valid,bank_rsp_ready,bank_ack_ready,
 output reg [575:0] bank_a,bank_b,bank_dst,
 output reg [262143:0] bank_wdata,output reg [2943:0] bank_wowner,
 output reg [15295:0] bank_root_tuple,output reg [3519:0] bank_root_owner,
 input wire [63:0] bank_rd_ready,bank_wr_ready,bank_rsp_valid,bank_ack_valid,
 input wire [262143:0] bank_rsp_a,bank_rsp_b,
 input wire [575:0] bank_ack_slot,input wire [2943:0] bank_ack_owner
);
 localparam LIVE=0,FAULT=1,QUARANTINE=2,WRITE=3,ACTOR=4,SLOT=10,OWNER=19,CURSOR=65;
 wire [70:0] state[0:63];reg [70:0] next_state[0:63];
 wire [63:0] clean,bad,repairing;
 genvar g;generate for(g=0;g<64;g=g+1)begin:bank_state
  ot_gpu_qwen_banked_manifest_source_record #(.BITS(71),.INDEX(g),.BASE(800),.KIND(5)) u_record(
   .clk(clk),.por_n(por_n[g]),.write_enable(ENABLE&&clean[g]&&!bad[g]),
   .next_data(next_state[g]),.data(state[g]),.clean(clean[g]),.bad(bad[g]),.repairing(repairing[g]));
  assign bank_pending_read[g]=clean[g]&&!bad[g]&&state[g][LIVE]&&!state[g][WRITE];
  assign bank_pending_write[g]=clean[g]&&!bad[g]&&state[g][LIVE]&&state[g][WRITE];
  assign bank_saved_read_slot[g*9+:9]=state[g][SLOT+:9];
  assign bank_saved_read_owner[g*46+:46]=state[g][OWNER+:46];
  assign route_fault[g]=ENABLE&&(bad[g]||state[g][FAULT]||state[g][QUARANTINE]);
  assign bank_routes_drained[g]=clean[g]&&!bad[g]&&!state[g][LIVE];
 end endgenerate
 integer b,a,j,choice;reg running,scope,wr,found;
 reg [70:0] s;reg [5:0] cursor;
 always @*begin
  actor_rd_ready=0;actor_wr_ready=0;actor_rsp_valid=0;actor_ack_valid=0;
  actor_rsp_a=0;actor_rsp_b=0;actor_ack_slot=0;actor_ack_owner=0;actor_routes_drained='1;
  bank_rd_valid=0;bank_wr_valid=0;bank_rsp_ready=0;bank_ack_ready=0;
  bank_a=0;bank_b=0;bank_dst=0;bank_wdata=0;bank_wowner=0;bank_root_tuple=0;bank_root_owner=0;
  s=0;cursor=0;running=0;scope=0;wr=0;found=0;choice=0;a=0;
  for(b=0;b<64;b=b+1)begin
   s=state[b];next_state[b]=s;
   running=ENABLE&&por_n[b]&&!warm_reset[b]&&clean[b]&&!bad[b]&&!s[FAULT]&&!s[QUARANTINE];
   if(!clean[b]||bad[b])actor_routes_drained=0;
   if(ENABLE&&clean[b]&&!bad[b]&&warm_reset[b])next_state[b][QUARANTINE]=1;
   if(s[LIVE])begin
    a=s[ACTOR+:6];actor_routes_drained[a]=0;
    wr=s[WRITE];scope=actor_busy[a]&&!actor_fault[a]&&authority_valid[a]&&bank_port_owned[b]&&
     authority_tuple[a*239+30+:6]==a;
    if(wr)scope=scope&&write_route_valid[a]&&write_bank[a*6+:6]==b&&write_slot[a*9+:9]==s[SLOT+:9]&&write_owner[a*46+:46]==s[OWNER+:46];
    else scope=scope&&read_route_valid[a]&&read_bank[a*6+:6]==b&&read_slot[a*9+:9]==s[SLOT+:9]&&read_owner[a*46+:46]==s[OWNER+:46];
    bank_root_tuple[b*239+:239]=authority_tuple[a*239+:239];bank_root_owner[b*55+:55]=authority_owner[a*55+:55];
    if(running&&!scope)next_state[b][FAULT]=1;
    if(running&&scope)begin
     if(wr)begin
      actor_ack_slot[a*9+:9]=bank_ack_slot[b*9+:9];actor_ack_owner[a*46+:46]=bank_ack_owner[b*46+:46];
      if(bank_ack_valid[b]&&(bank_ack_slot[b*9+:9]!=s[SLOT+:9]||bank_ack_owner[b*46+:46]!=s[OWNER+:46]))next_state[b][FAULT]=1;
      else begin
       actor_ack_valid[a]=bank_ack_valid[b];bank_ack_ready[b]=actor_ack_ready[a];
       if(bank_ack_valid[b]&&bank_ack_ready[b])begin next_state[b][LIVE]=0;next_state[b][CURSOR+:6]=a+1;end
      end
     end else begin
      if(bank_rsp_valid[b]&&bank_rsp_a[b*4096+:4096]!=bank_rsp_b[b*4096+:4096])next_state[b][FAULT]=1;
      else begin
       actor_rsp_valid[a]=bank_rsp_valid[b];actor_rsp_a[a*4096+:4096]=bank_rsp_a[b*4096+:4096];actor_rsp_b[a*4096+:4096]=bank_rsp_b[b*4096+:4096];bank_rsp_ready[b]=actor_rsp_ready[a];
       if(bank_rsp_valid[b]&&bank_rsp_ready[b])begin next_state[b][LIVE]=0;next_state[b][CURSOR+:6]=a+1;end
      end
     end
    end
   end else if(running&&bank_port_owned[b])begin
    cursor=s[CURSOR+:6];found=0;choice=0;wr=0;
    // Counter-protected controllers never offer both request kinds together.
    for(j=0;j<64;j=j+1)begin
     a=(cursor+j)&63;
     scope=actor_busy[a]&&!actor_fault[a]&&authority_valid[a]&&authority_tuple[a*239+30+:6]==a;
     if(!found&&scope&&actor_rd_valid[a]&&!actor_wr_valid[a]&&read_route_valid[a]&&read_bank[a*6+:6]==b&&actor_a[a*9+:9]==read_slot[a*9+:9]&&actor_b[a*9+:9]==read_slot[a*9+:9])begin choice=a;found=1;wr=0;end
     if(!found&&scope&&actor_wr_valid[a]&&!actor_rd_valid[a]&&write_route_valid[a]&&write_bank[a*6+:6]==b&&actor_dst[a*9+:9]==write_slot[a*9+:9]&&actor_wowner[a*46+:46]==write_owner[a*46+:46])begin choice=a;found=1;wr=1;end
    end
    if(found)begin
     a=choice;bank_root_tuple[b*239+:239]=authority_tuple[a*239+:239];bank_root_owner[b*55+:55]=authority_owner[a*55+:55];
     if(wr)begin
      bank_wr_valid[b]=1;bank_dst[b*9+:9]=write_slot[a*9+:9];bank_wowner[b*46+:46]=write_owner[a*46+:46];bank_wdata[b*4096+:4096]=actor_wdata[a*4096+:4096];actor_wr_ready[a]=bank_wr_ready[b];
      if(bank_wr_ready[b])begin next_state[b][LIVE]=1;next_state[b][WRITE]=1;next_state[b][ACTOR+:6]=a;next_state[b][SLOT+:9]=write_slot[a*9+:9];next_state[b][OWNER+:46]=write_owner[a*46+:46];end
     end else begin
      bank_rd_valid[b]=1;bank_a[b*9+:9]=read_slot[a*9+:9];bank_b[b*9+:9]=read_slot[a*9+:9];actor_rd_ready[a]=bank_rd_ready[b];
      if(bank_rd_ready[b])begin next_state[b][LIVE]=1;next_state[b][WRITE]=0;next_state[b][ACTOR+:6]=a;next_state[b][SLOT+:9]=read_slot[a*9+:9];next_state[b][OWNER+:46]=read_owner[a*46+:46];end
     end
    end
   end
  end
 end
endmodule
