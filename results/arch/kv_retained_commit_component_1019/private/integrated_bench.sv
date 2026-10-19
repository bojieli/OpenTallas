`timescale 1ns/1ps
// External-interface component bench. No hierarchical force, deposit or setup.
module integrated_bench;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,raw_por_n=0,warm_rst_n=0,pll_locked_i=0;
  reg health_bad_i=0,health_armed_i=0,health_cutoff_i=0;
  reg execution_restart_i=0,role_fault_i=0,owner_drained_i=0;
  wire[79:0] rc_identity;
  reg[79:0] model_health_identity=0;
  wire[79:0] health_identity_i={43'd0,16'h1234,2'd1,1'b0,18'd0};
  wire rc_bad,rc_armed,rc_retained_owned,rc_poison,rc_failure_pending,rc_report_once;
  wire[17:0]rc_mirror_pos,rc_mirror_tok,rc_mirror_ngen;
  wire[1:0]rc_mirror_state;
  wire rc_word0_offer,rc_response_confirmed;
  wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready;
  wire[12:0]s_awaddr,s_araddr;wire[31:0]s_wdata;wire[3:0]s_wstrb;
  wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;wire[31:0]s_rdata;wire[1:0]s_bresp,s_rresp;
  wire m_arvalid,m_rready,m_awvalid,m_wvalid,m_bready,m_wlast;
  wire[63:0]m_araddr,m_awaddr,m_wdata;wire[7:0]m_arlen,m_awlen,m_wstrb;wire[2:0]m_arsize,m_awsize;
  wire m_arready,m_rvalid,m_rlast,m_awready,m_wready,m_bvalid;
  wire[63:0]m_rdata;wire[1:0]m_rresp,m_bresp;
  wire irq,pb_we,pb_re;wire[13:0]pb_waddr,pb_raddr;wire[17:0]pb_wdata;reg[17:0]pb_q=0;
  wire eng_start,eng_slot,eng_clr_req;wire[17:0]eng_token,eng_pos;wire[23:0]kv_base;
  wire eng_done,eng_fault;reg eng_clr_ack=0;wire[17:0]eng_next_token;wire[31:0]eng_cycles;
  wire arr_rst_n;wire[7:0]cfg_users;wire[17:0]cfg_prompt_len,cfg_gen_len;
  wire cq_commit_v;wire[15:0]cq_client_tag;wire[7:0]cq_slot;wire[17:0]cq_pos,cq_token;wire[1:0]cq_kind;wire[3:0]cq_status;
  wire step_issue_v,step_retire_v,step_retire_cq;wire[15:0]step_client_tag,step_retire_client_tag;
  wire[7:0]step_slot,step_retire_slot;wire[17:0]step_pos,step_retire_pos,step_retire_token;wire host_idle,host_observer_fault;
  ot_host_if_pb2_observed_rc #(.ENABLE_RETAINED_COMMIT(1),.HEALTH_CUTOFF_EDGES(64),.STEP_RESPONSE_DEADLINE_EDGES(48),.COMPONENT_FIXTURE(1),
    .NSLOT(1),.ENG_CTX(1),.MODE(0),.MU_OUT(0),.NW(18),.PLB(13),.CTX_MAX(8192),.FMT(1)) dut (
    .clk(clk),.rst_n(rst_n),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),
    .health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.health_identity_i(health_identity_i),.health_cutoff_i(health_cutoff_i),
    .execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.owner_drained_i(owner_drained_i),
    .rc_bad(rc_bad),.rc_armed(rc_armed),.rc_retained_owned(rc_retained_owned),.rc_poison(rc_poison),.rc_failure_pending(rc_failure_pending),.rc_report_once(rc_report_once),
    .rc_mirror_pos(rc_mirror_pos),.rc_mirror_tok(rc_mirror_tok),.rc_mirror_ngen(rc_mirror_ngen),.rc_mirror_state(rc_mirror_state),.rc_identity(rc_identity),.rc_word0_offer(rc_word0_offer),.rc_response_confirmed(rc_response_confirmed),
    .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr[11:0]),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),
    .s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr[11:0]),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),
    .m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
    .m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),
    .irq(irq),.pb_we(pb_we),.pb_waddr(pb_waddr),.pb_wdata(pb_wdata),.pb_re(pb_re),.pb_raddr(pb_raddr),.pb_q(pb_q),
    .eng_start(eng_start),.eng_token(eng_token),.eng_pos(eng_pos),.eng_slot(eng_slot),.kv_base(kv_base),.eng_done(eng_done),.eng_next_token(eng_next_token),.eng_cycles(eng_cycles),.eng_fault(eng_fault),.eng_clr_req(eng_clr_req),.eng_clr_ack(eng_clr_ack),
    .arr_rst_n(arr_rst_n),.cfg_users(cfg_users),.cfg_prompt_len(cfg_prompt_len),.cfg_gen_len(cfg_gen_len),.pr_re(1'b0),.pr_user(8'd0),.pr_pos(18'd0),.tok_valid(1'b0),.tok_user(8'd0),.tok_pos(18'd0),.tok_id(18'd0),.users_done(8'd0),.arr_fault(1'b0),
    .cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cq_kind(cq_kind),.cq_status(cq_status),
    .step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),.host_idle(host_idle),.host_observer_fault(host_observer_fault));

reg rx_v=0,tx_cr=0;reg[511:0]rx_d=0;wire rx_cr,tx_v,bridge_fault,bridge_bad,bridge_owned;wire[511:0]tx_d;
qkd_host_axi_packet_rc #(.ENABLE_RETAINED_COMMIT(1)) bridge(.ck(clk),.rst_n(rst_n),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),.health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.retained_bad_i(rc_bad),.retained_bad_o(bridge_bad),.retained_owned_o(bridge_owned),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.fault(bridge_fault),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),.m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),.m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp));

wire[181:0]hc;wire[743:0]tk;wire[119:0]ctl_res;
qkd_host_ctl_service_pins #(.ENABLE_SERVICE(0)) ctl(.ck(clk),.rst_n(raw_por_n),.sys_ready(1'b1),.pb_fault(1'b0),.die_id(3'd0),.req({kv_base,eng_pos,eng_token,eng_start}),.pr(143'd0),.tk(tk),.service_abort(1'b0),.service_ready(1'b1),.begin_block(1'b0),.epoch_fault(1'b0),.service_ready8(8'hff),.hc(hc),.res(ctl_res));
assign eng_done=ctl_res[0];assign eng_fault=ctl_res[1];assign eng_next_token=ctl_res[19:2];assign eng_cycles=ctl_res[83:52];
wire[7:0]ep_owned,ep_bad,request_v,result_cr;wire[58:0]request_tag[8];wire[1:0]request_gen[8];wire[17:0]request_token[8],request_pos[8];
reg[7:0]result_v=0,request_cr=0;reg[58:0]result_tag[8];reg[1:0]result_gen[8];reg[17:0]result_token[8];
for(genvar d=0;d<8;d++)begin:e
qkd_host_native_token_endpoint_cancel_rc #(.ENABLE_NATIVE(1),.ENABLE_RETAINED_COMMIT(1)) endpoint(
.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),.health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.retained_bad_o(ep_bad[d]),.retained_owned_o(ep_owned[d]),.retained_armed_o(),
.ck(clk),.por_n(raw_por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(1'b1),.shared_epoch(16'd7),
.request_v(request_v[d]),.request_tag(request_tag[d]),.request_trace(),.request_gen(request_gen[d]),.request_token(request_token[d]),.request_pos(request_pos[d]),.request_cr(request_cr[d]),.native_pr(),
.result_v(result_v[d]),.result_tag(result_tag[d]),.result_gen(result_gen[d]),.result_done(1'b1),.result_fault(1'b0),.result_cause(4'd0),.result_token(result_token[d]),.result_value(32'd100),.result_cycles(32'd3),.result_cr(result_cr[d]),
.kv_drained(1'b1),.vm_drained(1'b1),.collective_drained(1'b1),.host_drained(1'b1),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(1'b0),.cancel_release_v(1'b0),.cancel_release_tag(59'd0),.cancel_release_gen(2'd0),.context_owned(),.cancel_released(),.local_tk(tk[93*d+:93]),.protocol_fault());
end
// Independently counted native pipeline: package launch106, done116 => ten busy edges.
localparam integer EXPECTED_PACKAGE_CYCLES=10;
integer hold_b=0;
integer edges=0,issues=0,requests=0,returns=0,writes=0,word0s=0,successes=0,errors=0,csr_acks=0,issue_edge=0,done_edge=0,case_id=0;
reg[17:0]pbmem[0:16383];reg[511:0] replies[$];reg[511:0]p;reg[511:0]manual_packet=0;reg manual_v=0;
reg[63:0]last_word0=0;integer i;
function automatic[63:0]memread(input[63:0]a);
case(a)
'h1000:memread=(64'd1<<48)|(64'd1<<32)|(64'h1234<<16)|64'h101;
'h1008:memread='h3000;
'h1010:memread=0;
'h1018:memread=64'h0003ffff0003ffff;
'h3000:memread=42;
default:$fatal(1,"UNEXPECTED_READ address=%h",a);
endcase
endfunction
always @(posedge clk)begin
 edges<=edges+1;
 if(edges>3000)$fatal(1,"INTEGRATED_TIMEOUT issues=%0d requests=%0d writes=%0d bad=%0b bridgefault=%0b",issues,requests,writes,rc_bad,bridge_fault);
 if(pb_we)pbmem[pb_waddr]<=pb_wdata;
 if(pb_re)pb_q<=pbmem[pb_raddr];
 eng_clr_ack<=eng_clr_req;
 if(dut.cut_now || dut.step_done || dut.ep_v)$display("DIAG e=%0d cut=%b stepdone=%b ep=%b bad=%b identitybad=%b saved=%h evhead=%h",edges,dut.cut_now,dut.step_done,dut.ep_v,rc_bad,dut.identity_bad,dut.saved_ngen,dut.ev_head);
 if(eng_start)begin
  if(eng_pos!=0||eng_token!=42||issues!=0)$fatal(1,"ENGINE_INPUT pos=%0d token=%0d",eng_pos,eng_token);
  if(rc_identity!=={43'd0,16'h1234,2'd1,1'b0,18'd0})$fatal(1,"INDEPENDENT_IDENTITY got=%h",rc_identity);
  issues<=issues+1;issue_edge<=edges;$display("ISSUE edge=%0d identity=%h",edges,rc_identity);
 end
 if(eng_done && done_edge==0)begin done_edge<=edges;if(case_id==0&&eng_cycles!=EXPECTED_PACKAGE_CYCLES)$fatal(1,"PACKAGE_CYCLE_GOLD got=%0d",eng_cycles);$display("ACTUAL_PACKAGE_DONE edge=%0d fault=%0b",edges,eng_fault);end
end
// Conditional packet memory responder. No DUT internal fields or mirrors form gold.
// Every DMA completion is an actual 0x13/0x15 packet through bridge queue/credits.
always @(negedge clk)begin
 rx_v=0;tx_cr=0;result_v=0;request_cr=0;
 if(raw_por_n)begin
  for(i=0;i<8;i++)if(request_v[i])begin
   if(request_gen[i]!=1||request_token[i]!=42||request_pos[i]!=0||request_tag[i]!={16'd7,6'd0,18'd42,13'd0,6'd0})$fatal(1,"NATIVE_REQUEST_ID d=%0d",i);
   request_cr[i]=1;result_v[i]=1;result_tag[i]={16'd7,6'd37,18'd42,13'd0,6'd0};result_gen[i]=1;result_token[i]=43;
   requests=requests+1;$display("NATIVE_REQUEST edge=%0d die=%0d gen=%0d",edges,i,request_gen[i]);
  end
  for(i=0;i<8;i++)if(result_cr[i])returns=returns+1;
  if(tx_v)begin
   tx_cr=1;p=0;p[15:8]=1;
   case(tx_d[7:0])
    'h81:begin if(tx_d[33:32]!=0)$fatal(1,"CONFIG_BRESP");csr_acks=csr_acks+1;end
    'h12:begin p[7:0]='h13;p[34]=1;p[159:96]=memread(tx_d[95:32]);replies.push_back(p);end
    'h14:begin
     if(tx_d[95:32]!='h2008&&tx_d[95:32]!='h2000)$fatal(1,"UNEXPECTED_WRITE address=%h",tx_d[95:32]);
     if(tx_d[167:160]!=8'hff)$fatal(1,"WRITE_STROBE");
     writes=writes+1;
     if(tx_d[95:32]=='h2008)begin
      if(case_id>=3)hold_b=12;
      if(writes!=1)$fatal(1,"CQ_WORD_ORDER");
      if((case_id==0||case_id>=3)&&(tx_d[143:128]!=1||tx_d[127:96]!=EXPECTED_PACKAGE_CYCLES))$fatal(1,"CQ_WORD1 data=%h cycles=%0d",tx_d[159:96],EXPECTED_PACKAGE_CYCLES);
     end else begin
      word0s=word0s+1;last_word0=tx_d[159:96];
      if(tx_d[103:100]==7&&tx_d[98:97]==3)begin
       errors=errors+1;
       if(tx_d[159:96]!==((case_id>=3)?64'h002b000012340077:64'h0000000012340077))$fatal(1,"CQ_ERROR_GOLD got=%h",tx_d[159:96]);
      end
      else if(tx_d[103:100]==2&&tx_d[98:97]==2)begin
       successes=successes+1;
       if(tx_d[159:96]!==64'h002b000012340025)$fatal(1,"CQ_GOLD_WORD0 got=%h",tx_d[159:96]);
      end else $fatal(1,"CQ_STATUS word0=%h",tx_d[159:96]);
      $display("ACTUAL_CQ_WORD0 edge=%0d data=%h",edges,last_word0);
     end
     p[7:0]='h15;replies.push_back(p);
    end
    default:$fatal(1,"UNEXPECTED_TX op=%h",tx_d[7:0]);
   endcase
  end
  if(manual_v)begin rx_v=1;rx_d=manual_packet;manual_v=0;end
  else if(replies.size()!=0 && hold_b==0)begin rx_v=1;rx_d=replies.pop_front();end
  if(hold_b>0)hold_b=hold_b-1;
 end
end
task automatic tick(input integer n);repeat(n)@(negedge clk);#1;endtask
task automatic csr(input[12:0]a,input[31:0]d);
 integer expected;
 expected=csr_acks+1;
 @(posedge clk);manual_packet=0;manual_packet[7:0]=1;manual_packet[15:8]=1;manual_packet[31:16]=16'(expected);manual_packet[44:32]=a;manual_packet[127:96]=d;manual_packet[131:128]=15;manual_v=1;
 while(csr_acks<expected)tick(1);
 tick(2);
endtask
initial begin
 if(!$value$plusargs("CASE=%d",case_id))case_id=0;
 tick(4);raw_por_n=1;warm_rst_n=1;pll_locked_i=1;rst_n=1;health_armed_i=1;health_cutoff_i=1;tick(5);
 csr('h010,'h1000);csr('h018,3);csr('h024,'h2000);csr('h02c,3);csr('h008,1);csr('h01c,1);
 while(issues==0)tick(1);
 if(case_id==1)begin
  while(requests<8)tick(1);
  health_bad_i=1;tick(1);health_bad_i=0;
 end
 if(case_id==2)begin
  while(requests<8)tick(1);
  warm_rst_n=0;rst_n=0;tick(3);warm_rst_n=1;rst_n=1;
 end
 if(case_id>=3)begin
  while(writes<1)tick(1);
  if(hold_b==0)$fatal(1,"MISSING_OUTSTANDING_DMA");
  if(case_id==3)health_bad_i=1;
  else begin warm_rst_n=0;rst_n=0;end
  tick(3);health_bad_i=0;warm_rst_n=1;rst_n=1;
 end
 while(word0s==0)tick(1);tick(30);
 if(requests!=8||returns!=8||issues!=1||(|ep_owned))$fatal(1,"REAL_NATIVE_DRAIN requests=%0d returns=%0d owned=%h",requests,returns,ep_owned);
 if(case_id==0)begin
  if(successes!=1||errors!=0||rc_bad||bridge_fault||rc_mirror_pos!=1||rc_mirror_tok!=43)$fatal(1,"HEALTHY_INTEGRATION");
 end else if(successes!=0||errors!=1||!rc_bad||!bridge_bad)$fatal(1,"POISON_INTEGRATION successes=%0d errors=%0d",successes,errors);
 $display("INTEGRATED_PASS case=%0d edges=%0d issues=%0d native_requests=%0d resultcredits=%0d CQwrites=%0d success=%0d errors=%0d measured_response=%0d H=64 deadline=48",case_id,edges,issues,requests,returns,writes,successes,errors,done_edge-issue_edge);
 $finish;
end
endmodule
