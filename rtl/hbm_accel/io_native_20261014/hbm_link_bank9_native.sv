`timescale 1ns/1ps
// All nine real digital SerDes paths; no geometry-only slab instances.
module hbm_link_bank9_native(input wire[8:0]clk,input wire rst_n,
input wire[9*487-1:0]tx,output wire[9*487-1:0]rx,
output wire[17:0]st,output wire[8:0]padding_fault,
output wire[9*544-1:0]pma_tx,output wire[8:0]pma_tck,
input wire[9*544-1:0]pma_rx,input wire[8:0]pma_rck);
hfd_serdes487 lk_S0(.clk(clk[0]),.rst_n(rst_n),.tx(tx[0*487+:487]),.rx(rx[0*487+:487]),.st(st[0*2+:2]),.padding_fault(padding_fault[0]),.pma_tx(pma_tx[0*544+:544]),.pma_tck(pma_tck[0]),.pma_rx(pma_rx[0*544+:544]),.pma_rck(pma_rck[0]));
hfd_serdes487 lk_S1(.clk(clk[1]),.rst_n(rst_n),.tx(tx[1*487+:487]),.rx(rx[1*487+:487]),.st(st[1*2+:2]),.padding_fault(padding_fault[1]),.pma_tx(pma_tx[1*544+:544]),.pma_tck(pma_tck[1]),.pma_rx(pma_rx[1*544+:544]),.pma_rck(pma_rck[1]));
hfd_serdes487 lk_S2(.clk(clk[2]),.rst_n(rst_n),.tx(tx[2*487+:487]),.rx(rx[2*487+:487]),.st(st[2*2+:2]),.padding_fault(padding_fault[2]),.pma_tx(pma_tx[2*544+:544]),.pma_tck(pma_tck[2]),.pma_rx(pma_rx[2*544+:544]),.pma_rck(pma_rck[2]));
hfd_serdes487 lk_S3(.clk(clk[3]),.rst_n(rst_n),.tx(tx[3*487+:487]),.rx(rx[3*487+:487]),.st(st[3*2+:2]),.padding_fault(padding_fault[3]),.pma_tx(pma_tx[3*544+:544]),.pma_tck(pma_tck[3]),.pma_rx(pma_rx[3*544+:544]),.pma_rck(pma_rck[3]));
hfd_serdes487 lk_S4(.clk(clk[4]),.rst_n(rst_n),.tx(tx[4*487+:487]),.rx(rx[4*487+:487]),.st(st[4*2+:2]),.padding_fault(padding_fault[4]),.pma_tx(pma_tx[4*544+:544]),.pma_tck(pma_tck[4]),.pma_rx(pma_rx[4*544+:544]),.pma_rck(pma_rck[4]));
hfd_serdes487 lk_N0(.clk(clk[5]),.rst_n(rst_n),.tx(tx[5*487+:487]),.rx(rx[5*487+:487]),.st(st[5*2+:2]),.padding_fault(padding_fault[5]),.pma_tx(pma_tx[5*544+:544]),.pma_tck(pma_tck[5]),.pma_rx(pma_rx[5*544+:544]),.pma_rck(pma_rck[5]));
hfd_serdes487 lk_N1(.clk(clk[6]),.rst_n(rst_n),.tx(tx[6*487+:487]),.rx(rx[6*487+:487]),.st(st[6*2+:2]),.padding_fault(padding_fault[6]),.pma_tx(pma_tx[6*544+:544]),.pma_tck(pma_tck[6]),.pma_rx(pma_rx[6*544+:544]),.pma_rck(pma_rck[6]));
hfd_serdes487 lk_N2(.clk(clk[7]),.rst_n(rst_n),.tx(tx[7*487+:487]),.rx(rx[7*487+:487]),.st(st[7*2+:2]),.padding_fault(padding_fault[7]),.pma_tx(pma_tx[7*544+:544]),.pma_tck(pma_tck[7]),.pma_rx(pma_rx[7*544+:544]),.pma_rck(pma_rck[7]));
hfd_serdes487 lk_N3(.clk(clk[8]),.rst_n(rst_n),.tx(tx[8*487+:487]),.rx(rx[8*487+:487]),.st(st[8*2+:2]),.padding_fault(padding_fault[8]),.pma_tx(pma_tx[8*544+:544]),.pma_tck(pma_tck[8]),.pma_rx(pma_rx[8*544+:544]),.pma_rck(pma_rck[8]));
endmodule
