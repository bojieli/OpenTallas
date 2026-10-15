`timescale 1ns/1ps
// True write-commit return: events originate at the SRAM write-enable edge.
// Every 512b write commits independently in four 128b slices; acknowledge only
// after all four events with the same transaction tag and row have arrived.
// Tags remain owned by the requester until this ACK crosses back to stream.
module dsfd_vm_write_ack #(parameter integer NS=4,NT=4,NTAG=32)(
 input wire ck,rst_n,cks,rss_n,
 input wire [NS*NT*8*28-1:0] records,
 output wire ack_v, output wire [7:0] ack_tag, output wire [15:0] ack_mask,
 output reg fault
);
 reg [3:0] seen[0:NTAG-1],seen_n[0:NTAG-1];
 reg [15:0] masks[0:NTAG-1],masks_n[0:NTAG-1];
 reg [13:0] rows[0:NTAG-1],rows_n[0:NTAG-1];
 reg [NTAG-1:0] ready,ready_n;
 integer h,t,b,id,j,pick; reg found,bad; reg [27:0] ev;
 wire fifo_ready; wire emit=found && fifo_ready;
 always @* begin
  ready_n=ready;bad=0;
  for(j=0;j<NTAG;j=j+1) begin seen_n[j]=seen[j];masks_n[j]=masks[j];rows_n[j]=rows[j];end
  found=0;pick=0;
  for(j=NTAG-1;j>=0;j=j-1) if(ready[j])begin found=1;pick=j;end
  if(found && fifo_ready)begin ready_n[pick]=0;seen_n[pick]=0;masks_n[pick]=0;end
  for(h=0;h<NS;h=h+1)for(t=0;t<NT;t=t+1)for(b=0;b<8;b=b+1)begin
   ev=records[28*((h*NT+t)*8+b)+:28]; id=ev[7:0];
   if(ev[27] && id>=NTAG)bad=1;
   if(ev[27] && id<NTAG)begin
    if(seen_n[id][h] || ready_n[id])bad=1;
    if(seen_n[id]!=0 && rows_n[id]!=ev[21:8])bad=1;
    rows_n[id]=ev[21:8];seen_n[id][h]=1;
    masks_n[id][4*h+:4]=ev[25:22];
    `ifdef OT_VMCOMMIT_MUT_EARLY
    ready_n[id]=1; // mutant: ACK after first slice instead of all physical slices
`else
    if(&seen_n[id])ready_n[id]=1;
`endif
   end
  end
 end
 wire reset_n=rst_n & rss_n;
 always @(posedge ck or negedge reset_n)begin
  if(!reset_n)begin ready<=0;fault<=0;for(integer z=0;z<NTAG;z=z+1)begin seen[z]<=0;masks[z]<=0;rows[z]<=0;end end
  else begin ready<=ready_n;fault<=fault|bad;for(integer z=0;z<NTAG;z=z+1)begin seen[z]<=seen_n[z];masks[z]<=masks_n[z];rows[z]<=rows_n[z];end end
 end
 wire [23:0] ack;
 ot_async_fifo #(.WIDTH(24),.DEPTH(64)) u_return(
 .wr_clk(ck),.wr_rst_n(rst_n & rss_n),.wr_valid(emit),.wr_ready(fifo_ready),
 .wr_data({masks[pick],8'(pick)}),.wr_overflow(),
 .rd_clk(cks),.rd_rst_n(rst_n & rss_n),.rd_valid(ack_v),.rd_ready(1'b1),
 .rd_data(ack),.rd_underflow());
 assign ack_tag=ack[7:0];assign ack_mask=ack[23:8];
 initial if(NS!=4)$error("write ACK requires four physical128b slices");
endmodule
