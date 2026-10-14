`timescale 1ns/1ps
module tb_qkd_host_fullcontrol;
parameter MUT=0;
localparam D=8,NW=18,AW=24,NL=6;
reg  ck_host, ck_csr, ck_rst, ck_ctl;
reg [2:0] die_id;
reg  por_n;
reg  s_awvalid;
wire  s_awready;
reg [12:0] s_awaddr;
reg  s_wvalid;
wire  s_wready;
reg [31:0] s_wdata;
reg [3:0] s_wstrb;
wire  s_bvalid;
reg  s_bready;
wire [1:0] s_bresp;
reg  s_arvalid;
wire  s_arready;
reg [12:0] s_araddr;
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
reg [63:0] m_rdata;
reg [1:0] m_rresp;
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
reg [1:0] m_bresp;
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
reg [17:0] pb_q;
reg  pb_fault;
reg [142:0] pr;
reg [743:0] tk8;
reg [79:0] kst8;
wire [181:0] hc;
reg clk=0;always #0.4165 clk=~clk;
always @* begin ck_host=clk;ck_csr=clk;ck_rst=clk;ck_ctl=clk;end
qkd_host_fullcontrol #(.T_LINK(200),.T_HBM(200),.WDOG(200),.MUT_DIAG(MUT==1),.MUT_DONE_GUARD(MUT==2),.MUT_FMT(MUT==3)) dut(.*);
reg [63:0] mem[0:2047];reg[17:0] prompt[0:8191];
reg[63:0] wa; reg have_aw=0,have_w=0;reg[63:0] wd;
integer cycles=0,starts=0,cq_writes=0,pb_writes=0,delay_step=0,d;
reg[1:0] gen;reg[17:0] tok,pos;
always @(posedge clk) begin
 cycles<=cycles+1;
 if(pb_we) begin prompt[pb_waddr[12:0]]<=pb_wdata;pb_writes<=pb_writes+1;end
 if(pb_re) pb_q<=prompt[pb_raddr[12:0]];
 if(m_rvalid && m_rready)m_rvalid<=0;
 if(m_arvalid && m_arready) begin m_rvalid<=1;m_rdata<=mem[m_araddr>>3];end
 if(m_bvalid && m_bready)m_bvalid<=0;
 if(m_awvalid && m_awready) begin wa<=m_awaddr;have_aw<=1;end
 if(m_wvalid && m_wready) begin wd<=m_wdata;have_w<=1;end
 if(have_aw && have_w) begin mem[wa>>3]<=wd;have_aw<=0;have_w<=0;m_bvalid<=1;cq_writes<=cq_writes+1;end
 if(c_start)begin starts<=starts+1;gen<=c_gen;tok<=c_token;pos<=c_pos;delay_step<=6;
  if((c_pos==0 && c_token!==18'h2aaaa)||(c_pos==1 && c_token!==18'h15555)||
     (c_pos==2 && c_token!==18'h3bbbb)||(c_pos==3 && c_token!==18'h3abcd))$fatal(1,"prompt/token mismatch pos=%d token=%h",c_pos,c_token);
 end
 if(delay_step>0)delay_step<=delay_step-1;
 if(delay_step==1)for(d=0;d<8;d=d+1)tk8[d*93+:93]<={1'b1,gen,1'b1,1'b0,6'b0,(pos==2?18'h3abcd:18'h23456),32'h3f800000,32'd17};
end
 task tick;begin @(negedge clk);end endtask
 task wr(input[12:0]a,input[31:0]v);integer n;begin
 tick;s_awaddr=a;s_wdata=v;s_awvalid=1;s_wvalid=1;n=0;
 while(!(s_awready && s_wready) && n<100)begin tick;n=n+1;end
 if(n==100)$fatal(1,"write timeout %h",a);tick;s_awvalid=0;s_wvalid=0;
 n=0;while(!s_bvalid && n<100)begin tick;n=n+1;end
 if(n==100)$fatal(1,"b timeout");tick;
 end endtask
 task rd(input[12:0]a,output[31:0]v);integer n;begin
 tick;s_araddr=a;s_arvalid=1;n=0;while(!s_arready && n<100)begin tick;n=n+1;end
 tick;s_arvalid=0;n=0;while(!s_rvalid && n<100)begin tick;n=n+1;end
 if(n==100)$fatal(1,"read timeout");v=s_rdata;tick;
 end endtask
integer i,n;reg[31:0]v;reg[79:0]expected_kst;
initial begin
 por_n=0;die_id=0;s_awvalid=0;s_awaddr=0;s_wvalid=0;s_wdata=0;s_wstrb=15;s_bready=1;
 s_arvalid=0;s_araddr=0;s_rready=1;m_arready=1;m_rvalid=0;m_rdata=0;m_rresp=0;m_rlast=1;
 m_awready=1;m_wready=1;m_bvalid=0;m_bresp=0;link_up=0;boot_done=0;boot_ok=0;
 transport_fault=0;physical_fault=0;crom_fault=0;pb_q=0;pb_fault=0;pr=0;tk8=0;kst8=0;
 for(i=0;i<2048;i=i+1)mem[i]=0;
 repeat(8)tick;por_n=1;repeat(12)tick;link_up=63;repeat(15)tick;
 boot_done=8'h7f;boot_ok=8'hff;repeat(12)tick;if(sys_ready)$fatal(1,"ignored die7 boot");
 boot_done=255;repeat(12)tick;if(!sys_ready)$fatal(1,"boot did not ready");
 // Original global and host IDs retain their exact offsets.
 rd(13'h1000,v);if(v!==32'h51535953)$fatal(1,"global ABI");rd(0,v);if(v!==32'h4f544849)$fatal(1,"host ABI");
 // Four words original32byte descriptor; FMT1 prompt slots32b, EOS32b.
 mem[32]=64'h0002_0003_cafe_0101;mem[33]=64'h400;mem[34]=0;mem[35]=64'h0003ffff_0003ffff;
 mem[128]=64'h00015555_0002aaaa;mem[129]=64'h00000000_0003bbbb;
 wr(13'h010,32'h100);wr(13'h014,0);wr(13'h018,2);wr(13'h024,32'h800);wr(13'h028,0);wr(13'h02c,2);wr(13'h008,1);wr(13'h01c,1);
 n=0;while(cq_writes<4 && n<1500)begin tick;n=n+1;end
 if(cq_writes!=4 || starts!=4 || pb_writes!=3)$fatal(1,"ring counts cq=%d starts=%d pb=%d",cq_writes,starts,pb_writes);
 if(mem[256]!==64'habcd_0002_cafe_0003 || mem[257][63:32]!==32'h0003_0001)$fatal(1,"FMT1 CQ first %h %h",mem[256],mem[257]);
 if(mem[258]!==64'h3456_0003_cafe_0025 || mem[259][63:32]!==32'h0002_0002)$fatal(1,"FMT1 CQ final %h %h",mem[258],mem[259]);
 // All32per-die mapped summaries retain upper dies; raw80causebank independent.
 transport_fault=8'h80;physical_fault=8'h40;tk8[5*93+88]=1;kst8[4*10+9]=1;
 expected_kst=kst8;repeat(5)tick;rd(13'h1080,v);if(v!==32'h48120000)$fatal(1,"die diagnostic lost %h",v);
 rd(13'h1090,v);if(v!==expected_kst[31:0])$fatal(1,"raw low");rd(13'h1094,v);if(v!==expected_kst[63:32])$fatal(1,"raw middle");rd(13'h1098,v);if(v!=={16'b0,expected_kst[79:64]})$fatal(1,"raw high");
 wr(13'h1084,32'h40000000);repeat(3)tick;if(!irq)$fatal(1,"die7 IRQ lost");
 transport_fault=0;physical_fault=0;tk8[5*93+88]=0;kst8=0;repeat(3)tick;wr(13'h1080,32'hffffffff);rd(13'h1080,v);if(v!==0)$fatal(1,"diag W1C");
 // Soft reset reruns genuine eight-die checker, does not reset host rings.
 boot_done=0;boot_ok=0;wr(13'h1008,1);repeat(20)tick;
 if(sys_ready)$fatal(1,"soft reset remained ready");boot_done=255;boot_ok=127;repeat(12)tick;
 rd(13'h1004,v);if(v[1]!==1 || v[11:8]!==3)$fatal(1,"die7 failed boot not surfaced %h",v);
 $display("PASS full host FMT1 descriptor/CQ, 18bit token feedback, prompt8192x18 external, TP8 boot,32bit diagnostic/raw80/W1C/IRQ starts=%d",starts);$finish;
end
initial begin #3000;$fatal(1,"timeout");end
endmodule
