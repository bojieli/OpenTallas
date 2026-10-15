`timescale 1ns/1ps
// Static 6-core-edge : 5-FDI-edge transport. Six {valid,597b CRCframe}
// slots =3588 bits occupy FOUR1043-bit FDI beats; beat4 is reserved idle.
// Core/FDI roots are1.2GHz/1.0GHz from a common PLL; first post-reset FDI
// edge must be within one core period of first core edge. No async PLL claim.
// Reset establishes the immutable block calendar. Every phase/address advances
// unconditionally. Missing/extra PHY validity faults without rescheduling.
// TX starts FDIedge5, physical latency4FDIedges, RXcapture starts FDIedge10.
// Core outputs block0 on coreedges24..29, then every6edges (constant24core
// transport edges). Three RXbanks protect the whole block through its last use.
// Storage is explicit kept flop banks; no behavioural SRAM or handshake FIFO.
module qfd_ucie_six_five #(parameter integer MUT=0)(
 input wire core_ck,fdi_ck,rst_n,input wire[2:0]fdi_rx_ck,
 input wire tx_valid,input wire[596:0]tx_frame,
 output reg phy_tx_valid,output reg[1042:0]phy_tx_frame,
 input wire phy_rx_valid,input wire[1042:0]phy_rx_frame,
 output reg rx_valid,output reg[596:0]rx_frame,
 output reg core_fault,output reg fdi_fault
);
 reg[2:0]cp,rp,tp,fp;reg cb,tb;reg[1:0]rb,fb;
 reg[4:0]core_warm;reg[3:0]fdi_warm;
 wire tx_go=fdi_warm>=5,rx_go=fdi_warm>=10,core_go=core_warm==24;
 wire[3587:0]txbank[0:1]; // exact3588bits
 wire[3587:0]rxbank[0:2];
 wire[597:0]core_word={tx_valid,tx_frame};
 for(genvar b=0;b<2;b=b+1)begin:g_tx
   (* keep *)reg[3587:0]bits;
   always @(posedge core_ck)if(cb==b)bits[cp*598+:598]<=core_word;
   assign txbank[b]=bits;
 end
 for(genvar b=0;b<3;b=b+1)begin:g_rx
   (* keep *)reg[3587:0]bits;
   always @(posedge fdi_rx_ck[b])if(rx_go && fb==b)case(fp)
     0:bits[0+:1043]<=phy_rx_frame;
     1:bits[1043+:1043]<=phy_rx_frame;
     2:bits[2086+:1043]<=phy_rx_frame;
     3:bits[3129+:459]<=phy_rx_frame[458:0];
     default:begin end
   endcase
   assign rxbank[b]=bits;
 end
 wire[3587:0]tx_bits=txbank[tb];
 wire[1:0]read_bank=(MUT==2)?(rb==2?0:rb+1'b1):rb;
 wire[597:0]read_word=rxbank[read_bank][rp*598+:598];
 always @(posedge core_ck or negedge rst_n)begin
  if(!rst_n)begin cp<=0;cb<=0;rp<=0;rb<=0;core_warm<=0;rx_valid<=0;core_fault<=0;end
  else begin
   if(cp==5)begin cp<=0;cb<=~cb;end else cp<=cp+1'b1;
   if(core_warm<24)core_warm<=core_warm+1'b1;
   rx_valid<=0;
   if(core_go)begin
    {rx_valid,rx_frame}<=read_word;
    if(rp==5)begin rp<=0;rb<=rb==2?0:rb+1'b1;end else rp<=rp+1'b1;
   end
   if(cp>5 || rp>5 || rb>2)core_fault<=1;
  end
 end
 always @(posedge fdi_ck or negedge rst_n)begin
  if(!rst_n)begin tp<=0;tb<=0;fp<=0;fb<=0;fdi_warm<=0;phy_tx_valid<=0;fdi_fault<=0;end
  else begin
   if(fdi_warm<10)fdi_warm<=fdi_warm+1'b1;
   phy_tx_valid<=tx_go && tp<4;
   if(tx_go)begin
    case(tp)
     0:phy_tx_frame<=tx_bits[0+:1043];
     1:phy_tx_frame<=tx_bits[1043+:1043];
     2:phy_tx_frame<=tx_bits[2086+:1043];
     3:phy_tx_frame<={(MUT==1),583'b0,tx_bits[3129+:459]};
     default:phy_tx_frame<=0;
    endcase
    if(tp==4)begin tp<=0;tb<=~tb;end else tp<=tp+1'b1;
   end
   if(phy_rx_valid!==(rx_go && fp<4))fdi_fault<=1;
   if(rx_go)begin
    if(fp==3 && |phy_rx_frame[1042:459])fdi_fault<=1;
    if(fp==4)begin fp<=0;fb<=fb==2?0:fb+1'b1;end else fp<=fp+1'b1;
   end
   if(tp>4 || fp>4 || fb>2)fdi_fault<=1;
  end
 end
endmodule
