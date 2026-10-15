`timescale 1ns/1ps
// One actual on-chip rank: endpoint, three digital PHY controllers and the
// local fixed alignment registers. PHY pins are the only off-chip boundary.
// Uniform PHY flight must be0 here; nonzero flight requires compiler-priced
// matching real local alignment stages, not a testbench delay on this path.
module s81_static_tp4_rank #(parameter integer RANK=0)(
 input wire clk,rst_n,issue_slot,src_valid,input wire[511:0]src_data,
 input wire[31:0]tag,input wire[15:0]seq,input wire last,input wire[3:0]rankmask,
 input wire commit_slot,input wire[31:0]commit_tag,input wire[15:0]commit_seq,
 input wire commit_last,input wire[3:0]commit_rankmask,input wire[59:0]commit_rows,
 output wire[2:0]phy_tx_valid,output wire[1535:0]phy_tx_data,
 input wire[2:0]phy_rx_valid,input wire[1535:0]phy_rx_data,
 output wire[3:0]vm_we,output wire[59:0]vm_rows,output wire[2047:0]vm_data,
 output wire fault
);
 wire txv,ef;wire[568:0]txf;wire[3:0]rv;wire[2275:0]rf;wire[2:0]lf;
 reg[2:0]local_v;reg[1706:0]local_f;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin local_v<=0;local_f<=0;end
  else begin local_v<={local_v[1:0],txv};local_f<={local_f[1137:0],txf};end
 end
 assign rv[RANK]=local_v[2];assign rf[RANK*569+:569]=local_f[1706:1138];
 s81_static_tp4_endpoint #(.RANK(RANK)) e(.*,.tx_valid(txv),.tx_frame(txf),.rx_valid(rv),.rx_frame(rf),.fault(ef));
 genvar g;
 generate for(g=0;g<3;g=g+1)begin:L
  localparam integer PEER=g<RANK ? g:g+1;
  s81_static_phy_digital l(.clk(clk),.rst_n(rst_n),.tx_valid(txv),.tx_frame(txf),
   .phy_tx_valid(phy_tx_valid[g]),.phy_tx_data(phy_tx_data[g*512+:512]),
   .phy_rx_valid(phy_rx_valid[g]),.phy_rx_data(phy_rx_data[g*512+:512]),
   .rx_valid(rv[PEER]),.rx_frame(rf[PEER*569+:569]),.fault(lf[g]));
 end endgenerate
 assign fault=ef || |lf;
endmodule
