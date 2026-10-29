// SIM-ONLY minimum binding vehicle: selected port names and exact three direct wires.
module SPB0_source(input wire clk,rst_n,input wire[511:0] provider_rx,provider_tx,input wire[1:0]provider_st,
 output wire[511:0] observed_rx,observed_phy_tx,output wire[1:0]observed_st);
 wire[511:0] link_rx,link_tx;wire[1:0]link_st;
 ot_pdie_serdes u_lk_S0(.clk(clk),.rst_n(rst_n),.rx(link_rx),.tx(link_tx),.st(link_st),
 .provider_rx(provider_rx),.provider_st(provider_st),.observed_phy_tx(observed_phy_tx));
 hfd_ep_static u_ep_S0(.clk(clk),.rst_n(rst_n),.sd_rx(link_rx),.sd_tx(link_tx),.sd_st(link_st),
 .provider_tx(provider_tx),.observed_rx(observed_rx),.observed_st(observed_st));
endmodule
