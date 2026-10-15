// Default-off protocol candidate. No physical ABI or global source adoption.
// All events sampled on live base_clk. core_step denotes an actual core edge.
// transport_flushed must certify ALL old source/transport/cache returns drained.
module ot_qwen_xcontext_protocol #(
 parameter integer DEPTH=8, ROOTS=32, TOKEN_START=0,
 parameter integer MUT_CONTEXT=0, MUT_DUP=0, MUT_GO=0, MUT_REUSE=0
)(
 input wire base_clk, rst_n, flush, transport_flushed,
 input wire req_v, input wire [ROOTS*96-1:0] req_addr,
 input wire [378:0] req_ib, input wire [31:0] req_version,
 input wire [20:0] req_epoch, input wire [3:0] req_mask, input wire [3:0] req_phase,
 output wire req_ready, output wire [15:0] req_token,
 input wire return_event, input wire [15:0] return_token,
 input wire [4:0] return_root, input wire [127:0] return_data,
 output wire return_ready, output wire fill_fire,
 output wire [95:0] fill_addr, output wire [378:0] fill_ib,
 output wire [31:0] fill_version, output wire [20:0] fill_epoch,
 output wire [3:0] fill_mask, output wire [3:0] fill_phase, output wire [127:0] fill_data,
 input wire ack_event, input wire [15:0] ack_token,input wire [4:0] ack_root,
 input wire ib_offer, input wire [378:0] ib_offer_data,
 output wire ib_offer_ready, input wire core_step,core_ready,
 output wire core_go, output wire [378:0] core_ib,
 output reg flushing, output reg fault
);
 reg live[0:DEPTH-1];reg [15:0] tok[0:DEPTH-1];
 reg [ROOTS*96-1:0] addr[0:DEPTH-1];reg [378:0] ib[0:DEPTH-1];
 reg [31:0] ver[0:DEPTH-1];reg [20:0] epoch[0:DEPTH-1];
 reg [3:0] mask[0:DEPTH-1],phase[0:DEPTH-1];reg [ROOTS-1:0] ret[0:DEPTH-1],ack[0:DEPTH-1];
 reg [15:0] next_token;reg pending;reg [378:0] held_ib;
 reg [ROOTS*96-1:0] latest_addr;reg [378:0] latest_ib;reg [31:0] latest_version;
 integer free_slot,return_slot,ack_slot,i;reg token_busy;
 always @* begin
  free_slot=-1;return_slot=-1;ack_slot=-1;token_busy=0;
  for(integer n=0;n<DEPTH;n=n+1) begin
   if(!live[n] && free_slot<0) free_slot=n;
   if(live[n] && tok[n]==next_token) token_busy=1;
   if(live[n] && tok[n]==return_token) return_slot=n;
   if(live[n] && tok[n]==ack_token) ack_slot=n;
  end
 end
 assign req_ready=rst_n&&!flushing&&!flush&&(free_slot>=0)&&(!token_busy||(MUT_REUSE!=0));
 assign req_token=next_token;
 assign return_ready=rst_n&&!flushing&&!flush&&(return_slot>=0)&&
  (return_root<ROOTS)&&((MUT_DUP!=0)||!ret[return_slot][return_root]);
 assign fill_fire=return_event&&return_ready;
 assign fill_addr=(MUT_CONTEXT!=0)?latest_addr[96*return_root+:96]:((return_slot>=0)?addr[return_slot][96*return_root+:96]:96'd0);
 assign fill_ib=(MUT_CONTEXT!=0)?latest_ib:((return_slot>=0)?ib[return_slot]:379'd0);
 assign fill_version=(MUT_CONTEXT!=0)?latest_version:((return_slot>=0)?ver[return_slot]:32'd0);
 assign fill_epoch=(return_slot>=0)?epoch[return_slot]:21'd0;
 assign fill_mask=(return_slot>=0)?mask[return_slot]:4'd0;
 assign fill_phase=(return_slot>=0)?phase[return_slot]:4'd0;
 assign fill_data=return_data;
 wire consume=pending&&core_step&&core_ready&&!flushing&&!flush;
 assign ib_offer_ready=rst_n&&!flushing&&!flush&&(!pending||consume);
 assign core_go=(MUT_GO!=0)?ib_offer:(pending&&!flushing&&!flush);
 assign core_ib=(MUT_GO!=0)?ib_offer_data:held_ib;
 always @(posedge base_clk) begin
  if(!rst_n) begin
   flushing<=1;fault<=0;next_token<=16'(TOKEN_START);pending<=0;held_ib<=0;
   latest_addr<=0;latest_ib<=0;latest_version<=0;
   for(i=0;i<DEPTH;i=i+1) begin live[i]<=0;ret[i]<=0;ack[i]<=0;tok[i]<=0;addr[i]<=0;ib[i]<=0;ver[i]<=0;epoch[i]<=0;mask[i]<=0;phase[i]<=0;end
  end else if(flush) begin
   // Block all acceptance immediately; release only after distributed drain.
   flushing<=1;pending<=0;
   for(i=0;i<DEPTH;i=i+1) begin live[i]<=0;ret[i]<=0;ack[i]<=0;end
  end else if(flushing) begin
   if(transport_flushed) flushing<=0;
  end else begin
   if(req_v&&req_ready) begin
    live[free_slot]<=1;tok[free_slot]<=next_token;next_token<=next_token+1'b1;
    addr[free_slot]<=req_addr;ib[free_slot]<=req_ib;ver[free_slot]<=req_version;
    epoch[free_slot]<=req_epoch;mask[free_slot]<=req_mask;phase[free_slot]<=req_phase;ret[free_slot]<=0;ack[free_slot]<=0;
    latest_addr<=req_addr;latest_ib<=req_ib;latest_version<=req_version;
   end
   if(return_event) begin
    if(return_ready) ret[return_slot][return_root]<=1;
    else fault<=1;
   end
   if(ack_event) begin
    if(ack_slot>=0 && ack_root<ROOTS && ret[ack_slot][ack_root] && !ack[ack_slot][ack_root]) begin
     ack[ack_slot][ack_root]<=1;
     // All ACKs imply unique returns already observed. No free on return alone.
     if((ack[ack_slot]|( {{(ROOTS-1){1'b0}},1'b1} << ack_root))=={ROOTS{1'b1}}) live[ack_slot]<=0;
    end else fault<=1;
   end
   if(consume) pending<=0;
   if(ib_offer&&ib_offer_ready) begin pending<=1;held_ib<=ib_offer_data;end
  end
 end
endmodule
