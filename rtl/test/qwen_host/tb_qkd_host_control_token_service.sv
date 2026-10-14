`timescale 1ns/1ps
module tb_qkd_host_control_token_service;
parameter STALL_GRANT=0;parameter MUT=0;parameter UE=0;parameter FAULT=0;
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
reg ck_rx,ck_tx,ck_axi,ck_ctrl,ck_hc,ck_prompt;reg[63:0]mem[0:2047];reg[92:0]raw_local_tk=0;wire[92:0]local_tk;reg[9:0]local_kst=0;reg[1:0]local_boot=0;
wire rx_cr,tx_v;reg rx_v=0,tx_cr=0;reg[527:0]rx_d=0;wire[527:0]tx_d;
wire source_cr,available,source_fault;wire[3:0]packet_faults;wire[7:0]seen;
wire ing_v,ing_t_cr;wire[1:0]ing_cls;wire[511:0]ing_d;reg[4:0]ing_crn=0;reg ing_t_v=0;reg[63:0]ing_t_d=0;
always @*begin ck_prompt=clk;ck_rx=clk;ck_tx=clk;ck_axi=clk;ck_ctrl=clk;ck_hc=clk;end
wire service_abort,service_ready;wire[15:0]local_service_epoch;
wire[25:0]service_diag_raw;wire[31:0]service_status;
wire begin_v,begin_cr,begin_available,begin_fault,epoch_busy,startup_allowed;
wire[15:0]begin_epoch,service_begin_epoch,pending_epoch;
wire service_begin_v,pending_advertised,ingest_permission;
wire[7:0]service_ready8,pending_ack8;wire[127:0]service_epoch8;
wire token_wrap_fence_valid=0,token_wrap_drained=0,token_wrap_link_reset_seen=0,token_wrap_retraining_done=0;wire package_abort;wire[3:0]abort_drained;wire token_request_valid,token_request_ready,token_grant_valid,token_grant_ready;
wire[17:0]token_request_token,token_request_position,token_grant_token,token_grant_position;
wire[1:0]token_request_generation,token_grant_generation;wire[15:0]token_grant_epoch;wire[58:0]token_grant_tag;
wire allocated_valid,allocated_delivered;wire[15:0]allocated_epoch;wire[17:0]allocated_token,allocated_position;wire[1:0]allocated_generation;
wire token_epoch_valid;wire[15:0]token_epoch;wire cancel_valid,cancel_done,cancel_fault,terminal_accepted;wire[58:0]cancel_tag;wire[1:0]cancel_generation;wire[3:0]cancel_drained;
wire allocfault,allocbusy;wire[7:1]peer_token_epoch_valid;wire[15:0]peer_token_epoch[1:7];reg[3:0]provider_drained[0:7];
reg normal_terminal_valid=0;reg[58:0]normal_terminal_tag=0;reg[1:0]normal_terminal_gen=0;reg[3:0]normal_terminal_drains=0;
integer allocation_requests=0,allocated_starts=0;reg token_request_last=0;
assign allocated_epoch=token_grant_epoch;assign allocated_token=token_grant_token;assign allocated_position=token_grant_position;assign allocated_generation=token_grant_generation;
assign abort_drained=normal_terminal_drains;
ot_qwen_tp8_token_epoch_allocator allocator(.clk(clk),.por_n(por_n),.warm_ready((&service_ready8)&&(!STALL_GRANT||!allocated_valid)),
.request_valid(token_request_valid),.request_ready(token_request_ready),.request_token(token_request_token),.request_position(token_request_position),.request_generation(token_request_generation),
.grant_valid(token_grant_valid),.grant_ready(token_grant_ready),.grant_epoch(token_grant_epoch),.grant_token(token_grant_token),.grant_position(token_grant_position),.grant_generation(token_grant_generation),.grant_tag(token_grant_tag),
.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),
.terminal_valid(cancel_valid||normal_terminal_valid),.terminal_tag(cancel_valid?cancel_tag:normal_terminal_tag),.terminal_generation(cancel_valid?cancel_generation:normal_terminal_gen),
.terminal_done(!cancel_valid&&normal_terminal_valid),.terminal_fault(cancel_valid),
.terminal_kv_drained(cancel_valid?cancel_drained[0]:normal_terminal_drains[0]),.terminal_vm_drained(cancel_valid?cancel_drained[1]:normal_terminal_drains[1]),
.terminal_collective_drained(cancel_valid?cancel_drained[2]:normal_terminal_drains[2]),.terminal_host_drained(cancel_valid?cancel_drained[3]:normal_terminal_drains[3]),
.wrap_fence_valid(1'b0),.wrap_links_drained(1'b0),.wrap_link_reset_seen(1'b0),.wrap_retraining_done(1'b0),.busy(allocbusy),.identity_fault(allocfault),.terminal_accepted(terminal_accepted));
always @(negedge clk)begin:terminal_provider_model
 reg all_done;reg[3:0]dr;
 all_done=allocated_delivered;dr=4'b1111;
 for(integer rank=0;rank<8;rank=rank+1)begin
  all_done=all_done&&dut.tk8[rank*93+92]&&dut.tk8[rank*93+89]&&dut.tk8[rank*93+90+:2]==token_grant_generation;
  dr=dr&provider_drained[rank];
 end
 normal_terminal_drains=dr;
 if(terminal_accepted)normal_terminal_valid=0;
 else if(all_done&&(&dr))begin normal_terminal_valid=1;normal_terminal_tag={token_grant_epoch,6'd37,token_grant_token,token_grant_position[12:0],6'd0};normal_terminal_gen=token_grant_generation;end
 if(token_request_valid&&!token_request_last)allocation_requests=allocation_requests+1;token_request_last=token_request_valid;
 if(allocfault)$fatal(1,"actual central allocator identity fault");
end

reg[24:0]service_raw_faults=0;reg root_barrier_v=0;
qkd_host_service_guard #(.MUT(0))root_guard(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(service_raw_faults),.service_protocol_fault(begin_fault),.die_id(3'd0),.physical_faults(8'b0),.transport_faults(8'b0),
.accepted_ing_v(ing_v),.accepted_ing_cls(ing_cls),.accepted_ing_header(ing_d[15:0]),.done_v(1'b0),.done_d(64'b0),.boot_barrier_v(root_barrier_v),.boot_barrier_target(32'b0),
.begin_v(service_begin_v),.begin_epoch(service_begin_epoch),.pending_advertised(pending_advertised),.pending_epoch(pending_epoch),.local_tk(raw_local_tk),.guarded_tk(local_tk),.abort(service_abort),.service_ready(service_ready),.service_epoch(local_service_epoch),.diag_raw(service_diag_raw),.status(service_status),.groups(),.physical_diag(),.transport_diag());
qkd_host_control_packet_capture_token_service #(.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.T_LINK(1000),.T_HBM(10000),.WDOG(10000),.HC_MUT(FAULT==0&&MUT==2),.PROMPT_MUT(MUT==3?3:MUT==4?2:0),.PROMPT_BIND_LATENCY(MUT==5?3:4))dut(.*);
assign c_start=dut.raw_hc[38];assign c_token=dut.raw_hc[35:18];assign c_pos=dut.raw_hc[17:0];assign c_gen=dut.raw_hc[37:36];
reg[7:1]peer_rx_v=0;reg[511:0]peer_rx_d[1:7];wire[7:1]peer_tx_v;wire[511:0]peer_tx_d[1:7];reg[7:1]peer_tx_cr=0;
reg[92:0]peer_tk[1:7];reg[9:0]peer_kst[1:7];reg[1:0]peer_boot[1:7];wire[181:0]peer_hc[1:7];wire[7:1]peer_fault;
wire[92:0]peer_guarded_tk[1:7];wire[7:1]peer_service_ready,peer_abort,peer_begin,peer_advert;
wire[15:0]peer_epoch[1:7],peer_begin_epoch[1:7],peer_advert_epoch[1:7];
reg[7:1]peer_ingress=0,peer_barrier=0;wire follower_ing_v;wire[1:0]follower_ing_cls;wire[511:0]follower_ing_d;wire follower_begin_fault;
 qkd_host_service_guard peer_guard_1(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(1==7?follower_begin_fault:1'b0),.die_id(3'(1)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(1==7?follower_ing_v:peer_ingress[1]),.accepted_ing_cls(1==7?follower_ing_cls:2'b0),.accepted_ing_header(1==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[1]),.boot_barrier_target(32'b0),.begin_v(peer_begin[1]),.begin_epoch(peer_begin_epoch[1]),
 .pending_advertised(peer_advert[1]),.pending_epoch(peer_advert_epoch[1]),.local_tk(peer_tk[1]),.guarded_tk(peer_guarded_tk[1]),.abort(peer_abort[1]),.service_ready(peer_service_ready[1]),.service_epoch(peer_epoch[1]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_service_guard peer_guard_2(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(2==7?follower_begin_fault:1'b0),.die_id(3'(2)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(2==7?follower_ing_v:peer_ingress[2]),.accepted_ing_cls(2==7?follower_ing_cls:2'b0),.accepted_ing_header(2==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[2]),.boot_barrier_target(32'b0),.begin_v(peer_begin[2]),.begin_epoch(peer_begin_epoch[2]),
 .pending_advertised(peer_advert[2]),.pending_epoch(peer_advert_epoch[2]),.local_tk(peer_tk[2]),.guarded_tk(peer_guarded_tk[2]),.abort(peer_abort[2]),.service_ready(peer_service_ready[2]),.service_epoch(peer_epoch[2]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_service_guard peer_guard_3(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(3==7?follower_begin_fault:1'b0),.die_id(3'(3)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(3==7?follower_ing_v:peer_ingress[3]),.accepted_ing_cls(3==7?follower_ing_cls:2'b0),.accepted_ing_header(3==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[3]),.boot_barrier_target(32'b0),.begin_v(peer_begin[3]),.begin_epoch(peer_begin_epoch[3]),
 .pending_advertised(peer_advert[3]),.pending_epoch(peer_advert_epoch[3]),.local_tk(peer_tk[3]),.guarded_tk(peer_guarded_tk[3]),.abort(peer_abort[3]),.service_ready(peer_service_ready[3]),.service_epoch(peer_epoch[3]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_service_guard peer_guard_4(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(4==7?follower_begin_fault:1'b0),.die_id(3'(4)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(4==7?follower_ing_v:peer_ingress[4]),.accepted_ing_cls(4==7?follower_ing_cls:2'b0),.accepted_ing_header(4==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[4]),.boot_barrier_target(32'b0),.begin_v(peer_begin[4]),.begin_epoch(peer_begin_epoch[4]),
 .pending_advertised(peer_advert[4]),.pending_epoch(peer_advert_epoch[4]),.local_tk(peer_tk[4]),.guarded_tk(peer_guarded_tk[4]),.abort(peer_abort[4]),.service_ready(peer_service_ready[4]),.service_epoch(peer_epoch[4]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_service_guard peer_guard_5(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(5==7?follower_begin_fault:1'b0),.die_id(3'(5)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(5==7?follower_ing_v:peer_ingress[5]),.accepted_ing_cls(5==7?follower_ing_cls:2'b0),.accepted_ing_header(5==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[5]),.boot_barrier_target(32'b0),.begin_v(peer_begin[5]),.begin_epoch(peer_begin_epoch[5]),
 .pending_advertised(peer_advert[5]),.pending_epoch(peer_advert_epoch[5]),.local_tk(peer_tk[5]),.guarded_tk(peer_guarded_tk[5]),.abort(peer_abort[5]),.service_ready(peer_service_ready[5]),.service_epoch(peer_epoch[5]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_service_guard peer_guard_6(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(6==7?follower_begin_fault:1'b0),.die_id(3'(6)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(6==7?follower_ing_v:peer_ingress[6]),.accepted_ing_cls(6==7?follower_ing_cls:2'b0),.accepted_ing_header(6==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[6]),.boot_barrier_target(32'b0),.begin_v(peer_begin[6]),.begin_epoch(peer_begin_epoch[6]),
 .pending_advertised(peer_advert[6]),.pending_epoch(peer_advert_epoch[6]),.local_tk(peer_tk[6]),.guarded_tk(peer_guarded_tk[6]),.abort(peer_abort[6]),.service_ready(peer_service_ready[6]),.service_epoch(peer_epoch[6]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
 qkd_host_service_guard peer_guard_7(.ck_guard(clk),.rst_n(host_rst_n),.raw_faults(25'b0),.service_protocol_fault(7==7?follower_begin_fault:1'b0),.die_id(3'(7)),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(7==7?follower_ing_v:peer_ingress[7]),.accepted_ing_cls(7==7?follower_ing_cls:2'b0),.accepted_ing_header(7==7?follower_ing_d[15:0]:16'd2),
 .done_v(1'b0),.done_d(64'b0),.boot_barrier_v(peer_barrier[7]),.boot_barrier_target(32'b0),.begin_v(peer_begin[7]),.begin_epoch(peer_begin_epoch[7]),
 .pending_advertised(peer_advert[7]),.pending_epoch(peer_advert_epoch[7]),.local_tk(peer_tk[7]),.guarded_tk(peer_guarded_tk[7]),.abort(peer_abort[7]),.service_ready(peer_service_ready[7]),.service_epoch(peer_epoch[7]),.diag_raw(),.status(),.groups(),.physical_diag(),.transport_diag());
for(genvar pd=1;pd<7;pd=pd+1)begin:g_peer
 qkd_host_ctrl_token_service_packet #(.DIE(pd),.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1))ctrl(.ck(clk),.rst_n(host_rst_n),.die_id(3'(pd)),
 .rx_v(peer_rx_v[pd]),.rx_d(peer_rx_d[pd]),.rx_cr(),.tx_v(peer_tx_v[pd]),.tx_d(peer_tx_d[pd]),.tx_cr(peer_tx_cr[pd]),
 .startup_allowed(1'b1),.local_service_ready(peer_service_ready[pd]),.local_service_epoch(peer_epoch[pd]),.begin_v(1'b0),.begin_epoch(16'b0),
 .service_begin_v(peer_begin[pd]),.service_begin_epoch(peer_begin_epoch[pd]),.pending_advertised(peer_advert[pd]),.pending_epoch(peer_advert_epoch[pd]),
 .local_tk(peer_guarded_tk[pd]),.local_kst(peer_kst[pd]),.local_boot(peer_boot[pd]),.cmd_v(1'b0),.cmd_hc(182'b0),.cmd_cr(),
 .por_n(por_n),.token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.package_abort(1'b0),.abort_drained(4'b0),.token_request_ready(1'b0),.token_grant_valid(1'b0),.token_grant_epoch(16'b0),.token_grant_token(18'b0),.token_grant_position(18'b0),.token_grant_generation(2'b0),.token_grant_tag(59'b0),.allocated_valid(1'b0),.allocated_delivered(1'b0),.allocated_epoch(16'b0),.allocated_token(18'b0),.allocated_position(18'b0),.allocated_generation(2'b0),.terminal_accepted(1'b0),.token_epoch_valid(peer_token_epoch_valid[pd]),.token_epoch(peer_token_epoch[pd]),
 .hc(peer_hc[pd]),.tk8(),.kst8(),.boot8(),.seen(),.fault(peer_fault[pd]));
end
wire follower_available,follower_source_cr,follower_source_fault,follower_tx_v,follower_ready,follower_die_rst;reg follower_tx_cr=0;wire[181:0]follower_hc;wire[527:0]follower_tx_d;wire[3:0]follower_packet_faults;
reg[5:0]follower_links=0;reg follower_rx_v=0;reg[527:0]follower_rx_d=0;
reg[527:0]fqueue[0:255];integer fw=0,fr=0,fgap=0;
task fenqueue(input[527:0]p);begin fqueue[fw]=p;fw=fw+1;end endtask
assign peer_tx_v[7]=follower_tx_v && follower_tx_d[527:524]==1;
assign peer_tx_d[7]=follower_tx_d[511:0];assign peer_hc[7]=follower_hc;assign peer_fault[7]=|follower_packet_faults;
qkd_host_control_packet_capture_token_service #(.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.T_LINK(1000),.T_HBM(10000)) follower(.ck_host(clk),.ck_csr(clk),.ck_rst(clk),.ck_ctl(clk),.ck_prompt(clk),
 .ck_rx(clk),.ck_tx(clk),.ck_axi(clk),.ck_ctrl(clk),.ck_hc(clk),.die_id(3'd7),.por_n(por_n),.link_up(follower_links),
 .transport_fault(8'b0),.physical_fault(8'b0),.crom_fault(1'b0),.pr(pr),.rx_v(follower_rx_v),.rx_d(follower_rx_d),.tx_v(follower_tx_v),.tx_d(follower_tx_d),.tx_cr(follower_tx_cr),
 .service_abort(peer_abort[7]),.service_ready(peer_service_ready[7]),.local_service_epoch(peer_epoch[7]),.service_diag_raw(26'b0),.service_status(32'b0),
 .service_begin_v(peer_begin[7]),.service_begin_epoch(peer_begin_epoch[7]),.pending_advertised(peer_advert[7]),.pending_epoch(peer_advert_epoch[7]),.begin_fault(follower_begin_fault),
 .ing_v(follower_ing_v),.ing_cls(follower_ing_cls),.ing_d(follower_ing_d),.local_tk(peer_guarded_tk[7]),.local_kst(peer_kst[7]),.local_boot(peer_boot[7]),.sys_ready(follower_ready),.die_rst_n(follower_die_rst),.packet_faults(follower_packet_faults),.hc(follower_hc),.source_cr(follower_source_cr),.available(follower_available),.source_fault(follower_source_fault),
 .token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.abort_drained(4'b0),.token_request_ready(1'b0),.token_grant_valid(1'b0),.token_grant_epoch(16'b0),.token_grant_token(18'b0),.token_grant_position(18'b0),.token_grant_generation(2'b0),.token_grant_tag(59'b0),.allocated_valid(1'b0),.allocated_delivered(1'b0),.allocated_epoch(16'b0),.allocated_token(18'b0),.allocated_position(18'b0),.allocated_generation(2'b0),.terminal_accepted(1'b0),.token_epoch_valid(peer_token_epoch_valid[7]),.token_epoch(peer_token_epoch[7]),
 .ing_crn(5'd0),.ing_t_v(1'b0),.ing_t_d(64'b0));
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
initial if(UE && MUT==1)force dut.u_control.u_control.u_pkg.pb_q=1'b0;
reg overlap_sent=0,overlap_clear=0;
always @(negedge clk)begin
 if(!overlap_sent && dut.u_control.u_control.u_pkg.req_q[0])begin
  if(!available)$fatal(1,"overlap metadata lacked prior source credit");
  pr={1'b1,3'd7,64'h0123456789abcdef,1'b1,10'd1023,64'hfedcba9876543210};overlap_sent=1;overlap_clear=1;
 end else if(overlap_clear)begin pr[142]=0;pr[74]=0;overlap_clear=0;end
end
function automatic[17:0]next_token(input[17:0]p);begin next_token=(p==2)?18'h21111:18'h20000+p;end endfunction
always @(posedge clk)begin
 if(source_cr)credit_count<=credit_count+1;
 if(UE && dut.u_control.u_control.pb_fault && !ue_fault_seen)begin ue_fault_seen<=1;$display("TRACE q4 UE fault cycle=%d",cycles);end
 if(UE && dut.u_control.u_control.eng_start)$display("TRACE q4 hostrequest cycle=%d qualifiedready=%b",cycles,dut.u_control.u_control.u_pkg.u_core.ready_q);
 if(UE && dut.u_control.u_control.u_pkg.u_core.req_q[0])$display("TRACE q4 sampledrequest cycle=%d qualifiedready=%b",cycles,dut.u_control.u_control.u_pkg.u_core.ready_q);
 if(c_start)begin
  if(UE||(FAULT==1)||(FAULT==2))$fatal(1,"service/ECC fault launched controller token=%h",c_token);
  if(hold7>0)$fatal(1,"die7 undrained completed early");
  expected_gen<=expected_gen+1'b1;step_count<=step_count+1;
  if(c_gen!==expected_gen+2'd1 || c_pos!==18'(step_count))$fatal(1,"generation wrap/position mismatch");
  if((c_pos==0&&c_token!==18'h22222)||(c_pos==1&&c_token!==18'h15555)||(c_pos==2&&c_token!==18'h23333)||
   (c_pos==3&&c_token!==18'h21111)||(c_pos>3&&c_token!==next_token(c_pos-1)))$fatal(1,"FMT1 transported token mismatch");
 end
 if(dut.raw_hc[38]||dut.raw_hc[113]||dut.raw_hc[181])begin expected_commands[expected_count]=dut.raw_hc;expected_count=expected_count+1;end
 if(hc[38]||hc[113]||hc[181])begin
  if(hc!==expected_commands[local_command_count])$fatal(1,"local rawhc mismatch");local_command_count=local_command_count+1;
  if(hc[38])begin
   if(!token_epoch_valid||token_epoch!==token_grant_epoch||(!allocated_delivered&&!(token_grant_valid&&token_grant_ready)))$fatal(1,"local start before genuinely consumed grant");
   allocated_starts=allocated_starts+1;provider_drained[0]=15;
  end
  if(hc[38])raw_local_tk<={1'b1,hc[37:36],1'b1,1'b0,6'b0,next_token(hc[17:0]),32'h3f800000,32'd17};
 end
 for(integer pd=1;pd<8;pd=pd+1)begin
  if(peer_hc[pd][38]||peer_hc[pd][113]||peer_hc[pd][181])begin
   if(peer_hc[pd]!==expected_commands[peer_command_count[pd]])$fatal(1,"remote rawhc/PW/DW mismatch die%d",pd);
   peer_command_count[pd]=peer_command_count[pd]+1;
   if(peer_hc[pd][113]||peer_hc[pd][181])peer_meta[pd]=peer_meta[pd]+1;
   if(peer_hc[pd][38])begin
    if(pd==7 && (!follower_ready || !follower_die_rst))$fatal(1,"transported peer7 start executed before local reset release");
    if(!peer_token_epoch_valid[pd]||peer_token_epoch[pd]!==token_grant_epoch)$fatal(1,"peer shared token epoch mismatch rank%d",pd);
    provider_drained[pd]=0;peer_starts[pd]=peer_starts[pd]+1;peer_delay[pd]=pd+2;peer_gen[pd]=peer_hc[pd][37:36];peer_pos[pd]=peer_hc[pd][17:0];peer_next[pd]=next_token(peer_hc[pd][17:0]);
    if(pd==7)hold7=600;
   end
  end
  if(peer_delay[pd]>0)begin peer_delay[pd]=peer_delay[pd]-1;
   if(peer_delay[pd]==0)begin provider_drained[pd]=(pd==7)?4'b1110:4'b1111;end
   if(peer_delay[pd]==0)peer_tk[pd]<={1'b1,peer_gen[pd],(pd!=7 || MUT==1),1'b0,6'b0,peer_next[pd],32'h3f800000,32'd17};
  end
 end
 if(hold7>0)begin hold7=hold7-1;if(hold7==0)begin peer_tk[7][89]<=1;provider_drained[7][0]=1;end end
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
 initial if(FAULT==3&&MUT==8)begin
 force dut.u_control.u_control.u_csr.u_core.decode_busy=1'b0;
 force dut.u_control.u_control.u_csr.u_core.decode_request=1'b0;
 force dut.u_control.u_control.u_csr.u_core.decode_start=1'b0;
 end
 initial if(FAULT==2&&MUT==7)force dut.u_control.u_control.u_pkg.faults_q=8'b0;
 initial if(FAULT==1&&MUT==6)begin
 force dut.u_control.u_control.u_pkg.faults_q=8'b0;
 force dut.u_control.u_control.u_pkg.abort_q=1'b0;
 force dut.u_control.u_control.u_pkg.epoch_fault_q=1'b0;
 force dut.u_control.u_control.u_pkg.service_q=1'b1;
 force dut.u_control.u_control.u_pkg.services_q=8'hff;
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
task warm_epoch;begin
 wr(13'h10a0,1);n=0;
 while(pending_ack8!=255&&n<3000)begin tick;n++;end
 repeat(10)tick;if(pending_ack8!=255||!ingest_permission||service_ready8!=0)$fatal(1,"epoch genuine all8 pending ACK ack=%h permit=%b ready=%h fault=%b",pending_ack8,ingest_permission,service_ready8,begin_fault);
 rd(13'h10a4,v);if(v[15:8]!=255||!v[16]||v[7:0]!=0)$fatal(1,"epoch actual BAR all8 pending/permission");
 enqueue(2,512'd2);fenqueue({4'd2,12'b0,512'd2});
 tick;peer_ingress=6'b111111;tick;peer_ingress=0;
 n=0;while((root_guard.mc!=1||peer_guard_7.mc!=1)&&n<1500)begin tick;n++;end
 if(root_guard.mc!=1||peer_guard_7.mc!=1)$fatal(1,"real packet BOOT_END admission");repeat(20)tick;root_barrier_v=1;peer_barrier[6:1]=6'b111111;tick;root_barrier_v=0;peer_barrier[6:1]=0;
 repeat(200)tick;if(service_ready8!=127||!epoch_busy)$fatal(1,"die7 genuine barrier wait");
 peer_barrier[7]=1;tick;peer_barrier[7]=0;n=0;
 while((service_ready8!=255||epoch_busy)&&n<3000)begin tick;n++;end
 if(service_ready8!=255||epoch_busy)$fatal(1,"all8 genuine epoch barriers");
 rd(13'h10a0,v);if(v[19]||v[15:0]!=1)$fatal(1,"epoch allocator actual BAR completion");
end endtask
integer i,n;reg[31:0]v;reg[63:0]expected_cq;reg[17:0]nt;
initial begin
 por_n=0;die_id=0;link_up=0;transport_fault=0;physical_fault=0;crom_fault=0;pr=0;
 for(i=0;i<2048;i=i+1)mem[i]=0;
 for(i=1;i<8;i=i+1)begin provider_drained[i]=15;peer_tk[i]=0;peer_kst[i]=10'(i*17);peer_boot[i]=0;peer_delay[i]=0;peer_starts[i]=0;peer_meta[i]=0;peer_command_count[i]=0;end
 provider_drained[0]=15;repeat(8)tick;por_n=1;repeat(12)tick;link_up=63;repeat(15)tick;if(follower_ready || follower_die_rst)$fatal(1,"peer released before links");follower_links=63;local_boot=3;
 for(i=1;i<7;i=i+1)peer_boot[i]=3;peer_boot[7]=2;repeat(150)tick;if(follower_ready || follower_die_rst)$fatal(1,"peer released before genuine own bootdone");if(sys_ready)$fatal(1,"transported die7 bootdone ignored");
 peer_boot[7]=3;n=0;while(!sys_ready&&n<1000)begin tick;n=n+1;end;if(!sys_ready||seen!=255||!follower_ready||!follower_die_rst)$fatal(1,"true transported boot8 readiness");
 warm_epoch();
 // Native metadata raw PW/DW ABI, source-credit reservation before every edge.
 for(i=0;i<3;i=i+1)begin
  n=0;while(!available&&n<1000)begin tick;n=n+1;end;if(!available)$fatal(1,"no metadata source credit");
  pr={1'b1,3'(i),64'hfedcba9876543210+64'(i),1'b1,10'(i+31),64'h123456789abcdef0+64'(i)};
  tick;pr[142]=0;pr[74]=0;repeat(30)tick;
 end
 n=0;while(credit_count<3&&n<1500)begin tick;n=n+1;end;if(credit_count!=3)$fatal(1,"seven-copy metadata credits");
 rd(13'h1000,v);if(v!==32'h51535953)$fatal(1,"globalBAR");rd(0,v);if(v!==32'h4f544849)$fatal(1,"hostBAR");
 mem[32]=64'h000a_0003_cafe_0101;mem[33]=64'h400;mem[34]=0;mem[35]=64'h0003ffff_0003ffff;
 mem[128]=64'h00015555_00022222;mem[129]=64'h00000000_00023333;
 if(FAULT==1)begin service_raw_faults=25'b1<<22;repeat(20)tick;rd(13'h1058,v);if(!v[22])$fatal(1,"actual packet BAR raw CTRL fault");rd(13'h105c,v);if(!v[2]||v[1])$fatal(1,"actual packet BAR abort ready blocked");end
 if(FAULT==2)begin peer_tk[7][88]=1;repeat(100)tick;if(!dut.tk8[7*93+88]||dut.tk8[7*93+92])$fatal(1,"genuine transported peer done0 fault");end
 if(UE||FAULT||STALL_GRANT)wr(13'h1014,32'hffffffff);wr(13'h010,32'h100);wr(13'h014,0);wr(13'h018,2);wr(13'h024,32'h800);wr(13'h028,0);wr(13'h02c,5);wr(13'h03c,1);wr(13'h008,1);wr(13'h01c,1);
 if(STALL_GRANT)begin
 n=0;while(cq_writes<2&&n<15000)begin tick;n++;end
 $display("TRACE watchdog CQ%d mem%h irq%b req%d rawsteps%d local%d cancel%b fault%b busy%b abort%b",cq_writes,mem[256],irq,allocation_requests,step_count,allocated_starts,cancel_valid,cancel_fault,allocbusy,package_abort);
 if(cq_writes!=2||mem[256]!==64'h00000000cafe0075||!irq||allocated_starts!=0||allocation_requests!=1||step_count!=1)$fatal(1,"actual package watchdog cancellation ring CQ/IRQ/start counts");
 repeat(200)tick;
 if(allocated_valid||allocbusy||allocfault||cancel_valid||!cancel_fault||cancel_done||allocated_starts!=0)$fatal(1,"hidden actual allocation not fault-retired after genuine idle provider/link drain model");
 for(i=1;i<8;i++)if(peer_starts[i]!=0)$fatal(1,"delayed grant package abort emitted peer start");
 $display("PASS actual FMT1/q4 ND8 watchdog abort hidden allocated epoch0 genuine fault-terminal no-local/no-peer start CQ=%h",mem[256]);$finish;
 end
 if(FAULT==3)begin
 n=0;while(step_count<1&&n<3000)begin tick;n++;end
 if(step_count!=1)$fatal(1,"no genuine active decode for BEGIN reject");
 n=0;while((!dut.ctrl_begin_available||credit_count<4||hold7==0)&&n<600)begin tick;n++;end
 if(!dut.ctrl_begin_available||hold7==0||cq_writes!=0)$fatal(1,"no HC-idle genuine decode busy window");repeat(8)tick;
 wr(13'h10a0,1);rd(13'h10a0,v);
 if(!v[21]||v[15:0]!=1)$fatal(1,"BEGIN during actual decode incorrectly admitted epoch%h status%h",begin_epoch,v);
 rd(13'h1058,v);if(!v[25])$fatal(1,"allocator protocol fault actual packet BAR diag25");
 end
 if(FAULT)begin
 n=0;while(cq_writes<2&&n<3000)begin tick;n++;end
 if(step_count!=(FAULT==3?1:0)||cq_writes!=2||mem[256]!==64'h00000000cafe0075||!irq)$fatal(1,"service package ring fault guard CQ/IRQ");
 repeat(200)tick;if(step_count!=(FAULT==3?1:0)||cq_writes!=2)$fatal(1,"service fault later successful launch");
 $display("PASS actual FMT1/q4 ND8 service epoch package fault done0 FAULT=%d CQ=%h IRQ",FAULT,mem[256]);$finish;
 end
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
 if(!overlap_sent || expected_count!=15 || local_command_count!=15 || credit_count!=15)$fatal(1,"bounded command events/returns expected%d local%d credit%d",expected_count,local_command_count,credit_count);
 for(i=1;i<8;i=i+1)if(peer_starts[i]!=12||peer_meta[i]!=4||peer_command_count[i]!=15)$fatal(1,"peer metadata/start loss die%d",i);
 if(dut.kst8[79:70]!==10'(7*17))$fatal(1,"transported actual kst die7");
 if(allocation_requests!=12||allocated_starts!=12)$fatal(1,"one genuine allocation required per actual HC auto step requests%d starts%d",allocation_requests,allocated_starts);
 $display("PASS token service epoch all8 pendingACK/actualBAR/barriers UNQUALIFIED capture256 q4/fault5 actual control/prompt/HOST+ND8CTRL FMT1ring12steps generationwrap3 die7undrained boot8 PW/DW4includingStartOverlap all7peer exact 15credits IRQ/CQ10 peer7localready_then_transportedexecution_pkgctl_silent");$finish;
end
initial begin #20000;$fatal(1,"timeout");end
endmodule
