module gearbox_sta(input wire pll_ref,rst_n,tx_valid,input wire[596:0]tx_frame,
 output wire phy_tx_valid,output wire[1042:0]phy_tx_frame,input wire phy_rx_valid,
 input wire[1042:0]phy_rx_frame,output wire rx_valid,output wire[596:0]rx_frame,
 output wire core_fault,fdi_fault);
 wire g_core;
 BUFx4_ASAP7_75t_R u_gen_core(.A(pll_ref),.Y(g_core));
 wire g_fdi;
 BUFx4_ASAP7_75t_R u_gen_fdi(.A(pll_ref),.Y(g_fdi));
 wire g_rx0;
 BUFx4_ASAP7_75t_R u_gen_rx0(.A(pll_ref),.Y(g_rx0));
 wire g_rx1;
 BUFx4_ASAP7_75t_R u_gen_rx1(.A(pll_ref),.Y(g_rx1));
 wire g_rx2;
 BUFx4_ASAP7_75t_R u_gen_rx2(.A(pll_ref),.Y(g_rx2));
 qfd_ucie_six_five u_g(.core_ck(g_core),.fdi_ck(g_fdi),.fdi_rx_ck({g_rx2,g_rx1,g_rx0}),.rst_n(rst_n),.tx_valid(tx_valid),.tx_frame(tx_frame),
  .phy_tx_valid(phy_tx_valid),.phy_tx_frame(phy_tx_frame),.phy_rx_valid(phy_rx_valid),
  .phy_rx_frame(phy_rx_frame),.rx_valid(rx_valid),.rx_frame(rx_frame),
  .core_fault(core_fault),.fdi_fault(fdi_fault));
endmodule
