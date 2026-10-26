`timescale 1ns/1ps
module tb_hbm_host_native;
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

 wire[512:0]pa,pb;wire ca,cb;wire[4:0]local_faults;wire[1:0]local_status,remote_status;wire local_locked;
 hfd_host_native #(.MUT(MUT==1?1:0))dut(.clk_controller(clk),.clk_landing(clk),.clk_ep(clk),.clk_face(clk),.clk_sub({12{clk}}),.clk_tx_shared(clk),.clk_rx_shared(clk),.clk_status_shared(clk),.clk_phy(clk),.rst_n(rst_n),.session(24'h3555),.h(h),.s_bresp(2'd0),.pma_tx(pa),.pma_tck(ca),.pma_rx(pb),.pma_rck(cb),.faults(local_faults),.phy_status(local_status),.ep_locked(local_locked));
 wire [486:0]remote_tx;wire[511:0]remote_rx;wire remote_tcr,remote_rv,remote_fault,remote_locked;wire[544:0]remote_rdata;
 reg[5:0]remote_credit=32;
 always @(posedge clk)if(!rst_n)remote_credit<=32;else remote_credit<=remote_credit+6'(remote_tcr)-6'(rx_valid&&rx_ready);
 assign rx_ready=remote_credit!=0;
 ot_hbm_lk_ep #(.HARD_CLOCKS(1))remote_endpoint(.clk(clk),.clk_sub({12{clk}}),.clk_tx_shared(clk),.clk_rx_shared(clk),.clk_status_shared(clk),.rst_n(rst_n),.session(24'h3555),.t_v(rx_valid&&rx_ready),.t_flit({33'd0,rx_packet}),.t_cr(remote_tcr),.r_v(remote_rv),.r_flit(remote_rdata),.r_cr(tx_ready&&tx_valid),.x_tx(remote_tx),.x_rx(remote_rx[486:0]),.fault(remote_fault),.locked(remote_locked));
 ot_pdie_ucie remote_phy(.clk(clk),.rst(rst_n),.tx({25'd0,remote_tx}),.rx(remote_rx),.st(remote_status),.pma_tx(pb),.pma_tck(cb),.pma_rx(pa),.pma_rck(ca));
 // Declared off-chip host capture queue; no internal chip memory/result model.
 reg[511:0]offchip_packets[0:255];integer ow=0,orp=0,oc=0;
 assign tx_valid=oc!=0;assign tx_packet=offchip_packets[orp];
 always @(posedge clk)begin
 if(!rst_n)begin ow<=0;orp<=0;oc<=0;end
 else begin
 if(remote_rv)begin offchip_packets[ow]<=remote_rdata[511:0];ow<=(ow+1)%256;end
 if(tx_valid&&tx_ready)orp<=(orp+1)%256;
 case({remote_rv,tx_valid&&tx_ready})2'b10:oc<=oc+1;2'b01:oc<=oc-1;default:;endcase
 end end
 assign protocol_fault=(|local_faults)|remote_fault|remote_status[0];
 task tick;begin #5;clk=1;#1;#4;clk=0;end endtask
 task check(input bit okay,input [255:0] label);begin checks=checks+1;if(!okay)begin errors=errors+1;$display("BAD %s iteration%0d",label,k);end end endtask
 function automatic[511:0] pkt(input[7:0]op,input[15:0]id,input[63:0]addr,input[63:0]data,input[7:0]strb);
 begin pkt={341'd0,1'b1,2'd0,strb,data,addr,id,8'd1,op};end endfunction
 function automatic bit event_ready(input integer which);
 case(which)0:event_ready=s_awvalid&&s_wvalid;1:event_ready=s_arvalid;2:event_ready=h_dma_arvalid;3:event_ready=h_dma_awvalid&&h_dma_wvalid;4:event_ready=h_bvalid;5:event_ready=h_rvalid;6:event_ready=m_rvalid;7:event_ready=m_bvalid;default:event_ready=0;endcase endfunction
 task await_event(input integer which);begin waits=0;while(!event_ready(which)&&waits<3000)begin tick;waits=waits+1;end check(event_ready(which),"native event arrival");end endtask
 task send(input[511:0]p);begin
 rx_packet=p;waits=0;while(!rx_ready&&waits<300000)begin tick;waits=waits+1;end
 check(rx_ready,"RX admission");rx_valid=1;tick;rx_valid=0;
 end endtask
 task take(input[7:0]op,input[15:0]id,input[63:0]addr,input[63:0]data,input[7:0]strb);begin
 waits=0;while(!tx_valid&&waits<3000)begin tick;waits=waits+1;end
 check(tx_valid,"TX completion");saved=tx_packet;
 check(saved[7:0]===op && saved[31:16]===id && saved[95:32]===addr && saved[159:96]===data && saved[167:160]===strb,"TX exact fields");
 repeat(2)begin tick;check(tx_valid && tx_packet===saved,"TX held while external stalls");end
 tx_ready=1;tick;tx_ready=0;
 end endtask
 initial begin
 repeat(4)tick;rst_n=1;repeat(300)tick;
 for(k=0;k<8;k=k+1)begin
 // Host BAR write: independently accepted AW and W, then completion.
 send(pkt(8'h01,16'(k),64'h104,64'(32'h12340000+k),8'hf));
 await_event(0);check(s_awvalid && s_wvalid && s_awaddr==12'h104 && s_wdata===32'h12340000+32'(k) && s_wstrb==4'hf,"BAR write pins");
 repeat(2)tick;s_awready=1;tick;s_awready=0;tick;s_wready=1;tick;s_wready=0;
 s_bvalid=1;tick;s_bvalid=0;take(8'h81,16'(k),0,0,0);
 // Host BAR read.
 send(pkt(8'h02,16'(k+64),64'h208,0,0));await_event(1);s_arready=1;tick;s_arready=0;s_rdata=32'h70000000+k;s_rvalid=1;tick;s_rvalid=0;
 take(8'h82,16'(k+64),0,64'(32'h70000000+k),0);
 // Host DMA reads/writes the loader's HBM aperture.
 send(pkt(8'h03,16'(k+128),64'h120000000+k*8,0,0));await_event(2);check(h_dma_arvalid && h_dma_araddr==64'h120000000+k*8,"HBM DMA read address");
 h_dma_arready=1;tick;h_dma_arready=0;h_dma_rvalid=1;h_dma_rdata=64'habc0000000000000+k;h_dma_rresp=0;h_dma_rlast=1;tick;h_dma_rvalid=0;
 take(8'h83,16'(k+128),0,64'habc0000000000000+k,0);
 send(pkt(8'h04,16'(k+192),64'h230000000+k*8,64'hdef0000000000000+k,8'hf7));
 await_event(3);check(h_dma_awvalid&&h_dma_wvalid&&h_dma_awaddr==64'h230000000+k*8&&h_dma_wdata==64'hdef0000000000000+k&&h_dma_wstrb==8'hf7,"HBM DMA write pins");
 h_dma_wready=1;tick;h_dma_wready=0;tick;h_dma_awready=1;tick;h_dma_awready=0;h_dma_bvalid=1;tick;h_dma_bvalid=0;take(8'h84,16'(k+192),0,0,0);
 // Loader accesses external host BAR. Deliberately split AW/W.
 h_awaddr=12'h340;h_awvalid=1;tick;h_awvalid=0;tick;h_wdata=32'hcafe0000+k;h_wstrb=4'hb;h_wvalid=1;tick;h_wvalid=0;
 take(8'h11,0,64'h340,64'(32'hcafe0000+k),8'hb);send(pkt(8'h91,0,0,0,0));await_event(4);check(h_bvalid,"external BAR B returned");h_bready=1;tick;h_bready=0;repeat(2)tick;
 h_araddr=12'h448;h_arvalid=1;tick;h_arvalid=0;take(8'h12,0,64'h448,0,0);send(pkt(8'h92,0,0,64'(32'habcd0000+k),0));
 await_event(5);check(h_rvalid && h_rdata==32'habcd0000+k,"external BAR R returned");h_rready=1;tick;h_rready=0;repeat(2)tick;
 // Loader DMA accesses host memory.
 m_araddr=64'h340000000+k*8;m_arvalid=1;tick;m_arvalid=0;take(8'h13,0,64'h340000000+k*8,0,0);
 send(pkt(8'h93,0,0,64'h1234567800000000+k,0));await_event(6);check(m_rvalid && m_rdata==64'h1234567800000000+k && m_rlast && m_rresp==0,"host DMA R returned");m_rready=1;tick;m_rready=0;repeat(2)tick;
 m_awaddr=64'h450000000+k*8;m_awvalid=1;tick;m_awvalid=0;tick;m_wdata=64'h9876543200000000+k;m_wstrb=8'he7;m_wvalid=1;tick;m_wvalid=0;
 take(8'h14,0,64'h450000000+k*8,64'h9876543200000000+k,8'he7);send(pkt(8'h94,0,0,0,0));await_event(7);check(m_bvalid && m_bresp==0,"host DMA B returned");m_bready=1;tick;m_bready=0;repeat(2)tick;
 check(protocol_fault===1'b0,"known normal protocol flags");
 end
 if(MUT==2)begin send(pkt(8'h01,0,0,0,0)^(512'd3<<8));check(protocol_fault===1'b0,"malformed version mutant rejected");end
 if(errors==0)$display("HBM_HOST_NATIVE_PASS checks%0d transactions64 source_exact_ports73 bits787",checks);
 else $display("HBM_HOST_NATIVE_FAIL errors%0d checks%0d MUT%0d",errors,checks,MUT);
 $finish;
 end
endmodule
