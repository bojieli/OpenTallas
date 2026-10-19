`timescale 1ns/1ps
// KV-HOST/PROMPT p8 (10-19): ot_host_if_pb2_observed (original) vs ot_host_if_pb2_observed_pd (gen_prompt_pd.py: registered
// cq_t1 == (cq_tail + 1) & cq_mask, c_cqfull / c_cycles / c_busy as ot_hkv_cnt_la) in lock-step under fully random AXI-lite,
// AXI master, engine and array inputs, biased so the completion queue fills often (CQ_LOG writes of 0..3, CQ_HEAD
// doorbells, SQ_TAIL / ENABLE writes, random descriptors -> error completions).  Every output and the internal c_cqfull /
// cq_room are compared on every edge; coverage (cycles counted by c_cqfull, CQ entries posted, CQ_LOG changes with an
// event pending) must be non-trivial.  Two shapes: the production child (NSLOT 4, FMT 1, NW 18, PB_READ_PIPE 2) and the
// module defaults (NSLOT 16, FMT 0, NW 16).  Generated once by KV-HOST/PROMPT; edit by hand.
// -DOT_HKV_CQ_MUTANT (cq_t1 ignores a CQ_LOG write) must FAIL.
module hkv_pb2_pair #(parameter integer NSLOT=4, FMT=1, NW=18, PRP=2, ENGC=4, SEED=1, CYC=300000) (input wire clk, output reg done, output reg ok);
 localparam integer SB = (NSLOT > 1) ? $clog2(NSLOT) : 1;
 localparam integer PLB = 8, AW = 24;
 reg rst_n;
 reg  s_awvalid;
 reg [11:0] s_awaddr;
 reg  s_wvalid;
 reg [31:0] s_wdata;
 reg [3:0] s_wstrb;
 reg  s_bready;
 reg  s_arvalid;
 reg [11:0] s_araddr;
 reg  s_rready;
 reg  m_arready;
 reg  m_rvalid;
 reg [63:0] m_rdata;
 reg [1:0] m_rresp;
 reg  m_rlast;
 reg  m_awready;
 reg  m_wready;
 reg  m_bvalid;
 reg [1:0] m_bresp;
 reg [NW-1:0] pb_q;
 reg  eng_done;
 reg [NW-1:0] eng_next_token;
 reg [31:0] eng_cycles;
 reg  eng_fault;
 reg  eng_clr_ack;
 reg  pr_re;
 reg [7:0] pr_user;
 reg [NW-1:0] pr_pos;
 reg  tok_valid;
 reg [7:0] tok_user;
 reg [NW-1:0] tok_pos;
 reg [NW-1:0] tok_id;
 reg [7:0] users_done;
 reg  arr_fault;
 wire  a_s_awready, b_s_awready;
 wire  a_s_wready, b_s_wready;
 wire  a_s_bvalid, b_s_bvalid;
 wire [1:0] a_s_bresp, b_s_bresp;
 wire  a_s_arready, b_s_arready;
 wire  a_s_rvalid, b_s_rvalid;
 wire [31:0] a_s_rdata, b_s_rdata;
 wire [1:0] a_s_rresp, b_s_rresp;
 wire  a_m_arvalid, b_m_arvalid;
 wire [63:0] a_m_araddr, b_m_araddr;
 wire [7:0] a_m_arlen, b_m_arlen;
 wire [2:0] a_m_arsize, b_m_arsize;
 wire  a_m_rready, b_m_rready;
 wire  a_m_awvalid, b_m_awvalid;
 wire [63:0] a_m_awaddr, b_m_awaddr;
 wire [7:0] a_m_awlen, b_m_awlen;
 wire [2:0] a_m_awsize, b_m_awsize;
 wire  a_m_wvalid, b_m_wvalid;
 wire [63:0] a_m_wdata, b_m_wdata;
 wire [7:0] a_m_wstrb, b_m_wstrb;
 wire  a_m_wlast, b_m_wlast;
 wire  a_m_bready, b_m_bready;
 wire  a_irq, b_irq;
 wire  a_pb_we, b_pb_we;
 wire [SB+PLB-1:0] a_pb_waddr, b_pb_waddr;
 wire [NW-1:0] a_pb_wdata, b_pb_wdata;
 wire  a_pb_re, b_pb_re;
 wire [SB+PLB-1:0] a_pb_raddr, b_pb_raddr;
 wire  a_eng_start, b_eng_start;
 wire [NW-1:0] a_eng_token, b_eng_token;
 wire [NW-1:0] a_eng_pos, b_eng_pos;
 wire [SB-1:0] a_eng_slot, b_eng_slot;
 wire [AW-1:0] a_kv_base, b_kv_base;
 wire  a_eng_clr_req, b_eng_clr_req;
 wire  a_arr_rst_n, b_arr_rst_n;
 wire [7:0] a_cfg_users, b_cfg_users;
 wire [NW-1:0] a_cfg_prompt_len, b_cfg_prompt_len;
 wire [NW-1:0] a_cfg_gen_len, b_cfg_gen_len;
 wire  a_cq_commit_v, b_cq_commit_v;
 wire [15:0] a_cq_client_tag, b_cq_client_tag;
 wire [7:0] a_cq_slot, b_cq_slot;
 wire [17:0] a_cq_pos, b_cq_pos;
 wire [17:0] a_cq_token, b_cq_token;
 wire [1:0] a_cq_kind, b_cq_kind;
 wire [3:0] a_cq_status, b_cq_status;
 wire  a_step_issue_v, b_step_issue_v;
 wire [15:0] a_step_client_tag, b_step_client_tag;
 wire [7:0] a_step_slot, b_step_slot;
 wire [17:0] a_step_pos, b_step_pos;
 wire  a_step_retire_v, b_step_retire_v;
 wire  a_step_retire_cq, b_step_retire_cq;
 wire [15:0] a_step_retire_client_tag, b_step_retire_client_tag;
 wire [7:0] a_step_retire_slot, b_step_retire_slot;
 wire [17:0] a_step_retire_pos, b_step_retire_pos;
 wire [17:0] a_step_retire_token, b_step_retire_token;
 wire  a_host_idle, b_host_idle;
 wire  a_host_observer_fault, b_host_observer_fault;
 ot_host_if_pb2_observed #(.PB_READ_PIPE(PRP),.NSLOT(NSLOT),.MODE(0),.ENG_CTX(ENGC),.NW(NW),.PLB(PLB),.AW(AW),.FMT(FMT),.MU_OUT(0)) u_a(
  .s_awready(a_s_awready),
  .s_wready(a_s_wready),
  .s_bvalid(a_s_bvalid),
  .s_bresp(a_s_bresp),
  .s_arready(a_s_arready),
  .s_rvalid(a_s_rvalid),
  .s_rdata(a_s_rdata),
  .s_rresp(a_s_rresp),
  .m_arvalid(a_m_arvalid),
  .m_araddr(a_m_araddr),
  .m_arlen(a_m_arlen),
  .m_arsize(a_m_arsize),
  .m_rready(a_m_rready),
  .m_awvalid(a_m_awvalid),
  .m_awaddr(a_m_awaddr),
  .m_awlen(a_m_awlen),
  .m_awsize(a_m_awsize),
  .m_wvalid(a_m_wvalid),
  .m_wdata(a_m_wdata),
  .m_wstrb(a_m_wstrb),
  .m_wlast(a_m_wlast),
  .m_bready(a_m_bready),
  .irq(a_irq),
  .pb_we(a_pb_we),
  .pb_waddr(a_pb_waddr),
  .pb_wdata(a_pb_wdata),
  .pb_re(a_pb_re),
  .pb_raddr(a_pb_raddr),
  .eng_start(a_eng_start),
  .eng_token(a_eng_token),
  .eng_pos(a_eng_pos),
  .eng_slot(a_eng_slot),
  .kv_base(a_kv_base),
  .eng_clr_req(a_eng_clr_req),
  .arr_rst_n(a_arr_rst_n),
  .cfg_users(a_cfg_users),
  .cfg_prompt_len(a_cfg_prompt_len),
  .cfg_gen_len(a_cfg_gen_len),
  .cq_commit_v(a_cq_commit_v),
  .cq_client_tag(a_cq_client_tag),
  .cq_slot(a_cq_slot),
  .cq_pos(a_cq_pos),
  .cq_token(a_cq_token),
  .cq_kind(a_cq_kind),
  .cq_status(a_cq_status),
  .step_issue_v(a_step_issue_v),
  .step_client_tag(a_step_client_tag),
  .step_slot(a_step_slot),
  .step_pos(a_step_pos),
  .step_retire_v(a_step_retire_v),
  .step_retire_cq(a_step_retire_cq),
  .step_retire_client_tag(a_step_retire_client_tag),
  .step_retire_slot(a_step_retire_slot),
  .step_retire_pos(a_step_retire_pos),
  .step_retire_token(a_step_retire_token),
  .host_idle(a_host_idle),
  .host_observer_fault(a_host_observer_fault),
  .s_awvalid(s_awvalid),
  .s_awaddr(s_awaddr),
  .s_wvalid(s_wvalid),
  .s_wdata(s_wdata),
  .s_wstrb(s_wstrb),
  .s_bready(s_bready),
  .s_arvalid(s_arvalid),
  .s_araddr(s_araddr),
  .s_rready(s_rready),
  .m_arready(m_arready),
  .m_rvalid(m_rvalid),
  .m_rdata(m_rdata),
  .m_rresp(m_rresp),
  .m_rlast(m_rlast),
  .m_awready(m_awready),
  .m_wready(m_wready),
  .m_bvalid(m_bvalid),
  .m_bresp(m_bresp),
  .pb_q(pb_q),
  .eng_done(eng_done),
  .eng_next_token(eng_next_token),
  .eng_cycles(eng_cycles),
  .eng_fault(eng_fault),
  .eng_clr_ack(eng_clr_ack),
  .pr_re(pr_re),
  .pr_user(pr_user),
  .pr_pos(pr_pos),
  .tok_valid(tok_valid),
  .tok_user(tok_user),
  .tok_pos(tok_pos),
  .tok_id(tok_id),
  .users_done(users_done),
  .arr_fault(arr_fault),
  .clk(clk),
  .rst_n(rst_n));
 ot_host_if_pb2_observed_pd #(.PB_READ_PIPE(PRP),.NSLOT(NSLOT),.MODE(0),.ENG_CTX(ENGC),.NW(NW),.PLB(PLB),.AW(AW),.FMT(FMT),.MU_OUT(0)) u_b(
  .s_awready(b_s_awready),
  .s_wready(b_s_wready),
  .s_bvalid(b_s_bvalid),
  .s_bresp(b_s_bresp),
  .s_arready(b_s_arready),
  .s_rvalid(b_s_rvalid),
  .s_rdata(b_s_rdata),
  .s_rresp(b_s_rresp),
  .m_arvalid(b_m_arvalid),
  .m_araddr(b_m_araddr),
  .m_arlen(b_m_arlen),
  .m_arsize(b_m_arsize),
  .m_rready(b_m_rready),
  .m_awvalid(b_m_awvalid),
  .m_awaddr(b_m_awaddr),
  .m_awlen(b_m_awlen),
  .m_awsize(b_m_awsize),
  .m_wvalid(b_m_wvalid),
  .m_wdata(b_m_wdata),
  .m_wstrb(b_m_wstrb),
  .m_wlast(b_m_wlast),
  .m_bready(b_m_bready),
  .irq(b_irq),
  .pb_we(b_pb_we),
  .pb_waddr(b_pb_waddr),
  .pb_wdata(b_pb_wdata),
  .pb_re(b_pb_re),
  .pb_raddr(b_pb_raddr),
  .eng_start(b_eng_start),
  .eng_token(b_eng_token),
  .eng_pos(b_eng_pos),
  .eng_slot(b_eng_slot),
  .kv_base(b_kv_base),
  .eng_clr_req(b_eng_clr_req),
  .arr_rst_n(b_arr_rst_n),
  .cfg_users(b_cfg_users),
  .cfg_prompt_len(b_cfg_prompt_len),
  .cfg_gen_len(b_cfg_gen_len),
  .cq_commit_v(b_cq_commit_v),
  .cq_client_tag(b_cq_client_tag),
  .cq_slot(b_cq_slot),
  .cq_pos(b_cq_pos),
  .cq_token(b_cq_token),
  .cq_kind(b_cq_kind),
  .cq_status(b_cq_status),
  .step_issue_v(b_step_issue_v),
  .step_client_tag(b_step_client_tag),
  .step_slot(b_step_slot),
  .step_pos(b_step_pos),
  .step_retire_v(b_step_retire_v),
  .step_retire_cq(b_step_retire_cq),
  .step_retire_client_tag(b_step_retire_client_tag),
  .step_retire_slot(b_step_retire_slot),
  .step_retire_pos(b_step_retire_pos),
  .step_retire_token(b_step_retire_token),
  .host_idle(b_host_idle),
  .host_observer_fault(b_host_observer_fault),
  .s_awvalid(s_awvalid),
  .s_awaddr(s_awaddr),
  .s_wvalid(s_wvalid),
  .s_wdata(s_wdata),
  .s_wstrb(s_wstrb),
  .s_bready(s_bready),
  .s_arvalid(s_arvalid),
  .s_araddr(s_araddr),
  .s_rready(s_rready),
  .m_arready(m_arready),
  .m_rvalid(m_rvalid),
  .m_rdata(m_rdata),
  .m_rresp(m_rresp),
  .m_rlast(m_rlast),
  .m_awready(m_awready),
  .m_wready(m_wready),
  .m_bvalid(m_bvalid),
  .m_bresp(m_bresp),
  .pb_q(pb_q),
  .eng_done(eng_done),
  .eng_next_token(eng_next_token),
  .eng_cycles(eng_cycles),
  .eng_fault(eng_fault),
  .eng_clr_ack(eng_clr_ack),
  .pr_re(pr_re),
  .pr_user(pr_user),
  .pr_pos(pr_pos),
  .tok_valid(tok_valid),
  .tok_user(tok_user),
  .tok_pos(tok_pos),
  .tok_id(tok_id),
  .users_done(users_done),
  .arr_fault(arr_fault),
  .clk(clk),
  .rst_n(rst_n));
 wire [4095:0] va = {a_s_awready,a_s_wready,a_s_bvalid,a_s_bresp,a_s_arready,a_s_rvalid,a_s_rdata,a_s_rresp,a_m_arvalid,a_m_araddr,a_m_arlen,a_m_arsize,a_m_rready,a_m_awvalid,a_m_awaddr,a_m_awlen,a_m_awsize,a_m_wvalid,a_m_wdata,a_m_wstrb,a_m_wlast,a_m_bready,a_irq,a_pb_we,a_pb_waddr,a_pb_wdata,a_pb_re,a_pb_raddr,a_eng_start,a_eng_token,a_eng_pos,a_eng_slot,a_kv_base,a_eng_clr_req,a_arr_rst_n,a_cfg_users,a_cfg_prompt_len,a_cfg_gen_len,a_cq_commit_v,a_cq_client_tag,a_cq_slot,a_cq_pos,a_cq_token,a_cq_kind,a_cq_status,a_step_issue_v,a_step_client_tag,a_step_slot,a_step_pos,a_step_retire_v,a_step_retire_cq,a_step_retire_client_tag,a_step_retire_slot,a_step_retire_pos,a_step_retire_token,a_host_idle,a_host_observer_fault};
 wire [4095:0] vb = {b_s_awready,b_s_wready,b_s_bvalid,b_s_bresp,b_s_arready,b_s_rvalid,b_s_rdata,b_s_rresp,b_m_arvalid,b_m_araddr,b_m_arlen,b_m_arsize,b_m_rready,b_m_awvalid,b_m_awaddr,b_m_awlen,b_m_awsize,b_m_wvalid,b_m_wdata,b_m_wstrb,b_m_wlast,b_m_bready,b_irq,b_pb_we,b_pb_waddr,b_pb_wdata,b_pb_re,b_pb_raddr,b_eng_start,b_eng_token,b_eng_pos,b_eng_slot,b_kv_base,b_eng_clr_req,b_arr_rst_n,b_cfg_users,b_cfg_prompt_len,b_cfg_gen_len,b_cq_commit_v,b_cq_client_tag,b_cq_slot,b_cq_pos,b_cq_token,b_cq_kind,b_cq_status,b_step_issue_v,b_step_client_tag,b_step_slot,b_step_pos,b_step_retire_v,b_step_retire_cq,b_step_retire_client_tag,b_step_retire_slot,b_step_retire_pos,b_step_retire_token,b_host_idle,b_host_observer_fault};

 integer seed, i, mism, full_cyc, posts, logchg, r;
 initial begin
  seed = SEED; mism = 0; full_cyc = 0; posts = 0; logchg = 0; done = 0; ok = 0; rst_n = 0;
  s_awvalid=0; s_awaddr=0; s_wvalid=0; s_wdata=0; s_wstrb=0; s_bready=0; s_arvalid=0; s_araddr=0; s_rready=0;
  m_arready=0; m_rvalid=0; m_rdata=0; m_rresp=0; m_rlast=0; m_awready=0; m_wready=0; m_bvalid=0; m_bresp=0;
  pb_q=0; eng_done=0; eng_next_token=0; eng_cycles=0; eng_fault=0; eng_clr_ack=0; pr_re=0; pr_user=0; pr_pos=0;
  tok_valid=0; tok_user=0; tok_pos=0; tok_id=0; users_done=0; arr_fault=0;
  repeat (4) @(negedge clk); rst_n = 1;
  for (i = 0; i < CYC; i = i + 1) begin
   @(negedge clk);
   if (i == CYC / 2) begin rst_n = 0; @(negedge clk); rst_n = 1; end
   s_awvalid = ($random(seed) & 3) == 0; s_wvalid = s_awvalid ? (($random(seed) & 7) != 0) : (($random(seed) & 3) == 0);
   r = $random(seed) & 15;
   case (r)
    0, 1:  begin s_awaddr = 12'h00B << 2; s_wdata = $random(seed) & 3; end          // CQ_LOG 0..3
    2, 3, 4: begin s_awaddr = 12'h00C << 2; s_wdata = $random(seed); end            // CQ_HEAD doorbell
    5, 6:  begin s_awaddr = 12'h007 << 2; s_wdata = $random(seed); end              // SQ_TAIL
    7:     begin s_awaddr = 12'h002 << 2; s_wdata = (($random(seed) & 7) != 0); end // ENABLE (mostly on)
    8:     begin s_awaddr = 12'h006 << 2; s_wdata = $random(seed) & 3; end          // SQ_LOG
    default: begin s_awaddr = {($random(seed) % 24) & 10'h3ff, 2'b00}; s_wdata = $random(seed); end
   endcase
   s_wstrb = $random(seed); s_bready = $random(seed); s_rready = $random(seed);
   s_arvalid = ($random(seed) & 3) == 0; s_araddr = ((r & 1) ? 12'h022 : (($random(seed) % 40) & 12'h3f)) << 2;
   m_arready = $random(seed); m_rvalid = ($random(seed) & 1); m_rdata = {$random(seed), $random(seed)};
   m_rresp = (($random(seed) & 63) == 0) ? 2'b10 : 2'b00; m_rlast = 1'b1;
   m_awready = $random(seed); m_wready = $random(seed); m_bvalid = ($random(seed) & 1);
   m_bresp = (($random(seed) & 63) == 0) ? 2'b10 : 2'b00;
   pb_q = $random(seed); eng_done = ($random(seed) & 7) == 0; eng_next_token = $random(seed); eng_cycles = $random(seed);
   eng_fault = ($random(seed) & 255) == 0; eng_clr_ack = $random(seed); pr_re = $random(seed); pr_user = $random(seed);
   pr_pos = $random(seed); tok_valid = $random(seed); tok_user = $random(seed); tok_pos = $random(seed); tok_id = $random(seed);
   users_done = $random(seed); arr_fault = ($random(seed) & 255) == 0;
  end
  ok = (mism == 0) && (full_cyc > 1000) && (posts > 200) && (logchg > 100);
  $display("HKV_PB2_CQ NSLOT=%0d FMT=%0d cycles=%0d cqfull_cycles=%0d cq_posts=%0d cqlog_changes_pending=%0d mismatches=%0d %s",
           NSLOT, FMT, i, full_cyc, posts, logchg, mism, ok ? "ok" : "BAD");
  done = 1;
 end
 always @(posedge clk) if (rst_n) begin
  if (u_a.ev_n != 0 && !u_a.cq_room) full_cyc <= full_cyc + 1;
  if (u_a.d_st == 4'd11 && m_bvalid) posts <= posts + 1;
  if (u_a.ev_n != 0 && s_awvalid && s_wvalid && !a_s_bvalid && s_awaddr[11:2] == 10'h00B && s_wdata[3:0] != u_a.cq_log) logchg <= logchg + 1;
  if (va !== vb || u_a.c_cqfull !== u_b.c_cqfull || u_a.cq_room !== u_b.cq_room) begin
   mism <= mism + 1;
   if (mism < 5) $display("MISMATCH NSLOT=%0d t=%0t c_cqfull %h/%h cq_room %b/%b", NSLOT, $time, u_a.c_cqfull, u_b.c_cqfull, u_a.cq_room, u_b.cq_room);
  end
 end
endmodule

module tb_hkv_pb2_cq_equiv;
 reg clk = 0;
 always #1 clk = ~clk;
 wire d0, o0, d1, o1;
 hkv_pb2_pair #(.NSLOT(4), .FMT(1), .NW(18), .PRP(2), .ENGC(4), .SEED(11)) p0(.clk(clk), .done(d0), .ok(o0));
 hkv_pb2_pair #(.NSLOT(16), .FMT(0), .NW(16), .PRP(0), .ENGC(16), .SEED(29)) p1(.clk(clk), .done(d1), .ok(o1));
 initial begin
  wait (d0 && d1);
  if (o0 && o1) $display("HKV_PB2_CQ PASS"); else $display("HKV_PB2_CQ FAIL");
  $finish;
 end
endmodule
