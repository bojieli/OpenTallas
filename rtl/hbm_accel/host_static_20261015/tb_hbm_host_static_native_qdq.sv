`timescale 1ns/1ps
module tb_hbm_host_static_native_qdq;
parameter integer MUT=0,FACE=1;
integer rows=1024,seen=0,cy=0,lastcy=-1,txn=0,launches=0;reg measure=0;
wire program_ready,program_active,program_done,configured,program_fault,ingress_fault,command_v;wire[47:0]command;wire[31:0]ordinal;
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
 hfd_host_static_native_qdq_program #(.MUT(MUT))dut(.clk_controller(clk),.clk_landing(clk),.clk_ep(clk),.clk_face(clk),.clk_sub({12{clk}}),.clk_tx_shared(clk),.clk_rx_shared(clk),.clk_status_shared(clk),.clk_phy(clk),.rst_n(rst_n),.session(24'h3555),.service_h({h[786:471],h[405:37]}),.pma_tx(pa),.pma_tck(ca),.pma_rx(pb),.pma_rck(cb),.host_faults(local_faults),.phy_status(local_status),.ep_locked(local_locked),.program_ready(program_ready),.program_active(program_active),.program_done(program_done),.configured(configured),.program_fault(program_fault),.ingress_fault(ingress_fault),.command(command),.command_v(command_v),.ordinal(ordinal));
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

 function automatic[47:0]expected_command(input integer n);
 integer row,beat;begin row=n/4;beat=n%4;
 expected_command={beat==3,16'(row*32+beat*4),16'(row*16+beat*4),8'(row),6'd4,1'b1};end endfunction
 always @(negedge clk)begin
 cy=cy+1;
 if(dut.lv)launches=launches+1;
 if(measure&&command_v)begin
 if(command!==expected_command(seen)||ordinal!==seen)$fatal(1,"HOST_NATIVE_QDQ exact command n=%0d got=%h expected=%h ord=%d",seen,command,expected_command(seen),ordinal);
 if(lastcy>=0&&cy!=lastcy+1)$fatal(1,"HOST_NATIVE_QDQ runtime gap n=%0d",seen);
 lastcy=cy;seen=seen+1;
 end
 end
 task reset_dut;begin
 rst_n=0;rx_valid=0;tx_ready=0;measure=0;repeat(8)tick;
 rst_n=1;repeat(350)tick;
 end endtask
 task write32(input[11:0]a,input[31:0]d,input[3:0]strb,input[1:0]expected_resp);
 begin
 txn=txn+1;send(pkt(8'h01,16'(txn),64'(a),64'(d),8'(strb)));
 waits=0;while(!tx_valid&&waits<10000)begin tick;waits=waits+1;end
 if(!tx_valid||tx_packet[7:0]!=8'h81||tx_packet[31:16]!==16'(txn)||tx_packet[169:168]!==expected_resp)
 $fatal(1,"HOST_NATIVE_QDQ BRESP a=%h exp=%h got=%h valid=%b packet=%h",a,expected_resp,tx_packet[169:168],tx_valid,tx_packet);
 saved=tx_packet;repeat(3)begin tick;if(!tx_valid||tx_packet!==saved)$fatal(1,"HOST_NATIVE_QDQ unstable completion");end
 tx_ready=1;tick;tx_ready=0;
 end endtask
 reg[255:0]word;
 initial begin
 if($value$plusargs("ROWS=%d",rows))begin end
 reset_dut();write32(12'hf30,1,15,2);
 if(!ingress_fault||launches!=0||!local_faults[3])$fatal(1,"HOST_NATIVE_QDQ premature launch");
 reset_dut();write32(12'hf20,48,15,0);
 for(integer row=0;row<rows;row=row+1)begin
 word=0;word[255:240]=16'hc7a1;word[233:224]=10'(row);
 word[31:0]=32'(8+row*4);word[47:32]=4;word[63:48]=16'(row*16);word[79:64]=16'(row*32);word[85:80]=4;word[93:86]=8'(row);
 for(integer piece=0;piece<8;piece=piece+1)write32(12'hf24,word[piece*32+:32],15,0);
 end
 write32(12'hf28,32'(rows<<12),15,0);write32(12'hf2c,1,15,0);
 repeat(rows+12)tick;
 if(!program_ready||program_fault||ingress_fault||protocol_fault)$fatal(1,"HOST_NATIVE_QDQ installed ready/fault");
 seen=0;lastcy=-1;measure=1;write32(12'hf30,1,15,0);
 waits=0;while(!program_done&&waits<rows*4+2000)begin tick;waits=waits+1;end
 repeat(4)tick;
 if(seen!=rows*4||program_fault||ingress_fault||protocol_fault)$fatal(1,"HOST_NATIVE_QDQ body seen=%d expected=%d pf=%b hf=%b lf=%b",seen,rows*4,program_fault,ingress_fault,local_faults);
 measure=0;
 // Missing installed SRAM rows, bad target, partial frame and unsupported
 // compact loop all fail through actual host error/readiness/fault paths.
 reset_dut();write32(12'hf20,48,15,0);write32(12'hf28,2<<12,15,0);write32(12'hf2c,1,15,0);
 repeat(12)tick;if(program_ready||!program_fault)$fatal(1,"HOST_NATIVE_QDQ missing rows ready");
 write32(12'hf30,1,15,2);
 reset_dut();write32(12'hf20,49,15,2);
 reset_dut();write32(12'hf20,48,3,2);
 reset_dut();write32(12'hf20,48,15,0);write32(12'hf24,32'h1234,15,0);write32(12'hf30,1,15,2);
 reset_dut();write32(12'hf20,48,15,0);write32(12'hf28,1<<12,15,0);write32(12'hf2c,2,15,0);
 repeat(8)tick;if(program_ready||!program_fault)$fatal(1,"HOST_NATIVE_QDQ compact loop accepted");
 if(errors)$fatal(1,"HOST_NATIVE_QDQ external link errors=%d",errors);
 $display("HBM_HOST_STATIC_NATIVE_QDQ_PASS rows=%0d records=%0d commands=%0d gapless=1 target48_compact1=1 real_UCIe_retry_landing_SRAM=1 BRESP=1 negatives=6",rows,rows,seen);$finish;
 end
endmodule
