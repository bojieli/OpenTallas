`timescale 1ns/1ps
// Default-off finite source-join preparation. Full operation storage protects
// the source SM's nonbackpressured row port. No SRAM/TMEM/physical qualification.
module ot_gpu_matrix_capture_audit #(
 parameter integer ENABLE=0, NC=8, RMAX=4096
)(
 input wire clk,rst_n,reserve_valid,input wire[12:0]reserve_rows,output wire reserve_ready,
 input wire row_valid,input wire[11:0]row_index,input wire[NC*32-1:0]row_data,
 output wire wr_valid,input wire wr_ready,output wire[8:0]wr_addr,output wire[4095:0]wr_data,
 input wire ack_valid,retire_enable,output wire ack_ready,
 input wire operands_visible,activation_visible,matrix_released,lease_release,
 output wire capture_done,rf_visible_done,consumer_eligible,busy,
 output wire[12:0]accepted_rows,output wire[9:0]committed_vectors,output wire fault
);
 localparam integer RP=128/NC, VMAX=RMAX/RP;
 generate if(ENABLE)begin:g_on
 reg live,err,waiting,visible;
 reg[12:0]rows_q,nrows;reg[9:0]nvec,wp,committed;
 reg[RMAX-1:0]seen;
 reg[VMAX-1:0]complete;
 reg[4:0]vrows[0:VMAX-1];
 reg[4095:0]data[0:VMAX-1];
 integer v,l,k,needed;
 assign reserve_ready=rst_n&&!live;
 assign busy=live;assign accepted_rows=nrows;assign committed_vectors=committed;assign fault=err;
 assign wr_valid=live&&!waiting&&wp<nvec&&complete[wp];
 assign wr_addr=wp[8:0];assign wr_data=wp<VMAX?data[wp]:4096'd0;
 assign ack_ready=live&&waiting&&retire_enable;
 assign capture_done=live&&nrows==rows_q;assign rf_visible_done=live&&visible;
 assign consumer_eligible=capture_done&&rf_visible_done&&operands_visible&&activation_visible&&matrix_released&&!err;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin live<=0;err<=0;waiting<=0;visible<=0;rows_q<=0;nrows<=0;nvec<=0;wp<=0;committed<=0;seen<=0;complete<=0;
   for(k=0;k<VMAX;k=k+1)vrows[k]<=0;
  end else begin
   if(reserve_valid&&reserve_ready)begin
    if(reserve_rows==0||reserve_rows>RMAX)err<=1;
    else begin live<=1;waiting<=0;visible<=0;rows_q<=reserve_rows;nrows<=0;nvec<=(reserve_rows+RP-1)/RP;wp<=0;committed<=0;seen<=0;complete<=0;
     for(k=0;k<VMAX;k=k+1)vrows[k]<=0;
    end
   end
   if(row_valid)begin
    if(!live||row_index>=rows_q||seen[row_index])err<=1;
    else begin
     v=row_index/RP;needed=(v==nvec-1)?rows_q-v*RP:RP;
     // First row clears unused padding lanes only; real rows update disjoint words.
     if(vrows[v]==0)data[v]<=0;
     for(l=0;l<NC;l=l+1)data[v][32*((row_index%RP)*NC+l)+:32]<=row_data[32*l+:32];
     seen[row_index]<=1;nrows<=nrows+1;vrows[v]<=vrows[v]+1;
     if(vrows[v]+1==needed)complete[v]<=1;
    end
   end
   if(wr_valid&&wr_ready)waiting<=1;
   if(ack_valid&&ack_ready)begin
    waiting<=0;wp<=wp+1;committed<=committed+1;
    if(committed+1==nvec)visible<=1;
   end
   if(lease_release)begin
    if(!consumer_eligible)err<=1;else live<=0;
   end
  end
 end
 end else begin:g_off
 assign reserve_ready=0;assign wr_valid=0;assign wr_addr=0;assign wr_data=0;assign ack_ready=0;
 assign capture_done=0;assign rf_visible_done=0;assign consumer_eligible=0;assign busy=0;
 assign accepted_rows=0;assign committed_vectors=0;assign fault=0;
 end endgenerate
endmodule
