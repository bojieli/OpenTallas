`timescale 1ns/1ps
module tb_qkd_host_prompt_ue;
parameter MUT=0;
localparam D=8,NW=18,AW=24,NL=6;
reg  ck_host, ck_csr, ck_rst, ck_ctl;
reg [2:0] die_id;
reg  por_n;
reg  s_awvalid;
wire  s_awready;
wire [12:0] s_awaddr;
reg  s_wvalid;
wire  s_wready;
wire [31:0] s_wdata;
wire [3:0] s_wstrb;
wire  s_bvalid;
reg  s_bready;
wire [1:0] s_bresp;
reg  s_arvalid;
wire  s_arready;
wire [12:0] s_araddr;
wire  s_rvalid;
reg  s_rready;
wire [31:0] s_rdata;
wire [1:0] s_rresp;
wire  m_arvalid;
reg  m_arready;
wire [63:0] m_araddr;
wire [7:0] m_arlen;
wire [2:0] m_arsize;
reg  m_rvalid;
wire  m_rready;
wire [63:0] m_rdata;
wire [1:0] m_rresp;
reg  m_rlast;
wire  m_awvalid;
reg  m_awready;
wire [63:0] m_awaddr;
wire [7:0] m_awlen;
wire [2:0] m_awsize;
wire  m_wvalid;
reg  m_wready;
wire [63:0] m_wdata;
wire [7:0] m_wstrb;
wire  m_wlast;
reg  m_bvalid;
wire  m_bready;
wire [1:0] m_bresp;
wire  irq;
reg [NL-1:0] link_up;
reg [D-1:0] boot_done;
reg [D-1:0] boot_ok;
wire  host_rst_n;
wire  link_rst_n;
wire  hbm_rst_n;
wire  boot_go;
wire  die_rst_n;
wire  sys_ready;
wire  c_start;
wire [NW-1:0] c_token;
wire [NW-1:0] c_pos;
wire [AW-1:0] c_kv_base;
wire [1:0] c_gen;
reg [7:0] transport_fault, physical_fault;
reg  crom_fault;
wire [31:0] fault_src;
wire  pb_we, pb_re;
wire [13:0] pb_waddr,pb_raddr;
wire [17:0] pb_wdata;
wire [17:0] pb_q;
wire pb_fault;
reg [142:0] pr;
reg [743:0] tk8;
reg [79:0] kst8;
wire [181:0] hc;
reg clk=0;always #0.4165 clk=~clk;
always @* begin ck_host=clk;ck_csr=clk;ck_rst=clk;ck_ctl=clk;end
qkd_host_prompt_pins #(.MUT(0))prompt_leaf(.ck(clk),.rst_n(host_rst_n),.we(pb_we),.re(pb_re),
 .waddr(pb_waddr[12:0]),.raddr(pb_raddr[12:0]),.wdata(pb_wdata),.q(pb_q),.fault(pb_fault));
reg ecc_injected=0;
// Real macro array cell for codeword0/data-bit0 (code bit2, physical mux2 col4).
// Inject after initial prompt writes; subsequent masked lane writes preserve it.
always @(negedge clk)if(pb_writes==3 && !ecc_injected)begin
 prompt_leaf.u_core.u_sram.arr[0][4]=!prompt_leaf.u_core.u_sram.arr[0][4];
 prompt_leaf.u_core.u_sram.arr[0][8]=!prompt_leaf.u_core.u_sram.arr[0][8];ecc_injected=1;
end
qkd_host_fullcontrol #(.T_LINK(200),.T_HBM(200),.WDOG(200),.PROMPT_READ_LATENCY(3)) dut(.*);
// Guard mutant removes prompt-fault qualification AFTER its input capture.
initial if(MUT!=0)force dut.u_pkg.pb_fault_q=1'b0;
reg [63:0] mem[0:2047];
reg rx_v=0,tx_cr=0;reg[527:0]rx_d=0;wire rx_cr,tx_v;wire[527:0]tx_d;
wire[3:0]packet_faults;wire[743:0]packet_tk;wire[79:0]packet_kst;wire[15:0]packet_boot;
wire[7:0]seen;wire[181:0]packet_hc;wire cmd_cr,ing_v,ing_t_cr;wire[1:0]ing_cls;wire[511:0]ing_d;
qkd_host_packet_bundle plane(.ck_rx(clk),.ck_tx(clk),.ck_axi(clk),.ck_ctrl(clk),.rst_n(host_rst_n),.die_id(die_id),
 .rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.irq(irq),
 .local_tk(93'b0),.local_kst(10'b0),.local_boot(2'b0),.cmd_v(1'b0),.cmd_hc(182'b0),.cmd_cr(cmd_cr),
 .hc(packet_hc),.tk8(packet_tk),.kst8(packet_kst),.boot8(packet_boot),.seen(seen),
 .ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(5'b0),.ing_t_v(1'b0),.ing_t_d(64'b0),.ing_t_cr(ing_t_cr),.faults(packet_faults),
.s_awvalid(s_awvalid),
.s_awready(s_awready),
.s_awaddr(s_awaddr),
.s_wvalid(s_wvalid),
.s_wready(s_wready),
.s_wdata(s_wdata),
.s_wstrb(s_wstrb),
.s_bvalid(s_bvalid),
.s_bready(s_bready),
.s_bresp(s_bresp),
.s_arvalid(s_arvalid),
.s_arready(s_arready),
.s_araddr(s_araddr),
.s_rvalid(s_rvalid),
.s_rready(s_rready),
.s_rdata(s_rdata),
.s_rresp(s_rresp),
.m_arvalid(m_arvalid),
.m_arready(m_arready),
.m_araddr(m_araddr),
.m_rvalid(m_rvalid),
.m_rready(m_rready),
.m_rdata(m_rdata),
.m_rresp(m_rresp),
.m_rlast(m_rlast),
.m_awvalid(m_awvalid),
.m_awready(m_awready),
.m_awaddr(m_awaddr),
.m_wvalid(m_wvalid),
.m_wready(m_wready),
.m_wdata(m_wdata),
.m_wstrb(m_wstrb),
.m_bvalid(m_bvalid),
.m_bready(m_bready),
.m_bresp(m_bresp));
reg[527:0]queue[0:255];integer qw=0,qr=0,gap=0;integer bwrites=0,breads=0;reg[31:0]board_rd;
reg[511:0]response;reg[23:0]credit;
task enqueue(input[3:0]c,input[511:0]payload);begin queue[qw]={c,12'b0,payload};qw=qw+1;end endtask
always @(negedge clk)begin
 rx_v=0;tx_cr=tx_v;
 if(tx_v)begin
  credit=0;if(tx_d[527:524]==0)credit[7:0]=1;else if(tx_d[527:524]==1)credit[15:8]=1;else if(tx_d[527:524]==4)credit[23:16]=1;
  if(credit!=0)enqueue(7,512'(credit));
  if(tx_d[527:524]==0)case(tx_d[7:0])
   8'h81:bwrites=bwrites+1;
   8'h82:begin breads=breads+1;board_rd=tx_d[127:96];end
   8'h12:begin response=512'h0113;response[34]=1;response[159:96]=mem[tx_d[95:32]>>3];enqueue(0,response);end
   8'h14:begin mem[tx_d[95:32]>>3]=tx_d[159:96];cq_writes=cq_writes+1;enqueue(0,512'h0115);end
   default:$fatal(1,"bad board HOST opcode %h",tx_d[7:0]);
  endcase
 end
 if(gap>0)gap=gap-1;
 else if(qr<qw)begin rx_v=1;rx_d=queue[qr];qr=qr+1;gap=10;end
 if(host_rst_n && packet_faults!=0)$fatal(1,"actual packet plane fault %h",packet_faults);
end
reg fault_seen=0;
integer cycles=0,starts=0,cq_writes=0,pb_writes=0,delay_step=0,d;
reg[1:0] gen;reg[17:0] tok,pos;
always @(posedge clk) begin
 cycles<=cycles+1;
 if(pb_we)pb_writes<=pb_writes+1;
 if(pb_re)$display("TRACE request cycle=%d addr=%h",cycles,pb_raddr);
 if(pb_fault && !fault_seen)begin fault_seen<=1;$display("TRACE fault cycle=%d q=%h",cycles,pb_q);end
 if(dut.eng_start)$display("TRACE host-start cycle=%d qualified-ready=%b",cycles,dut.u_pkg.u_core.ready_q);
 if(dut.u_pkg.u_core.req_q[0])$display("TRACE sampled-request cycle=%d qualified-ready=%b",cycles,dut.u_pkg.u_core.ready_q);

 if(c_start)$fatal(1,"UE corrupted prompt launched controller token=%h pos=%d",c_token,c_pos);
 if(delay_step>0)delay_step<=delay_step-1;
 if(delay_step==1)for(d=0;d<8;d=d+1)tk8[d*93+:93]<={1'b1,gen,1'b1,1'b0,6'b0,(pos==2?18'h3abcd:18'h23456),32'h3f800000,32'd17};
end
 task tick;begin @(negedge clk);end endtask
 task wr(input[12:0]a,input[31:0]v);integer n,goal;reg[511:0]h;begin
 h=512'h0101;h[44:32]=a;h[127:96]=v;h[131:128]=15;goal=bwrites+1;enqueue(0,h);n=0;
 while(bwrites<goal&&n<300)begin tick;n=n+1;end
 if(n==300)$fatal(1,"board write timeout %h",a);
 end endtask
 task rd(input[12:0]a,output[31:0]v);integer n,goal;reg[511:0]h;begin
 h=512'h0102;h[44:32]=a;goal=breads+1;enqueue(0,h);n=0;
 while(breads<goal&&n<300)begin tick;n=n+1;end
 if(n==300)$fatal(1,"board read timeout %h",a);v=board_rd;
 end endtask
integer i,n;reg[31:0]v;reg[79:0]expected_kst;
initial begin
 por_n=0;die_id=0;link_up=0;boot_done=0;boot_ok=0;
 transport_fault=0;physical_fault=0;crom_fault=0;pr=0;tk8=0;kst8=0;
 for(i=0;i<2048;i=i+1)mem[i]=0;
 repeat(8)tick;por_n=1;repeat(12)tick;link_up=63;repeat(15)tick;
 boot_done=8'h7f;boot_ok=8'hff;repeat(12)tick;if(sys_ready)$fatal(1,"ignored die7 boot");
 boot_done=255;repeat(12)tick;if(!sys_ready)$fatal(1,"boot did not ready");
 // Original global and host IDs retain their exact offsets.
 rd(13'h1000,v);if(v!==32'h51535953)$fatal(1,"global ABI");rd(0,v);if(v!==32'h4f544849)$fatal(1,"host ABI");
 // Four words original32byte descriptor; FMT1 prompt slots32b, EOS32b.
 mem[32]=64'h0002_0003_cafe_0101;mem[33]=64'h400;mem[34]=0;mem[35]=64'h0003ffff_0003ffff;
 mem[128]=64'h00015555_0002aaaa;mem[129]=64'h00000000_0003bbbb;
 wr(13'h1014,32'h00400000);wr(13'h010,32'h100);wr(13'h014,0);wr(13'h018,2);wr(13'h024,32'h800);wr(13'h028,0);wr(13'h02c,2);wr(13'h008,1);wr(13'h01c,1);
 n=0;while(cq_writes<2 && n<2500)begin tick;n=n+1;end
 if(!ecc_injected || !pb_fault || !irq || cq_writes!=2 || starts!=0 || pb_writes!=3)
  $fatal(1,"UE guard failed injected=%b fault=%b irq=%b cq=%d starts=%d",ecc_injected,pb_fault,irq,cq_writes,starts);
 if(mem[256]!==64'h0000_0000_cafe_0075)$fatal(1,"UE accepted successful CQ %h",mem[256]);
 rd(13'h101c,v);if(!v[22] || !v[18])$fatal(1,"UE fault missing prompt/start-unready %h",v);
 repeat(60)tick;if(cq_writes!=2 || !pb_fault || !irq)$fatal(1,"UE fault/stall not retained");
 $display("PASS actual HOST packet double-ECC prompt fail-closed: q3 fault4 stickyIRQ no-controller-start CQfault=%h",mem[256]);$finish;
end
initial begin #6000;$fatal(1,"timeout");end
endmodule
