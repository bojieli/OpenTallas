`timescale 1ns/1ps
`default_nettype none
// One actual full2MiB backend. Raw diagnostic only, not protected publication.
// Callers retain one owned transaction; reverse receipts certify consumption.
module ot_ds_shared_native_vm_provider #(parameter integer ENABLE=0)(
 input wire clk,cold_n,rst_n,abort,
 input wire [4:0] r_v, output reg [4:0] r_ready,
 input wire [19:0] r_enable,input wire [599:0] r_addr,input wire [1139:0] r_owner,
 output reg [4:0] q_v,input wire [4:0] q_ready,output wire [10239:0] q_data,
 output wire [1139:0] q_owner,
 input wire [4:0] consumed,input wire [1139:0] consumed_owner,
 output wire [4:0] r_retire,input wire [4:0] r_retire_ready,
 output wire [1139:0] r_retire_owner,
 input wire [2:0] w_v,output reg [2:0] w_ready,
 input wire [383:0] w_enable,input wire [11519:0] w_addr,input wire [12287:0] w_data,
 input wire [2:0] w_format_bad,input wire [683:0] w_owner,
 output reg [2:0] w_retire,input wire [2:0] w_retire_ready,output wire [683:0] w_retire_owner,
 output reg fault,quarantined,output wire [7:0] debt,
 output wire [3:0] debug_native_write_accept,debug_native_visible,
 output wire debug_native_read_accept
);
 localparam [3:0] IDLE=0,R_SETUP=1,R_ISSUE=2,R_WAIT=3,R_EXTRACT=4,R_SEND=5,
 W_ISSUE=6,W_WAIT=7,W_ADVANCE=8,W_RETURN=9;
 reg [3:0] state;reg [2:0] turn,active;
 reg [227:0] owner;
 reg [119:0] addresses;reg [3:0] enables;reg [1:0] lane;
 reg [18:0] start;reg [6:0] length;reg second;
 reg [4095:0] buffer;reg [2047:0] result;
 reg [127:0] we,done_lanes;reg [3839:0] wa;reg [4095:0] wd;
 reg [3:0] ack_seen;
 reg [4:0] read_pending,read_released,read_sent;reg [1139:0] read_owners;
 wire n_rd_accept,n_rd_valid,n_rd_fault,n_wr_fault,n_collision;
 wire [2047:0] n_q;wire [227:0] n_qowner;wire [1:0] n_rot;
 wire [3:0] n_waccept,n_ack;wire [911:0] n_ack_owner;
 wire [59:0] n_ack_addr;wire [63:0] n_ack_mask;
 reg [3:0] batch_v;reg [59:0] batch_addr;reg [2047:0] batch_data;
 reg [63:0] batch_mask;reg [127:0] batch_lanes;
 reg [4:0] read_bad;reg [2:0] write_bad;
 integer c,j,b,pick,ix;reg [19:0] first,last;
 always @(*)begin
  read_bad=0;write_bad=w_format_bad;
  for(c=0;c<5;c=c+1)begin
   if((r_enable[c*4+:4] & (c<3 ? 4'h1 : 4'hf))==0 || (c<3 && r_enable[c*4+:4]!=1))read_bad[c]=1;
   for(j=0;j<4;j=j+1)if(r_enable[c*4+j])begin
    first={1'b0,r_addr[c*120+j*30+:19]};
    if(|r_addr[c*120+j*30+19+:11])read_bad[c]=1;
    last=first+(c==0 ? 64 : c==2 || c==4 ? 16 : 1);
    if(last>524288)read_bad[c]=1;
   end
  end
  for(c=0;c<3;c=c+1)begin
   if(w_enable[c*128+:128]==0)write_bad[c]=1;
   for(j=0;j<128;j=j+1)if(w_enable[c*128+j] && (|w_addr[c*3840+j*30+19+:11]))write_bad[c]=1;
  end
 end
 // Four physical write banks, one word per bank. Later same-word lanes win.
 always @(*)begin
  batch_v=0;batch_addr=0;batch_data=0;batch_mask=0;batch_lanes=0;
  for(j=0;j<128;j=j+1)if(we[j]&&!done_lanes[j])begin
   b=wa[j*30+4+:2];
   if(!batch_v[b])begin batch_v[b]=1;batch_addr[b*15+:15]=wa[j*30+4+:15];end
   if(batch_addr[b*15+:15]==wa[j*30+4+:15])begin
    batch_mask[b*16+wa[j*30+:4]]=1;
    batch_data[b*512+wa[j*30+:4]*32+:32]=wd[j*32+:32];batch_lanes[j]=1;
   end
  end
 end
 always @(*)begin
  r_ready=0;w_ready=0;q_v=0;w_retire=0;pick=-1;
  if(ENABLE&&cold_n&&rst_n&&!abort&&!fault&&!quarantined)begin
   if(state==IDLE)begin
    for(c=0;c<8;c=c+1)begin
     ix=(turn+c)%8;
     if(pick==-1)begin
      if(ix<5 && r_v[ix]&&!read_pending[ix]&&!read_bad[ix])pick=ix;
      if(ix>=5 && w_v[ix-5]&&!write_bad[ix-5])pick=ix;
     end
    end
    if(pick>=0)begin if(pick<5)r_ready[pick]=1;else w_ready[pick-5]=1;end
   end
   if(state==R_SEND)q_v[active]=1;
   if(state==W_RETURN)w_retire[active-5]=1;
  end
 end
 genvar g;
 generate for(g=0;g<5;g=g+1)begin: read_outputs
  assign q_data[g*2048+:2048]=result;
  assign q_owner[g*228+:228]=owner;
  assign r_retire[g]=ENABLE&&cold_n&&rst_n&&!abort&&!quarantined&&read_released[g];
 end
 for(g=0;g<3;g=g+1)begin: write_outputs
  assign w_retire_owner[g*228+:228]=owner;
 end endgenerate
 assign r_retire_owner=read_owners;
 assign debt={state>=W_ISSUE ? (3'b001 << (active-5)) : 3'b0,read_pending};
 wire [14:0] group_word={start[18:6],2'b0}+(second ? 15'd4 : 15'd0);
 assign debug_native_write_accept=n_waccept;assign debug_native_visible=n_ack;
 assign debug_native_read_accept=n_rd_accept;
 ot_v41_vm_bank4_macro_pipe_masked_visible_r2 #(.MASKED_VISIBLE(1),.DEPTH_GROUPS(16),.AW(15),.TAG_W(228)) native(
 .clk(clk),.rst_n(cold_n),.rd_v(state==R_ISSUE&&!fault&&!quarantined&&!abort&&rst_n),
 .rd_base_word(group_word),.rd_owner(owner),.rd_accept_v(n_rd_accept),.rd_out_v(n_rd_valid),
 .rd_out_rot(n_rot),.rd_out_bank_words(n_q),.rd_out_owner(n_qowner),.rd_fault(n_rd_fault),
 .wr_v(state==W_ISSUE&&!fault&&!quarantined&&!abort&&rst_n ? batch_v : 4'b0),
 .wr_word_addr(batch_addr),.wr_word_data(batch_data),.wr_lane_mask(batch_mask),.wr_owner({4{owner}}),
 .wr_accept_v(n_waccept),.wr_ack_v(n_ack),.wr_ack_owner(n_ack_owner),
 .wr_ack_word_addr(n_ack_addr),.wr_ack_lane_mask(n_ack_mask),.wr_fault(n_wr_fault),.rw_collision_fault(n_collision));
 always @(posedge clk)begin
  if(!cold_n)begin
   state<=IDLE;turn<=0;active<=0;owner<=0;addresses<=0;enables<=0;lane<=0;start<=0;length<=0;
   second<=0;buffer<=0;result<=0;we<=0;wa<=0;wd<=0;done_lanes<=0;ack_seen<=0;
   read_pending<=0;read_released<=0;read_sent<=0;read_owners<=0;fault<=0;quarantined<=0;
  end else begin
   if((abort||!rst_n)&&(state!=IDLE||read_pending!=0))quarantined<=1;
   if(n_rd_fault||n_wr_fault||n_collision)fault<=1;
   // Invalid offered requests are retained by their owned FIFO, never granted.
   if((|(r_v&read_bad)) || (|(w_v&write_bad)))begin fault<=1;quarantined<=1;end
   for(integer r=0;r<5;r=r+1)begin
    if(consumed[r])begin
     if(!read_pending[r]||!read_sent[r]||read_released[r]||consumed_owner[r*228+:228]!=read_owners[r*228+:228])begin fault<=1;quarantined<=1;end
     else read_released[r]<=1;
    end
    if(r_retire[r]&&r_retire_ready[r])begin read_pending[r]<=0;read_released[r]<=0;read_sent[r]<=0;end
   end
   if(ENABLE&&rst_n&&!abort&&!quarantined&&!fault)case(state)
    IDLE:if(pick>=0)begin
     active<=pick;turn<=3'(pick+1);result<=0;
     if(pick<5)begin
      owner<=r_owner[pick*228+:228];read_owners[pick*228+:228]<=r_owner[pick*228+:228];read_pending[pick]<=1;
      addresses<=r_addr[pick*120+:120];enables<=r_enable[pick*4+:4];lane<=0;state<=R_SETUP;
     end else begin
      owner<=w_owner[(pick-5)*228+:228];we<=w_enable[(pick-5)*128+:128];
      wa<=w_addr[(pick-5)*3840+:3840];wd<=w_data[(pick-5)*4096+:4096];done_lanes<=0;state<=W_ISSUE;
     end
    end
    R_SETUP:begin
     if(!enables[lane])begin if(lane==3||active<3)state<=R_SEND;else lane<=lane+1'b1;end
     else begin start<=addresses[lane*30+:19];length<=active==0 ? 64 : active==2||active==4 ? 16 : 1;
      second<=0;buffer<=0;state<=R_ISSUE;end
    end
    R_ISSUE:if(n_rd_accept)state<=R_WAIT;
    R_WAIT:if(n_rd_valid)begin
     if(n_qowner!=owner||n_rot!=0)begin fault<=1;quarantined<=1;end
     else begin
      if(second)buffer[4095:2048]<=n_q;else buffer[2047:0]<=n_q;
      if(!second && ({1'b0,start[5:0]}+length>64))begin second<=1;state<=R_ISSUE;end
      else state<=R_EXTRACT;
     end
    end
    R_EXTRACT:begin
     case(active)
      0:result<=buffer >> (start[5:0]*32);
      1:result[31:0]<=buffer >> (start[5:0]*32);
      2:result[511:0]<=buffer >> (start[5:0]*32);
      3:result[lane*32+:32]<=buffer >> (start[5:0]*32);
      4:result[lane*512+:512]<=buffer >> (start[5:0]*32);
     endcase
     if(active<3||lane==3)state<=R_SEND;else begin lane<=lane+1'b1;state<=R_SETUP;end
    end
    R_SEND:if(q_ready[active])begin read_sent[active]<=1;state<=IDLE;end
    W_ISSUE:begin
     if(batch_v==0)begin fault<=1;quarantined<=1;end
     else if(n_waccept==batch_v)begin ack_seen<=0;state<=W_WAIT;end
    end
    W_WAIT:begin
     for(integer wb=0;wb<4;wb=wb+1)if(n_ack[wb])begin
      if(!batch_v[wb]||n_ack_owner[wb*228+:228]!=owner||n_ack_addr[wb*15+:15]!=batch_addr[wb*15+:15]||n_ack_mask[wb*16+:16]!=batch_mask[wb*16+:16])begin fault<=1;quarantined<=1;end
      else ack_seen[wb]<=1;
     end
     if(((ack_seen|n_ack)&batch_v)==batch_v)state<=W_ADVANCE;
    end
    W_ADVANCE:begin done_lanes<=done_lanes|batch_lanes;
     state<=((done_lanes|batch_lanes)&we)==we ? W_RETURN : W_ISSUE;
    end
    W_RETURN:if(w_retire_ready[active-5])state<=IDLE;
    default:begin fault<=1;quarantined<=1;end
   endcase
  end
 end
endmodule
`default_nettype wire
