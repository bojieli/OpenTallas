`timescale 1ns/1ps
// Source-legal COMPONENT trace. Boot/link/drain inputs are explicit conditional
// producers, not complete package receipts. No forced DUT state or reset input.
module actual_ingress_reset_tb #(parameter ING_MUT=0);
 reg raw_por_n=0,refclk=0;always #1 refclk=~refclk;
 wire ck,locked; wire qualified_por=raw_por_n&&locked;
 qkd_pll_analog_model pll(.refclk(refclk),.por_n(raw_por_n),.pll_c(ck),.locked(locked));
 reg[2:0]die_id=0;wire host_rst_n,sys_ready,boot_fault;wire[3:0]boot_state,boot_err;wire soft_rst;
 qkd_host_rst_role_pins resets(.clk(ck),.por_n(qualified_por),.soft_rst(soft_rst),.die_id(die_id),
 .link_up(6'h3f),.boot_done(8'hff),.boot_ok(8'hff),.host_rst_n(host_rst_n),.sys_ready(sys_ready),.boot_fault(boot_fault),.boot_state(boot_state),.boot_err(boot_err));
 reg cfg_we=0,go=0;reg[1:0]cfg_addr=0;reg[31:0]cfg_data=0;
 wire reserved,valid,native,active,done,configured,calendar_fault;wire[31:0]cycle;wire[7:0]fault_code;
 // Conditional producer promises all32 group drains and upstream quiet during
 // this isolated no-engine experiment. These do not qualify a real calendar.
 qkd_static_kv_ownership_calendar calendar(.ck(ck),.rst_n(host_rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.go(go),
 .host_quiet(launch_quiet),.upstream_quiet(1'b1),.group_drained(32'hffffffff),.group_fault(32'b0),
 .native_mode(native),.ownership_valid(valid),.native_reserved(reserved),.active(active),.done(done),.configured(configured),.cycle(cycle),.fault(calendar_fault),.fault_code(fault_code));
 reg rx_v=0;reg[527:0]rx_d=0;wire rx_cr,host_v,host_cr,ingress_fault,launch_quiet,deferred,admission_open;wire[511:0]host_d;
 qkd_host_rx_class_admission #(.MUT(ING_MUT)) ingress(.ck(ck),.rst_n(host_rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),
 .native_reserved(reserved),.ownership_valid(valid),.host_v(host_v),.host_d(host_d),.host_cr(host_cr),
 .ctrl_cr(1'b0),.ing_crn(5'b0),.fault(ingress_fault),.launch_quiet(launch_quiet),.deferred(deferred),.admission_open(admission_open));
 wire tx_v;wire[511:0]tx_d;reg tx_cr=0;wire bridge_fault;
 wire s_awvalid,s_awready,s_wvalid,s_wready,s_bvalid,s_bready,s_arvalid,s_arready,s_rvalid,s_rready;
 wire[12:0]s_awaddr,s_araddr;wire[31:0]s_wdata,s_rdata;wire[3:0]s_wstrb;wire[1:0]s_bresp,s_rresp;
 qkd_host_axi_packet bridge(.ck(ck),.rst_n(host_rst_n),.rx_v(host_v),.rx_d(host_d),.rx_cr(host_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.fault(bridge_fault),
 .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
 .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),
 .m_arvalid(1'b0),.m_araddr(64'b0),.m_rready(1'b0),.m_awvalid(1'b0),.m_awaddr(64'b0),.m_wvalid(1'b0),.m_wdata(64'b0),.m_wstrb(8'b0),.m_bready(1'b0));
 qkd_host_csr_service_pins csr(.clk(ck),.rst_n(host_rst_n),.por_n(raw_por_n),
 .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
 .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),
 .h_awready(1'b0),.h_wready(1'b0),.h_bvalid(1'b0),.h_arready(1'b0),.h_rvalid(1'b0),.h_rdata(32'b0),.h_irq(1'b0),
 .sys_ready(sys_ready),.boot_fault(boot_fault),.boot_state(boot_state),.boot_err(boot_err),.soft_rst(soft_rst),
 .fault_src(32'b0),.die_fault_vec(32'b0),.die_kst(80'b0),.cnt(512'b0),.begin_tx_cr(1'b0),.begin_tx_available(1'b0),
 .service_ready8(8'b0),.pending_ack8(8'b0),.service_epoch8(128'b0),.service_fault(1'b0),.ingest_permission(1'b0),
 .decode_request(1'b0),.decode_start(1'b0),.decode_done(1'b0));
 integer edge_n=0,soft_count=0,tx_count=0,launches=0;reg monitoring=0,saw_deferred=0,saw_restart=0;
 always @(posedge ck)begin
  edge_n<=edge_n+1;tx_cr<=tx_v;
  if(monitoring)begin
   if(!locked)$fatal(1,"STARTUP_ONLY_PLL_RUNTIME_LOSS edge=%0d",edge_n);
   if(!host_rst_n)$fatal(1,"UNREACHABLE_WARM_RESET violated edge=%0d",edge_n);
   if(ingress_fault||bridge_fault||calendar_fault)$fatal(1,"ACTUAL_PATH_PROTOCOL_FAULT edge=%0d ingress=%b bridge=%b calendar=%h",edge_n,ingress_fault,bridge_fault,fault_code);
   if(deferred) saw_deferred<=1;
   if(host_v)begin launches<=launches+1;$display("TRACE edge=%0d host_launch reserved=%b addr=%h",edge_n,reserved,host_d[44:32]);end
   if(reserved&&soft_rst)$fatal(1,"RESERVED_CSR_RESTART edge=%0d",edge_n);
   if(soft_rst)begin soft_count<=soft_count+1;saw_restart<=1;$display("TRACE edge=%0d accepted_SYS_CTRL_restart rawPOR=%b host_rst_n=%b reserved=%b",edge_n,raw_por_n,host_rst_n,reserved);end
   if(tx_v)begin
    if(tx_d[7:0]!=8'h81||tx_d[31:16]!=16'h5ac3||tx_d[33:32]!=0)$fatal(1,"CSR_RESPONSE_ID_OR_STATUS");
    tx_count<=tx_count+1;$display("TRACE edge=%0d real_CSR_response op=%h id=%h",edge_n,tx_d[7:0],tx_d[31:16]);
   end
   if(saw_restart&&!sys_ready)$display("TRACE edge=%0d boot_restart state=%0d host_rst_n=%b",edge_n,boot_state,host_rst_n);
  end
 end
 task edges(input integer n);repeat(n)@(negedge ck);endtask
 task cfg(input[1:0]a,input[31:0]v);begin @(negedge ck);cfg_we=1;cfg_addr=a;cfg_data=v;@(negedge ck);cfg_we=0;edges(3);end endtask
 initial begin
  #4 raw_por_n=1;
  wait(sys_ready);edges(10);monitoring=1;
  cfg(0,20);cfg(1,50);cfg(2,70);cfg(3,32'h514b564d);edges(8);
  if(!configured||!valid)$fatal(1,"CALENDAR_NOT_CONFIGURED");
  go=1;edges(1);go=0;wait(reserved);edges(5);
  rx_d=0;rx_d[7:0]=8'h01;rx_d[15:8]=1;rx_d[31:16]=16'h5ac3;rx_d[44:32]=13'h1008;rx_d[127:96]=1;rx_d[131:128]=4'hf;
  rx_v=1;edges(1);rx_v=0;edges(20);
  if(!deferred||soft_count!=0||launches!=0)$fatal(1,"RESERVATION_EXCLUSION_MISSING");
  $display("TRACE edge=%0d reservation_excludes_CSR deferred=%b calendar_cycle=%0d",edge_n,deferred,cycle);
  wait(!reserved);edges(120);
  if(soft_count!=1||tx_count!=1||launches!=1||!saw_deferred||!saw_restart||!sys_ready)$fatal(1,"ACTUAL_TRACE_INCOMPLETE soft=%0d tx=%0d launch=%0d",soft_count,tx_count,launches);
  $display("PASS ACTUAL_INGRESS_CSR_RESET_REACHABILITY bounded COMPONENT trace; no owned-reset bug established; warm/runtime PLL pulse unreachable in selected model");$finish;
 end
 initial begin #10000;$fatal(1,"FIXTURE_DEADLINE no expected trace within explicit10000ns test calendar");end
endmodule
