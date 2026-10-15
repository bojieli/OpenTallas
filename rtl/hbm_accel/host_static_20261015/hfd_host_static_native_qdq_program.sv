`timescale 1ns/1ps
`default_nettype none
// Native host installation composition, ending at the actual QDQ COMPACT1
// programme command port. This does not replace the QDQ engine/VM consumers.
// All clocks must be the declared same synchronous family: separate entry
// pins preserve hardened-child ownership and do not imply CDC tolerance.
// Remaining external-service ports are explicit, all685bits used.
module hfd_host_static_native_qdq_program #(parameter integer MUT=0,READY_MUT=0)(
 input wire clk_controller,clk_landing,clk_ep,clk_face,input wire[11:0]clk_sub,
 input wire clk_tx_shared,clk_rx_shared,clk_status_shared,clk_phy,rst_n,
 input wire[23:0]session,inout wire[684:0]service_h,
 output wire[512:0]pma_tx,output wire pma_tck,input wire[512:0]pma_rx,input wire pma_rck,
 output wire[4:0]host_faults,output wire[1:0]phy_status,output wire ep_locked,
 output wire program_ready,program_active,program_done,configured,program_fault,ingress_fault,
 output wire[47:0]command,output wire command_v,output wire[31:0]ordinal);
 tri[786:0]h;wire[1:0]bresp;
 assign h[37]=service_h[0];
 assign service_h[369]=h[471];
 assign h[49:38]=service_h[12:1];
 assign h[50]=service_h[13];
 assign service_h[370]=h[472];
 assign h[82:51]=service_h[45:14];
 assign h[86:83]=service_h[49:46];
 assign service_h[371]=h[473];
 assign h[87]=service_h[50];
 assign h[88]=service_h[51];
 assign service_h[372]=h[474];
 assign h[100:89]=service_h[63:52];
 assign service_h[373]=h[475];
 assign h[101]=service_h[64];
 assign service_h[405:374]=h[507:476];
 assign service_h[406]=h[508];
 assign h[102]=service_h[65];
 assign service_h[470:407]=h[572:509];
 assign h[103]=service_h[66];
 assign service_h[471]=h[573];
 assign h[167:104]=service_h[130:67];
 assign h[169:168]=service_h[132:131];
 assign h[170]=service_h[133];
 assign service_h[472]=h[574];
 assign h[171]=service_h[134];
 assign service_h[536:473]=h[638:575];
 assign service_h[537]=h[639];
 assign h[172]=service_h[135];
 assign service_h[601:538]=h[703:640];
 assign service_h[609:602]=h[711:704];
 assign h[173]=service_h[136];
 assign service_h[610]=h[712];
 assign h[175:174]=service_h[138:137];
 assign h[176]=service_h[139];
 assign service_h[611]=h[713];
 assign h[240:177]=service_h[203:140];
 assign h[248:241]=service_h[211:204];
 assign h[251:249]=service_h[214:212];
 assign service_h[612]=h[714];
 assign h[252]=service_h[215];
 assign service_h[676:613]=h[778:715];
 assign service_h[678:677]=h[780:779];
 assign service_h[679]=h[781];
 assign h[253]=service_h[216];
 assign service_h[680]=h[782];
 assign h[317:254]=service_h[280:217];
 assign h[325:318]=service_h[288:281];
 assign h[328:326]=service_h[291:289];
 assign h[329]=service_h[292];
 assign service_h[681]=h[783];
 assign h[393:330]=service_h[356:293];
 assign h[401:394]=service_h[364:357];
 assign h[402]=service_h[365];
 assign service_h[682]=h[784];
 assign h[403]=service_h[366];
 assign service_h[684:683]=h[786:785];
 assign h[404]=service_h[367];
 assign h[405]=service_h[368];
 hfd_host_native #(.MUT(MUT==3?3:0)) u_host(
 .clk_controller(clk_controller),.clk_landing(clk_landing),.clk_ep(clk_ep),.clk_face(clk_face),.clk_sub(clk_sub),
 .clk_tx_shared(clk_tx_shared),.clk_rx_shared(clk_rx_shared),.clk_status_shared(clk_status_shared),.clk_phy(clk_phy),.rst_n(rst_n),
 .session(session),.h(h),.s_bresp(bresp),.pma_tx(pma_tx),.pma_tck(pma_tck),.pma_rx(pma_rx),.pma_rck(pma_rck),
 .faults(host_faults),.phy_status(phy_status),.ep_locked(ep_locked));
 wire cv,dv,lv;wire[7:0]target;wire[11:0]addr,base;wire[12:0]limit;wire[15:0]loops;wire[255:0]data;
 ot_hbm_host_static_ingress #(.MUT(MUT==1?1:(MUT==2?2:0))) u_ingress(
 .clk(clk_controller),.rst_n(rst_n),.s_awvalid(h[406]),.s_awready(h[0]),.s_awaddr(h[418:407]),
 .s_wvalid(h[419]),.s_wready(h[1]),.s_wdata(h[451:420]),.s_wstrb(h[455:452]),
 .s_bvalid(h[2]),.s_bready(h[456]),.s_bresp(bresp),.s_arvalid(h[457]),.s_arready(h[3]),.s_araddr(h[469:458]),
 .s_rvalid(h[4]),.s_rready(h[470]),.s_rdata(h[36:5]),
 .block_ready(program_ready),.program_active(program_active),.program_fault(program_fault),
 .cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(dv),.desc_base(base),.desc_limit(limit),
 .desc_loops(loops),.launch_v(lv),.fault(ingress_fault));
 ot_hbm_host_qdq_installed_target #(.MUT(READY_MUT)) u_target(
 .clk(clk_controller),.rst_n(rst_n),.cfg_v(cv),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),
 .desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),
 .block_ready(program_ready),.active(program_active),.done(program_done),.configured(configured),.fault(program_fault),
 .command(command),.command_v(command_v),.ordinal(ordinal));
endmodule
`default_nettype wire
