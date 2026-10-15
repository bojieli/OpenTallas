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
module qkd_host_splitboot_service #(
 parameter T_LINK=200000,T_HBM=200000,WDOG=1<<22,
 parameter ENABLE_SERVICE=0,ENABLE_NATIVE=0,ENABLE_TOKEN=0,
 parameter PHY_MUT=0,QM_MUT=0,ORDER_MUT=0,BRIDGE_MUT=0,HC_MUT=0,PROMPT_MUT=0
)(
 input wire[7:0]ck_phy,input wire ck_pad,ck_phy_rx_w,ck_phy_rx_r,ck_phy_tx_w,ck_phy_tx_r,
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
 input wire[5:0]link_up,input wire[7:0]transport_fault,physical_fault,input wire crom_fault,
 input wire[142:0]pr,input wire[92:0]local_tk,input wire[9:0]local_kst,input wire[1:0]local_boot,
 output wire[181:0]hc,output wire[7:0]seen,output wire irq,
 output wire host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,
 output wire[31:0]fault_src,output wire source_cr,available,
 output wire[282:0]hb,input wire hb_cr,input wire[12:0]est,
 input wire[36863:0]land_es,output wire[33407:0]land_er,
 output wire[36863:0]ctrl_es,input wire[33407:0]ctrl_er,
 input wire[127:0]completion_v,completion_we,
 output wire marker_v,output wire[65:0]marker,input wire marker_cr,
 output wire[31:0]issued,landed,output wire[7:0]physical_ack_n,
 output wire[24:0]service_faults
);
 wire d_rv,d_rcr,d_cv,d_ccr;wire[1023:0]d_rd,d_cd;wire adapter_fault;
 wire rx_v,rx_cr,tx_v,tx_cr;wire[527:0]rx_d,tx_d;wire[4:0]phy_faults;
 qfd_link_adp512_split #(.MUT(PHY_MUT))u_adapter(.ck(ck_phy),.rst_n(host_rst_n),
 .c_v(d_cv),.c_d(d_cd),.c_cr(d_ccr),.r_v(d_rv),.r_d(d_rd),.r_cr(d_rcr),
 .tx_up(phy_up),.tx_v(phy_tx_v),.tx_flit(phy_tx_flit),.rx_v(phy_rx_v),.rx_flit(phy_rx_flit),.fault(adapter_fault));
 qkd_host_phy_cdc5 u_phy(.ck_pad(ck_pad),.rx_wck(ck_phy_rx_w),.rx_rck(ck_phy_rx_r),.tx_wck(ck_phy_tx_w),.tx_rck(ck_phy_tx_r),.rst_n(host_rst_n),
 .phy_rx_v(d_rv),.phy_rx_d(d_rd),.phy_rx_cr(d_rcr),.phy_tx_v(d_cv),.phy_tx_d(d_cd),.phy_tx_cr(d_ccr),
 .core_rx_v(rx_v),.core_rx_d(rx_d),.core_rx_cr(rx_cr),.core_tx_v(tx_v),.core_tx_d(tx_d),.core_tx_cr(tx_cr),.faults(phy_faults));
 wire ing_v,done_v,done_cr;wire[1:0]ing_cls;wire[511:0]ing_d;wire[4:0]ing_crn;wire[63:0]done_d;
 wire source_fault;wire[3:0]packet_faults;
 wire[92:0]native_tk,guarded_tk;wire native_protocol_fault;
 wire[7:0]guarded_physical,guarded_transport,peer_service_ready,peer_pending_ack;wire[127:0]peer_service_epoch;
 wire service_begin_v,pending_advertised,begin_fault;wire[15:0]service_begin_epoch,pending_epoch;
 qkd_host_control_packet_capture_token_service #(.ENABLE_TOKEN(ENABLE_TOKEN),.ENABLE_SERVICE(ENABLE_SERVICE),.T_LINK(T_LINK),.T_HBM(T_HBM),.WDOG(WDOG),.HC_MUT(HC_MUT),.PROMPT_MUT(PROMPT_MUT))u_control(
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
 .die_id(die_id),.por_n(por_n&&pll_locked),.link_up(link_up),.transport_fault(ENABLE_SERVICE?guarded_transport:transport_fault),.physical_fault(ENABLE_SERVICE?guarded_physical:physical_fault),.crom_fault(crom_fault),.pr(pr),
 .irq(irq),.host_rst_n(host_rst_n),.link_rst_n(link_rst_n),.hbm_rst_n(hbm_rst_n),.boot_go(boot_go),.die_rst_n(die_rst_n),.sys_ready(sys_ready),.fault_src(fault_src),
 .rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),
 .local_tk(ENABLE_SERVICE?guarded_tk:(ENABLE_NATIVE?native_tk:local_tk)),.local_kst(local_kst),.local_boot(local_boot),.hc(hc),.seen(seen),
 .source_cr(source_cr),.available(available),.source_fault(source_fault),.packet_faults(packet_faults),
 .ing_v(ing_v),.ing_cls(ing_cls),.ing_d(ing_d),.ing_crn(ing_crn),.ing_t_v(done_v),.ing_t_d(done_d),.ing_t_cr(done_cr),
 .service_abort(service_abort),.service_ready(service_ready),.local_service_epoch(local_service_epoch),
 .service_diag_raw(service_diag_raw),.service_status(service_status),
 .service_begin_v(service_begin_v),.service_begin_epoch(service_begin_epoch),
 .pending_advertised(pending_advertised),.pending_epoch(pending_epoch),
 .service_ready8(peer_service_ready),.pending_ack8(peer_pending_ack),.service_epoch8(peer_service_epoch),
 .ingest_permission(ingest_permission),.begin_fault(begin_fault));
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
 .ing(kv_ing),.ing_cr(kv_ing_cr),.all_acks(all_acks),.land_es(land_es),.land_er(land_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),.completion_v(completion_v),.completion_we(completion_we),
 .marker_v(local_marker_v),.marker(local_marker),.marker_cr(local_marker_cr),.issued(kv_issued),.landed(kv_landed),.map_fault(map_fault),.chain_fault(chain_fault),.ack_n(prefix_ack_n),.physical_ack_n(physical_ack_n),.order_fault(order_fault));
 qkd_host_visibility_fence u_fence(.rst_n(host_rst_n),.ck(ck_fence_core),.clk_h(ck_fence_host),.ack_n({7'd0,global_prefix_v}),
 .in_v(qm_t_v),.in_d(qm_t_d),.in_cr(qm_t_cr),.out_v(fenced_v),.out_d(fenced_d),.out_cr(fenced_cr),.fault(fence_fault),.landed_debug(fence_landed));
 qkd_host_native_token_endpoint #(.ENABLE_NATIVE(ENABLE_NATIVE))u_native(
 .ck(ck_native),.por_n(por_n&&pll_locked),.rst_n(host_rst_n),.hc(hc),.legacy_tk(local_tk),
 .shared_epoch_valid(token_epoch_valid),.shared_epoch(token_epoch),
 .request_v(native_request_v),.request_tag(native_request_tag),.request_trace(native_request_trace),.request_gen(native_request_gen),
 .request_token(native_request_token),.request_pos(native_request_pos),.request_cr(native_request_cr),.native_pr(native_pr),
 .result_v(native_result_v),.result_tag(native_result_tag),.result_gen(native_result_gen),
 .result_done(native_result_done),.result_fault(native_result_fault),.result_cause(native_result_cause),
 .result_token(native_result_token),.result_value(native_result_value),.result_cycles(native_result_cycles),.result_cr(native_result_cr),
 .kv_drained(native_kv_drained),.vm_drained(native_vm_drained),.collective_drained(native_collective_drained),.host_drained(native_host_drained),
 .collective_busy(native_collective_busy),.kv_flush(native_kv_flush),.local_tk(native_tk),.protocol_fault(native_protocol_fault));
 qkd_host_service_guard u_guard(.ck_guard(ck_guard),.rst_n(host_rst_n),.raw_faults(service_faults),
 .die_id(die_id),.physical_faults(physical_fault),.transport_faults(transport_fault),
 .accepted_ing_v(ing_v),.accepted_ing_cls(ing_cls),.accepted_ing_header(ing_d[15:0]),
 .done_v(done_v),.done_d(done_d),.boot_barrier_v(marker_v),.boot_barrier_target(landed),
 .begin_v(service_begin_v),.begin_epoch(service_begin_epoch),.pending_advertised(pending_advertised),.pending_epoch(pending_epoch),
 .local_tk(ENABLE_NATIVE?native_tk:local_tk),.guarded_tk(guarded_tk),.abort(service_abort),.service_ready(service_ready),
 .service_epoch(local_service_epoch),.diag_raw(service_diag_raw),.status(service_status),
 .physical_diag(guarded_physical),.transport_diag(guarded_transport),.service_protocol_fault(begin_fault));
 initial if(ENABLE_NATIVE&&(!ENABLE_SERVICE||!ENABLE_TOKEN))$fatal(1,"native HOST requires transported token identity and real service guard");
 assign service_faults={source_fault|dispatch_fault|bootbarrier_fault|est[1]|(ENABLE_NATIVE&&native_protocol_fault),packet_faults,chain_fault,fence_fault,order_fault,map_fault,qm_fault,bridge_faults,phy_faults,adapter_fault};
endmodule
