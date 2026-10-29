`default_nettype none
// Distinct opt-in source: statically scheduled4-slot write demux to the same
// four real line SRAM banks as the parallel master. No arithmetic and no FIFO.
// Existing parallel masters/interfaces stay unchanged. All4 lanes x171rows
// must be resident before the scorer uses common pre/replay controls.
module ot_hnx_idxn_keybuf_serial_np4(
 input wire clk,rst_n,clear,input wire[2:0]strap_lane_base,
 input wire ingest_v,input wire[1:0]ingest_lane,input wire[7:0]ingest_index,
 input wire[1098:0]ingest_line,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire[4395:0]key_out,output wire fault,output reg loaded
);
 reg[1:0]next_lane;reg[7:0]next_row;reg ingest_fault;
 wire[9:0]expected_tag={strap_lane_base+3'(ingest_lane),7'b0}+{2'b0,ingest_index};
 wire[3:0]lane_fault;
 for(genvar p=0;p<4;p=p+1)begin:gp
  ot_hnx_idxn_keybuf_slice u_line(.clk(clk),.rst_n(rst_n),.clear(clear),
   .strap_lane_id(strap_lane_base+3'(p)),
   .live_v(ingest_v && ingest_lane==2'(p)),.live_index(ingest_index),.key_in(ingest_line),
   .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
   .key_out(key_out[p*1099+:1099]),.fault(lane_fault[p]));
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin next_lane<=0;next_row<=0;loaded<=0;ingest_fault<=0;end
  else begin
   if(clear)begin next_lane<=0;next_row<=0;loaded<=0;end
   else if(ingest_v)begin
    if(loaded || !ingest_line[0] || ingest_line[10:1]!=expected_tag ||
       ingest_lane!=next_lane || ingest_index!=next_row || ingest_index>8'd170)
      ingest_fault<=1;
    next_lane<=next_lane+2'd1;
    if(next_lane==2'd3)begin
     if(next_row==8'd170)loaded<=1;
     else next_row<=next_row+8'd1;
    end
   end
   if((pre_v||replay_v)&&!loaded)ingest_fault<=1;
  end
 end
 assign fault=ingest_fault|(|lane_fault);
endmodule
`default_nettype wire
