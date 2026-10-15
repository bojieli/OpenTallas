`timescale 1ns/1ps
// Real HBM host: source-exact787-bit loader service face -> packet engine ->
// unchanged native endpoint CRC/replay545 -> actual UCIe digital rate-match
// -> declared behavioural PMA pads. No invented GPU/Qwen token producer.
// Controller/landing/endpoint/PHY clocks are delivered separately; current
// implementation requires one synchronous link family, not fake CDC phase.
module hfd_host_native #(parameter integer MUT=0)(
 input wire clk_controller,clk_landing,clk_ep,clk_face,
 input wire[11:0]clk_sub,input wire clk_tx_shared,clk_rx_shared,clk_status_shared,
 input wire clk_phy,rst_n,input wire[23:0]session,
 inout wire[786:0]h,
 output wire[512:0]pma_tx,output wire pma_tck,
 input wire[512:0]pma_rx,input wire pma_rck,
 output wire[4:0]faults,output wire[1:0]phy_status,output wire ep_locked
);
 wire cv,cr,lv,lr,pop,landing_fault,packet_fault;
 wire[511:0]cd,ld;
 tri[1119:0]f_lk;tri[973:0]phy;
 reg[5:0]tx_credits;
 wire send=cv&&(tx_credits!=0);
 assign cr=tx_credits!=0;
 always @(posedge clk_controller or negedge rst_n)
 if(!rst_n)tx_credits<=32;
 else tx_credits<=tx_credits+6'(f_lk[1093])-6'(send);
 hfd_host_packet_face #(.MUT(MUT))u_packet(.clk(clk_controller),.rst_n(rst_n),.h(h),
 .rx_valid(lv),.rx_packet(ld),.rx_ready(lr),.tx_valid(cv),.tx_packet(cd),.tx_ready(cr),.protocol_fault(packet_fault));
 assign f_lk[0]=send;assign f_lk[545:1]={33'd0,cd};assign f_lk[546]=pop;assign f_lk[1117:1094]=session;
 hfd_lk_ep #(.HARD_CLOCKS(1))u_endpoint(.clk(clk_ep),.clk_face(clk_face),.clk_sub(clk_sub),
 .clk_tx_shared(clk_tx_shared),.clk_rx_shared(clk_rx_shared),.clk_status_shared(clk_status_shared),
 .rst_n(rst_n),.f_lk(f_lk),.phy(phy));
 ot_hbm_host_landing256 u_landing(.clk(clk_landing),.rst_n(rst_n),.in_v(f_lk[547]),.in_data(f_lk[1092:548]),
 .out_v(lv),.out_data(ld),.out_ready(lr),.pop(pop),.fault(landing_fault));
 wire[511:0]phy_rx;
 ot_pdie_ucie u_phy(.clk(clk_phy),.rst(rst_n),.tx({25'd0,phy[486:0]}),.rx(phy_rx),.st(phy_status),
 .pma_tx(pma_tx),.pma_tck(pma_tck),.pma_rx(pma_rx),.pma_rck(pma_rck));
 assign phy[973:487]=phy_rx[486:0];
 reg pad_fault;
 always @(posedge clk_phy or negedge rst_n)if(!rst_n)pad_fault<=0;else if(phy_status[1] && phy_rx[511:487]!==25'd0)pad_fault<=1;
 assign faults={pad_fault,packet_fault,landing_fault,f_lk[1118],phy_status[0]};
 assign ep_locked=f_lk[1119];
endmodule
