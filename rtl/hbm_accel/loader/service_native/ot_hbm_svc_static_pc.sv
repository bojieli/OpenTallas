`default_nettype none
// A real PHY-local PC leaf. Variable request/response waits are confined here,
// at the HBM boundary. Compiler fill/read pulses have no ready and never retry.
// Native PHY addresses are PC-local byte addresses; step is explicit.
module ot_hbm_svc_static_pc (
 input wire clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,
 input wire fill_v,fill_bank,input wire [15:0] fill_epoch,input wire [5:0] fill_slot,
 input wire [255:0] fill_data,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_slot,
 output reg out_v,output wire [255:0] out_data,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 // cmd_write=0 prefetches into an empty open bank. cmd_write=1 writes a
 // complete staged bank and retires it only after every real k_wr_done.
 input wire cmd_v,cmd_write,cmd_bank,input wire [15:0] cmd_epoch,
 input wire [29:0] cmd_addr,cmd_step,
 output wire [1:0] block_ready,output wire [1:0] bank_owned,output wire busy,output reg done,output wire fault,
 output wire k_v,input wire k_rdy,output wire [29:0] k_addr,
 output wire [3:0] k_len,output wire [16:0] k_tag,output wire k_we,
 output wire [255:0] k_wdata,output wire [31:0] k_wstrb,input wire k_wr_done,
 input wire kr_v,output wire kr_rdy,input wire [16:0] kr_tag,
 input wire [3:0] kr_beat,input wire [255:0] kr_data
);
 localparam [2:0] IDLE=0,RREQ=1,RWAIT=2,WREAD=3,WCAP=4,WREQ=5,WDONE=6;
 reg [2:0] state;
 reg [1:0] owned;
 reg [15:0] epoch[0:1];reg [6:0] count[0:1];reg [63:0] seen[0:1];
 reg bank_q;reg [15:0] epoch_q;reg [29:0] addr_q,step_q;
 reg [5:0] slot_q;reg [255:0] write_q;reg sticky;
 wire [255:0] mem_data;
 function automatic all_seen(input [63:0] bits,input [6:0] n);
  integer i;begin all_seen=n!=0;for(i=0;i<64;i=i+1)if(i<n&&!bits[i])all_seen=0;end
 endfunction
 assign block_ready={owned[1]&&all_seen(seen[1],count[1]),owned[0]&&all_seen(seen[0],count[0])};
 assign bank_owned=owned;
 wire [30:0] next_addr={1'b0,addr_q}+{1'b0,step_q};
 assign busy=state!=IDLE;assign fault=sticky;
 wire scheduled_read=read_v && owned[read_bank] && block_ready[read_bank] &&
      read_epoch==epoch[read_bank] && {1'b0,read_slot}<count[read_bank] && !sticky;
 wire response=kr_v&&state==RWAIT&&kr_tag=={bank_q,epoch_q}&&kr_beat==0&&!sticky;
 wire staged_fill=fill_v&&owned[fill_bank]&&fill_epoch==epoch[fill_bank]&&
      {1'b0,fill_slot}<count[fill_bank]&&!seen[fill_bank][fill_slot]&&
      !(busy&&bank_q==fill_bank)&&!sticky;
 wire write_read=state==WREAD&&!sticky;
 wire conflict_read=read_v&&write_read;
 wire conflict_write=fill_v&&response;
 wire wr=staged_fill||response;
 wire wb=response?bank_q:fill_bank;
 wire [5:0] ws=response?slot_q:fill_slot;
 wire command_ok=cmd_v&&state==IDLE&&owned[cmd_bank]&&cmd_epoch==epoch[cmd_bank]&&
     (cmd_write?block_ready[cmd_bank]:seen[cmd_bank]==0)&&cmd_addr[4:0]==0&&cmd_step[4:0]==0&&!sticky;
 assign k_v=(state==RREQ||state==WREQ)&&!sticky;
 assign k_addr=addr_q;assign k_len=4'd1;assign k_tag={bank_q,epoch_q};
 assign k_we=state==WREQ;assign k_wdata=write_q;assign k_wstrb=32'hffffffff;
 assign kr_rdy=state==RWAIT&&!sticky;
 assign out_data=mem_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;owned<=0;epoch[0]<=0;epoch[1]<=0;count[0]<=0;count[1]<=0;
   seen[0]<=0;seen[1]<=0;bank_q<=0;epoch_q<=0;addr_q<=0;step_q<=0;
   slot_q<=0;write_q<=0;sticky<=0;out_v<=0;done<=0;
  end else begin
   done<=0;out_v<=scheduled_read&&!conflict_read;
   if(open_v)begin
    if(owned[open_bank]||open_count==0||open_count>64||
       (cmd_v&&cmd_bank==open_bank))sticky<=1;
    else begin owned[open_bank]<=1;epoch[open_bank]<=open_epoch;count[open_bank]<=open_count;seen[open_bank]<=0;end
   end
   if(fill_v&&!staged_fill)sticky<=1;
   if(read_v&&!scheduled_read)sticky<=1;
   if(conflict_read||conflict_write)sticky<=1;
   if(retire_v)begin
    if(!owned[retire_bank]||retire_epoch!=epoch[retire_bank]||
       (busy&&bank_q==retire_bank)|| (read_v&&read_bank==retire_bank)||
       (fill_v&&fill_bank==retire_bank)||(cmd_v&&cmd_bank==retire_bank))sticky<=1;
    else owned[retire_bank]<=0;
   end
   if(wr&&!conflict_write)seen[wb][ws]<=1;
   if(kr_v&&!response)sticky<=1;
   if(k_wr_done && !(state==WDONE||(state==WREQ&&k_rdy)))sticky<=1;
   if(cmd_v)begin
    if(!command_ok)sticky<=1;
    else begin bank_q<=cmd_bank;epoch_q<=cmd_epoch;addr_q<=cmd_addr;step_q<=cmd_step;slot_q<=0;state<=cmd_write?WREAD:RREQ;end
   end
   if(state==RREQ&&k_rdy&&!sticky)state<=RWAIT;
   if(response)begin
    if({1'b0,slot_q}+1==count[bank_q])begin state<=IDLE;done<=1;end
    else begin slot_q<=slot_q+1'b1;addr_q<=next_addr[29:0];if(next_addr[30])sticky<=1;state<=RREQ;end
   end
   if(state==WREAD&&!sticky)state<=WCAP;
   if(state==WCAP&&!sticky)begin write_q<=mem_data;state<=WREQ;end
   if(state==WREQ&&k_rdy&&!sticky)state<=WDONE;
   if((state==WDONE||(state==WREQ&&k_rdy))&&k_wr_done&&!sticky)begin
    if({1'b0,slot_q}+1==count[bank_q])begin state<=IDLE;owned[bank_q]<=0;done<=1;end
    else begin slot_q<=slot_q+1'b1;addr_q<=next_addr[29:0];if(next_addr[30])sticky<=1;state<=WREAD;end
   end
  end
 end
 ot_sram_1r1w_128x256_m1_r2c2 u_payload (
 .clk(clk),.r_ce_in((scheduled_read||write_read)&&!conflict_read),
 .r_addr_in(write_read?{bank_q,slot_q}:{read_bank,read_slot}),.rd_out(mem_data),
 .w_ce_in(wr&&!conflict_write),.w_addr_in({wb,ws}),.wd_in(response?kr_data:fill_data),
 .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
endmodule
`default_nettype wire
