`timescale 1ns/1ps
`default_nettype none
// Fixed-cycle SFU VM prefetch/drain bridge. Requests and selectors come from
// an actual compiler programme. No request FIFO, credits, leases or retries.
// Mid-tap READ_RETURN14 is measured at response pins after edge n+14 for a
// request captured n; SRAM/scalar store consumes the response at n+15.
// The metadata delay crosses exactly those14 response edges alongside data.
module ot_hgi_sfu_vm_static_bridge #(
 parameter integer LWB=15, READ_RETURN=14, WRITE_RETURN=11
)(
 input wire clk,rst_n,
 input wire [7:0] prefetch_v,
 input wire [127:0] prefetch_sector,
 input wire [15:0] prefetch_group,
 input wire [8*LWB-1:0] prefetch_local_addr,
 input wire [7:0] prefetch_scalar,
 input wire [23:0] prefetch_word,
 input wire [95:0] scalar_addr,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [7:0] stage_v,
 output wire [15:0] stage_group,
 output wire [8*LWB-1:0] stage_addr,
 output wire [2047:0] stage_data,
 output wire [63:0] stage_mask,
 output reg [3:0] scalar_load,
 output wire [95:0] scalar_load_addr,
 output reg [127:0] scalar_data,
 input wire [1:0] drain_v,drain_round_bf16,
 input wire [31:0] drain_vm_sector,
 input wire [1:0] drain_result_v,
 input wire [511:0] drain_data,
 output reg [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output reg fault
);
 localparam META=8+16+8*LWB+8+24+96;
 reg [META-1:0] meta[0:READ_RETURN];
 wire [7:0] expect_v,scalar;
 wire [23:0] word_sel;
 assign {expect_v,stage_group,stage_addr,scalar,word_sel,scalar_load_addr}=meta[READ_RETURN];
 assign stage_v=expect_v&~scalar;
 assign stage_mask=64'hffffffffffffffff;
 for(genvar b=0;b<8;b=b+1)begin:g_read
  assign local_rq[b*17+:17]={prefetch_v[b],prefetch_sector[b*16+:16]};
  assign stage_data[b*256+:256]=local_rr[b*257+:256];
 end
 reg scalar_collision;
 reg [3:0] used_group;
 always @*begin
  scalar_load=0;scalar_data=0;used_group=0;scalar_collision=0;
  for(integer b=0;b<8;b=b+1)if(expect_v[b]&&scalar[b])begin
   if(used_group[stage_group[2*b+:2]])scalar_collision=1;
   used_group[stage_group[2*b+:2]]=1;
   scalar_load[stage_group[2*b+:2]]=1;
   scalar_data[32*stage_group[2*b+:2]+:32]=local_rr[257*b+32*word_sel[3*b+:3]+:32];
  end
 end
 function automatic [255:0] round_sector(input [255:0] data,input do_round);
  reg [31:0] word,rounded;
  for(integer w=0;w<8;w=w+1)begin
   word=data[32*w+:32];
`ifdef OT_SFU_VM_BF16_MUTANT
   rounded=word+32'h00007fff; // true negative: ties with odd high word round the wrong way
`else
   rounded=word+32'h00007fff+{31'd0,word[16]};
`endif
   round_sector[32*w+:32]=do_round?{rounded[31:16],16'd0}:word;
  end
 endfunction
 reg [1:0] drain_round_q;
 reg [31:0] drain_sector_q;
 reg [1:0] drain_expected;
 reg [7:0] write_expected[0:WRITE_RETURN+1];
 reg [7:0] write_v;
 reg write_collision;
 always @*begin
  write_v=0;write_collision=0;
  for(integer s=0;s<2;s=s+1)if(drain_expected[s])begin
   if(write_v[drain_sector_q[16*s+:3]])write_collision=1;
   write_v[drain_sector_q[16*s+:3]]=1;
  end
 end
 always @(posedge clk)begin
  drain_sector_q<=drain_vm_sector;drain_round_q<=drain_round_bf16;
  local_wq<=0;
  for(integer s=0;s<2;s=s+1)if(drain_expected[s])
   local_wq[281*drain_sector_q[16*s+:3]+:281]<=
    {1'b1,drain_sector_q[16*s+:16],round_sector(drain_data[256*s+:256],drain_round_q[s]),8'hff};
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;drain_expected<=0;
   for(integer i=0;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=0;
   for(integer i=0;i<=READ_RETURN;i=i+1)meta[i]<=0;
  end else begin
   meta[0]<={prefetch_v,prefetch_group,prefetch_local_addr,prefetch_scalar,prefetch_word,scalar_addr};
   for(integer i=1;i<=READ_RETURN;i=i+1)meta[i]<=meta[i-1];
   drain_expected<=drain_v;
   // local_wq emitted after this edge is captured by the tap next edge;
   // committed done arrives WRITE_RETURN after that tap capture.
   write_expected[0]<=write_v;
   for(integer i=1;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=write_expected[i-1];
   for(integer b=0;b<8;b=b+1)begin
    if(prefetch_v[b]&&prefetch_sector[16*b+:3]!=b)fault<=1;
    if(expect_v[b]!=local_rr[b*257+256])fault<=1;
    if(write_expected[WRITE_RETURN+1][b]!=local_w_done[b])fault<=1;
   end
   if(drain_result_v!=drain_expected || scalar_collision || write_collision)fault<=1;
  end
 end
endmodule
`default_nettype wire
