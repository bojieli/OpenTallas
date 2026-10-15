`timescale 1ns/1ps
module tb_hbm_host_packet;
parameter integer MUT=0,FACE=1;
reg clk=0,rst_n=0,rx_valid=0,tx_ready=0;reg [511:0]rx_packet=0;wire rx_ready,tx_valid,protocol_fault;wire[511:0]tx_packet;
integer checks=0,errors=0,k,waits;reg[511:0] saved;
wire  s_awvalid;
reg  s_awready=0;
wire [11:0] s_awaddr;
wire  s_wvalid;
reg  s_wready=0;
wire [31:0] s_wdata;
wire [3:0] s_wstrb;
reg  s_bvalid=0;
wire  s_bready;
wire  s_arvalid;
reg  s_arready=0;
wire [11:0] s_araddr;
reg  s_rvalid=0;
wire  s_rready;
reg [31:0] s_rdata=0;
reg  h_awvalid=0;
wire  h_awready;
reg [11:0] h_awaddr=0;
reg  h_wvalid=0;
wire  h_wready;
reg [31:0] h_wdata=0;
reg [3:0] h_wstrb=0;
wire  h_bvalid;
reg  h_bready=0;
reg  h_arvalid=0;
wire  h_arready;
reg [11:0] h_araddr=0;
wire  h_rvalid;
reg  h_rready=0;
wire [31:0] h_rdata;
wire  h_dma_arvalid;
reg  h_dma_arready=0;
wire [63:0] h_dma_araddr;
reg  h_dma_rvalid=0;
wire  h_dma_rready;
reg [63:0] h_dma_rdata=0;
reg [1:0] h_dma_rresp=0;
reg  h_dma_rlast=0;
wire  h_dma_awvalid;
reg  h_dma_awready=0;
wire [63:0] h_dma_awaddr;
wire  h_dma_wvalid;
reg  h_dma_wready=0;
wire [63:0] h_dma_wdata;
wire [7:0] h_dma_wstrb;
reg  h_dma_bvalid=0;
wire  h_dma_bready;
reg [1:0] h_dma_bresp=0;
reg  m_arvalid=0;
wire  m_arready;
reg [63:0] m_araddr=0;
reg [7:0] m_arlen=0;
reg [2:0] m_arsize=3;
wire  m_rvalid;
reg  m_rready=0;
wire [63:0] m_rdata;
wire [1:0] m_rresp;
wire  m_rlast;
reg  m_awvalid=0;
wire  m_awready;
reg [63:0] m_awaddr=0;
reg [7:0] m_awlen=0;
reg [2:0] m_awsize=3;
reg  m_wvalid=0;
wire  m_wready;
reg [63:0] m_wdata=0;
reg [7:0] m_wstrb=0;
reg  m_wlast=1;
wire  m_bvalid;
reg  m_bready=0;
wire [1:0] m_bresp;
reg  irq=0;
reg  fault=0;
generate if(FACE)begin:g_face
tri[786:0]h;
assign s_awvalid=h[406];
assign h[0]=s_awready;
assign s_awaddr=h[418:407];
assign s_wvalid=h[419];
assign h[1]=s_wready;
assign s_wdata=h[451:420];
assign s_wstrb=h[455:452];
assign h[2]=s_bvalid;
assign s_bready=h[456];
assign s_arvalid=h[457];
assign h[3]=s_arready;
assign s_araddr=h[469:458];
assign h[4]=s_rvalid;
assign s_rready=h[470];
assign h[36:5]=s_rdata;
assign h[37]=h_awvalid;
assign h_awready=h[471];
assign h[49:38]=h_awaddr;
assign h[50]=h_wvalid;
assign h_wready=h[472];
assign h[82:51]=h_wdata;
assign h[86:83]=h_wstrb;
assign h_bvalid=h[473];
assign h[87]=h_bready;
assign h[88]=h_arvalid;
assign h_arready=h[474];
assign h[100:89]=h_araddr;
assign h_rvalid=h[475];
assign h[101]=h_rready;
assign h_rdata=h[507:476];
assign h_dma_arvalid=h[508];
assign h[102]=h_dma_arready;
assign h_dma_araddr=h[572:509];
assign h[103]=h_dma_rvalid;
assign h_dma_rready=h[573];
assign h[167:104]=h_dma_rdata;
assign h[169:168]=h_dma_rresp;
assign h[170]=h_dma_rlast;
assign h_dma_awvalid=h[574];
assign h[171]=h_dma_awready;
assign h_dma_awaddr=h[638:575];
assign h_dma_wvalid=h[639];
assign h[172]=h_dma_wready;
assign h_dma_wdata=h[703:640];
assign h_dma_wstrb=h[711:704];
assign h[173]=h_dma_bvalid;
assign h_dma_bready=h[712];
assign h[175:174]=h_dma_bresp;
assign h[176]=m_arvalid;
assign m_arready=h[713];
assign h[240:177]=m_araddr;
assign h[248:241]=m_arlen;
assign h[251:249]=m_arsize;
assign m_rvalid=h[714];
assign h[252]=m_rready;
assign m_rdata=h[778:715];
assign m_rresp=h[780:779];
assign m_rlast=h[781];
assign h[253]=m_awvalid;
assign m_awready=h[782];
assign h[317:254]=m_awaddr;
assign h[325:318]=m_awlen;
assign h[328:326]=m_awsize;
assign h[329]=m_wvalid;
assign m_wready=h[783];
assign h[393:330]=m_wdata;
assign h[401:394]=m_wstrb;
assign h[402]=m_wlast;
assign m_bvalid=h[784];
assign h[403]=m_bready;
assign m_bresp=h[786:785];
assign h[404]=irq;
assign h[405]=fault;
hfd_host_packet_face #(.MUT(MUT==1?1:0))dut(.clk(clk),.rst_n(rst_n),.h(h),.rx_valid(rx_valid),.rx_packet(rx_packet),.rx_ready(rx_ready),.tx_valid(tx_valid),.tx_packet(tx_packet),.tx_ready(tx_ready),.protocol_fault(protocol_fault));
end else begin:g_direct
ot_hbm_host_packet #(.MUT(MUT==1?1:0)) dut(.clk(clk),.rst_n(rst_n),.rx_valid(rx_valid),.rx_packet(rx_packet),.rx_ready(rx_ready),.tx_valid(tx_valid),.tx_packet(tx_packet),.tx_ready(tx_ready),.protocol_fault(protocol_fault),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.h_awvalid(h_awvalid),.h_awready(h_awready),.h_awaddr(h_awaddr),.h_wvalid(h_wvalid),.h_wready(h_wready),.h_wdata(h_wdata),.h_wstrb(h_wstrb),.h_bvalid(h_bvalid),.h_bready(h_bready),.h_arvalid(h_arvalid),.h_arready(h_arready),.h_araddr(h_araddr),.h_rvalid(h_rvalid),.h_rready(h_rready),.h_rdata(h_rdata),.h_dma_arvalid(h_dma_arvalid),.h_dma_arready(h_dma_arready),.h_dma_araddr(h_dma_araddr),.h_dma_rvalid(h_dma_rvalid),.h_dma_rready(h_dma_rready),.h_dma_rdata(h_dma_rdata),.h_dma_rresp(h_dma_rresp),.h_dma_rlast(h_dma_rlast),.h_dma_awvalid(h_dma_awvalid),.h_dma_awready(h_dma_awready),.h_dma_awaddr(h_dma_awaddr),.h_dma_wvalid(h_dma_wvalid),.h_dma_wready(h_dma_wready),.h_dma_wdata(h_dma_wdata),.h_dma_wstrb(h_dma_wstrb),.h_dma_bvalid(h_dma_bvalid),.h_dma_bready(h_dma_bready),.h_dma_bresp(h_dma_bresp),.m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),.m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),.irq(irq),.fault(fault));
end endgenerate
 task tick;begin #5;clk=1;#1;#4;clk=0;end endtask
 task check(input bit okay,input [255:0] label);begin checks=checks+1;if(!okay)begin errors=errors+1;$display("BAD %s iteration%0d",label,k);end end endtask
 function automatic[511:0] pkt(input[7:0]op,input[15:0]id,input[63:0]addr,input[63:0]data,input[7:0]strb);
 begin pkt={341'd0,1'b1,2'd0,strb,data,addr,id,8'd1,op};end endfunction
 task send(input[511:0]p);begin
 rx_packet=p;waits=0;while(!rx_ready&&waits<20)begin tick;waits=waits+1;end
 check(rx_ready,"RX admission");rx_valid=1;tick;rx_valid=0;
 end endtask
 task take(input[7:0]op,input[15:0]id,input[63:0]addr,input[63:0]data,input[7:0]strb);begin
 waits=0;while(!tx_valid&&waits<30)begin tick;waits=waits+1;end
 check(tx_valid,"TX completion");saved=tx_packet;
 check(saved[7:0]===op && saved[31:16]===id && saved[95:32]===addr && saved[159:96]===data && saved[167:160]===strb,"TX exact fields");
 repeat(2)begin tick;check(tx_valid && tx_packet===saved,"TX held while external stalls");end
 tx_ready=1;tick;tx_ready=0;
 end endtask
 initial begin
 repeat(4)tick;rst_n=1;repeat(3)tick;
 for(k=0;k<32;k=k+1)begin
 // Host BAR write: independently accepted AW and W, then completion.
 send(pkt(8'h01,16'(k),64'h104,64'(32'h12340000+k),8'hf));
 check(s_awvalid && s_wvalid && s_awaddr==12'h104 && s_wdata===32'h12340000+32'(k) && s_wstrb==4'hf,"BAR write pins");
 repeat(2)tick;s_awready=1;tick;s_awready=0;tick;s_wready=1;tick;s_wready=0;
 s_bvalid=1;tick;s_bvalid=0;take(8'h81,16'(k),0,0,0);
 // Host BAR read.
 send(pkt(8'h02,16'(k+64),64'h208,0,0));s_arready=1;tick;s_arready=0;s_rdata=32'h70000000+k;s_rvalid=1;tick;s_rvalid=0;
 take(8'h82,16'(k+64),0,64'(32'h70000000+k),0);
 // Host DMA reads/writes the loader's HBM aperture.
 send(pkt(8'h03,16'(k+128),64'h120000000+k*8,0,0));check(h_dma_arvalid && h_dma_araddr==64'h120000000+k*8,"HBM DMA read address");
 h_dma_arready=1;tick;h_dma_arready=0;h_dma_rvalid=1;h_dma_rdata=64'habc0000000000000+k;h_dma_rresp=0;h_dma_rlast=1;tick;h_dma_rvalid=0;
 take(8'h83,16'(k+128),0,64'habc0000000000000+k,0);
 send(pkt(8'h04,16'(k+192),64'h230000000+k*8,64'hdef0000000000000+k,8'hf7));
 check(h_dma_awvalid&&h_dma_wvalid&&h_dma_awaddr==64'h230000000+k*8&&h_dma_wdata==64'hdef0000000000000+k&&h_dma_wstrb==8'hf7,"HBM DMA write pins");
 h_dma_wready=1;tick;h_dma_wready=0;tick;h_dma_awready=1;tick;h_dma_awready=0;h_dma_bvalid=1;tick;h_dma_bvalid=0;take(8'h84,16'(k+192),0,0,0);
 // Loader accesses external host BAR. Deliberately split AW/W.
 h_awaddr=12'h340;h_awvalid=1;tick;h_awvalid=0;tick;h_wdata=32'hcafe0000+k;h_wstrb=4'hb;h_wvalid=1;tick;h_wvalid=0;
 take(8'h11,0,64'h340,64'(32'hcafe0000+k),8'hb);send(pkt(8'h91,0,0,0,0));check(h_bvalid,"external BAR B returned");h_bready=1;tick;h_bready=0;repeat(2)tick;
 h_araddr=12'h448;h_arvalid=1;tick;h_arvalid=0;take(8'h12,0,64'h448,0,0);send(pkt(8'h92,0,0,64'(32'habcd0000+k),0));
 check(h_rvalid && h_rdata==32'habcd0000+k,"external BAR R returned");h_rready=1;tick;h_rready=0;repeat(2)tick;
 // Loader DMA accesses host memory.
 m_araddr=64'h340000000+k*8;m_arvalid=1;tick;m_arvalid=0;take(8'h13,0,64'h340000000+k*8,0,0);
 send(pkt(8'h93,0,0,64'h1234567800000000+k,0));check(m_rvalid && m_rdata==64'h1234567800000000+k && m_rlast && m_rresp==0,"host DMA R returned");m_rready=1;tick;m_rready=0;repeat(2)tick;
 m_awaddr=64'h450000000+k*8;m_awvalid=1;tick;m_awvalid=0;tick;m_wdata=64'h9876543200000000+k;m_wstrb=8'he7;m_wvalid=1;tick;m_wvalid=0;
 take(8'h14,0,64'h450000000+k*8,64'h9876543200000000+k,8'he7);send(pkt(8'h94,0,0,0,0));check(m_bvalid && m_bresp==0,"host DMA B returned");m_bready=1;tick;m_bready=0;repeat(2)tick;
 check(protocol_fault===1'b0,"known normal protocol flags");
 end
 if(MUT==2)begin send(pkt(8'h01,0,0,0,0)^(512'd3<<8));check(protocol_fault===1'b0,"malformed version mutant rejected");end
 if(errors==0)$display("HBM_HOST_PACKET_PASS checks%0d transactions256 source_exact_ports73 bits787",checks);
 else $display("HBM_HOST_PACKET_FAIL errors%0d checks%0d MUT%0d",errors,checks,MUT);
 $finish;
 end
endmodule
