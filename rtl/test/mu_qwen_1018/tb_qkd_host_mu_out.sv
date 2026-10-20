`timescale 1ns/1ps
// MU-QWEN-HOST 10-19: 4-user host plane, end to end (qkd_host_fullcontrol_observed MU 1: qkd_host_if_pins_observed
// MU_OUT 1 -> ot_host_if_pb2_observed, qkd_host_ctl_service_pins MU 1 -> qkd_host_ctl -> ot_qfd_pkgctl MU 1).
// Four requests (slots 0..3, different prompt and generation lengths) go through the real SQ DMA, prompt SRAM
// ({slot2, pos11}), step issue, the 8-die package controller and CQ DMA.  The die model answers every start (all 8
// dies, same word) a fixed 48 edges later, so steps of different users overlap.  Checks:
//   - every die start names its user on hc pos[17:16], the user's next position and the right input token (prompt
//     token, else that user's previous output), and a user never has two steps outstanding;
//   - at least 3 steps are outstanding at once (4 users, static issue, no credits);
//   - per user, the CQ entries are the generated tokens in order: slot, tag, position, token (FMT 1 split), tokens
//     generated, kind TOKEN then LAST with status LENGTH; 12 entries, 18 steps; no fault, no observer fault.
module tb_qkd_host_mu_out;
localparam D=8,NW=18,AW=24,NL=6,NU=4,LAT=48;
reg  ck_host, ck_csr, ck_rst, ck_ctl;
reg [2:0] die_id;
reg  por_n;
reg  s_awvalid; wire s_awready; reg [12:0] s_awaddr; reg s_wvalid; wire s_wready; reg [31:0] s_wdata; reg [3:0] s_wstrb;
wire s_bvalid; reg s_bready; wire [1:0] s_bresp; reg s_arvalid; wire s_arready; reg [12:0] s_araddr; wire s_rvalid;
reg  s_rready; wire [31:0] s_rdata; wire [1:0] s_rresp;
wire m_arvalid; reg m_arready; wire [63:0] m_araddr; wire [7:0] m_arlen; wire [2:0] m_arsize; reg m_rvalid; wire m_rready;
reg [63:0] m_rdata; reg [1:0] m_rresp; reg m_rlast; wire m_awvalid; reg m_awready; wire [63:0] m_awaddr; wire [7:0] m_awlen;
wire [2:0] m_awsize; wire m_wvalid; reg m_wready; wire [63:0] m_wdata; wire [7:0] m_wstrb; wire m_wlast; reg m_bvalid;
wire m_bready; reg [1:0] m_bresp;
wire irq;
reg [NL-1:0] link_up; reg [D-1:0] boot_done, boot_ok;
wire host_rst_n, link_rst_n, hbm_rst_n, boot_go, die_rst_n, sys_ready;
wire c_start; wire [NW-1:0] c_token, c_pos; wire [AW-1:0] c_kv_base; wire [1:0] c_gen;
reg [7:0] transport_fault, physical_fault; reg crom_fault; wire [31:0] fault_src;
wire pb_we, pb_re; wire [13:0] pb_waddr, pb_raddr; wire [17:0] pb_wdata; reg [17:0] pb_q; reg pb_fault;
reg [142:0] pr; reg [743:0] tk8; reg [79:0] kst8; wire [181:0] hc;
reg service_abort=0, service_ready=1; reg [7:0] service_ready8=8'hff; reg [25:0] service_diag_raw=0; reg [31:0] service_status=0;
reg begin_tx_cr=0, begin_tx_available=0; reg [7:0] pending_ack8=0; reg [127:0] service_epoch8=0; reg service_fault=0;
reg ingest_permission=0;
wire begin_v; wire [15:0] begin_epoch; wire begin_available, begin_fault, epoch_busy, startup_allowed, package_abort;
wire cq_commit_v; wire [15:0] cq_client_tag; wire [7:0] cq_slot; wire [17:0] cq_pos, cq_token; wire [1:0] cq_kind; wire [3:0] cq_status;
wire step_issue_v; wire [15:0] step_client_tag; wire [7:0] step_slot; wire [17:0] step_pos;
wire step_retire_v, step_retire_cq; wire [15:0] step_retire_client_tag; wire [7:0] step_retire_slot; wire [17:0] step_retire_pos, step_retire_token;
wire host_idle, host_observer_fault;
reg peer_reset_request=0;
reg clk=0; always #0.4165 clk=~clk;
always @* begin ck_host=clk; ck_csr=clk; ck_rst=clk; ck_ctl=clk; end
qkd_host_fullcontrol_observed #(.T_LINK(200),.T_HBM(200),.WDOG(4000),.MU(1),.NSLOT(4),.PLB(11)) dut(.*);

// per-user request
integer plen[0:NU-1], maxn[0:NU-1];
initial begin plen[0]=2; plen[1]=3; plen[2]=1; plen[3]=4; maxn[0]=3; maxn[1]=2; maxn[2]=4; maxn[3]=3; end
function automatic [17:0] ptok(input integer u, input integer i); ptok = 18'(256*(u+1) + i + 5); endfunction
function automatic [17:0] otok(input integer u, input integer p); otok = 18'(32'h20000 + u*4096 + p*5 + 3); endfunction

reg [63:0] mem[0:2047]; reg [17:0] prompt[0:8191];
reg [63:0] wa; reg have_aw=0, have_w=0; reg [63:0] wd;
integer cycles=0, starts=0, cq_writes=0, pb_writes=0, errors=0, d, outstanding=0, max_out=0, retires=0;
integer nxt[0:NU-1], busy[0:NU-1];
// die pipeline: report q[i] at t_rep[i]
integer q_t[0:63], q_u[0:63], q_p[0:63], q_g[0:63], q_w=0, q_r=0;
integer u, p;
always @(posedge clk) begin
 cycles<=cycles+1;
 if(pb_we) begin prompt[pb_waddr[12:0]]<=pb_wdata; pb_writes<=pb_writes+1; if(pb_waddr[13])begin errors=errors+1;$display("ERR prompt addr bit13");end end
 if(pb_re) pb_q<=prompt[pb_raddr[12:0]];
 if(m_rvalid && m_rready) m_rvalid<=0;
 if(m_arvalid && m_arready) begin m_rvalid<=1; m_rdata<=mem[m_araddr>>3]; end
 if(m_bvalid && m_bready) m_bvalid<=0;
 if(m_awvalid && m_awready) begin wa<=m_awaddr; have_aw<=1; end
 if(m_wvalid && m_wready) begin wd<=m_wdata; have_w<=1; end
 if(have_aw && have_w) begin mem[wa>>3]<=wd; have_aw<=0; have_w<=0; m_bvalid<=1; cq_writes<=cq_writes+1; end
end
// die model at the negedge (hc leaves pin flops)
always @(negedge clk) if (sys_ready) begin
 if (hc[38]) begin
  u = hc[17:16]; p = hc[15:0];
  if (busy[u] || p != nxt[u] || hc[35:18] !== ((p < plen[u]) ? ptok(u,p) : otok(u,p-1))) begin
   errors=errors+1; if(errors<6) $display("ERR start user %0d pos %0d/%0d busy %0d token %h", u, p, nxt[u], busy[u], hc[35:18]);
  end
  busy[u]=1; starts=starts+1; outstanding=outstanding+1; if(outstanding>max_out) max_out=outstanding;
  q_t[q_w%64]=cycles+LAT; q_u[q_w%64]=u; q_p[q_w%64]=p; q_g[q_w%64]=hc[37:36]; q_w=q_w+1;
 end
 if (q_r < q_w && q_t[q_r%64] <= cycles) begin
  for(d=0;d<D;d=d+1) tk8[d*93+:93]={1'b1,2'(q_g[q_r%64]),1'b1,1'b0,6'b0,otok(q_u[q_r%64],q_p[q_r%64]),32'h3f800000,32'd17};
  q_r=q_r+1;
 end
 if (step_retire_v) begin
  u = step_retire_slot;
  if (!busy[u] || step_retire_pos != nxt[u] || step_retire_token !== otok(u, nxt[u])) begin
   errors=errors+1; if(errors<6) $display("ERR retire slot %0d pos %0d/%0d token %h", u, step_retire_pos, nxt[u], step_retire_token);
  end
  busy[u]=0; nxt[u]=nxt[u]+1; outstanding=outstanding-1; retires=retires+1;
 end
 if (host_observer_fault || package_abort) begin errors=errors+1; if(errors<6) $display("ERR fault observer %0d abort %0d", host_observer_fault, package_abort); end
end
task tick; begin @(negedge clk); end endtask
task wr(input [12:0] a, input [31:0] v); integer n; begin
 tick; s_awaddr=a; s_wdata=v; s_awvalid=1; s_wvalid=1; n=0;
 while(!(s_awready && s_wready) && n<100) begin tick; n=n+1; end
 if(n==100) $fatal(1,"write timeout %h",a); tick; s_awvalid=0; s_wvalid=0;
 n=0; while(!s_bvalid && n<100) begin tick; n=n+1; end
 if(n==100) $fatal(1,"b timeout"); tick;
end endtask
task rd(input [12:0] a, output [31:0] v); integer n; begin
 tick; s_araddr=a; s_arvalid=1; n=0; while(!s_arready && n<100) begin tick; n=n+1; end
 tick; s_arvalid=0; n=0; while(!s_rvalid && n<100) begin tick; n=n+1; end
 if(n==100) $fatal(1,"read timeout"); v=s_rdata; tick;
end endtask
integer i, n, e, nent, steps_exp, ngen[0:NU-1], ent_seen[0:NU-1]; reg [31:0] v; reg [63:0] w0, w1; reg [17:0] tk;
initial begin
 por_n=0; die_id=0; s_awvalid=0; s_awaddr=0; s_wvalid=0; s_wdata=0; s_wstrb=15; s_bready=1;
 s_arvalid=0; s_araddr=0; s_rready=1; m_arready=1; m_rvalid=0; m_rdata=0; m_rresp=0; m_rlast=1;
 m_awready=1; m_wready=1; m_bvalid=0; m_bresp=0; link_up=0; boot_done=0; boot_ok=0;
 transport_fault=0; physical_fault=0; crom_fault=0; pb_q=0; pb_fault=0; pr=0; tk8=0; kst8=0;
 for(i=0;i<2048;i=i+1) mem[i]=0;
 for(u=0;u<NU;u=u+1) begin nxt[u]=0; busy[u]=0; ngen[u]=0; ent_seen[u]=0; end
 repeat(8) tick; por_n=1; repeat(12) tick; link_up=63; repeat(15) tick;
 boot_done=255; boot_ok=255; repeat(12) tick; if(!sys_ready) $fatal(1,"boot did not ready");
 rd(13'h0004,v); $display("CAPS %h", v);
 // SQ at 0x100 (32 B entries), prompts at 0x400 + 0x40*u, CQ at 0x800 (16 B entries)
 for(u=0;u<NU;u=u+1) begin
  mem[32+4*u]   = {16'(maxn[u]), 16'(plen[u]), 16'(16'hA0 + u), 8'h01, 8'h01};
  mem[32+4*u+1] = 64'(32'h400 + 32'h40*u);
  mem[32+4*u+2] = 64'(u);
  mem[32+4*u+3] = 64'h0003ffff_0003ffff;
  for(i=0;i<plen[u];i=i+1)
   if(i%2==0) mem[128+8*u+i/2][31:0] = 32'(ptok(u,i)); else mem[128+8*u+i/2][63:32] = 32'(ptok(u,i));
 end
 wr(13'h010,32'h100); wr(13'h014,0); wr(13'h018,3); wr(13'h024,32'h800); wr(13'h028,0); wr(13'h02c,5); wr(13'h008,1); wr(13'h01c,4);
 nent=0; steps_exp=0; for(u=0;u<NU;u=u+1) begin nent=nent+maxn[u]; steps_exp=steps_exp+plen[u]+maxn[u]-1; end
 n=0; while(cq_writes<2*nent && n<20000) begin tick; n=n+1; end
 repeat(40) tick;
 if(cq_writes!=2*nent || starts!=steps_exp || retires!=steps_exp || outstanding!=0) begin
  errors=errors+1; $display("ERR counts cq_writes %0d/%0d starts %0d retires %0d / %0d outstanding %0d", cq_writes, 2*nent, starts, retires, steps_exp, outstanding);
 end
 if(max_out < 3) begin errors=errors+1; $display("ERR max outstanding %0d < 3", max_out); end
 // CQ: per user, generated positions plen-1 .. plen+max-2 in order
 for(e=0;e<nent;e=e+1) begin
  w0=mem[256+2*e]; w1=mem[256+2*e+1]; u=w0[11:4]; // slot8 at [15:8]? decode below
  u=w0[15:8];
  if(u>=NU) begin errors=errors+1; $display("ERR CQ %0d slot %0d", e, u); end
  else begin
   p=plen[u]-1+ent_seen[u]; tk={w1[49:48], w0[63:48]};
   if(w0[31:16]!==16'(16'hA0+u) || w0[47:32]!==16'(p) || tk!==otok(u,p) || w1[47:32]!==16'(ent_seen[u]+1) ||
      w0[2:1]!==((ent_seen[u]==maxn[u]-1)?2'd2:2'd1) || w0[7:4]!==((ent_seen[u]==maxn[u]-1)?4'd2:4'd0) || w0[0]!==1'b1) begin
    errors=errors+1; $display("ERR CQ %0d w0 %h w1 %h user %0d expect pos %0d token %h", e, w0, w1, u, p, otok(u,p));
   end
   ent_seen[u]=ent_seen[u]+1;
  end
 end
 for(u=0;u<NU;u=u+1) if(ent_seen[u]!=maxn[u]) begin errors=errors+1; $display("ERR user %0d entries %0d/%0d", u, ent_seen[u], maxn[u]); end
 rd(13'h00c,v); if(v[1]) begin errors=errors+1; $display("ERR STATUS fault %h", v); end
 if(errors) begin $display("FAIL host MU_OUT errors=%0d starts %0d max_outstanding %0d", errors, starts, max_out); $fatal(1); end
 $display("PASS host MU_OUT users4 steps%0d CQ entries%0d per-user in order (slot/tag/pos/token/ngen/kind), hc user=pos[17:16], max outstanding %0d, no fault", starts, nent, max_out);
 $finish;
end
initial begin #200000; $fatal(1,"timeout"); end
endmodule
