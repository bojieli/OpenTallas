`timescale 1ns/1ps
module tb_qkd_host_control_role;
parameter MUT=0;parameter UE=0;
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
reg ck_rx,ck_tx,ck_axi,ck_ctrl,ck_hc,ck_prompt;reg[63:0]mem[0:2047];reg[92:0]local_tk=0;reg[9:0]local_kst=0;reg[1:0]local_boot=0;
wire rx_cr,tx_v;reg rx_v=0,tx_cr=0;reg[527:0]rx_d=0;wire[527:0]tx_d;
wire source_cr,available,source_fault;wire[3:0]packet_faults;wire[7:0]seen;
wire ing_v,ing_t_cr;wire[1:0]ing_cls;wire[511:0]ing_d;reg[4:0]ing_crn=0;reg ing_t_v=0;reg[63:0]ing_t_d=0;
always @*begin ck_prompt=clk;ck_rx=clk;ck_tx=clk;ck_axi=clk;ck_ctrl=clk;ck_hc=clk;end
qkd_host_control_packet_capture_role #(.T_LINK(1000),.T_HBM(10000),.WDOG(10000),.HC_MUT(MUT==2),.PROMPT_MUT(MUT==3?3:MUT==4?2:0),.PROMPT_BIND_LATENCY(MUT==5?3:4))dut(.*);
assign c_start=dut.raw_hc[38];assign c_token=dut.raw_hc[35:18];assign c_pos=dut.raw_hc[17:0];assign c_gen=dut.raw_hc[37:36];
reg[7:1]peer_rx_v=0;reg[511:0]peer_rx_d[1:7];wire[7:1]peer_tx_v;wire[511:0]peer_tx_d[1:7];reg[7:1]peer_tx_cr=0;
reg[92:0]peer_tk[1:7];reg[9:0]peer_kst[1:7];reg[1:0]peer_boot[1:7];wire[181:0]peer_hc[1:7];wire[7:1]peer_fault;
for(genvar pd=1;pd<7;pd=pd+1)begin:g_peer
 qkd_host_ctrl_packet #(.DIE(pd),.STRAPPED(1))ctrl(.ck(clk),.rst_n(host_rst_n),.die_id(3'(pd)),
 .rx_v(peer_rx_v[pd]),.rx_d(peer_rx_d[pd]),.rx_cr(),.tx_v(peer_tx_v[pd]),.tx_d(peer_tx_d[pd]),.tx_cr(peer_tx_cr[pd]),
 .local_tk(peer_tk[pd]),.local_kst(peer_kst[pd]),.local_boot(peer_boot[pd]),.cmd_v(1'b0),.cmd_hc(182'b0),.cmd_cr(),
 .hc(peer_hc[pd]),.tk8(),.kst8(),.boot8(),.seen(),.fault(peer_fault[pd]));
end
wire follower_available,follower_source_cr,follower_source_fault,follower_tx_v,follower_ready,follower_die_rst;reg follower_tx_cr=0;wire[181:0]follower_hc;wire[527:0]follower_tx_d;wire[3:0]follower_packet_faults;
reg[5:0]follower_links=0;reg follower_rx_v=0;reg[527:0]follower_rx_d=0;
reg[527:0]fqueue[0:255];integer fw=0,fr=0,fgap=0;
task fenqueue(input[527:0]p);begin fqueue[fw]=p;fw=fw+1;end endtask
assign peer_tx_v[7]=follower_tx_v && follower_tx_d[527:524]==1;
assign peer_tx_d[7]=follower_tx_d[511:0];assign peer_hc[7]=follower_hc;assign peer_fault[7]=|follower_packet_faults;
qkd_host_control_packet_capture_role #(.T_LINK(1000),.T_HBM(10000)) follower(.ck_host(clk),.ck_csr(clk),.ck_rst(clk),.ck_ctl(clk),.ck_prompt(clk),
 .ck_rx(clk),.ck_tx(clk),.ck_axi(clk),.ck_ctrl(clk),.ck_hc(clk),.die_id(3'd7),.por_n(por_n),.link_up(follower_links),
 .transport_fault(8'b0),.physical_fault(8'b0),.crom_fault(1'b0),.pr(pr),.rx_v(follower_rx_v),.rx_d(follower_rx_d),.tx_v(follower_tx_v),.tx_d(follower_tx_d),.tx_cr(follower_tx_cr),
 .local_tk(peer_tk[7]),.local_kst(peer_kst[7]),.local_boot(peer_boot[7]),.sys_ready(follower_ready),.die_rst_n(follower_die_rst),.packet_faults(follower_packet_faults),.hc(follower_hc),.source_cr(follower_source_cr),.available(follower_available),.source_fault(follower_source_fault),
 .ing_crn(5'b0),.ing_t_v(1'b0),.ing_t_d(64'b0));
always @(negedge clk)begin
 follower_tx_cr=follower_tx_v;follower_rx_v=0;
 if(follower_tx_v && follower_tx_d[527:524]==1)fenqueue({4'd7,12'd0,488'b0,8'b0,8'd1,8'b0});
 if(follower_tx_v && follower_tx_d[527:524]==7 && follower_tx_d[15:8]!=0)enqueue(7,512'(follower_tx_d[23:0]));
 if(fgap>0)fgap=fgap-1;
 else if(fr<fw)begin follower_rx_v=1;follower_rx_d=fqueue[fr];fr=fr+1;fgap=10;end
end
integer peer_delay[1:7],peer_starts[1:7],peer_meta[1:7],hold7=0,step_count=0,credit_count=0,metadata_count=0,d;
reg[1:0]peer_gen[1:7];reg[17:0]peer_pos[1:7],peer_next[1:7];
reg[181:0]expected_commands[0:63];integer expected_count=0,peer_command_count[1:7],local_command_count=0;
reg[1:0]expected_gen=0;
integer prompt_writes=0;reg injected=0,ue_fault_seen=0;
always @(posedge clk)if(dut.u_control.u_control.pb_we)prompt_writes<=prompt_writes+1;
always @(negedge clk)if(prompt_writes==3 && !injected)begin
 dut.u_control.u_prompt.u_core.u_sram.arr[0][4]=!dut.u_control.u_prompt.u_core.u_sram.arr[0][4];
 if(UE)dut.u_control.u_prompt.u_core.u_sram.arr[0][8]=!dut.u_control.u_prompt.u_core.u_sram.arr[0][8];
 injected=1;
end
initial if(UE && MUT==1)force dut.u_control.u_control.u_pkg.pb_fault_q=1'b0;
reg overlap_sent=0,overlap_clear=0;
always @(negedge clk)begin
 if(!overlap_sent && dut.u_control.u_control.u_pkg.u_core.req_q[0])begin
  if(!available)$fatal(1,"overlap metadata lacked prior source credit");
  pr={1'b1,3'd7,64'h0123456789abcdef,1'b1,10'd1023,64'hfedcba9876543210};overlap_sent=1;overlap_clear=1;
 end else if(overlap_clear)begin pr[142]=0;pr[74]=0;overlap_clear=0;end
end
function automatic[17:0]next_token(input[17:0]p);begin next_token=(p==2)?18'h3abcd:18'h20000+p;end endfunction
always @(posedge clk)begin
 if(source_cr)credit_count<=credit_count+1;
 if(UE && dut.u_control.u_control.pb_fault && !ue_fault_seen)begin ue_fault_seen<=1;$display("TRACE q4 UE fault cycle=%d",cycles);end
 if(UE && dut.u_control.u_control.eng_start)$display("TRACE q4 hostrequest cycle=%d qualifiedready=%b",cycles,dut.u_control.u_control.u_pkg.u_core.ready_q);
 if(UE && dut.u_control.u_control.u_pkg.u_core.req_q[0])$display("TRACE q4 sampledrequest cycle=%d qualifiedready=%b",cycles,dut.u_control.u_control.u_pkg.u_core.ready_q);
 if(c_start)begin
  if(UE)$fatal(1,"UE corrupted prompt launched controller token=%h",c_token);
  if(hold7>0)$fatal(1,"die7 undrained completed early");
  expected_gen<=expected_gen+1'b1;step_count<=step_count+1;
  if(c_gen!==expected_gen+2'd1 || c_pos!==18'(step_count))$fatal(1,"generation wrap/position mismatch");
  if((c_pos==0&&c_token!==18'h2aaaa)||(c_pos==1&&c_token!==18'h15555)||(c_pos==2&&c_token!==18'h3bbbb)||
   (c_pos==3&&c_token!==18'h3abcd)||(c_pos>3&&c_token!==next_token(c_pos-1)))$fatal(1,"FMT1 transported token mismatch");
 end
 if(dut.raw_hc[38]||dut.raw_hc[113]||dut.raw_hc[181])begin expected_commands[expected_count]=dut.raw_hc;expected_count=expected_count+1;end
 if(hc[38]||hc[113]||hc[181])begin
  if(hc!==expected_commands[local_command_count])$fatal(1,"local rawhc mismatch");local_command_count=local_command_count+1;
  if(hc[38])local_tk<={1'b1,hc[37:36],1'b1,1'b0,6'b0,next_token(hc[17:0]),32'h3f800000,32'd17};
 end
 for(integer pd=1;pd<8;pd=pd+1)begin
  if(peer_hc[pd][38]||peer_hc[pd][113]||peer_hc[pd][181])begin
   if(peer_hc[pd]!==expected_commands[peer_command_count[pd]])$fatal(1,"remote rawhc/PW/DW mismatch die%d",pd);
   peer_command_count[pd]=peer_command_count[pd]+1;
   if(peer_hc[pd][113]||peer_hc[pd][181])peer_meta[pd]=peer_meta[pd]+1;
   if(peer_hc[pd][38])begin
    if(pd==7 && (!follower_ready || !follower_die_rst))$fatal(1,"transported peer7 start executed before local reset release");
    peer_starts[pd]=peer_starts[pd]+1;peer_delay[pd]=pd+2;peer_gen[pd]=peer_hc[pd][37:36];peer_pos[pd]=peer_hc[pd][17:0];peer_next[pd]=next_token(peer_hc[pd][17:0]);
    if(pd==7)hold7=600;
   end
  end
  if(peer_delay[pd]>0)begin peer_delay[pd]=peer_delay[pd]-1;
   if(peer_delay[pd]==0)peer_tk[pd]<={1'b1,peer_gen[pd],(pd!=7 || MUT==1),1'b0,6'b0,peer_next[pd],32'h3f800000,32'd17};
  end
 end
 if(hold7>0)begin hold7=hold7-1;if(hold7==0)peer_tk[7][89]<=1;end
 if(host_rst_n && cycles>40 && (follower_available || follower_source_cr || follower_source_fault || follower.raw_hc[38]))
  $fatal(1,"nonzero role ran independent host/controller or emitted metadata");
 if(source_fault || peer_fault!=0)$fatal(1,"control transport/source fault");
end
reg[527:0]queue[0:4095];integer qw=0,qr=0,gap=0;integer bwrites=0,breads=0;reg[31:0]board_rd;
reg[511:0]response;reg[23:0]credit;
task enqueue(input[3:0]c,input[511:0]payload);begin queue[qw]={c,12'b0,payload};qw=qw+1;end endtask
always @(negedge clk)begin
 rx_v=0;tx_cr=tx_v;peer_rx_v=0;peer_tx_cr=peer_tx_v;
 for(integer pd=1;pd<8;pd=pd+1)if(peer_tx_v[pd])enqueue(1,peer_tx_d[pd]);
 if(tx_v)begin
  credit=0;if(tx_d[527:524]==0)credit[7:0]=1;else if(tx_d[527:524]==1)credit[15:8]=(tx_d[31:24]==8'h80)?0:1;else if(tx_d[527:524]==4)credit[23:16]=1;
  if(credit!=0)enqueue(7,512'(credit));
  if(tx_d[527:524]==1)begin
 for(integer pd=1;pd<8;pd=pd+1)if(tx_d[24+pd])begin peer_rx_v[pd]=1;peer_rx_d[pd]=tx_d[511:0];if(pd==7)fenqueue(tx_d);end
end
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
integer cycles=0,cq_writes=0;always @(posedge clk)cycles<=cycles+1;
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
integer i,n;reg[31:0]v;reg[63:0]expected_cq;reg[17:0]nt;
initial begin
 por_n=0;die_id=0;link_up=0;transport_fault=0;physical_fault=0;crom_fault=0;pr=0;
 for(i=0;i<2048;i=i+1)mem[i]=0;
 for(i=1;i<8;i=i+1)begin peer_tk[i]=0;peer_kst[i]=10'(i*17);peer_boot[i]=0;peer_delay[i]=0;peer_starts[i]=0;peer_meta[i]=0;peer_command_count[i]=0;end
 repeat(8)tick;por_n=1;repeat(12)tick;link_up=63;repeat(15)tick;if(follower_ready || follower_die_rst)$fatal(1,"peer released before links");follower_links=63;local_boot=3;
 for(i=1;i<7;i=i+1)peer_boot[i]=3;peer_boot[7]=2;repeat(150)tick;if(follower_ready || follower_die_rst)$fatal(1,"peer released before genuine own bootdone");if(sys_ready)$fatal(1,"transported die7 bootdone ignored");
 peer_boot[7]=3;n=0;while(!sys_ready&&n<1000)begin tick;n=n+1;end;if(!sys_ready||seen!=255||!follower_ready||!follower_die_rst)$fatal(1,"true transported boot8 readiness");
 // Native metadata raw PW/DW ABI, source-credit reservation before every edge.
 for(i=0;i<3;i=i+1)begin
  n=0;while(!available&&n<1000)begin tick;n=n+1;end;if(!available)$fatal(1,"no metadata source credit");
  pr={1'b1,3'(i),64'hfedcba9876543210+64'(i),1'b1,10'(i+31),64'h123456789abcdef0+64'(i)};
  tick;pr[142]=0;pr[74]=0;repeat(30)tick;
 end
 n=0;while(credit_count<3&&n<1500)begin tick;n=n+1;end;if(credit_count!=3)$fatal(1,"seven-copy metadata credits");
 rd(13'h1000,v);if(v!==32'h51535953)$fatal(1,"globalBAR");rd(0,v);if(v!==32'h4f544849)$fatal(1,"hostBAR");
 mem[32]=64'h000a_0003_cafe_0101;mem[33]=64'h400;mem[34]=0;mem[35]=64'h0003ffff_0003ffff;
 mem[128]=64'h00015555_0002aaaa;mem[129]=64'h00000000_0003bbbb;
 if(UE)wr(13'h1014,32'h00400000);wr(13'h010,32'h100);wr(13'h014,0);wr(13'h018,2);wr(13'h024,32'h800);wr(13'h028,0);wr(13'h02c,5);wr(13'h03c,1);wr(13'h008,1);wr(13'h01c,1);
 if(UE)begin
  n=0;while(cq_writes<2&&n<3000)begin tick;n=n+1;end
  if(!injected || !dut.u_control.u_control.pb_fault || !irq || cq_writes!=2 || step_count!=0 || mem[256]!==64'h0000_0000_cafe_0075)
   $fatal(1,"q4 UE failclosed status irq=%b fault=%b steps%d CQ%h",irq,dut.u_control.u_control.pb_fault,step_count,mem[256]);
  rd(13'h101c,v);if(!v[22] || !v[18])$fatal(1,"q4 UE CSR missingfault");
  repeat(200)tick;if(expected_count!=4 || credit_count!=4)$fatal(1,"UE metadata credit lost");
  for(i=1;i<8;i=i+1)if(peer_meta[i]!=4 || peer_starts[i]!=0)$fatal(1,"UE remote metadata/start mismatch");
  if(step_count!=0 || cq_writes!=2)$fatal(1,"q4 UE later successful launch/CQ");
  $display("PASS capture256 q4/fault5 actual ND8 transported HOSTpacket UE stickyIRQ no-controllerstart CQfault=%h",mem[256]);$finish;
 end
 n=0;while(cq_writes<20&&n<12000)begin tick;n=n+1;end;
 if(cq_writes!=20||step_count!=12||!irq)$fatal(1,"transported ring/IRQ counts cq%d steps%d",cq_writes,step_count);
 for(i=0;i<10;i=i+1)begin
  nt=next_token(18'(i+2));expected_cq={nt[15:0],16'(i+2),16'hcafe,(i==9?16'h0025:16'h0003)};
  if(mem[256+i*2]!==expected_cq||mem[257+i*2][63:32]!=={14'b0,nt[17:16],16'(i+1)})$fatal(1,"exact CQ token highbits/phase/kind/status i%d",i);
 end
 repeat(200)tick;
 if(!overlap_sent || expected_count!=15 || local_command_count!=15 || credit_count!=15)$fatal(1,"bounded command events/returns");
 for(i=1;i<8;i=i+1)if(peer_starts[i]!=12||peer_meta[i]!=4||peer_command_count[i]!=15)$fatal(1,"peer metadata/start loss die%d",i);
 if(dut.kst8[79:70]!==10'(7*17))$fatal(1,"transported actual kst die7");
 $display("PASS UNQUALIFIED capture256 q4/fault5 actual control/prompt/HOST+ND8CTRL FMT1ring12steps generationwrap3 die7undrained boot8 PW/DW4includingStartOverlap all7peer exact 15credits IRQ/CQ10 peer7localready_then_transportedexecution_pkgctl_silent");$finish;
end
initial begin #20000;$fatal(1,"timeout");end
endmodule
