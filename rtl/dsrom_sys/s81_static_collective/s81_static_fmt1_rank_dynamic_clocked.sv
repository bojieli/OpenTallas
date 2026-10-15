`timescale 1ns/1ps
// Native leaf-root clock version. clk_core/clk_lane must share the priced
// stream epoch; no CDC or phase compensation is inferred here.
// Protocol-compatible normal-mode successor. Compiler beat period4 and three
// records/group produce source issues4,4,8cycles. ZeroPHYflight component
// source issue->gather11cycles; actual relays/flight require static alignment.
module s81_static_fmt1_rank_dynamic_clocked(
 input wire [1:0] rank,input wire clk_core,input wire[2:0]clk_lane,input wire rst_n,issue_slot,src_valid,input wire[511:0]src_data,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,input wire[3:0]rankmask,
 input wire commit_slot,input wire[31:0]commit_tag,input wire[15:0]commit_seq,
 input wire commit_last,input wire[3:0]commit_rankmask,input wire[59:0]commit_rows,
 input wire tx_beat_slot,input wire[1:0]tx_phase,input wire tx_frame_slot,
 input wire rx_beat_slot,input wire[1:0]rx_phase,input wire rx_frame_slot,
 output wire[2:0]phy_tx_valid,output wire[1535:0]phy_tx_data,
 input wire[2:0]phy_rx_valid,input wire[1535:0]phy_rx_data,
 output wire[3:0]vm_we,output wire[59:0]vm_rows,output wire[2047:0]vm_data,
 output wire [31:0] gather_tag,output wire [15:0] gather_seq,output wire gather_last,
 output wire fault
);
 reg [1:0] rank_q;reg rank_set,rank_fault;
 wire configuration_fault=rank_fault || (rank_set && rank!=rank_q) || (!rank_set && (issue_slot || commit_slot));
 always @(posedge clk_core or negedge rst_n)begin
  if(!rst_n)begin rank_q<=0;rank_set<=0;rank_fault<=0;end
  else if(!rank_set)begin rank_q<=rank;rank_set<=1;end
  else if(rank!=rank_q)rank_fault<=1;
 end
 wire txv,ef;wire[568:0]txf;wire[3:0]rv;wire[2275:0]rf;wire[2:0]lf;
 s81_static_fmt1_core_dynamic core(.*,.clk(clk_core),.rank(rank_q),.tx_valid(txv),.tx_frame(txf),.remote_v(rv),.remote_frame(rf),.fault(ef));
 wire[2:0] lane_rx_v;wire[1706:0]lane_rx_record;
 reg[3:0] remote_v_map;reg[2275:0]remote_frame_map;
 always @*begin
  remote_v_map=0;remote_frame_map=0;
  for(integer j=0;j<3;j=j+1)begin
   remote_v_map[int'(rank_q) ^ (j+1)]=lane_rx_v[j];
   remote_frame_map[(int'(rank_q) ^ (j+1))*569+:569]=lane_rx_record[j*569+:569];
  end
 end
 assign rv=remote_v_map;assign rf=remote_frame_map;
 genvar g;
 generate for(g=0;g<3;g=g+1)begin:L
  wire[1:0]peer=rank_q ^ 2'(g+1);
  s81_static_fmt1_lane_dynamic lane(.peer(peer),.clk(clk_lane[g]),.rst_n(rst_n),.tx_v(txv),.tx_record(txf),
   .rx_v(lane_rx_v[g]),.rx_record(lane_rx_record[g*569+:569]),
   .tx_beat_slot(tx_beat_slot),.tx_phase(tx_phase),.tx_frame_slot(tx_frame_slot),
   .rx_beat_slot(rx_beat_slot),.rx_phase(rx_phase),.rx_frame_slot(rx_frame_slot),
   .phy_tx_valid(phy_tx_valid[g]),.phy_tx_data(phy_tx_data[g*512+:512]),
   .phy_rx_valid(phy_rx_valid[g]),.phy_rx_data(phy_rx_data[g*512+:512]),.fault(lf[g]));
 end endgenerate
 assign fault=ef || |lf || configuration_fault;
endmodule
