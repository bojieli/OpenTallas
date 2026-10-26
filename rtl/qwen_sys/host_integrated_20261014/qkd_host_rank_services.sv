`timescale 1ns/1ps
// Split KV/system HOST successor assembly with real embedding hb producer and
// shared in-order physical completion ledger. Source tests/physical binding pending.
// Complete production-candidate HOST assembly. Wires only; each named clock
// entry belongs to its actual physical child, never a historical parent alias.
// PHY family: ck_phy[7:0], ck_pad, ck_phy_rx_w, ck_phy_tx_r.
// Packet/core833 family: all ten control entries, ck_phy_rx_r/tx_w, queue,
// QM-ing-w/done-r, QM-core, map/sum/order/stations/arbiters/fence-core/guard.
// QM-host1000 family: QM-host, QM-ing-r/credit/done-w and fence-host.
// Ingest600 family: QM-ingest/control, two banks and output. Within a family
// physical insertion compensation and real cross-child setup/hold are required.
// The PHY split parent is source0d401fc0b, eight actual RXD512 controllers;
// its real distribution remains UNQUALIFIED. The 78-root proxy is not bound.
// DEFAULT_OFF warm service and native execution candidates. Full-source
// composition proof remains required. Token epoch comes from actual HC22v2 transport.
// Sole allocator is external; token_cancel_accepted is identity-qualified collector ACK.
// Endpoint warm reset is host_rst_n; native execution must share this reset/flush contract.
module qkd_host_rank_services #(
 parameter T_LINK=200000,T_HBM=200000,WDOG=1<<22,
 parameter ENABLE_SERVICE=0,ENABLE_NATIVE=0,ENABLE_TOKEN=0,
 parameter PHY_MUT=0,QM_MUT=0,ORDER_MUT=0,BRIDGE_MUT=0,HC_MUT=0,PROMPT_MUT=0,
 parameter NL=6
)(
 input wire[7:0]ck_phy,input wire ck_pad,ck_phy_rx_w,ck_phy_rx_r,ck_phy_tx_w,ck_phy_tx_r,
 input wire peer_reset_request,native_recovery_clear,input wire ck_peer,input wire peer_tx_valid,input wire[511:0]peer_tx_data,output wire peer_tx_ready,
 output wire peer_rx_valid,output wire[511:0]peer_rx_data,input wire peer_rx_ready,output wire peer_link_drained,
 input wire ck_program_rx,ck_program_loader,input wire[127:0]ck_boot,ck_boot_test,
 input wire ck_host,ck_csr,ck_rst,ck_ctl,ck_prompt,ck_rx,ck_tx,ck_axi,ck_ctrl,ck_hc,
 input wire ck_qm_queue,ck_qm_ing_w,ck_qm_ing_r,ck_qm_credit,ck_qm_done_w,ck_qm_done_r,
 input wire ck_qm_core,ck_qm_host,ck_qm_ingest,input wire[1:0]ck_qm_bank,input wire ck_qm_out,
 input wire ck_map,ck_sum,ck_order,ck_dispatch,ck_retire,ck_bootbarrier,input wire[127:0]ck_station,ck_static,
 input wire ck_fence_core,ck_fence_host,ck_guard,ck_native,
 input wire token_allocator_fault,
 input wire token_wrap_fence_valid,token_wrap_drained,token_wrap_link_reset_seen,token_wrap_retraining_done,
 output wire package_abort,input wire[3:0]abort_drained,
 output wire token_request_valid,input wire token_request_ready,
 output wire[17:0]token_request_token,token_request_position,output wire[1:0]token_request_generation,
 input wire cancel_release_v,input wire[58:0]cancel_release_tag,input wire[1:0]cancel_release_gen,output wire cancel_released,native_context_owned,
 input wire token_grant_valid,output wire token_grant_ready,
 input wire[15:0]token_grant_epoch,input wire[17:0]token_grant_token,token_grant_position,
 input wire[1:0]token_grant_generation,input wire[58:0]token_grant_tag,
 input wire allocated_valid,allocated_delivered,input wire[15:0]allocated_epoch,
 input wire[17:0]allocated_token,allocated_position,input wire[1:0]allocated_generation,
 output wire token_epoch_valid,output wire[15:0]token_epoch,
 output wire cancel_valid,output wire[58:0]cancel_tag,output wire[1:0]cancel_generation,
 output wire cancel_done,cancel_fault,output wire[3:0]cancel_drained,input wire token_cancel_accepted,
 output wire native_request_v,output wire[58:0]native_request_tag,output wire[31:0]native_request_trace,
 output wire[1:0]native_request_gen,output wire[17:0]native_request_token,native_request_pos,
 input wire native_request_cr,output wire[142:0]native_pr,
 input wire native_result_v,input wire[58:0]native_result_tag,input wire[1:0]native_result_gen,
 input wire native_result_done,native_result_fault,input wire[3:0]native_result_cause,
 input wire[17:0]native_result_token,input wire[31:0]native_result_value,native_result_cycles,
 output wire native_result_cr,input wire native_kv_drained,native_vm_drained,native_collective_drained,native_host_drained,
 input wire native_collective_busy,native_kv_flush,
 output wire service_ready,service_abort,ingest_permission,output wire[15:0]local_service_epoch,
 output wire[25:0]service_diag_raw,output wire[31:0]service_status,
 input wire[2:0]die_id,input wire por_n,pll_locked,phy_up,phy_rx_v,input wire[1042:0]phy_rx_flit,
 output wire phy_tx_v,output wire[1042:0]phy_tx_flit,
 input wire[NL-1:0]link_up,input wire[7:0]transport_fault,physical_fault,input wire crom_fault,
 input wire[92:0]local_tk,input wire[9:0]local_kst,
 input wire program_installed_valid,input wire execution_active,program_commit_v,input wire[15:0]program_commit_epoch,input wire[63:0]program_commit_digest,
 output wire program_ready,output wire[15:0]program_epoch,output wire[63:0]program_digest,
 output wire program_authorized_footer_v,output wire[63:0]program_authorized_footer64,
 output wire[15:0]program_begin_epoch,output wire program_begin_v,program_auth_v,output wire[10:0]program_expected_pw,output wire[3:0]program_expected_dw,output wire[15:0]program_auth_epoch,output wire[63:0]program_auth_digest,
 output wire[181:0]hc,output wire[7:0]seen,output wire irq,
 output wire host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,
 output wire[31:0]fault_src,output wire source_cr,available,
 output wire[282:0]hb,input wire hb_cr,input wire[12:0]est,
 input wire[36863:0]land_es,output wire[33407:0]land_er,
 output wire[36863:0]ctrl_es,input wire[33407:0]ctrl_er,
 input wire[127:0]ctrl_completion_v,ctrl_completion_we,ctrl_completion_fault,
 output wire marker_v,output wire[65:0]marker,
 output wire certificate_v,output wire[65:0]certificate,output wire[31:0]certificate_prefix,
 output wire[31:0]issued,landed,output wire[7:0]physical_ack_n,
 output wire[24:0]service_faults,
 output wire cq_commit_v,output wire[15:0]cq_client_tag,output wire[7:0]cq_slot,
 output wire[17:0]cq_pos,cq_token,output wire[1:0]cq_kind,output wire[3:0]cq_status,
 output wire step_issue_v,output wire[15:0]step_client_tag,output wire[7:0]step_slot,output wire[17:0]step_pos,output wire step_retire_v,step_retire_cq,output wire[15:0]step_retire_client_tag,output wire[7:0]step_retire_slot,output wire[17:0]step_retire_pos,step_retire_token,
 output wire host_idle,host_observer_fault
);
 wire[142:0]pr;wire[1:0]local_boot;
 wire[127:0]completion_v,completion_we,boot_done_pc,boot_ok_pc,boot_fault_pc;
 wire[36863:0]normal_ctrl_es;wire[33407:0]normal_ctrl_er;
 assign local_boot={&boot_ok_pc,&boot_done_pc};
 for(genvar pc=0;pc<128;pc=pc+1)begin:g_boot
  qkd_hbm_boot_static_completion u_boot(.ck(ck_boot[pc]),.ck_test(ck_boot_test[pc]),.rst_n(hbm_rst_n),.boot_go(boot_go),
  .normal_es(normal_ctrl_es[pc*288+:288]),.normal_er(normal_ctrl_er[pc*261+:261]),
  .ctrl_es(ctrl_es[pc*288+:288]),.ctrl_er(ctrl_er[pc*261+:261]),
  .completion_v(ctrl_completion_v[pc]),.completion_we(ctrl_completion_we[pc]),
  .normal_completion_v(completion_v[pc]),.normal_completion_we(completion_we[pc]),
  .boot_completion_v(),.boot_completion_we(),.boot_done(boot_done_pc[pc]),.boot_ok(boot_ok_pc[pc]),.boot_cause(),.fault(boot_fault_pc[pc]));
 end
 wire ingress_fault,program_fault;wire begin_image,word_v,word_desc,seal,auth_v;
 wire[15:0]image_epoch,auth_epoch;wire[10:0]pw_count;wire[3:0]dw_count;
 wire[9:0]word_addr;wire[63:0]word_data,auth_digest;wire replay_done;
 assign program_begin_epoch=image_epoch;assign program_begin_v=begin_image;assign program_auth_v=auth_v;assign program_expected_pw=pw_count;assign program_expected_dw=dw_count;assign program_auth_epoch=auth_epoch;assign program_auth_digest=auth_digest;
 reg committed,commit_fault;
 always @(posedge ck_program_loader or negedge host_rst_n)begin
  if(!host_rst_n)begin committed<=0;commit_fault<=0;end
  else begin
   if(begin_image||!program_installed_valid)committed<=0;
   else if(program_commit_v)begin
    if(!replay_done||program_commit_epoch!=program_epoch||program_commit_digest!=program_digest)commit_fault<=1;
    else committed<=1;
   end
  end
 end
 assign program_ready=program_installed_valid&&replay_done&&committed&&!program_fault&&!commit_fault&&!begin_image;
 qkd_host_program_loader u_program(.ck(ck_program_loader),.rst_n(host_rst_n),.begin_image(begin_image),.image_epoch(image_epoch),.pw_count(pw_count),.dw_count(dw_count),
 .word_v(word_v),.word_desc(word_desc),.word_addr(word_addr),.word_data(word_data),.seal(seal),.auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),
 .execution_active(execution_active),.pr(pr),.program_ready(replay_done),.fault(program_fault),.digest(program_digest),.program_epoch(program_epoch),.authorized_footer_valid(program_authorized_footer_v),.authorized_footer(program_authorized_footer64));
 wire[7:0]observed_physical_faults=physical_fault|((8'((|boot_fault_pc)||(|ctrl_completion_fault)||ingress_fault||program_fault||commit_fault||host_observer_fault||peer_link_fault))<<die_id);
 wire d_rv,d_rcr,d_cv,d_ccr;wire[1023:0]d_rd,d_cd;wire adapter_fault;
 wire raw_rx_v,raw_rx_cr,program_rx_v,program_rx_cr;wire[527:0]raw_rx_d,program_rx_d;
 wire physical_tx_v,physical_tx_cr,peer_link_fault;wire[527:0]physical_tx_d;
 qkd_host_peer_link u_peer(.ck(ck_peer),.rst_n(host_rst_n),.rx_v(raw_rx_v),.rx_d(raw_rx_d),.rx_cr(raw_rx_cr),.normal_rx_v(program_rx_v),.normal_rx_d(program_rx_d),.normal_rx_cr(program_rx_cr),
 .peer_rx_valid(peer_rx_valid),.peer_rx_data(peer_rx_data),.peer_rx_ready(peer_rx_ready),.normal_tx_v(tx_v),.normal_tx_d(tx_d),.normal_tx_cr(tx_cr),.peer_tx_valid(peer_tx_valid),.peer_tx_data(peer_tx_data),.peer_tx_ready(peer_tx_ready),.tx_v(physical_tx_v),.tx_d(physical_tx_d),.tx_cr(physical_tx_cr),.drained(peer_link_drained),.fault(peer_link_fault));
 wire rx_v,rx_cr,tx_v,tx_cr;wire[527:0]rx_d,tx_d;wire[4:0]phy_faults;
 qfd_link_adp512_split #(.MUT(PHY_MUT))u_adapter(.ck(ck_phy),.rst_n(host_rst_n),
 .c_v(d_cv),.c_d(d_cd),.c_cr(d_ccr),.r_v(d_rv),.r_d(d_rd),.r_cr(d_rcr),
 .tx_up(phy_up),.tx_v(phy_tx_v),.tx_flit(phy_tx_flit),.rx_v(phy_rx_v),.rx_flit(phy_rx_flit),.fault(adapter_fault));
 qkd_host_phy_cdc5 u_phy(.ck_pad(ck_pad),.rx_wck(ck_phy_rx_w),.rx_rck(ck_phy_rx_r),.tx_wck(ck_phy_tx_w),.tx_rck(ck_phy_tx_r),.rst_n(host_rst_n),
 .phy_rx_v(d_rv),.phy_rx_d(d_rd),.phy_rx_cr(d_rcr),.phy_tx_v(d_cv),.phy_tx_d(d_cd),.phy_tx_cr(d_ccr),
 .core_rx_v(raw_rx_v),.core_rx_d(raw_rx_d),.core_rx_cr(raw_rx_cr),.core_tx_v(physical_tx_v),.core_tx_d(physical_tx_d),.core_tx_cr(physical_tx_cr),.faults(phy_faults));
 qkd_host_program_rx u_program_rx(.ck(ck_program_rx),.rst_n(host_rst_n),.rx_v(program_rx_v),.rx_d(program_rx_d),.rx_cr(program_rx_cr),
 .normal_v(rx_v),.normal_d(rx_d),.normal_cr(rx_cr),.begin_image(begin_image),.image_epoch(image_epoch),.pw_count(pw_count),.dw_count(dw_count),
 .word_v(word_v),.word_desc(word_desc),.word_addr(word_addr),.word_data(word_data),.seal(seal),.auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.fault(ingress_fault));
 wire ing_v,done_v,done_cr;wire[1:0]ing_cls;wire[511:0]ing_d;wire[4:0]ing_crn;wire[63:0]done_d;
 wire source_fault;wire[3:0]packet_faults;
 wire[92:0]native_tk,guarded_tk;wire native_protocol_fault;
 wire[7:0]guarded_physical,guarded_transport,peer_service_ready,peer_pending_ack;wire[127:0]peer_service_epoch;
 wire service_begin_v,pending_advertised,begin_fault;wire[15:0]service_begin_epoch,pending_epoch;
 qkd_host_control_packet_observed #(.NL(NL),.ENABLE_TOKEN(ENABLE_TOKEN),.ENABLE_SERVICE(ENABLE_SERVICE),.T_LINK(T_LINK),.T_HBM(T_HBM),.WDOG(WDOG),.HC_MUT(HC_MUT),.PROMPT_MUT(PROMPT_MUT))u_control(.peer_reset_request(peer_reset_request),.cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cq_kind(cq_kind),.cq_status(cq_status),.step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.host_idle(host_idle),.host_observer_fault(host_observer_fault),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
 .token_allocator_fault(token_allocator_fault),
 .token_wrap_fence_valid(token_wrap_fence_valid),.token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),
 .package_abort(package_abort),.abort_drained(abort_drained),
 .token_request_valid(token_request_valid),.token_request_ready(token_request_ready),.token_request_token(token_request_token),.token_request_position(token_request_position),.token_request_generation(token_request_generation),
 .token_grant_valid(token_grant_valid),.token_grant_ready(token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),.token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),
 .allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),.allocated_position(allocated_position),.allocated_generation(allocated_generation),
 .token_epoch_valid(token_epoch_valid),.token_epoch(token_epoch),
 .cancel_valid(cancel_valid),.cancel_tag(cancel_tag),.cancel_generation(cancel_generation),.cancel_done(cancel_done),.cancel_fault(cancel_fault),.cancel_drained(cancel_drained),.terminal_accepted(token_cancel_accepted),
 .ck_host(ck_host),.ck_csr(ck_csr),.ck_rst(ck_rst),.ck_ctl(ck_ctl),.ck_prompt(ck_prompt),
 .ck_rx(ck_rx),.ck_tx(ck_tx),.ck_axi(ck_axi),.ck_ctrl(ck_ctrl),.ck_hc(ck_hc),
 .die_id(die_id),.por_n(por_n&&pll_locked),.link_up(link_up),.transport_fault(ENABLE_SERVICE?guarded_transport:transport_fault),.physical_fault(ENABLE_SERVICE?guarded_physical:observed_physical_faults),.crom_fault(crom_fault),.pr(pr),
 .irq(irq),.host_rst_n(host_rst_n),.link_rst_n(link_rst_n),.hbm_rst_n(hbm_rst_n),.boot_go(boot_go),.die_rst_n(die_rst_n),.sys_ready(sys_ready),.fault_src(fault_src),
 .rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),
 .local_tk(ENABLE_SERVICE?guarded_tk:(ENABLE_NATIVE?native_tk:local_tk)),.local_kst(local_kst),.local_boot(local_boot),.hc(hc),.seen(seen),
 .source_cr(source_cr),.available(available),.source_fault(source_fault),.packet_faults(packet_faults),
 .ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(ing_crn),.ing_t_v(done_v),.ing_t_d(done_d),.ing_t_cr(done_cr),
 .service_abort(service_abort),.service_ready(service_ready&&program_ready),.local_service_epoch(local_service_epoch),
 .service_diag_raw(service_diag_raw),.service_status(service_status),
 .service_begin_v(service_begin_v),.service_begin_epoch(service_begin_epoch),
 .pending_advertised(pending_advertised),.pending_epoch(pending_epoch),
 .service_ready8(peer_service_ready),.pending_ack8(peer_pending_ack),.service_epoch8(peer_service_epoch),
 .ingest_permission(ingest_permission),.begin_fault(begin_fault));
 wire marker_cr,marker_consumer_fault;
 qkd_host_marker_consumer u_marker_consumer(.ck(ck_bootbarrier),.rst_n(host_rst_n),.marker_v(marker_v),.marker(marker),.issued(issued),.landed(landed),.est(est),.source_fault(source_fault),.marker_cr(marker_cr),.certificate_v(certificate_v),.certificate(certificate),.certificate_prefix(certificate_prefix),.fault(marker_consumer_fault));
 wire qm_v,qm_t_v,qm_t_cr,fenced_v,fenced_cr;wire[1:0]qm_cls;wire[511:0]qm_d;wire[4:0]qm_crn;wire[63:0]qm_t_d,fenced_d;wire[5:0]bridge_faults;
 qkd_host_qm_clock_bridge_service #(.ENABLE_SERVICE(ENABLE_SERVICE),.MUT(BRIDGE_MUT))u_bridge(.cq(ck_qm_queue),.qw(ck_qm_ing_w),.qr(ck_qm_ing_r),.qp(ck_qm_credit),.ccw(ck_qm_done_w),.ccr(ck_qm_done_r),.rst_n(host_rst_n),
 .ingest_permission(ingest_permission),.ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(ing_crn),.qm_v(qm_v),.qm_cls(qm_cls),.qm_d(qm_d),.qm_crn(qm_crn),
 .done_v(fenced_v),.done_d(fenced_d),.done_cr(fenced_cr),.packet_done_v(done_v),.packet_done_d(done_d),.packet_done_cr(done_cr),.faults(bridge_faults));
 wire ov,owe,ocr,qm_fault;wire[31:0]oa;wire[255:0]od;
 qkd_host_native_qm #(.AW(32),.HDMAX(128),.KVHMAX(2),.RMW_EN(0),.QPIPE(2),.NATIVE_ROWS(1),.MUT(QM_MUT))u_qm(
 .rst_n(host_rst_n),.clk_h(ck_qm_host),.h_v(qm_v),.h_cls(qm_cls),.h_d(qm_d),.h_crn(qm_crn),.t_v(qm_t_v),.t_d(qm_t_d),.t_cr(qm_t_cr),
 .clk_i(ck_qm_ingest),.clk_i_bank(ck_qm_bank),.clk_i_out(ck_qm_out),.ck(ck_qm_core),
 .o_v(ov),.o_we(owe),.o_addr(oa),.o_d(od),.o_cr(ocr),.i_rv(1'b0),.i_rd(256'd0),.fault(qm_fault));
 wire[289:0]kv_ing;wire kv_ing_cr;wire[127:0]all_acks;wire global_prefix_v,dispatch_fault;
 wire[31:0]kv_issued,kv_landed;wire local_marker_v,local_marker_cr,bootbarrier_fault,image_check;wire[65:0]local_marker;
 qkd_host_emb_boot_barrier u_bootbarrier(.ck(ck_bootbarrier),.rst_n(host_rst_n),.in_v(local_marker_v),.in_d(local_marker),.in_cr(local_marker_cr),.est(est),.require_fresh(image_check),.out_v(marker_v),.out_d(marker),.out_cr(marker_cr),.fault(bootbarrier_fault));
 qkd_host_boot_dispatch u_dispatch(.ck(ck_dispatch),.ck_order(ck_retire),.rst_n(host_rst_n),.boot_release(local_marker_cr),
 .ing({od,oa,owe,ov}),.ing_cr(ocr),.kv(kv_ing),.kv_cr(kv_ing_cr),.hb(hb),.hb_cr(hb_cr),.image_check(image_check),
 .acks(all_acks),.prefix_v(global_prefix_v),.issued(issued),.landed(landed),.fault(dispatch_fault));
 wire map_fault,order_fault,fence_fault;wire[3:0]chain_fault;wire[7:0]prefix_ack_n;wire[31:0]fence_landed;
 qkd_host_ingest_chain_splitboot #(.ORDER_MUT(ORDER_MUT))u_chain(.ck_map(ck_map),.ck_sum(ck_sum),.ck_order(ck_order),.ck_station(ck_station),.ck_static(ck_static),.rst_n(host_rst_n),
 .ing(kv_ing),.ing_cr(kv_ing_cr),.all_acks(all_acks),.land_es(land_es),.land_er(land_er),.ctrl_es(normal_ctrl_es),.ctrl_er(normal_ctrl_er),.completion_v(completion_v),.completion_we(completion_we),
 .marker_v(local_marker_v),.marker(local_marker),.marker_cr(local_marker_cr),.issued(kv_issued),.landed(kv_landed),.map_fault(map_fault),.chain_fault(chain_fault),.ack_n(prefix_ack_n),.physical_ack_n(physical_ack_n),.order_fault(order_fault));
 qkd_host_visibility_fence u_fence(.rst_n(host_rst_n),.ck(ck_fence_core),.clk_h(ck_fence_host),.ack_n({7'd0,global_prefix_v}),
 .in_v(qm_t_v),.in_d(qm_t_d),.in_cr(qm_t_cr),.out_v(fenced_v),.out_d(fenced_d),.out_cr(fenced_cr),.fault(fence_fault),.landed_debug(fence_landed));
 qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(ENABLE_NATIVE))u_native(
 .ck(ck_native),.por_n(por_n&&pll_locked),.rst_n(host_rst_n),.hc(hc),.legacy_tk(local_tk),
 .recovery_clear(native_recovery_clear),.cancel_release_v(cancel_release_v),.cancel_release_tag(cancel_release_tag),.cancel_release_gen(cancel_release_gen),.cancel_released(cancel_released),.context_owned(native_context_owned),
 .image_ready(program_ready),.shared_epoch_valid(token_epoch_valid),.shared_epoch(token_epoch),
 .request_v(native_request_v),.request_tag(native_request_tag),.request_trace(native_request_trace),.request_gen(native_request_gen),
 .request_token(native_request_token),.request_pos(native_request_pos),.request_cr(native_request_cr),.native_pr(native_pr),
 .result_v(native_result_v),.result_tag(native_result_tag),.result_gen(native_result_gen),
 .result_done(native_result_done),.result_fault(native_result_fault),.result_cause(native_result_cause),
 .result_token(native_result_token),.result_value(native_result_value),.result_cycles(native_result_cycles),.result_cr(native_result_cr),
 .kv_drained(native_kv_drained),.vm_drained(native_vm_drained),.collective_drained(native_collective_drained),.host_drained(native_host_drained),
 .collective_busy(native_collective_busy),.kv_flush(native_kv_flush),.local_tk(native_tk),.protocol_fault(native_protocol_fault));
 qkd_host_service_guard u_guard(.ck_guard(ck_guard),.rst_n(host_rst_n),.raw_faults(service_faults),
 .die_id(die_id),.physical_faults(observed_physical_faults),.transport_faults(transport_fault),
 .accepted_ing_v(ing_v),.accepted_ing_cls(ing_cls),.accepted_ing_header(ing_d[15:0]),
 .done_v(done_v),.done_d(done_d),.boot_barrier_v(certificate_v),.boot_barrier_target(certificate_prefix),
 .begin_v(service_begin_v),.begin_epoch(service_begin_epoch),.pending_advertised(pending_advertised),.pending_epoch(pending_epoch),
 .local_tk(ENABLE_NATIVE?native_tk:local_tk),.guarded_tk(guarded_tk),.abort(service_abort),.service_ready(service_ready),
 .service_epoch(local_service_epoch),.diag_raw(service_diag_raw),.status(service_status),
 .physical_diag(guarded_physical),.transport_diag(guarded_transport),.service_protocol_fault(begin_fault));
 initial if(ENABLE_NATIVE&&(!ENABLE_SERVICE||!ENABLE_TOKEN))$fatal(1,"native HOST requires transported token identity and real service guard");
 assign service_faults={source_fault|dispatch_fault|bootbarrier_fault|marker_consumer_fault|est[1]|(ENABLE_NATIVE&&native_protocol_fault),packet_faults,chain_fault,fence_fault,order_fault,map_fault,qm_fault,bridge_faults,phy_faults,adapter_fault};
endmodule
