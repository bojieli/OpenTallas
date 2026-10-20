`timescale 1ns/1ps
// External-interface component bench. No hierarchical force, deposit or setup.
module scheduler_descriptor_baseline;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,raw_por_n=0,warm_rst_n=0,pll_locked_i=0;
  reg health_bad_i=0,health_armed_i=0,health_cutoff_i=0;
  reg execution_restart_i=0,role_fault_i=0,owner_drained_i=0;
  wire[79:0] rc_identity;
  reg[79:0] model_health_identity=0;
  wire[79:0] health_identity_i=model_health_identity ^ ((case_id==7)?80'd1:80'd0);
  wire rc_bad,rc_armed,rc_retained_owned,rc_poison,rc_failure_pending,rc_report_once;
  wire[17:0]rc_mirror_pos,rc_mirror_tok,rc_mirror_ngen;
  wire[1:0]rc_mirror_state;
  wire rc_word0_offer,rc_response_confirmed;
  reg s_awvalid=0,s_wvalid=0,s_bready=1,s_arvalid=0,s_rready=1;
  reg[11:0]s_awaddr=0,s_araddr=0; reg[31:0]s_wdata=0;reg[3:0]s_wstrb=15;
  wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;wire[31:0]s_rdata;wire[1:0]s_bresp,s_rresp;
  wire m_arvalid,m_rready,m_awvalid,m_wvalid,m_bready,m_wlast;
  wire[63:0]m_araddr,m_awaddr,m_wdata;wire[7:0]m_arlen,m_awlen,m_wstrb;wire[2:0]m_arsize,m_awsize;
  reg m_arready=1,m_rvalid=0,m_rlast=1,m_awready=1,m_wready=1,m_bvalid=0;
  reg[63:0]m_rdata=0;reg[1:0]m_rresp=0,m_bresp=0;
  wire irq,pb_we,pb_re;wire[13:0]pb_waddr,pb_raddr;wire[17:0]pb_wdata;reg[17:0]pb_q=0;
  wire eng_start,eng_slot,eng_clr_req;wire[17:0]eng_token,eng_pos;wire[23:0]kv_base;
  reg eng_done=0,eng_fault=0,eng_clr_ack=0;reg[17:0]eng_next_token=0;reg[31:0]eng_cycles=3;
  wire arr_rst_n;wire[7:0]cfg_users;wire[17:0]cfg_prompt_len,cfg_gen_len;
  wire cq_commit_v;wire[15:0]cq_client_tag;wire[7:0]cq_slot;wire[17:0]cq_pos,cq_token;wire[1:0]cq_kind;wire[3:0]cq_status;
  wire step_issue_v,step_retire_v,step_retire_cq;wire[15:0]step_client_tag,step_retire_client_tag;
  wire[7:0]step_slot,step_retire_slot;wire[17:0]step_pos,step_retire_pos,step_retire_token;wire host_idle,host_observer_fault;
  ot_host_if_pb2_observed_rc #(.ENABLE_RETAINED_COMMIT(1),.HEALTH_CUTOFF_EDGES(12),.STEP_RESPONSE_DEADLINE_EDGES(8),.COMPONENT_FIXTURE(1),
    .NSLOT(1),.ENG_CTX(1),.MODE(0),.MU_OUT(0),.NW(18),.PLB(13),.CTX_MAX(8192),.FMT(1)) dut (
    .clk(clk),.rst_n(rst_n),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),
    .health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.health_identity_i(health_identity_i),.health_cutoff_i(health_cutoff_i),
    .execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.owner_drained_i(owner_drained_i),
    .rc_bad(rc_bad),.rc_armed(rc_armed),.rc_retained_owned(rc_retained_owned),.rc_poison(rc_poison),.rc_failure_pending(rc_failure_pending),.rc_report_once(rc_report_once),
    .rc_mirror_pos(rc_mirror_pos),.rc_mirror_tok(rc_mirror_tok),.rc_mirror_ngen(rc_mirror_ngen),.rc_mirror_state(rc_mirror_state),.rc_identity(rc_identity),.rc_word0_offer(rc_word0_offer),.rc_response_confirmed(rc_response_confirmed),
    .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),
    .s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),
    .m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
    .m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),
    .irq(irq),.pb_we(pb_we),.pb_waddr(pb_waddr),.pb_wdata(pb_wdata),.pb_re(pb_re),.pb_raddr(pb_raddr),.pb_q(pb_q),
    .eng_start(eng_start),.eng_token(eng_token),.eng_pos(eng_pos),.eng_slot(eng_slot),.kv_base(kv_base),.eng_done(eng_done),.eng_next_token(eng_next_token),.eng_cycles(eng_cycles),.eng_fault(eng_fault),.eng_clr_req(eng_clr_req),.eng_clr_ack(eng_clr_ack),
    .arr_rst_n(arr_rst_n),.cfg_users(cfg_users),.cfg_prompt_len(cfg_prompt_len),.cfg_gen_len(cfg_gen_len),.pr_re(1'b0),.pr_user(8'd0),.pr_pos(18'd0),.tok_valid(1'b0),.tok_user(8'd0),.tok_pos(18'd0),.tok_id(18'd0),.users_done(8'd0),.arr_fault(1'b0),
    .cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cq_kind(cq_kind),.cq_status(cq_status),
    .step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),.host_idle(host_idle),.host_observer_fault(host_observer_fault));
  scheduler_baseline #(.ENABLE_RETAINED_COMMIT(1),.HEALTH_CUTOFF_EDGES(12),.STEP_RESPONSE_DEADLINE_EDGES(8),.COMPONENT_FIXTURE(1),
    .NSLOT(1),.ENG_CTX(1),.MODE(0),.MU_OUT(0),.NW(18),.PLB(13),.CTX_MAX(8192),.FMT(1)) refdut (
    .clk(clk),.rst_n(rst_n),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),
    .health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.health_identity_i(health_identity_i),.health_cutoff_i(health_cutoff_i),
    .execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.owner_drained_i(owner_drained_i),
    .rc_bad(),.rc_armed(),.rc_retained_owned(),.rc_poison(),.rc_failure_pending(),.rc_report_once(),
    .rc_mirror_pos(),.rc_mirror_tok(),.rc_mirror_ngen(),.rc_mirror_state(),.rc_identity(),.rc_word0_offer(),.rc_response_confirmed(),
    .s_awvalid(s_awvalid),.s_awready(),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(),.s_bready(s_bready),.s_bresp(),
    .s_arvalid(s_arvalid),.s_arready(),.s_araddr(s_araddr),.s_rvalid(),.s_rready(s_rready),.s_rdata(),.s_rresp(),
    .m_arvalid(),.m_arready(m_arready),.m_araddr(),.m_arlen(),.m_arsize(),.m_rvalid(m_rvalid),.m_rready(),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
    .m_awvalid(),.m_awready(m_awready),.m_awaddr(),.m_awlen(),.m_awsize(),.m_wvalid(),.m_wready(m_wready),.m_wdata(),.m_wstrb(),.m_wlast(),.m_bvalid(m_bvalid),.m_bready(),.m_bresp(m_bresp),
    .irq(),.pb_we(),.pb_waddr(),.pb_wdata(),.pb_re(),.pb_raddr(),.pb_q(pb_q),
    .eng_start(),.eng_token(),.eng_pos(),.eng_slot(),.kv_base(),.eng_done(eng_done),.eng_next_token(eng_next_token),.eng_cycles(eng_cycles),.eng_fault(eng_fault),.eng_clr_req(),.eng_clr_ack(eng_clr_ack),
    .arr_rst_n(),.cfg_users(),.cfg_prompt_len(),.cfg_gen_len(),.pr_re(1'b0),.pr_user(8'd0),.pr_pos(18'd0),.tok_valid(1'b0),.tok_user(8'd0),.tok_pos(18'd0),.tok_id(18'd0),.users_done(8'd0),.arr_fault(1'b0),
    .cq_commit_v(),.cq_client_tag(),.cq_slot(),.cq_pos(),.cq_token(),.cq_kind(),.cq_status(),
    .step_issue_v(),.step_client_tag(),.step_slot(),.step_pos(),.step_retire_v(),.step_retire_cq(),.step_retire_client_tag(),.step_retire_slot(),.step_retire_pos(),.step_retire_token(),.host_idle(),.host_observer_fault());
  integer compared_edges=0;
  always @(negedge clk) begin
    compared_edges=compared_edges+1;
    if (dut.rc_bad !== refdut.rc_bad) $fatal(1,"DEFAULT_MISMATCH rc_bad edge=%0d",edge_n);
    if (dut.rc_armed !== refdut.rc_armed) $fatal(1,"DEFAULT_MISMATCH rc_armed edge=%0d",edge_n);
    if (dut.rc_retained_owned !== refdut.rc_retained_owned) $fatal(1,"DEFAULT_MISMATCH rc_retained_owned edge=%0d",edge_n);
    if (dut.rc_poison !== refdut.rc_poison) $fatal(1,"DEFAULT_MISMATCH rc_poison edge=%0d",edge_n);
    if (dut.rc_failure_pending !== refdut.rc_failure_pending) $fatal(1,"DEFAULT_MISMATCH rc_failure_pending edge=%0d",edge_n);
    if (dut.rc_report_once !== refdut.rc_report_once) $fatal(1,"DEFAULT_MISMATCH rc_report_once edge=%0d",edge_n);
    if (dut.rc_mirror_pos !== refdut.rc_mirror_pos) $fatal(1,"DEFAULT_MISMATCH rc_mirror_pos edge=%0d",edge_n);
    if (dut.rc_mirror_tok !== refdut.rc_mirror_tok) $fatal(1,"DEFAULT_MISMATCH rc_mirror_tok edge=%0d",edge_n);
    if (dut.rc_mirror_ngen !== refdut.rc_mirror_ngen) $fatal(1,"DEFAULT_MISMATCH rc_mirror_ngen edge=%0d",edge_n);
    if (dut.rc_mirror_state !== refdut.rc_mirror_state) $fatal(1,"DEFAULT_MISMATCH rc_mirror_state edge=%0d",edge_n);
    if (dut.rc_identity !== refdut.rc_identity) $fatal(1,"DEFAULT_MISMATCH rc_identity edge=%0d",edge_n);
    if (dut.rc_word0_offer !== refdut.rc_word0_offer) $fatal(1,"DEFAULT_MISMATCH rc_word0_offer edge=%0d",edge_n);
    if (dut.rc_response_confirmed !== refdut.rc_response_confirmed) $fatal(1,"DEFAULT_MISMATCH rc_response_confirmed edge=%0d",edge_n);
    if (dut.s_awready !== refdut.s_awready) $fatal(1,"DEFAULT_MISMATCH s_awready edge=%0d",edge_n);
    if (dut.s_wready !== refdut.s_wready) $fatal(1,"DEFAULT_MISMATCH s_wready edge=%0d",edge_n);
    if (dut.s_bvalid !== refdut.s_bvalid) $fatal(1,"DEFAULT_MISMATCH s_bvalid edge=%0d",edge_n);
    if (dut.s_bresp !== refdut.s_bresp) $fatal(1,"DEFAULT_MISMATCH s_bresp edge=%0d",edge_n);
    if (dut.s_arready !== refdut.s_arready) $fatal(1,"DEFAULT_MISMATCH s_arready edge=%0d",edge_n);
    if (dut.s_rvalid !== refdut.s_rvalid) $fatal(1,"DEFAULT_MISMATCH s_rvalid edge=%0d",edge_n);
    if (dut.s_rdata !== refdut.s_rdata) $fatal(1,"DEFAULT_MISMATCH s_rdata edge=%0d",edge_n);
    if (dut.s_rresp !== refdut.s_rresp) $fatal(1,"DEFAULT_MISMATCH s_rresp edge=%0d",edge_n);
    if (dut.m_arvalid !== refdut.m_arvalid) $fatal(1,"DEFAULT_MISMATCH m_arvalid edge=%0d",edge_n);
    if (dut.m_araddr !== refdut.m_araddr) $fatal(1,"DEFAULT_MISMATCH m_araddr edge=%0d",edge_n);
    if (dut.m_arlen !== refdut.m_arlen) $fatal(1,"DEFAULT_MISMATCH m_arlen edge=%0d",edge_n);
    if (dut.m_arsize !== refdut.m_arsize) $fatal(1,"DEFAULT_MISMATCH m_arsize edge=%0d",edge_n);
    if (dut.m_rready !== refdut.m_rready) $fatal(1,"DEFAULT_MISMATCH m_rready edge=%0d",edge_n);
    if (dut.m_awvalid !== refdut.m_awvalid) $fatal(1,"DEFAULT_MISMATCH m_awvalid edge=%0d",edge_n);
    if (dut.m_awaddr !== refdut.m_awaddr) $fatal(1,"DEFAULT_MISMATCH m_awaddr edge=%0d",edge_n);
    if (dut.m_awlen !== refdut.m_awlen) $fatal(1,"DEFAULT_MISMATCH m_awlen edge=%0d",edge_n);
    if (dut.m_awsize !== refdut.m_awsize) $fatal(1,"DEFAULT_MISMATCH m_awsize edge=%0d",edge_n);
    if (dut.m_wvalid !== refdut.m_wvalid) $fatal(1,"DEFAULT_MISMATCH m_wvalid edge=%0d",edge_n);
    if (dut.m_wdata !== refdut.m_wdata) $fatal(1,"DEFAULT_MISMATCH m_wdata edge=%0d",edge_n);
    if (dut.m_wstrb !== refdut.m_wstrb) $fatal(1,"DEFAULT_MISMATCH m_wstrb edge=%0d",edge_n);
    if (dut.m_wlast !== refdut.m_wlast) $fatal(1,"DEFAULT_MISMATCH m_wlast edge=%0d",edge_n);
    if (dut.m_bready !== refdut.m_bready) $fatal(1,"DEFAULT_MISMATCH m_bready edge=%0d",edge_n);
    if (dut.irq !== refdut.irq) $fatal(1,"DEFAULT_MISMATCH irq edge=%0d",edge_n);
    if (dut.pb_we !== refdut.pb_we) $fatal(1,"DEFAULT_MISMATCH pb_we edge=%0d",edge_n);
    if (dut.pb_waddr !== refdut.pb_waddr) $fatal(1,"DEFAULT_MISMATCH pb_waddr edge=%0d",edge_n);
    if (dut.pb_wdata !== refdut.pb_wdata) $fatal(1,"DEFAULT_MISMATCH pb_wdata edge=%0d",edge_n);
    if (dut.pb_re !== refdut.pb_re) $fatal(1,"DEFAULT_MISMATCH pb_re edge=%0d",edge_n);
    if (dut.pb_raddr !== refdut.pb_raddr) $fatal(1,"DEFAULT_MISMATCH pb_raddr edge=%0d",edge_n);
    if (dut.eng_start !== refdut.eng_start) $fatal(1,"DEFAULT_MISMATCH eng_start edge=%0d",edge_n);
    if (dut.eng_token !== refdut.eng_token) $fatal(1,"DEFAULT_MISMATCH eng_token edge=%0d",edge_n);
    if (dut.eng_pos !== refdut.eng_pos) $fatal(1,"DEFAULT_MISMATCH eng_pos edge=%0d",edge_n);
    if (dut.eng_slot !== refdut.eng_slot) $fatal(1,"DEFAULT_MISMATCH eng_slot edge=%0d",edge_n);
    if (dut.kv_base !== refdut.kv_base) $fatal(1,"DEFAULT_MISMATCH kv_base edge=%0d",edge_n);
    if (dut.eng_clr_req !== refdut.eng_clr_req) $fatal(1,"DEFAULT_MISMATCH eng_clr_req edge=%0d",edge_n);
    if (dut.arr_rst_n !== refdut.arr_rst_n) $fatal(1,"DEFAULT_MISMATCH arr_rst_n edge=%0d",edge_n);
    if (dut.cfg_users !== refdut.cfg_users) $fatal(1,"DEFAULT_MISMATCH cfg_users edge=%0d",edge_n);
    if (dut.cfg_prompt_len !== refdut.cfg_prompt_len) $fatal(1,"DEFAULT_MISMATCH cfg_prompt_len edge=%0d",edge_n);
    if (dut.cfg_gen_len !== refdut.cfg_gen_len) $fatal(1,"DEFAULT_MISMATCH cfg_gen_len edge=%0d",edge_n);
    if (dut.cq_commit_v !== refdut.cq_commit_v) $fatal(1,"DEFAULT_MISMATCH cq_commit_v edge=%0d",edge_n);
    if (dut.cq_client_tag !== refdut.cq_client_tag) $fatal(1,"DEFAULT_MISMATCH cq_client_tag edge=%0d",edge_n);
    if (dut.cq_slot !== refdut.cq_slot) $fatal(1,"DEFAULT_MISMATCH cq_slot edge=%0d",edge_n);
    if (dut.cq_pos !== refdut.cq_pos) $fatal(1,"DEFAULT_MISMATCH cq_pos edge=%0d",edge_n);
    if (dut.cq_token !== refdut.cq_token) $fatal(1,"DEFAULT_MISMATCH cq_token edge=%0d",edge_n);
    if (dut.cq_kind !== refdut.cq_kind) $fatal(1,"DEFAULT_MISMATCH cq_kind edge=%0d",edge_n);
    if (dut.cq_status !== refdut.cq_status) $fatal(1,"DEFAULT_MISMATCH cq_status edge=%0d",edge_n);
    if (dut.step_issue_v !== refdut.step_issue_v) $fatal(1,"DEFAULT_MISMATCH step_issue_v edge=%0d",edge_n);
    if (dut.step_client_tag !== refdut.step_client_tag) $fatal(1,"DEFAULT_MISMATCH step_client_tag edge=%0d",edge_n);
    if (dut.step_slot !== refdut.step_slot) $fatal(1,"DEFAULT_MISMATCH step_slot edge=%0d",edge_n);
    if (dut.step_pos !== refdut.step_pos) $fatal(1,"DEFAULT_MISMATCH step_pos edge=%0d",edge_n);
    if (dut.step_retire_v !== refdut.step_retire_v) $fatal(1,"DEFAULT_MISMATCH step_retire_v edge=%0d",edge_n);
    if (dut.step_retire_cq !== refdut.step_retire_cq) $fatal(1,"DEFAULT_MISMATCH step_retire_cq edge=%0d",edge_n);
    if (dut.step_retire_client_tag !== refdut.step_retire_client_tag) $fatal(1,"DEFAULT_MISMATCH step_retire_client_tag edge=%0d",edge_n);
    if (dut.step_retire_slot !== refdut.step_retire_slot) $fatal(1,"DEFAULT_MISMATCH step_retire_slot edge=%0d",edge_n);
    if (dut.step_retire_pos !== refdut.step_retire_pos) $fatal(1,"DEFAULT_MISMATCH step_retire_pos edge=%0d",edge_n);
    if (dut.step_retire_token !== refdut.step_retire_token) $fatal(1,"DEFAULT_MISMATCH step_retire_token edge=%0d",edge_n);
    if (dut.host_idle !== refdut.host_idle) $fatal(1,"DEFAULT_MISMATCH host_idle edge=%0d",edge_n);
    if (dut.host_observer_fault !== refdut.host_observer_fault) $fatal(1,"DEFAULT_MISMATCH host_observer_fault edge=%0d",edge_n);
  end

  reg[17:0]pbmem[0:16383];
  integer retires=0;
  integer edge_n=0,issues=0,raw_dones=0,commits=0,writes=0,engine_wait=0,health_age=0;
  reg read_pending=0,aw_seen=0,w_seen=0; reg[63:0]read_addr,write_addr,write_data;
  reg stalled_aw=0,stalled_w=0;reg[63:0]held_aw,held_w;reg[7:0]held_strb;
  integer peak_events=0;
  integer case_id=0;integer max_tokens=1;integer prompt_len=1;integer engine_delay=3;
  reg engine_enable=1,auto_cutoff=1,word0_fault_injected=0;reg[31:0]read_tokens,read_reqs;reg[63:0]last_word1=0;
  reg[63:0]last_word0=0;reg[15:0]last_commit_tag=0;
  function automatic[63:0] memread(input[63:0]a);
    case(a)
      64'h1000,64'h1020:memread=(64'(max_tokens)<<48)|(64'(prompt_len)<<32)|((64'h1234+64'(a[5]))<<16)|64'h101;
      64'h1008,64'h1028:memread=64'h3000;
      64'h1010,64'h1030:memread=0;
      64'h1018,64'h1038:memread=64'h0003ffff0003ffff;
      default:memread=64'h0000002b0000002a;
    endcase
  endfunction
  // Real synchronous external prompt RAM and independent engine/DMA responder.
  always @(posedge clk) begin
    edge_n<=edge_n+1;
    if(dut.ev_n>peak_events)peak_events<=dut.ev_n; // read-only capacity observation; never setup/force
    if(edge_n>2000)$fatal(1,"SCHED_TIMEOUT case=%0d issues=%0d writes=%0d bad=%0b armed=%0b",case_id,issues,writes,rc_bad,rc_armed);
    if(pb_we)pbmem[pb_waddr]<=pb_wdata;
    if(pb_re)pb_q<=pbmem[pb_raddr];
    eng_clr_ack<=eng_clr_req;
    m_rvalid<=read_pending;
    if(read_pending)m_rdata<=memread(read_addr);
    read_pending<=m_arvalid&&m_arready;
    if(m_arvalid&&m_arready)read_addr<=m_araddr;
    m_bvalid<=0;
    if(m_awvalid&&m_awready)begin aw_seen<=1;write_addr<=m_awaddr;end
    if(m_wvalid&&m_wready)begin w_seen<=1;write_data<=m_wdata;end
    if(aw_seen&&w_seen&&!m_bvalid)begin
      m_bvalid<=1;m_bresp<=((case_id==12&&write_addr[3:0]==8)||(case_id==13&&write_addr[3:0]==0)||(case_id==25&&write_addr==64'h4000))?2'b10:2'b00;aw_seen<=0;w_seen<=0;writes<=writes+1;
      if(write_addr>=64'h2000&&write_addr<64'h2080&&write_addr[3:0]==8)last_word1<=write_data;
      if(write_addr>=64'h2000&&write_addr<64'h2080&&write_addr[3:0]==0)begin last_word0<=write_data;
        if(word0_fault_injected&&(write_data[7:4]!=7||write_data[2:1]!=3))$fatal(1,"SCHED_WORD0_FAULT data=%h",write_data);
        $display("WORD0 edge=%0d data=%h",edge_n,write_data);end
    end
    if(stalled_aw&&(!m_awvalid||m_awaddr!==held_aw))$fatal(1,"SCHED_AW_STABILITY");
    if(stalled_w&&(!m_wvalid||m_wdata!==held_w||m_wstrb!==held_strb))$fatal(1,"SCHED_W_STABILITY");
    stalled_aw<=m_awvalid&&!m_awready;held_aw<=m_awaddr;
    stalled_w<=m_wvalid&&!m_wready;held_w<=m_wdata;held_strb<=m_wstrb;
    if(case_id==3&&issues==1&&health_age>0&&health_age<12&&(rc_mirror_pos!=0||rc_mirror_ngen!=0))$fatal(1,"SCHED_PROMPT_EARLY_COMMIT");
    if(health_age==1&&rc_identity!==model_health_identity)$fatal(1,"SCHED_IDENTITY_PRODUCER");
    eng_done<=0;
    if(eng_start)begin
      issues<=issues+1;
      model_health_identity<={59'(16'h1234+((case_id==6)?issues:0)),2'((case_id==6)?issues+1:1),1'b0,eng_pos};
      if(eng_pos!==18'((case_id==6)?0:issues)||eng_token!==18'((case_id==6)?42:42+issues))$fatal(1,"SCHED_ENGINE_INPUT pos=%0d tok=%0d issue=%0d",eng_pos,eng_token,issues);
      engine_wait<=engine_delay;eng_next_token<=18'((case_id==6)?43:43+issues);
      $display("ISSUE edge=%0d pos=%0d identity=%h",edge_n,eng_pos,rc_identity);
    end else if(engine_wait>0&&engine_enable)begin
      engine_wait<=engine_wait-1;
      if(engine_wait==1)begin eng_done<=1;raw_dones<=raw_dones+1;end
    end
    if(step_retire_v)retires<=retires+1;
    if(cq_commit_v)begin last_commit_tag<=cq_client_tag;commits<=commits+1;$display("COMMIT edge=%0d status=%0d pos=%0d token=%0d",edge_n,cq_status,cq_pos,cq_token);end
    if(eng_start)begin health_age<=1;health_cutoff_i<=0;end
    else if(health_age>0)begin
      health_age<=health_age+1;
      // Conditional health arrival precedes the fixed H=12 evaluation edge.
      if(auto_cutoff&&health_age>=10)health_cutoff_i<=1;
    end

  end
  task automatic tick(input integer n);repeat(n)@(negedge clk);endtask
  task automatic csr(input[11:0]a,input[31:0]d);
    @(negedge clk);s_awaddr=a;s_wdata=d;s_awvalid=1;s_wvalid=1;
    do @(posedge clk);while(!(s_awready&&s_wready));
    @(negedge clk);s_awvalid=0;s_wvalid=0;
    while(!s_bvalid)@(negedge clk);tick(1);
  endtask
  task automatic csr_read(input[11:0]a,output[31:0]value);
    @(negedge clk);s_araddr=a;s_arvalid=1;
    do @(posedge clk);while(!s_arready);
    @(negedge clk);s_arvalid=0;while(!s_rvalid)@(negedge clk);
    value=s_rdata;tick(1);
  endtask
  task automatic setup_request;
    if(case_id==14||case_id==25)begin csr('h040,'h4000);csr('h048,'hdeadbeef);csr('h03c,1);csr('h04c,1);end
    csr('h010,'h1000);csr('h018,3);csr('h024,'h2000);csr('h02c,3);csr('h008,1);csr('h01c,1);
  endtask
  task automatic await_issue;while(issues==0)tick(1);endtask
  initial begin
    if(!$value$plusargs("CASE=%d",case_id))case_id=0;
    tick(4);raw_por_n=1;warm_rst_n=1;pll_locked_i=1;rst_n=1;health_armed_i=1;tick(4);
    if(case_id==1||case_id==3||case_id==8||(case_id>=16&&case_id<=18))prompt_len=2;
    if(case_id==21)max_tokens=40;
    if(case_id==2||case_id==3||case_id==21)begin m_awready=0;m_wready=0;end
    if(case_id==10)m_wready=0;
    if(case_id==11)m_awready=0;
    if(case_id==5||case_id==15)engine_enable=0;
    setup_request();await_issue();
    case(case_id)
      0:begin while(commits==0)tick(1);if(rc_mirror_pos!=1||rc_mirror_tok!=43||rc_mirror_ngen!=1||!rc_response_confirmed||rc_bad||last_word0!==64'h002b000012340025||last_word1!==64'h0000000100000003)$fatal(1,"SCHED_HEALTHY");end
      1:begin health_bad_i=1;tick(1);health_bad_i=0;tick(40);if(!rc_bad||issues!=1||raw_dones!=1||retires!=1||rc_mirror_pos!=0||rc_mirror_ngen!=0)$fatal(1,"SCHED_RAWDONE_CLEANUP");end
      2,10,11:begin
        while(!m_awvalid&&!m_wvalid)tick(1);tick(2);
        warm_rst_n=0;tick(3);warm_rst_n=1;
        if(!rc_bad||!rc_retained_owned)$fatal(1,"SCHED_RETAIN_WARM");
        tick(4);m_awready=1;m_wready=1;tick(30);
      end
      3:begin
        // Cutoff fixture must finish independently from CQ/DMA readiness.
        while(health_age<12)tick(1);
        if(!rc_armed||writes!=0||rc_mirror_pos!=1||rc_mirror_tok!=43||rc_mirror_ngen!=0)$fatal(1,"SCHED_CUTOFF_NO_DMA");
        m_awready=1;m_wready=1;while(commits==0)tick(1);
      end
      4:begin
        // Fault arrives on the very edge where CQ word zero is first offered.
        while(!rc_word0_offer)tick(1);word0_fault_injected=1;health_bad_i=1;tick(1);health_bad_i=0;tick(30);
        if(!rc_bad||rc_mirror_pos!=0||rc_mirror_ngen!=0||last_word0[7:4]!=7||last_word0[2:1]!=3)$fatal(1,"SCHED_WORD0_FAULT data=%h",last_word0);
      end
      5:begin
        tick(8);if(!rc_bad)$fatal(1,"SCHED_DEADLINE");
        engine_enable=1;tick(30);if(raw_dones!=1||issues!=1||retires!=1)$fatal(1,"SCHED_LATE_DONE_CLEANUP");
      end
      6:begin
        while(commits==0)tick(1);owner_drained_i=1;tick(8);owner_drained_i=0;
        csr('h01c,2);while(commits<2)tick(1);
        if(rc_bad||issues!=2||last_commit_tag!='h1235)$fatal(1,"SCHED_OWNER_REUSE");
      end
      7:begin tick(14);if(!rc_bad)$fatal(1,"SCHED_IDENTITY_REFUSAL");end
      8:begin while(commits==0)tick(1);if(rc_bad||issues!=2||last_word0[47:32]!=1)$fatal(1,"SCHED_PROMPT_CERTIFY");end
      9:begin
        while(!rc_word0_offer)tick(1);m_awready=0;m_wready=0;tick(1);
        if(rc_mirror_pos!=1||rc_mirror_tok!=43||rc_mirror_ngen!=1||rc_mirror_state!=2)$fatal(1,"SCHED_MIRROR_OFFER");
        warm_rst_n=0;tick(3);warm_rst_n=1;tick(3);
        if(!rc_bad||rc_mirror_pos!=1||rc_mirror_tok!=43||rc_mirror_ngen!=1||!m_awvalid||!m_wvalid)$fatal(1,"SCHED_MIRROR_RETAIN");
        m_awready=1;m_wready=1;tick(20);
      end
      12,13:begin while(!rc_bad)tick(1);tick(25);if(!rc_poison)$fatal(1,"SCHED_BRESP_POISON");end
      14:begin while(writes<3)tick(1);tick(4);if(rc_bad||commits!=1)$fatal(1,"SCHED_MSI_FLOW");end
      15:begin tick(2);raw_por_n=0;tick(2);if(rc_retained_owned||rc_bad||rc_poison||rc_mirror_pos!=0)$fatal(1,"SCHED_RAWPOR_CLEAR");raw_por_n=1;tick(3);end
      16,17,18:begin
        while(health_age<(case_id-6))tick(1);health_bad_i=1;tick(1);health_bad_i=0;tick(30);
        if(!rc_bad||((case_id<18)&&rc_mirror_pos!=0)||((case_id==18)&&rc_mirror_pos!=1))$fatal(1,"SCHED_H_BOUNDARY");
      end
      19:begin
        while(!(aw_seen&&w_seen))tick(1);health_bad_i=1;tick(1);health_bad_i=0;tick(30);
        if(!rc_bad||rc_mirror_pos!=0)$fatal(1,"SCHED_PRE_WORD0");
      end
      20:begin
        while(!rc_word0_offer)tick(1);tick(1);health_bad_i=1;tick(1);health_bad_i=0;tick(30);
        if(!rc_bad||rc_mirror_pos!=1||rc_mirror_ngen!=1)$fatal(1,"SCHED_POST_WORD0");
      end
      21:begin
        // Legal traffic only. Capacity is observed, never forced to a desired count.
        tick(400);$display("QUEUE_OBSERVED peak=%0d issues=%0d current=%0d",peak_events,issues,dut.ev_n);
        if(peak_events<2||writes!=0)$fatal(1,"SCHED_QUEUE_NOT_EXERCISED");
        health_bad_i=1;tick(1);health_bad_i=0;word0_fault_injected=1;
        m_awready=1;m_wready=1;tick(100);
        if(!rc_bad||!rc_retained_owned||commits!=1||!rc_report_once)$fatal(1,"SCHED_QUEUE_FAILSTOP");
      end
      22,23,24:begin
        if(case_id==22)pll_locked_i=0;
        if(case_id==23)execution_restart_i=1;
        if(case_id==24)role_fault_i=1;
        tick(2);pll_locked_i=1;execution_restart_i=0;role_fault_i=0;tick(30);
        if(!rc_bad||!rc_poison||!rc_retained_owned||rc_mirror_pos!=0)$fatal(1,"SCHED_OBSERVED_CAUSE");
      end
      25:begin
        while(!rc_bad)tick(1);tick(25);
        if(!rc_poison||rc_mirror_pos!=1||rc_mirror_ngen!=1)$fatal(1,"SCHED_MSI_BRESP");
      end
      default:$fatal(1,"SCHED_UNKNOWN_CASE");
    endcase
    csr_read('h070,read_tokens);csr_read('h078,read_reqs);
    if((case_id==0||case_id==25)&&(read_tokens!=1||read_reqs!=1))$fatal(1,"SCHED_HEALTHY_COUNTERS");
    if((case_id==1||case_id==2||case_id==4||case_id==5||case_id==7||case_id==10||case_id==11||case_id==12||case_id==13||case_id==22||case_id==23||case_id==24)&&(read_tokens!=0||read_reqs!=0))$fatal(1,"SCHED_FAULT_COUNTERS tokens=%0d requests=%0d",read_tokens,read_reqs);
    $display("DEFAULT_SCHED_PASS outputs=70 case=%0d edges=%0d issues=%0d rawdone=%0d commits=%0d writes=%0d",case_id,edge_n,issues,raw_dones,commits,writes);$finish;
  end
endmodule
