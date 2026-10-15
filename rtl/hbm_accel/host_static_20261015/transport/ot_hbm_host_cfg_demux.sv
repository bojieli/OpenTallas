`timescale 1ns/1ps
`default_nettype none
// Explicit host installation address map. QDQ F20/F24/F28/F2c/F30;
// SU serial F34/F38/F3c/F40/F44; SU stream E34/E38/E3c/E40/E44,
// rewritten to the existing local Fxx ABI. No on-chip execution dispatch.
module ot_hbm_host_cfg_demux(
 input wire clk,rst_n,
 input wire[11:0]s_awaddr,input wire s_awvalid,output wire s_awready,
 input wire[31:0]s_wdata,input wire[3:0]s_wstrb,input wire s_wvalid,output wire s_wready,
 output reg[1:0]s_bresp,output reg s_bvalid,input wire s_bready,
 input wire[11:0]s_araddr,input wire s_arvalid,output wire s_arready,
 output reg[31:0]s_rdata,output reg[1:0]s_rresp,output reg s_rvalid,input wire s_rready,
 output reg[2:0][11:0]m_awaddr,output reg[2:0]m_awvalid,input wire[2:0]m_awready,
 output reg[2:0][31:0]m_wdata,output reg[2:0][3:0]m_wstrb,output reg[2:0]m_wvalid,input wire[2:0]m_wready,
 input wire[2:0][1:0]m_bresp,input wire[2:0]m_bvalid,output wire[2:0]m_bready,
 output reg[2:0][11:0]m_araddr,output reg[2:0]m_arvalid,input wire[2:0]m_arready,
 input wire[2:0][31:0]m_rdata,input wire[2:0][1:0]m_rresp,input wire[2:0]m_rvalid,output wire[2:0]m_rready,
 output reg fault);
 function automatic[1:0]route(input[11:0]a);
 begin case(a)
  12'hf20,12'hf24,12'hf28,12'hf2c,12'hf30:route=0;
  12'hf34,12'hf38,12'hf3c,12'hf40,12'hf44:route=1;
  12'he34,12'he38,12'he3c,12'he40,12'he44:route=2;
  default:route=3;
 endcase end endfunction
 reg ah,wh,rh,wb,rb;reg[11:0]aa,ra;reg[31:0]wd;reg[3:0]ws;reg[1:0]wt,rt;
 assign s_awready=rst_n&&!ah&&!wb&&!s_bvalid;
 assign s_wready=rst_n&&!wh&&!wb&&!s_bvalid;
 assign s_arready=rst_n&&!rh&&!rb&&!s_rvalid;
 assign m_bready=wb&&!s_bvalid ? (3'b001<<wt):3'b0;
 assign m_rready=rb&&!s_rvalid ? (3'b001<<rt):3'b0;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin ah<=0;wh<=0;rh<=0;wb<=0;rb<=0;wt<=0;rt<=0;
  m_awvalid<=0;m_wvalid<=0;m_arvalid<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;fault<=0;
 end else begin
  if(s_awvalid&&s_awready)begin ah<=1;aa<=s_awaddr;end
  if(s_wvalid&&s_wready)begin wh<=1;wd<=s_wdata;ws<=s_wstrb;end
  if(s_arvalid&&s_arready)begin rh<=1;ra<=s_araddr;end
  if(s_bvalid&&s_bready)s_bvalid<=0;
  if(s_rvalid&&s_rready)s_rvalid<=0;
  for(integer t=0;t<3;t=t+1)begin
   if(m_awvalid[t]&&m_awready[t])m_awvalid[t]<=0;
   if(m_wvalid[t]&&m_wready[t])m_wvalid[t]<=0;
   if(m_arvalid[t]&&m_arready[t])m_arvalid[t]<=0;
  end
  if(ah&&wh&&!wb&&!s_bvalid)begin
   ah<=0;wh<=0;wt<=route(aa);
   if(route(aa)==3)begin s_bvalid<=1;s_bresp<=2;fault<=1;end
   else begin
    wb<=1;m_awvalid[route(aa)]<=1;m_wvalid[route(aa)]<=1;
    m_awaddr[route(aa)]<={4'hf,aa[7:0]};m_wdata[route(aa)]<=wd;m_wstrb[route(aa)]<=ws;
   end
  end
  if(rh&&!rb&&!s_rvalid)begin
   rh<=0;rt<=route(ra);
   if(route(ra)==3)begin s_rvalid<=1;s_rresp<=2;s_rdata<=32'hffffffff;fault<=1;end
   else begin rb<=1;m_arvalid[route(ra)]<=1;m_araddr[route(ra)]<={4'hf,ra[7:0]};end
  end
  if(wb&&m_bvalid[wt]&&m_bready[wt])begin
   wb<=0;s_bvalid<=1;s_bresp<=m_bresp[wt];if(m_bresp[wt]>=2)fault<=1;
  end
  if(rb&&m_rvalid[rt]&&m_rready[rt])begin
   rb<=0;s_rvalid<=1;s_rdata<=m_rdata[rt];s_rresp<=m_rresp[rt];if(m_rresp[rt]>=2)fault<=1;
  end
 end end
endmodule
`default_nettype wire
