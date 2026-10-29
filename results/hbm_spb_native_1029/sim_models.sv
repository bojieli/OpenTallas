// SIM-ONLY endpoint models expose the direct transport mechanism; no EP/PHY functional qualification.
module ot_pdie_serdes(input wire clk,rst_n,input wire[511:0]tx,provider_rx,input wire[1:0]provider_st,
 output wire[511:0]rx,observed_phy_tx,output wire[1:0]st);
 assign rx=provider_rx;assign st=provider_st;assign observed_phy_tx=tx;
endmodule
module hfd_ep_static(input wire clk,rst_n,input wire[511:0]sd_rx,provider_tx,input wire[1:0]sd_st,
 output wire[511:0]sd_tx,observed_rx,output wire[1:0]observed_st);
 assign sd_tx=provider_tx;assign observed_rx=sd_rx;assign observed_st=sd_st;
endmodule
