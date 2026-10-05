`timescale 1ns/1ps
// EXEC-only combined successor: one shared SM0 owner. Standalone bf3 sources untouched.
// Existing executor and provider interfaces; opt-in, physical unqualified.
// Existing LAUNCH PC bank and SM0 IM64 loader, unchanged doorbell/CPL authority.
// Source-selected DS cluster with real SM/memory/collective ports exposed on
// clk_sm for the DSpark sequencer. Host16/rings are intentionally not in this
// path. Token17 reaches UR0 and actual RESULT17; no truncation or synthetic ACK.
module ot_ds_hbm_cluster20_integrated #(
 parameter integer COMBINED_ENABLE=0,SU_ENABLE=0,SU_REGISTERED_OUTPUTS=0,SU_REGISTERED_STATUS=0,W2_RESULT_ENABLE=0,FORMATTER_ENABLE=0,NORMAL_GATHER_ENABLE=0,LOCAL_CP_RESET_ENABLE=0,VM_AW=0,
 parameter integer ENABLE=0, TW=17, PW=20, CONTEXT_POSITIONS=1048576, ND=2, NSM=2, NL=128, IMW=14,
 parameter integer CB=8, NS=2, NPC=2, MEM_WORDS=2097152,
 parameter integer SW_PIPE=8, USE_W2=0, HAS_DIV=1, HAS_BD=1
)(
 input wire por_n, clk_host, clk_sm, clk_mem, clk_link,
 // Local reset is deferred; it never resets shared credit or the provider.
 input wire [ND-1:0] cp_reset_req,output wire [ND-1:0] cp_reset_ack,
 input wire [ND-1:0] cmd_we,
 input wire [ND*CB-1:0] cmd_addr,
 input wire [ND*64-1:0] cmd_wdata,
 input wire [ND-1:0] db_v, output wire [ND-1:0] db_rdy,
 input wire [ND*TW-1:0] db_token,
 input wire [ND*PW-1:0] db_pos,
 input wire [ND*32-1:0] db_job,
 input wire [ND*4-1:0] db_generation,
 output wire [ND-1:0] cpl_v, input wire [ND-1:0] cpl_rdy,
 output wire [ND*(TW+PW+72)-1:0] cpl_data,
 input wire [ND*NSM-1:0] im_we,
 input wire [IMW-1:0] im_addr, input wire [63:0] im_data,
 // Owned combined callbacks. Descriptor/GO must originate from the actual
 // installed recipe; absent 96x512 source/entry remains compiler-failclosed.
 input wire [ND-1:0] gather_desc_v,gather_start_v,gather_book_valid,gather_req_v,gather_rsp_r,
 input wire [ND*3-1:0] gather_desc_index,input wire [ND*64-1:0] gather_desc_data,
 input wire [ND*649-1:0] gather_req,
 output wire [ND-1:0] gather_desc_r,gather_start_r,gather_req_r,gather_rsp_v,
 output wire [ND*637-1:0] gather_rsp,
 input wire [ND-1:0] gather_release_v,gather_result_published,gather_reverse_done,
 input wire [ND*73-1:0] gather_release_frame,output wire [ND-1:0] gather_release_r,
 output wire [ND-1:0] gather_retained,gather_arena_visible,gather_sink_visible,
 // Original normal W15 synchronous VM / collective ports; no ready/data ties.
 input wire [ND-1:0] normal_go,normal_id_plane,normal_e_ready,normal_o_valid,normal_o_last,normal_o_err,normal_engine_fault,
 input wire [ND*16-1:0] normal_command_tag,input wire [ND*32-1:0] normal_source_word,
 input wire [ND*512-1:0] normal_vm_rq,normal_o_data,input wire [ND*7-1:0] normal_o_rank,
 output wire [ND-1:0] normal_busy,normal_done,normal_vm_re,normal_e_valid,normal_e_last,normal_e_mode,normal_o_ready,
 output wire [ND*32-1:0] normal_vm_raddr,output wire [ND*512-1:0] normal_e_data,output wire [ND*16-1:0] normal_e_tag,
 // Ordered adapter request85 low tag16/word6/rank7/pos20/gen4/job32.
 // Response599 low UE1/checked1/data512/tag16/word6/rank7/pos20/gen4/job32.
 input wire [ND-1:0] formatter_start_v,index_pair_v,index_pairs_r,formatter_release_v,
 input wire [ND*85-1:0] index_pair,
 output wire [ND-1:0] formatter_start_r,index_pair_r,index_pairs_v,formatter_release_r,
 output wire [ND*599-1:0] index_pairs,
 // Existing caller rv/rop/rrow NC8 fields, held installed output extents.
 input wire [ND-1:0] w2_reserve_v,w2_output_installed,w2_pair_op,w2_result_v,w2_native_done,w2_assembly_drained,
 input wire [ND*2-1:0] w2_rows_a,w2_rows_b,
 input wire [ND*32-1:0] w2_op_a,w2_op_b,w2_output_base_a,w2_output_limit_a,w2_output_base_b,w2_output_limit_b,w2_result_op,
 input wire [ND*16-1:0] w2_output_tag,input wire [ND*12-1:0] w2_result_row,
 input wire [ND*256-1:0] w2_result_data,
 output wire [ND-1:0] w2_reserve_r,w2_source_permit,w2_output_done,
 input wire [ND-1:0] w2_lease_v,w2_release_v,w2_quiet,w2_req_v,w2_rsp_r,
 input wire [ND*73-1:0] w2_lease_frame,w2_release_frame,
 input wire [ND*337-1:0] w2_req,output wire [ND*273-1:0] w2_rsp,
 output wire [ND-1:0] w2_lease_granted,w2_release_r,w2_req_r,w2_rsp_v,
 output wire rst_sm_n, output wire sys_fault
);
initial if(COMBINED_ENABLE && (TW!=17 || PW!=20 || NSM!=2 || IMW!=14 || NS!=2 || NPC!=2 || USE_W2!=0))
 $fatal(1,"installed SU parent requires NSM2/IMW14/NS2/NPC2/defaultW2");
generate if(COMBINED_ENABLE==0) begin:g_original
 ot_ds_hbm_cluster20 #(.ENABLE(ENABLE),.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),
  .ND(ND),.NSM(NSM),.NL(NL),.IMW(IMW),.CB(CB),.NS(NS),.NPC(NPC),.MEM_WORDS(MEM_WORDS),
  .SW_PIPE(SW_PIPE),.USE_W2(USE_W2),.HAS_DIV(HAS_DIV),.HAS_BD(HAS_BD)) u_original(
  .por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
  .cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),.db_v(db_v),.db_rdy(db_rdy),
  .db_token(db_token),.db_pos(db_pos),.db_job(db_job),.db_generation(db_generation),
  .cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_data(cpl_data),.im_we(im_we),.im_addr(im_addr),.im_data(im_data),
  .rst_sm_n(rst_sm_n),.sys_fault(sys_fault));

 assign normal_busy=0;assign normal_done=0;assign normal_vm_re=0;assign normal_vm_raddr=0;
 assign normal_e_valid=0;assign normal_e_data=0;assign normal_e_last=0;assign normal_e_mode=0;assign normal_e_tag=0;assign normal_o_ready=0;
 assign cp_reset_ack=0;
 assign formatter_start_r=0;assign index_pair_r=0;assign index_pairs_v=0;assign index_pairs=0;assign formatter_release_r=0;
 assign gather_desc_r=0;assign gather_start_r=0;assign gather_req_r=0;assign gather_rsp_v=0;assign gather_rsp=0;
 assign gather_release_r=0;assign gather_retained=0;assign gather_arena_visible=0;assign gather_sink_visible=0;
 assign w2_reserve_r=0;assign w2_source_permit=0;assign w2_output_done=0;
 assign w2_lease_granted=0;assign w2_release_r=0;assign w2_req_r=0;assign w2_rsp_v=0;assign w2_rsp=0;
end else if(ENABLE==0) begin:g_off
 assign db_rdy=0; assign cpl_v=0; assign cpl_data=0;
 assign rst_sm_n=0; assign sys_fault=0;
 assign normal_busy=0;assign normal_done=0;assign normal_vm_re=0;assign normal_vm_raddr=0;
 assign normal_e_valid=0;assign normal_e_data=0;assign normal_e_last=0;assign normal_e_mode=0;assign normal_e_tag=0;assign normal_o_ready=0;
 assign cp_reset_ack=0;
 assign formatter_start_r=0;assign index_pair_r=0;assign index_pairs_v=0;assign index_pairs=0;assign formatter_release_r=0;
 assign gather_desc_r=0;assign gather_start_r=0;assign gather_req_r=0;assign gather_rsp_v=0;assign gather_rsp=0;
 assign gather_release_r=0;assign gather_retained=0;assign gather_arena_visible=0;assign gather_sink_visible=0;
 assign w2_reserve_r=0;assign w2_source_permit=0;assign w2_output_done=0;
 assign w2_lease_granted=0;assign w2_release_r=0;assign w2_req_r=0;assign w2_rsp_v=0;assign w2_rsp=0;

end else begin:g_on
 localparam integer NCL=2*NSM;
 wire rst_host_n, rst_mem_n, rst_link_n;
 ot_gpu_reset_ctrl #(.ENABLE(1)) u_rst(.por_n(por_n),
 .clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
 .rst_host_n(rst_host_n),.rst_sm_n(rst_sm_n),.rst_mem_n(rst_mem_n),.rst_link_n(rst_link_n));
    // ------------------------------------------------------------------ collective fabric
    wire [ND-1:0]         ep_req_v, ep_req_rdy, ep_mode, ep_rsp_v, ep_rsp_rdy;
    wire [ND*8-1:0]       ep_count;
    wire [ND*NL*32-1:0]   ep_data, ep_rsp_data;
    wire                  coll_fault;
    ot_gpu_coll_system #(.ENABLE(1), .R(ND), .NL(NL), .SW_PIPE(SW_PIPE)) u_coll (
        .clk_sm(clk_sm), .rst_sm_n(rst_sm_n), .clk_link(clk_link), .rst_link_n(rst_link_n),
        .req_v(ep_req_v), .req_rdy(ep_req_rdy), .mode(ep_mode), .count(ep_count), .data(ep_data),
        .rsp_v(ep_rsp_v), .rsp_rdy(ep_rsp_rdy), .rsp_data(ep_rsp_data), .fault(coll_fault));

    // ------------------------------------------------------------------ dies
    wire [ND-1:0] die_fault;
    genvar d, s;
    for (d = 0; d < ND; d = d + 1) begin : g_die
        wire [NSM-1:0] launch_v, sm_done, sm_fault, res_v, bar_arr, bar_rel, busy;
        wire [NSM-1:0] native_done,native_fault;
        wire su_pending,su_owned,su_done,su_fault,su_exec_done,su_exec_fault;
        wire [31:0] su_pc;
        wire [NSM-1:0] native_launch;
        wire su_selected,su_quiet;wire [31:0] su_job;wire [3:0] su_gen;
        wire [16:0] su_token;wire [19:0] su_pos;
        wire su_lease_v,su_release_v,su_release_r;wire [3:0] su_retired;
        wire cp_idle,cp_cpl_v,cp_retire_ready,native_credit_empty,shared_idle;
        wire cp_reset_wait,cp_reset_n,cp_reset_fault;
        ot_hbm_integrated_cp_reset #(.ENABLE(LOCAL_CP_RESET_ENABLE)) u_cp_reset(
         .clk(clk_sm),.por_n(rst_sm_n),.reset_req(cp_reset_req[d]),.cp_idle(cp_idle),
         .routes_drained(all_routes_drained),.cp_reset_n(cp_reset_n),.reset_ack(cp_reset_ack[d]),
         .block_new(cp_reset_wait),.fault(cp_reset_fault));
        wire shared_fault;wire [1:0] peer_grants,peer_releases;
        wire [3:0] response_authorized,return_offer;
        assign sm_done=su_selected?{{(NSM-1){1'b0}},su_done}:native_done;
        assign sm_fault=native_fault | {NSM{su_fault|su_exec_fault|fmt_fault|cp_reset_fault|store_fault}};
        wire [31:0] launch_pc;
        wire [TW-1:0] launch_token; wire [PW-1:0] launch_pos;
        wire [NSM*32-1:0] res_data;
        wire [TW-1:0] cpl_token; wire [PW-1:0] cpl_position; wire [31:0] cpl_job; wire [3:0] cpl_generation; wire [3:0] cpl_status; wire [31:0] cpl_cycles, st_kernels, st_busy;
        ot_ds_hbm_cmdproc20 #(.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS), .ENABLE(1), .NSM(NSM), .NCMD(1 << CB)) u_cp (
            .clk(clk_sm), .rst_n(cp_reset_n), .cmd_we(cmd_we[d]&&!cp_reset_wait), .cmd_addr(cmd_addr[d*CB +: CB]), .cmd_wdata(cmd_wdata[d*64 +: 64]),
            .db_v(db_v[d] && db_rdy[d]), .db_rdy(cp_idle), .db_token(db_token[d*TW +: TW]), .db_pos(db_pos[d*PW +: PW]),
            .db_job(db_job[d*32+:32]),.db_generation(db_generation[d*4+:4]),
            .cpl_position(cpl_position),.cpl_job(cpl_job),.cpl_generation(cpl_generation),
            .launch_v(launch_v), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
            .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data),
            .cpl_v(cp_cpl_v), .cpl_rdy(cp_retire_ready), .cpl_token(cpl_token), .cpl_status(cpl_status),
            .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy));
        // The CP's context cannot change across any prior native/borrower debt.
        wire all_prior_quiet=!(|busy)&&!(|launch_v)&&!(|a_req_v)&&!(|a_rsp_v)&&
                             !(|obs_req)&&!(|obs_rsp);
        wire all_routes_drained=native_credit_empty&&shared_idle&&!su_pending&&!su_owned&&
                                !gather_retained[d]&&!fmt_retained&&w2_quiet[d]&&!w2_sink_retained&&all_prior_quiet;
        assign db_rdy[d]=cp_idle&&all_routes_drained&&!cp_reset_wait;
        assign cpl_v[d]=cp_cpl_v&&all_routes_drained;
        assign cp_retire_ready=cpl_rdy[d]&&all_routes_drained;
        assign cpl_data[d*(TW+PW+72) +: (TW+PW+72)] = {cpl_job,cpl_generation,cpl_cycles,cpl_status,cpl_position,cpl_token};
        // grid barrier: one node, the SMs of the die as children (root: release = own arrival sense)
        wire bar_up;
        ot_gpu_barrier_node #(.K(NSM)) u_bar (.clk(clk_sm), .rst_n(rst_sm_n), .arr(bar_arr), .up(bar_up),
                                              .rel_in(bar_up), .rel(bar_rel));
        // memory clients (clk_sm side) and their crossings
        wire [NCL-1:0]       c_req_v, c_req_rdy, c_req_we, c_rsp_v, c_rsp_rdy, c_rsp_we;
        wire [NCL*32-1:0]    c_req_addr, c_req_wstrb;
        wire [NCL*256-1:0]   c_req_wdata, c_rsp_data;
        wire [NCL*16-1:0]    c_req_tag, c_rsp_tag;
        wire [NCL-1:0]       x_req_v, x_req_rdy, x_req_we, x_rsp_v, x_rsp_rdy, x_rsp_we, cdc_f;
        wire [NCL*32-1:0]    x_req_addr, x_req_wstrb;
        wire [NCL*256-1:0]   x_req_wdata, x_rsp_data;
        wire [NCL*16-1:0]    x_req_tag, x_rsp_tag;
        // Original producer side of the actual LSU/bulk interfaces.
        wire [NCL-1:0] a_req_v,a_req_rdy,a_req_we,a_rsp_v,a_rsp_rdy,a_rsp_we;
        wire [NCL*32-1:0] a_req_addr,a_req_wstrb;
        wire [NCL*256-1:0] a_req_wdata,a_rsp_data;
        wire [NCL*16-1:0] a_req_tag,a_rsp_tag;
        wire su_req_v,su_req_rdy,su_rsp_v,su_rsp_rdy;
        wire [336:0] su_request;
        wire [272:0] su_response;
        wire [NCL-1:0] obs_req,obs_rsp,obs_req_we,obs_rsp_we;
        wire [NCL*16-1:0] obs_req_tag,obs_rsp_tag;
        wire [2:0] p_req_v,p_req_rdy,p_req_we,p_rsp_v,p_rsp_rdy,p_rsp_we;
        wire [95:0] p_req_addr,p_req_wstrb;wire [767:0] p_req_wdata,p_rsp_data;
        wire [47:0] p_req_tag,p_rsp_tag;
        wire w2_sink_req_v,w2_sink_req_r,w2_sink_rsp_v,w2_sink_rsp_r,w2_sink_retained,w2_sink_fault,w2_sink_retire_r;
        wire [336:0] w2_sink_req;wire [272:0] w2_provider_rsp;
        wire w2_sink_route=W2_RESULT_ENABLE&&w2_sink_req_v&&w2_assembly_drained[d];
        wire w2_native_permit=!W2_RESULT_ENABLE||(w2_source_permit[d]&&!w2_native_done[d]);
        assign p_req_v={w2_sink_route||(w2_req_v[d]&&w2_native_permit),su_req_v,a_req_v[0]};
        assign {p_req_we[2],p_req_addr[95:64],p_req_wdata[767:512],p_req_wstrb[95:64],p_req_tag[47:32]}=
         w2_sink_route?w2_sink_req:w2_req[d*337+:337];
        assign {p_req_we[1],p_req_addr[63:32],p_req_wdata[511:256],p_req_wstrb[63:32],p_req_tag[31:16]}=su_request;
        assign {p_req_we[0],p_req_addr[31:0],p_req_wdata[255:0],p_req_wstrb[31:0],p_req_tag[15:0]}=
               {a_req_we[0],a_req_addr[31:0],a_req_wdata[255:0],a_req_wstrb[31:0],a_req_tag[15:0]};
        assign w2_req_r[d]=p_req_rdy[2]&&!w2_sink_route&&w2_native_permit;assign w2_sink_req_r=p_req_rdy[2]&&w2_sink_route;assign su_req_rdy=p_req_rdy[1];assign a_req_rdy[0]=p_req_rdy[0];
        assign w2_provider_rsp={p_rsp_tag[47:32],p_rsp_we[2],p_rsp_data[767:512]};
        // Assembly drains before a result write starts; the sink retains the
        // same single CAP1 route through write ACK and readback consumption.
        wire sink_response=W2_RESULT_ENABLE&&w2_assembly_drained[d]&&w2_sink_retained;
        assign w2_sink_rsp_v=p_rsp_v[2]&&sink_response;
        assign w2_rsp_v[d]=p_rsp_v[2]&&!sink_response;assign w2_rsp[d*273+:273]=w2_provider_rsp;
        assign su_rsp_v=p_rsp_v[1];assign su_response={p_rsp_tag[31:16],p_rsp_we[1],p_rsp_data[511:256]};
        assign a_rsp_v[0]=p_rsp_v[0]&&response_authorized[0];
        assign a_rsp_tag[15:0]=p_rsp_tag[15:0];assign a_rsp_we[0]=p_rsp_we[0];assign a_rsp_data[255:0]=p_rsp_data[255:0];
        assign p_rsp_rdy={sink_response?w2_sink_rsp_r:w2_rsp_r[d],su_rsp_rdy,a_rsp_rdy[0]&&response_authorized[0]};
        assign return_offer[0]=p_rsp_v[0];
        assign obs_req[0]=a_req_v[0]&&a_req_rdy[0];assign obs_rsp[0]=a_rsp_v[0]&&a_rsp_rdy[0];
        assign obs_req_tag[15:0]=a_req_tag[15:0];assign obs_req_we[0]=a_req_we[0];
        assign obs_rsp_tag[15:0]=p_rsp_tag[15:0];assign obs_rsp_we[0]=p_rsp_we[0];
        assign w2_lease_granted[d]=peer_grants[1];
        assign w2_release_r[d]=peer_releases[1]&&(!W2_RESULT_ENABLE||w2_sink_retire_r);
        ot_hbm_integrated_w2_result_sink #(.ENABLE(W2_RESULT_ENABLE)) u_w2_sink(
         .clk(clk_sm),.por_n(rst_sm_n),.owned(peer_grants[1]),.installed(w2_output_installed[d]),
         .reserve_v(w2_reserve_v[d]),.reserve_r(w2_reserve_r[d]),.pair_op(w2_pair_op[d]),
         .rows_a(w2_rows_a[d*2+:2]),.rows_b(w2_rows_b[d*2+:2]),
         .op_a(w2_op_a[d*32+:32]),.op_b(w2_op_b[d*32+:32]),
         .base_a(w2_output_base_a[d*32+:32]),.limit_a(w2_output_limit_a[d*32+:32]),
         .base_b(w2_output_base_b[d*32+:32]),.limit_b(w2_output_limit_b[d*32+:32]),
         .provider_tag(w2_output_tag[d*16+:16]),.frame(w2_lease_frame[d*73+:73]),
         .source_permit(w2_source_permit[d]),.retained(w2_sink_retained),.done(w2_output_done[d]),.quiet(),.fault(w2_sink_fault),
         .result_v(w2_result_v[d]),.result_op(w2_result_op[d*32+:32]),.result_row(w2_result_row[d*12+:12]),
         .result_data(w2_result_data[d*256+:256]),.native_done(w2_native_done[d]),
         .retire_v(w2_release_v[d]&&peer_releases[1]),.retire_r(w2_sink_retire_r),
         .req_v(w2_sink_req_v),.req_r(w2_sink_req_r&&w2_assembly_drained[d]),.req(w2_sink_req),
         .rsp_v(w2_sink_rsp_v),.rsp_r(w2_sink_rsp_r),.rsp(w2_provider_rsp));
        assign su_owned=peer_grants[0];assign su_release_r=peer_releases[0];
        ot_hbm_integrated_su_cp_bind #(.ENABLE(SU_ENABLE),.REGISTERED_OUTPUTS(SU_REGISTERED_OUTPUTS),.REGISTERED_STATUS(SU_REGISTERED_STATUS)) u_su_cp(
         .clk(clk_sm),.por_n(rst_sm_n),.launch_v(launch_v),.launch_pc(launch_pc),
         .cp_job(cpl_job),.cp_gen(cpl_generation),.launch_token(launch_token),.launch_pos(launch_pos),
         .native_launch(native_launch),.lease_v(su_lease_v),.lease_granted(su_owned),
         .release_v(su_release_v),.release_r(su_release_r),.exec_done(su_exec_done),.exec_fault(su_exec_fault),
         .retired_original_ops(su_retired),.shared_fault(shared_fault),.owned(),.pending(su_pending),
         .quiet(su_quiet),.selected(su_selected),.done(su_done),.fault(su_fault),
         .selected_pc(su_pc),.held_job(su_job),.held_gen(su_gen),.held_token(su_token),.held_pos(su_pos));
        wire [648:0] shared_gather_req,fmt_req,store_req;
        wire [636:0] shared_gather_rsp;
        wire shared_gather_req_v,shared_gather_req_r,shared_gather_rsp_v,shared_gather_rsp_r;
        wire fmt_req_v,fmt_req_r,fmt_rsp_r,fmt_retained,fmt_fault,bridge_release_r;
        wire store_req_v,store_req_r,store_rsp_r,store_fault;
        wire [VM_AW-1:0] store_vm_raddr;
        assign normal_vm_raddr[d*32+:32]=32'(store_vm_raddr);
        wire [31:0] bound_arena_base,bound_arena_limit;
        // Normal producer and formatter consume their own real tagged response.
        wire formatter_response=FORMATTER_ENABLE&&shared_gather_rsp[3:1]==3'd3;
        wire store_response=NORMAL_GATHER_ENABLE&&(shared_gather_rsp[3:1]==3'd1||shared_gather_rsp[3:1]==3'd2);
        assign shared_gather_req_v=fmt_req_v||store_req_v||gather_req_v[d];
        assign shared_gather_req=fmt_req_v?fmt_req:store_req_v?store_req:gather_req[d*649+:649];
        assign fmt_req_r=shared_gather_req_r&&fmt_req_v;
        assign store_req_r=shared_gather_req_r&&!fmt_req_v&&store_req_v;
        assign gather_req_r[d]=shared_gather_req_r&&!fmt_req_v&&!store_req_v;
        assign gather_rsp_v[d]=shared_gather_rsp_v&&!formatter_response&&!store_response;
        assign gather_rsp[d*637+:637]=shared_gather_rsp;
        assign shared_gather_rsp_r=formatter_response?fmt_rsp_r:store_response?store_rsp_r:gather_rsp_r[d];
        assign gather_release_r[d]=bridge_release_r&&!fmt_retained;
        ot_hbm_integrated_w15_store #(.ENABLE(NORMAL_GATHER_ENABLE),.VM_AW(VM_AW)) u_normal_store(
         .clk(clk_sm),.por_n(rst_sm_n),.go(normal_go[d]),.id_plane(normal_id_plane[d]),
         .command_tag(normal_command_tag[d*16+:16]),.source_word(normal_source_word[d*32+:32]),
         .arena_base(bound_arena_base),.arena_limit(bound_arena_limit),
         .job(cpl_job),.gen(cpl_generation),.token(launch_token),.pos(launch_pos),.gather_retained(gather_retained[d]),
         .busy(normal_busy[d]),.done(normal_done[d]),.fault(store_fault),
         .vm_re(normal_vm_re[d]),.vm_raddr(store_vm_raddr),.vm_rq(normal_vm_rq[d*512+:512]),
         .e_valid(normal_e_valid[d]),.e_ready(normal_e_ready[d]),.e_data(normal_e_data[d*512+:512]),
         .e_last(normal_e_last[d]),.e_mode(normal_e_mode[d]),.e_tag(normal_e_tag[d*16+:16]),
         .o_valid(normal_o_valid[d]),.o_ready(normal_o_ready[d]),.o_data(normal_o_data[d*512+:512]),
         .o_last(normal_o_last[d]),.o_rank(normal_o_rank[d*7+:7]),.o_err(normal_o_err[d]),.engine_fault(normal_engine_fault[d]),
         .bridge_req_v(store_req_v),.bridge_req_r(store_req_r),.bridge_req(store_req),
         .bridge_rsp_v(shared_gather_rsp_v&&store_response),.bridge_rsp_r(store_rsp_r),.bridge_rsp(shared_gather_rsp));
        ot_hbm_integrated_formatter_provider #(.ENABLE(FORMATTER_ENABLE),.VM_AW(VM_AW)) u_formatter_provider(
         .clk(clk_sm),.por_n(rst_sm_n),.start(formatter_start_v[d]),.start_ready(formatter_start_r[d]),
         .job(cpl_job),.gen(cpl_generation),.token(launch_token),.pos(launch_pos),
         .arena_base(bound_arena_base),.arena_limit(bound_arena_limit),
         .gather_retained(gather_retained[d]),.arena_visible(gather_arena_visible[d]),
         .pair_v(index_pair_v[d]),.pair_r(index_pair_r[d]),
         .pair_job(index_pair[d*85+53+:32]),.pair_gen(index_pair[d*85+49+:4]),.pair_pos(index_pair[d*85+29+:20]),
         .pair_rank(index_pair[d*85+22+:7]),.pair_word(index_pair[d*85+16+:6]),.pair_tag(index_pair[d*85+:16]),
         .pairs_v(index_pairs_v[d]),.pairs_r(index_pairs_r[d]),.pairs(index_pairs[d*599+2+:512]),
         .pairs_job(index_pairs[d*599+567+:32]),.pairs_gen(index_pairs[d*599+563+:4]),.pairs_pos(index_pairs[d*599+543+:20]),
         .pairs_rank(index_pairs[d*599+536+:7]),.pairs_word(index_pairs[d*599+530+:6]),.pairs_tag(index_pairs[d*599+514+:16]),
         .pairs_checked(index_pairs[d*599+1]),.pairs_uncorrectable(index_pairs[d*599]),.retained(fmt_retained),.fault(fmt_fault),
         .bridge_req_v(fmt_req_v),.bridge_req_r(fmt_req_r),.bridge_req(fmt_req),
         .bridge_rsp_v(shared_gather_rsp_v&&formatter_response),.bridge_rsp_r(fmt_rsp_r),.bridge_rsp(shared_gather_rsp),
         .release_v(formatter_release_v[d]),.release_r(formatter_release_r[d]),
         .release_job(gather_release_frame[d*73+:32]),.release_gen(gather_release_frame[d*73+32+:4]),
         .release_pos(gather_release_frame[d*73+53+:20]),
         .publication_done(gather_result_published[d]),.source_reverse_done(gather_reverse_done[d]));
        ot_hbm_integrated_gather_owner #(.ENABLE(1),.VM_AW(VM_AW)) u_shared(
         .clk(clk_sm),.por_n(rst_sm_n),
         .desc_v(gather_desc_v[d]),.desc_r(gather_desc_r[d]),.desc_index(gather_desc_index[d*3+:3]),.desc_data(gather_desc_data[d*64+:64]),
         .start_v(gather_start_v[d]),.start_r(gather_start_r[d]),.installed_book_valid(gather_book_valid[d]),
         .job(cpl_job),.gen(cpl_generation),.token(launch_token),.pos(launch_pos),
         .retained(gather_retained[d]),.arena_visible(gather_arena_visible[d]),.sink_visible(gather_sink_visible[d]),.fault(shared_fault),
         .bound_arena_base(bound_arena_base),.bound_arena_limit(bound_arena_limit),
         .req_v(shared_gather_req_v),.req_r(shared_gather_req_r),
         .req_kind(shared_gather_req[0+:3]),.req_addr(shared_gather_req[3+:32]),.req_tag(shared_gather_req[35+:16]),
         .req_rank(shared_gather_req[51+:7]),.req_word(shared_gather_req[58+:6]),.req_data(shared_gather_req[64+:512]),
         .req_job(shared_gather_req[576+:32]),.req_gen(shared_gather_req[608+:4]),
         .req_token(shared_gather_req[612+:17]),.req_pos(shared_gather_req[629+:20]),
         .rsp_v(shared_gather_rsp_v),.rsp_r(shared_gather_rsp_r),
         .rsp_checked(shared_gather_rsp[0]),.rsp_kind(shared_gather_rsp[1+:3]),.rsp_tag(shared_gather_rsp[4+:16]),
         .rsp_addr(shared_gather_rsp[20+:32]),.rsp_data(shared_gather_rsp[52+:512]),
         .held_job(shared_gather_rsp[564+:32]),.held_gen(shared_gather_rsp[596+:4]),
         .held_token(shared_gather_rsp[600+:17]),.held_pos(shared_gather_rsp[617+:20]),
         .release_v(gather_release_v[d]&&!fmt_retained),.release_r(bridge_release_r),
         .release_job(gather_release_frame[d*73+:32]),.release_gen(gather_release_frame[d*73+32+:4]),
         .release_token(gather_release_frame[d*73+36+:17]),.release_pos(gather_release_frame[d*73+53+:20]),
         .result_published(gather_result_published[d]),.source_reverse_done(gather_reverse_done[d]),
         .native_clients_drained(all_prior_quiet),.cdc_drained(native_credit_empty),.provider_fault(w2_sink_fault|(|cdc_f)|mem_fault|fmt_fault|store_fault),
         .observe_req(obs_req),.observe_rsp(obs_rsp),.observe_req_we(obs_req_we),.observe_rsp_we(obs_rsp_we),
         .observe_req_tag(obs_req_tag),.observe_rsp_tag(obs_rsp_tag),.return_offer(return_offer),.response_authorized(response_authorized),
         .native_job(cpl_job),.native_gen(cpl_generation),.native_token(launch_token),.native_pos(launch_pos),
         .native_credit_empty(native_credit_empty),.shared_idle(shared_idle),
         .peer_lease_v({w2_lease_v[d],su_lease_v}),.peer_quiet({w2_quiet[d]&&!w2_sink_retained,su_quiet}),
         .peer_release_v({w2_release_v[d]&&(!W2_RESULT_ENABLE||w2_sink_retire_r),su_release_v}),.peer_release_r(peer_releases),.peer_lease_granted(peer_grants),
         .peer_lease_job({w2_lease_frame[d*73+:32],su_job}),.peer_lease_gen({w2_lease_frame[d*73+32+:4],su_gen}),
         .peer_lease_token({w2_lease_frame[d*73+36+:17],su_token}),.peer_lease_pos({w2_lease_frame[d*73+53+:20],su_pos}),
         .peer_release_job({w2_release_frame[d*73+:32],su_job}),.peer_release_gen({w2_release_frame[d*73+32+:4],su_gen}),
         .peer_release_token({w2_release_frame[d*73+36+:17],su_token}),.peer_release_pos({w2_release_frame[d*73+53+:20],su_pos}),
         .p_req_v(p_req_v),.p_req_rdy(p_req_rdy),.p_req_we(p_req_we),.p_req_addr(p_req_addr),.p_req_wdata(p_req_wdata),
         .p_req_wstrb(p_req_wstrb),.p_req_tag(p_req_tag),.p_rsp_v(p_rsp_v),.p_rsp_rdy(p_rsp_rdy),
         .p_rsp_we(p_rsp_we),.p_rsp_tag(p_rsp_tag),.p_rsp_data(p_rsp_data),
         .m_req_v(c_req_v[0]),.m_req_rdy(c_req_rdy[0]),.m_req_we(c_req_we[0]),.m_req_addr(c_req_addr[31:0]),
         .m_req_wdata(c_req_wdata[255:0]),.m_req_wstrb(c_req_wstrb[31:0]),.m_req_tag(c_req_tag[15:0]),
         .m_rsp_v(c_rsp_v[0]),.m_rsp_rdy(c_rsp_rdy[0]),.m_rsp_we(c_rsp_we[0]),.m_rsp_tag(c_rsp_tag[15:0]),.m_rsp_data(c_rsp_data[255:0]));
        ot_hbm_accel_su_parent_exec #(.ENABLE(SU_ENABLE),.IMW(IMW)) u_su_exec(
         .clk(clk_sm),.rst_n(rst_sm_n),.owned(su_owned),.config_idle(db_rdy[d]&&!su_selected&&!gather_retained[d]&&!fmt_retained&&w2_quiet[d]),
         .loader_we(SU_ENABLE && im_we[d*NSM] && im_addr[IMW-1]),.loader_addr(im_addr),.loader_data(im_data),
         .selected_pc(su_pc),.job_id(su_job),.req_v(su_req_v),.req_rdy(su_req_rdy),.req(su_request),
         .rsp_v(su_rsp_v),.rsp_rdy(su_rsp_rdy),.rsp(su_response),.done(su_exec_done),.fault(su_exec_fault),
         .virtual_edges(),.read_requests(),.write_requests(),.publication_requests(),.retired_original_ops(su_retired));
        genvar u;
        for(u=1;u<NCL;u=u+1) begin:g_prior
         assign c_req_v[u]=a_req_v[u];assign a_req_rdy[u]=c_req_rdy[u];
         assign c_req_we[u]=a_req_we[u];assign c_req_addr[u*32+:32]=a_req_addr[u*32+:32];
         assign c_req_wdata[u*256+:256]=a_req_wdata[u*256+:256];
         assign c_req_wstrb[u*32+:32]=a_req_wstrb[u*32+:32];assign c_req_tag[u*16+:16]=a_req_tag[u*16+:16];
         assign a_rsp_v[u]=c_rsp_v[u]&&response_authorized[u];assign c_rsp_rdy[u]=a_rsp_rdy[u]&&response_authorized[u];
         assign return_offer[u]=c_rsp_v[u];
         assign a_rsp_we[u]=c_rsp_we[u];assign a_rsp_tag[u*16+:16]=c_rsp_tag[u*16+:16];
         assign a_rsp_data[u*256+:256]=c_rsp_data[u*256+:256];
         assign obs_req[u]=a_req_v[u] && a_req_rdy[u];assign obs_rsp[u]=a_rsp_v[u] && a_rsp_rdy[u];
         assign obs_req_tag[u*16+:16]=a_req_tag[u*16+:16];assign obs_rsp_tag[u*16+:16]=a_rsp_tag[u*16+:16];
         assign obs_req_we[u]=a_req_we[u];assign obs_rsp_we[u]=a_rsp_we[u];
        end
        // collective ports of the SMs
        wire [NSM-1:0] cs_req_v, cs_req_rdy, cs_mode, cs_rsp_v, cs_rsp_rdy;
        wire [NSM*8-1:0] cs_count;
        wire [NSM*NL*32-1:0] cs_data;
        wire [NL*32-1:0] cs_rsp_data;
        for (s = 0; s < NSM; s = s + 1) begin : g_sm
            wire [31:0] st_instr, st_cycles, st_stall_mem, st_tc_rows;
            wire [31:0] rd;
            assign res_data[s*32 +: 32] = rd;
            ot_ds_hbm_simt_sm20 #(.TW(TW),.PW(PW), .ENABLE(1), .NL(NL), .IMW(IMW), .HAS_DIV(HAS_DIV), .HAS_BD(HAS_BD)) u_sm (
                .clk(clk_sm), .rst_n(rst_sm_n), .sm_id(s[7:0]), .die_id(d[7:0]),
                .im_we(im_we[d*NSM + s] && !(SU_ENABLE && s==0 && im_addr[IMW-1])), .im_addr(im_addr), .im_data(im_data),
                .launch_v(native_launch[s]), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
                .sm_done(native_done[s]), .sm_fault(native_fault[s]), .res_v(res_v[s]), .res_data(rd), .busy(busy[s]),
                .bar_arrive(bar_arr[s]), .bar_release(bar_rel[s]),
                .lreq_v(a_req_v[2*s]), .lreq_rdy(a_req_rdy[2*s]), .lreq_we(a_req_we[2*s]),
                .lreq_addr(a_req_addr[2*s*32 +: 32]), .lreq_wdata(a_req_wdata[2*s*256 +: 256]),
                .lreq_wstrb(a_req_wstrb[2*s*32 +: 32]), .lreq_tag(a_req_tag[2*s*16 +: 16]),
                .lrsp_v(a_rsp_v[2*s]), .lrsp_rdy(a_rsp_rdy[2*s]), .lrsp_tag(a_rsp_tag[2*s*16 +: 16]),
                .lrsp_we(a_rsp_we[2*s]), .lrsp_data(a_rsp_data[2*s*256 +: 256]),
                .treq_v(a_req_v[2*s+1]), .treq_rdy(a_req_rdy[2*s+1]), .treq_addr(a_req_addr[(2*s+1)*32 +: 32]),
                .treq_tag(a_req_tag[(2*s+1)*16 +: 16]), .trsp_v(a_rsp_v[2*s+1]), .trsp_rdy(a_rsp_rdy[2*s+1]),
                .trsp_tag(a_rsp_tag[(2*s+1)*16 +: 16]), .trsp_data(a_rsp_data[(2*s+1)*256 +: 256]),
                .coll_req_v(cs_req_v[s]), .coll_req_rdy(cs_req_rdy[s]), .coll_mode(cs_mode[s]),
                .coll_count(cs_count[s*8 +: 8]), .coll_data(cs_data[s*NL*32 +: NL*32]), .coll_rsp_v(cs_rsp_v[s]),
                .coll_rsp_rdy(cs_rsp_rdy[s]), .coll_rsp_data(cs_rsp_data),
                .st_instr(st_instr), .st_cycles(st_cycles), .st_stall_mem(st_stall_mem), .st_tc_rows(st_tc_rows));
            // the bulk-copy port only reads
            assign a_req_we[2*s+1] = 1'b0;
            assign a_req_wdata[(2*s+1)*256 +: 256] = 256'd0;
            assign a_req_wstrb[(2*s+1)*32 +: 32] = 32'd0;
        end
        genvar c;
        for (c = 0; c < NCL; c = c + 1) begin : g_cdc
            ot_gpu_mreq_cdc #(.ENABLE(1), .AW(3)) u_x (
                .clk_s(clk_sm), .rst_s_n(rst_sm_n), .clk_m(clk_mem), .rst_m_n(rst_mem_n),
                .s_req_v(c_req_v[c]), .s_req_rdy(c_req_rdy[c]), .s_req_we(c_req_we[c]), .s_req_addr(c_req_addr[c*32 +: 32]),
                .s_req_wdata(c_req_wdata[c*256 +: 256]), .s_req_wstrb(c_req_wstrb[c*32 +: 32]), .s_req_tag(c_req_tag[c*16 +: 16]),
                .s_rsp_v(c_rsp_v[c]), .s_rsp_rdy(c_rsp_rdy[c]), .s_rsp_tag(c_rsp_tag[c*16 +: 16]), .s_rsp_we(c_rsp_we[c]),
                .s_rsp_data(c_rsp_data[c*256 +: 256]),
                .m_req_v(x_req_v[c]), .m_req_rdy(x_req_rdy[c]), .m_req_we(x_req_we[c]), .m_req_addr(x_req_addr[c*32 +: 32]),
                .m_req_wdata(x_req_wdata[c*256 +: 256]), .m_req_wstrb(x_req_wstrb[c*32 +: 32]), .m_req_tag(x_req_tag[c*16 +: 16]),
                .m_rsp_v(x_rsp_v[c]), .m_rsp_rdy(x_rsp_rdy[c]), .m_rsp_tag(x_rsp_tag[c*16 +: 16]), .m_rsp_we(x_rsp_we[c]),
                .m_rsp_data(x_rsp_data[c*256 +: 256]), .fault(cdc_f[c]));
        end
        wire mem_fault;
        ot_gpu_memsys_adapter #(.ENABLE(1), .NC(NCL), .NS(NS), .NPC(NPC), .MEM_WORDS(MEM_WORDS), .DIE(d), .USE_W2(USE_W2)) u_mem (
            .clk(clk_mem), .rst_n(rst_mem_n),
            .c_req_v(x_req_v), .c_req_rdy(x_req_rdy), .c_req_we(x_req_we), .c_req_addr(x_req_addr),
            .c_req_wdata(x_req_wdata), .c_req_wstrb(x_req_wstrb), .c_req_tag(x_req_tag),
            .c_rsp_v(x_rsp_v), .c_rsp_rdy(x_rsp_rdy), .c_rsp_tag(x_rsp_tag), .c_rsp_we(x_rsp_we), .c_rsp_data(x_rsp_data),
            .fault(mem_fault));
        ot_gpu_coll_mux #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_cmux (
            .clk(clk_sm), .rst_n(rst_sm_n), .s_req_v(cs_req_v), .s_req_rdy(cs_req_rdy), .s_mode(cs_mode),
            .s_count(cs_count), .s_data(cs_data), .s_rsp_v(cs_rsp_v), .s_rsp_rdy(cs_rsp_rdy), .s_rsp_data(cs_rsp_data),
            .m_req_v(ep_req_v[d]), .m_req_rdy(ep_req_rdy[d]), .m_mode(ep_mode[d]), .m_count(ep_count[d*8 +: 8]),
            .m_data(ep_data[d*NL*32 +: NL*32]), .m_rsp_v(ep_rsp_v[d]), .m_rsp_rdy(ep_rsp_rdy[d]),
            .m_rsp_data(ep_rsp_data[d*NL*32 +: NL*32]));
        assign die_fault[d] = (|sm_fault) | (|cdc_f) | mem_fault | shared_fault;
    end
    assign sys_fault = (|die_fault) | coll_fault;
end endgenerate
endmodule
