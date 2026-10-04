// Additive HA1 scheduler-visibility counter. No RF lease or drain release.
// w4_accept/w6_accept MUST be actual accepted common ACK/visible handshakes.
// tx_index is the frozen manifest index from the canonical owner; never a timer.
module ot_hbm_txcount_sm #(parameter bit ENABLE=0)(
 input wire clk,por_n,rst_n,
 input wire begin_valid, output wire begin_ready,
 input wire [6:0] begin_rank, input wire [31:0] begin_job,
 input wire [3:0] begin_gen, input wire [5:0] begin_count,
 input wire manifest_valid, output wire manifest_ready,
 input wire [54:0] manifest_owner55,
 input wire w4_accept, input wire [4:0] w4_index,
 input wire [54:0] w4_owner55, input wire [6:0] w4_rank,
 input wire [31:0] w4_job, input wire [3:0] w4_gen,
 input wire w6_accept, input wire [4:0] w6_index,
 input wire [54:0] w6_owner55, input wire [6:0] w6_rank,
 input wire [31:0] w6_job, input wire [3:0] w6_gen,
 input wire source_fault,
 output wire complete_valid, input wire complete_ready,
 output wire [6:0] complete_rank, output wire [31:0] complete_job,
 output wire [3:0] complete_gen, output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign begin_ready=0;assign manifest_ready=0;assign complete_valid=0;
  assign complete_rank=0;assign complete_job=0;assign complete_gen=0;assign fault=0;
 end else begin:on
  reg [71:0] context_code,state_code,seen_code;
  reg [71:0] identities[0:31];
  wire [65:0] context_dec=decode64(context_code), state_dec=decode64(state_code),seen_dec=decode64(seen_code);
  wire [63:0] ctx=context_dec[63:0],st=state_dec[63:0],seen=seen_dec[63:0];
  // context: rank[6:0], job[38:7], gen[42:39], expected[48:43]
  // state: loaded[5:0], ack_count[11:6], fence_count[17:12], active[18], fault[19]
  wire [65:0] ack_id=decode64(identities[w4_index]), fence_id=decode64(identities[w6_index]);
  wire bad=context_dec[65]||state_dec[65]||seen_dec[65]||(|ctx[63:49])||(|st[63:20]);
  wire live=por_n&&rst_n&&!bad&&!st[19];
  wire sealed=st[18]&&st[5:0]==ctx[48:43];
  wire ack_match=sealed&&{w4_gen,w4_job,w4_rank}==ctx[42:0]&&
   {1'b0,w4_index}<ctx[48:43]&&!ack_id[65]&&ack_id[63:55]==0&&ack_id[54:0]==w4_owner55&&!seen[w4_index];
  wire fence_match=sealed&&{w6_gen,w6_job,w6_rank}==ctx[42:0]&&
   {1'b0,w6_index}<ctx[48:43]&&!fence_id[65]&&fence_id[63:55]==0&&fence_id[54:0]==w6_owner55&&!seen[32+w6_index];
  reg manifest_bad;
  reg [65:0] loaded_id;
  integer m;
  always @* begin
   manifest_bad=({manifest_owner55[12:9],manifest_owner55[44:13],manifest_owner55[54:48]}!=ctx[42:0]) || manifest_owner55[47:45]>=6;
   loaded_id=0;
   for(m=0;m<32;m=m+1)if(m<st[5:0])begin
    loaded_id=decode64(identities[m]);
    if(loaded_id[65] || loaded_id[54:0]==manifest_owner55)manifest_bad=1;
   end
  end
  wire invalid_manifest=manifest_valid&&st[18]&&st[5:0]<ctx[48:43]&&manifest_bad;
  wire invalid_event=invalid_manifest||(w4_accept&&!ack_match)||(w6_accept&&!fence_match)||source_fault;
  // Invalid simultaneous evidence masks completion on the same edge.
  assign begin_ready=live&&!st[18]&&begin_count>=1&&begin_count<=32;
  assign manifest_ready=live&&st[18]&&st[5:0]<ctx[48:43]&&!manifest_bad;
  assign complete_valid=live&&!invalid_event&&sealed&&st[11:6]==ctx[48:43]&&st[17:12]==ctx[48:43];
  assign complete_rank=ctx[6:0];assign complete_job=ctx[38:7];assign complete_gen=ctx[42:39];
  assign fault=bad||st[19];
  reg [63:0] next_st,next_seen;
  integer i;
  always @* begin
   next_st=st;next_seen=seen;
   if(invalid_event)next_st[19]=1;
   if(w4_accept&&ack_match)begin next_st[11:6]=st[11:6]+1'b1;next_seen[w4_index]=1;end
   if(w6_accept&&fence_match)begin next_st[17:12]=st[17:12]+1'b1;next_seen[32+w6_index]=1;end
   if(manifest_valid&&manifest_ready)next_st[5:0]=st[5:0]+1'b1;
   if(complete_valid&&complete_ready)next_st[18]=0;
  end
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin
    context_code<=encode64(0);state_code<=encode64(0);seen_code<=encode64(0);
    for(i=0;i<32;i=i+1)identities[i]<=encode64(0);
   end else if(!bad)begin
    // Runtime reset cannot erase held count/identity debt.
    if(!rst_n)begin
     if(st[18])state_code<=encode64(st|64'h80000);
    end else if(live)begin
     if(begin_valid&&begin_ready&&!invalid_event)begin
      context_code<=encode64({15'b0,begin_count,begin_gen,begin_job,begin_rank});
      state_code<=encode64(64'h40000);seen_code<=encode64(0);
     end else begin
      state_code<=encode64(next_st);seen_code<=encode64(next_seen);
      if(manifest_valid&&manifest_ready)identities[st[4:0]]<=encode64({9'b0,manifest_owner55});
     end
    end
   end
  end
 end endgenerate
endmodule
