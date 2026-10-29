// SIM-only transport endpoints; actual emitted names and full-bus spelling.
module SPB0_source(input clk,phy_rst_n,ep_rst_n,input [511:0] provider_rx,provider_tx,input[1:0]provider_st,
 output[511:0]observed_rx,observed_phy_tx,output[1:0]observed_st);
 wire rst_n=phy_rst_n,rst_n_t20=ep_rst_n;
 wire[511:0]w_u_lk_S0_rx;wire[1:0]w_u_lk_S0_st;wire[511:0]w_u_ep_S0_sd_tx;
 ot_pdie_serdes u_u_lk_S0(.clk(clk),.rst(rst_n),.rx(w_u_lk_S0_rx),.st(w_u_lk_S0_st),.tx(w_u_ep_S0_sd_tx[511:0]),.provider_rx(provider_rx),.provider_st(provider_st),.observed_phy_tx(observed_phy_tx));
 hfd_ep_static u_u_ep_S0(.clk(clk),.rst_n(rst_n_t20),.sd_rx(w_u_lk_S0_rx[511:0]),.sd_st(w_u_lk_S0_st[1:0]),.sd_tx(w_u_ep_S0_sd_tx),.provider_tx(provider_tx),.observed_rx(observed_rx),.observed_st(observed_st));
endmodule
