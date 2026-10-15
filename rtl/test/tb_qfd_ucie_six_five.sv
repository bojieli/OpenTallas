`timescale 1ns/1ps
module tb_qfd_ucie_six_five #(parameter integer MUT=0)(
 input wire core_ck,fdi_ck,rst_n,tx_valid,input wire[596:0]tx_frame,
 output wire rx_valid,output wire[596:0]rx_frame,output wire core_fault,fdi_fault);
 wire pv;wire[1042:0]pd;localparam integer PL=MUT==3?5:4;reg[PL*1044-1:0]p;
 always @(posedge fdi_ck or negedge rst_n)if(!rst_n)p<=0;else p<={p,pv,pd};
 qfd_ucie_six_five #(.MUT(MUT==3?0:MUT))u_dut(.core_ck(core_ck),.fdi_ck(fdi_ck),.fdi_rx_ck({3{fdi_ck}}),.rst_n(rst_n),
 .tx_valid(tx_valid),.tx_frame(tx_frame),.phy_tx_valid(pv),.phy_tx_frame(pd),
 .phy_rx_valid(p[PL*1044-1]),.phy_rx_frame(p[PL*1044-2-:1043]),
 .rx_valid(rx_valid),.rx_frame(rx_frame),.core_fault(core_fault),.fdi_fault(fdi_fault));
endmodule
