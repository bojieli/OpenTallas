`timescale 1ns/1ps
// Board HOST payload ABI v1. See docs/QWEN_TP8_HOST_TRANSPORT.md.
// One outstanding transaction per AXI channel. Every link input is captured,
// every AXI/link output is registered. Link flow control is credits (RX_DEPTH
// initially), not ready/valid; ignored credits latch fault and stop issuance.
module qkd_host_axi_packet_rc #(parameter integer RX_DEPTH=4, TX_CRED=4, MUT=0, ENABLE_RETAINED_COMMIT=0, RC_MUT=0)(
 input wire ck,rst_n,
 input wire raw_por_n,warm_rst_n,pll_locked_i,health_bad_i,health_armed_i,
 input wire execution_restart_i,role_fault_i,retained_bad_i,
 output wire retained_bad_o,retained_owned_o,
 input wire rx_v,input wire[511:0] rx_d,output reg rx_cr,
 output reg tx_v,output reg[511:0] tx_d,input wire tx_cr,
 output reg fault,
 output reg s_awvalid,input wire s_awready,output reg[12:0] s_awaddr,
 output reg s_wvalid,input wire s_wready,output reg[31:0] s_wdata,output reg[3:0] s_wstrb,
 input wire s_bvalid,output reg s_bready,input wire[1:0] s_bresp,
 output reg s_arvalid,input wire s_arready,output reg[12:0] s_araddr,
 input wire s_rvalid,output reg s_rready,input wire[31:0] s_rdata,input wire[1:0] s_rresp,
 input wire m_arvalid,output reg m_arready,input wire[63:0] m_araddr,
 output reg m_rvalid,input wire m_rready,output reg[63:0] m_rdata,output reg[1:0] m_rresp,output reg m_rlast,
 input wire m_awvalid,output reg m_awready,input wire[63:0] m_awaddr,
 input wire m_wvalid,output reg m_wready,input wire[63:0] m_wdata,input wire[7:0] m_wstrb,
 output reg m_bvalid,input wire m_bready,output reg[1:0] m_bresp
);

 wire island_rst_n=ENABLE_RETAINED_COMMIT ? raw_por_n : rst_n;
 reg bad_q,ever_armed_q;
 reg csr_error_pending;reg[15:0] csr_error_id;reg[7:0] csr_error_op;
 wire retained_owned = bw||br||dr||dw||ba||bd||ar_pending||m_rvalid||m_bvalid||
                       s_awvalid||s_wvalid||s_arvalid||s_bready||s_rready||
                       count!=0||rv||tx_v||credits!=TX_CRED||csr_error_pending;
 wire lifecycle=ever_armed_q||retained_owned;
 wire bad_next=bad_q||fault||health_bad_i||retained_bad_i||
     (lifecycle&&(!warm_rst_n||!pll_locked_i||execution_restart_i||role_fault_i))||
     (rv&&count==(PA+1)'(RX_DEPTH))||(tc&&credits==TX_CRED);
 wire admission_ok=health_armed_i&&!bad_next;
 assign retained_bad_o=ENABLE_RETAINED_COMMIT&&bad_next;
 assign retained_owned_o=retained_owned;
 always @(posedge ck or negedge island_rst_n)begin
  if(!island_rst_n)begin bad_q<=0;ever_armed_q<=0;end
  else if(ENABLE_RETAINED_COMMIT)begin
   bad_q<=bad_next;if(health_armed_i)ever_armed_q<=1;
  end
 end
 // All inter-child input pins capture before control/enable logic.
 reg s_awready_q;
 reg s_wready_q;
 reg s_bvalid_q;
 reg[1:0]s_bresp_q;
 reg s_arready_q;
 reg s_rvalid_q;
 reg[31:0]s_rdata_q;
 reg[1:0]s_rresp_q;
 reg m_arvalid_q;
 reg[63:0]m_araddr_q;
 reg m_rready_q;
 reg m_awvalid_q;
 reg[63:0]m_awaddr_q;
 reg m_wvalid_q;
 reg[63:0]m_wdata_q;
 reg[7:0]m_wstrb_q;
 reg m_bready_q;
 always @(posedge ck)begin
  s_bresp_q<=s_bresp;
  s_rdata_q<=s_rdata;
  s_rresp_q<=s_rresp;
  m_araddr_q<=m_araddr;
  m_awaddr_q<=m_awaddr;
  m_wdata_q<=m_wdata;
  m_wstrb_q<=m_wstrb;
 end
 always @(posedge ck or negedge island_rst_n)begin
  if(!island_rst_n)begin s_awready_q<=0;s_wready_q<=0;s_bvalid_q<=0;s_arready_q<=0;s_rvalid_q<=0;m_arvalid_q<=0;m_rready_q<=0;m_awvalid_q<=0;m_wvalid_q<=0;m_bready_q<=0; end
  else begin s_awready_q<=s_awready;s_wready_q<=s_wready;s_bvalid_q<=s_bvalid;s_arready_q<=s_arready;s_rvalid_q<=s_rvalid;m_arvalid_q<=m_arvalid;m_rready_q<=m_rready;m_awvalid_q<=m_awvalid;m_wvalid_q<=m_wvalid;m_bready_q<=m_bready; end
 end
 localparam integer PA=$clog2(RX_DEPTH);
 reg rv;reg[511:0] rd;reg tc;
 reg[511:0] q[0:RX_DEPTH-1];reg[PA-1:0] wp,rp;reg[PA:0] count;
 reg[7:0] credits;
 reg bw,br,dr,dw;
 reg ba,bd;reg[63:0] dma_addr,dma_data;reg[7:0] dma_strb;
 reg[15:0] wid,rid; // echoed BAR transaction identifiers
 wire[511:0] h=q[rp];wire[7:0] op=h[7:0];
 wire valid_header=h[15:8]==8'd1 && h[511:160]==0;
 wire idle_write=!bw&&!s_awvalid&&!s_wvalid&&!s_bready;
 wire idle_read=!br&&!s_arvalid&&!s_rready;
 wire original_consume=count!=0&&!fault&&(
  !valid_header || (op==8'h01&&idle_write) || (op==8'h02&&idle_read) ||
  (op==8'h13&&!m_rvalid) || (op==8'h15&&!m_bvalid) ||
  (op!=8'h01&&op!=8'h02&&op!=8'h13&&op!=8'h15));
 // Drain predicates retain the exact header, outstanding and reserved-bit checks.
 wire accept_R=count!=0&&valid_header&&op==8'h13&&dr&&!m_rvalid&&
               h[31:16]==0&&h[95:35]==0;
 wire accept_B=count!=0&&valid_header&&op==8'h15&&dw&&!m_bvalid&&
               h[31:16]==0&&h[159:34]==0;
 wire csr_queued=(op==8'h01||op==8'h02);
 wire retained_consume=count!=0&&(
   !valid_header ||
   (csr_queued&&((admission_ok&&((op==8'h01&&idle_write)||(op==8'h02&&idle_read)))||
                (!admission_ok&&!csr_error_pending)))||
   accept_R||accept_B||
   (op==8'h13&&!m_rvalid)||(op==8'h15&&!m_bvalid)||
   (!csr_queued&&op!=8'h13&&op!=8'h15));
 wire consume=ENABLE_RETAINED_COMMIT ? retained_consume : original_consume;
 wire emit=credits!=0&&!tx_v&&
   ((!ENABLE_RETAINED_COMMIT||RC_MUT==1)?!fault:1'b1);
 // AXI ready outputs are pulses paired with the capture edge; a pending pulse
 // inhibits another capture while the producer observes it.
 wire capture_ar=!dr&&!m_arready&&m_arvalid_q;
 wire capture_aw=!dw&&!ba&&!m_awready&&m_awvalid_q;
 wire capture_w=!dw&&!bd&&!m_wready&&m_wvalid_q;
 reg ar_pending;reg[63:0] read_addr;
 always @(posedge ck)begin rd<=rx_d; if(rv&&count<(PA+1)'(RX_DEPTH))q[wp]<=rd;end
 always @(posedge ck or negedge island_rst_n)begin
  if(!island_rst_n)begin
   rv<=0;tc<=0;wp<=0;rp<=0;count<=0;credits<=TX_CRED;fault<=0;csr_error_pending<=0;csr_error_id<=0;csr_error_op<=0;rx_cr<=0;tx_v<=0;tx_d<=0;
   s_awvalid<=0;s_wvalid<=0;s_arvalid<=0;s_bready<=0;s_rready<=0;
   s_awaddr<=0;s_wdata<=0;s_wstrb<=0;s_araddr<=0;
   m_arready<=0;m_awready<=0;m_wready<=0;m_rvalid<=0;m_bvalid<=0;
   m_rdata<=0;m_rresp<=0;m_rlast<=0;m_bresp<=0;
   bw<=0;br<=0;dr<=0;dw<=0;ba<=0;bd<=0;ar_pending<=0;wid<=0;rid<=0;
   dma_addr<=0;dma_data<=0;dma_strb<=0;read_addr<=0;
  end else begin
   rv<=rx_v;tc<=tx_cr;rx_cr<=consume;tx_v<=0;
   // Negative control only: retracting an existing offer is forbidden.
   if(ENABLE_RETAINED_COMMIT&&RC_MUT==4&&bad_next)begin s_awvalid<=0;s_wvalid<=0;s_arvalid<=0;end
   m_arready<=0;m_awready<=0;m_wready<=0;s_bready<=0;s_rready<=0;
   if(s_awvalid&&s_awready_q)s_awvalid<=0;
   if(s_wvalid&&s_wready_q)s_wvalid<=0;
   if(s_arvalid&&s_arready_q)s_arvalid<=0;
   if(m_rvalid&&m_rready_q)begin m_rvalid<=0;dr<=0;end
   if(m_bvalid&&m_bready_q)begin m_bvalid<=0;dw<=0;end
   if(rv&&(!fault||ENABLE_RETAINED_COMMIT))begin
    if(count==(PA+1)'(RX_DEPTH))fault<=1;
    else wp<=wp+1'b1;
   end
   if(consume)rp<=rp+1'b1;
   case({rv&&(!fault||ENABLE_RETAINED_COMMIT)&&count<(PA+1)'(RX_DEPTH),consume})
    2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;
   endcase
   if(tc)begin if(credits==TX_CRED)fault<=1;else credits<=credits+1'b1;end
   if(capture_ar&&(!fault||ENABLE_RETAINED_COMMIT))begin dr<=1;ar_pending<=1;read_addr<=m_araddr_q;m_arready<=1;end
   if(capture_aw&&(!fault||ENABLE_RETAINED_COMMIT))begin ba<=1;dma_addr<=m_awaddr_q;m_awready<=1;end
   if(capture_w&&(!fault||ENABLE_RETAINED_COMMIT))begin bd<=1;dma_data<=m_wdata_q;dma_strb<=m_wstrb_q;m_wready<=1;end
   if(consume)begin
    if(!valid_header)fault<=1;
    else case(op)
     8'h01:begin
      if(h[95:45]!=0||h[159:132]!=0)fault<=1;
      else if(ENABLE_RETAINED_COMMIT&&!admission_ok&&RC_MUT!=3)begin
       csr_error_pending<=1;csr_error_id<=(RC_MUT==2)?16'd0:h[31:16];csr_error_op<=8'h81;
      end else begin bw<=1;wid<=h[31:16];s_awvalid<=1;s_awaddr<=h[44:32];
       s_wvalid<=1;s_wdata<=h[127:96];s_wstrb<=h[131:128];end
     end
     8'h02:begin
      if(h[159:45]!=0)fault<=1;
      else if(ENABLE_RETAINED_COMMIT&&!admission_ok&&RC_MUT!=3)begin
       csr_error_pending<=1;csr_error_id<=(RC_MUT==2)?16'd0:h[31:16];csr_error_op<=8'h82;
      end else begin br<=1;rid<=h[31:16];s_arvalid<=1;s_araddr<=h[44:32];end
     end
     8'h13:begin
      if(!dr||h[31:16]!=0||h[95:35]!=0)fault<=1;
      else begin m_rvalid<=1;m_rdata<=(MUT==1)?h[159:96]^64'd1:h[159:96];m_rresp<=h[33:32];m_rlast<=h[34];
       if(!h[34])fault<=1;end
     end
     8'h15:begin
      if(!dw||h[31:16]!=0||h[159:34]!=0)fault<=1;
      else begin m_bvalid<=1;m_bresp<=h[33:32];end
     end
     default:fault<=1;
    endcase
   end
   if(emit)begin
    // Fixed priority responses then reads then writes; single-beat DMA limits
    // each source to one outstanding item, so a response cannot starve DMA.
    if(bw&&!s_awvalid&&!s_wvalid&&s_bvalid_q&&!s_bready)begin
     tx_v<=1;tx_d<={480'd0,wid,8'd1,8'h81}|(512'(s_bresp_q)<<32);s_bready<=1;bw<=0;
     credits<=credits+8'(tc)-1'b1;
    end else if(br&&!s_arvalid&&s_rvalid_q&&!s_rready)begin
     tx_v<=1;tx_d<={480'd0,rid,8'd1,8'h82}|(512'(s_rresp_q)<<32)|(512'(s_rdata_q)<<96);s_rready<=1;br<=0;
     credits<=credits+8'(tc)-1'b1;
    end else if(ar_pending)begin
     tx_v<=1;tx_d<=512'h0112|(512'(read_addr)<<32);ar_pending<=0;credits<=credits+8'(tc)-1'b1;
    end else if(ba&&bd&&!dw)begin
     tx_v<=1;tx_d<=512'h0114|(512'(dma_addr)<<32)|(512'(dma_data)<<96)|(512'(dma_strb)<<160);
     ba<=0;bd<=0;dw<=1;credits<=credits+8'(tc)-1'b1;
    end else if(ENABLE_RETAINED_COMMIT&&csr_error_pending)begin
     tx_v<=1;tx_d<={480'd0,csr_error_id,8'd1,csr_error_op}|(512'(2'b10)<<32);
     csr_error_pending<=0;credits<=credits+8'(tc)-1'b1;
    end
   end
  end
 end
endmodule
