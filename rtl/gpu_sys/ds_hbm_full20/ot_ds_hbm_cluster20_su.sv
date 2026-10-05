`timescale 1ns/1ps
// Additive opt-in successor: original sources remain byte-identical.
// Priced by e72bb27c1 hbm_su_finite_native_parent_model; physical unqualified.
// Existing LAUNCH PC bank and SM0 IM64 loader, unchanged doorbell/CPL authority.
// Source-selected DS cluster with real SM/memory/collective ports exposed on
// clk_sm for the DSpark sequencer. Host16/rings are intentionally not in this
// path. Token17 reaches UR0 and actual RESULT17; no truncation or synthetic ACK.
module ot_ds_hbm_cluster20_su #(
 parameter integer SU_ENABLE=0,
 parameter integer ENABLE=0, TW=17, PW=20, CONTEXT_POSITIONS=1048576, ND=2, NSM=2, NL=128, IMW=14,
 parameter integer CB=8, NS=2, NPC=2, MEM_WORDS=2097152,
 parameter integer SW_PIPE=8, USE_W2=0, HAS_DIV=1, HAS_BD=1
)(
 input wire por_n, clk_host, clk_sm, clk_mem, clk_link,
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
 output wire rst_sm_n, output wire sys_fault
);
initial if(SU_ENABLE && (NSM!=2 || IMW!=14 || NS!=2 || NPC!=2 || USE_W2!=0))
 $fatal(1,"priced installed SU parent requires NSM2/IMW14/NS2/NPC2/defaultW2");
generate if(SU_ENABLE==0) begin:g_original
 ot_ds_hbm_cluster20 #(.ENABLE(ENABLE),.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),
  .ND(ND),.NSM(NSM),.NL(NL),.IMW(IMW),.CB(CB),.NS(NS),.NPC(NPC),.MEM_WORDS(MEM_WORDS),
  .SW_PIPE(SW_PIPE),.USE_W2(USE_W2),.HAS_DIV(HAS_DIV),.HAS_BD(HAS_BD)) u_original(
  .por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
  .cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),.db_v(db_v),.db_rdy(db_rdy),
  .db_token(db_token),.db_pos(db_pos),.db_job(db_job),.db_generation(db_generation),
  .cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_data(cpl_data),.im_we(im_we),.im_addr(im_addr),.im_data(im_data),
  .rst_sm_n(rst_sm_n),.sys_fault(sys_fault));
end else if(ENABLE==0) begin:g_off
 assign db_rdy=0; assign cpl_v=0; assign cpl_data=0;
 assign rst_sm_n=0; assign sys_fault=0;
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
        wire [NSM-1:0] native_launch=SU_ENABLE && launch_pc[31]?{NSM{1'b0}}:launch_v;
        assign sm_done=native_done | {{(NSM-1){1'b0}},su_done};
        assign sm_fault=native_fault | {NSM{su_fault|su_exec_fault}};
        wire [31:0] launch_pc;
        wire [TW-1:0] launch_token; wire [PW-1:0] launch_pos;
        wire [NSM*32-1:0] res_data;
        wire [TW-1:0] cpl_token; wire [PW-1:0] cpl_position; wire [31:0] cpl_job; wire [3:0] cpl_generation; wire [3:0] cpl_status; wire [31:0] cpl_cycles, st_kernels, st_busy;
        ot_ds_hbm_cmdproc20 #(.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS), .ENABLE(1), .NSM(NSM), .NCMD(1 << CB)) u_cp (
            .clk(clk_sm), .rst_n(rst_sm_n), .cmd_we(cmd_we[d]), .cmd_addr(cmd_addr[d*CB +: CB]), .cmd_wdata(cmd_wdata[d*64 +: 64]),
            .db_v(db_v[d]), .db_rdy(db_rdy[d]), .db_token(db_token[d*TW +: TW]), .db_pos(db_pos[d*PW +: PW]),
            .db_job(db_job[d*32+:32]),.db_generation(db_generation[d*4+:4]),
            .cpl_position(cpl_position),.cpl_job(cpl_job),.cpl_generation(cpl_generation),
            .launch_v(launch_v), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
            .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data),
            .cpl_v(cpl_v[d]), .cpl_rdy(cpl_rdy[d]), .cpl_token(cpl_token), .cpl_status(cpl_status),
            .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy));
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
        wire [336:0] su_request,route_request;
        wire [272:0] su_response;
        wire [NCL-1:0] obs_req,obs_rsp,obs_req_we,obs_rsp_we;
        wire [NCL*16-1:0] obs_req_tag,obs_rsp_tag;
        assign obs_req[0]=su_owned?(su_req_v && su_req_rdy):(a_req_v[0] && a_req_rdy[0]);
        assign obs_rsp[0]=su_owned?(su_rsp_v && su_rsp_rdy):(a_rsp_v[0] && a_rsp_rdy[0]);
        assign obs_req_tag[15:0]=su_owned?su_request[15:0]:a_req_tag[15:0];
        assign obs_req_we[0]=su_owned?su_request[336]:a_req_we[0];
        assign obs_rsp_tag[15:0]=su_owned?su_response[272:257]:a_rsp_tag[15:0];
        assign obs_rsp_we[0]=su_owned?su_response[256]:a_rsp_we[0];
        ot_hbm_accel_su_parent_borrow #(.ENABLE(1),.NSM(NSM)) u_su_owner(
         .clk(clk_sm),.rst_n(rst_sm_n),.launch_v(launch_v),.launch_pc(launch_pc),.sm_busy(busy),
         .su_done(su_exec_done),.su_fault(su_exec_fault),.pending(su_pending),.owned(su_owned),
         .done(su_done),.fault(su_fault),.selected_pc(su_pc),
         .observe_req(obs_req),.observe_rsp(obs_rsp),.observe_req_tag(obs_req_tag),.observe_rsp_tag(obs_rsp_tag),
         .observe_req_we(obs_req_we),.observe_rsp_we(obs_rsp_we),
         .sm_req_v(a_req_v[0]),.sm_req_rdy(a_req_rdy[0]),
         .sm_req({a_req_we[0],a_req_addr[31:0],a_req_wdata[255:0],a_req_wstrb[31:0],a_req_tag[15:0]}),
         .sm_rsp_v(a_rsp_v[0]),.sm_rsp_rdy(a_rsp_rdy[0]),
         .sm_rsp({a_rsp_tag[15:0],a_rsp_we[0],a_rsp_data[255:0]}),
         .su_req_v(su_req_v),.su_req_rdy(su_req_rdy),.su_req(su_request),
         .su_rsp_v(su_rsp_v),.su_rsp_rdy(su_rsp_rdy),.su_rsp(su_response),
         .req_v(c_req_v[0]),.req_rdy(c_req_rdy[0]),.req(route_request),
         .rsp_v(c_rsp_v[0]),.rsp_rdy(c_rsp_rdy[0]),.rsp({c_rsp_tag[15:0],c_rsp_we[0],c_rsp_data[255:0]}));
        assign {c_req_we[0],c_req_addr[31:0],c_req_wdata[255:0],c_req_wstrb[31:0],c_req_tag[15:0]}=route_request;
        // Existing CP holds this real accepted job/generation/token/position until CPL.
        // The only completion to CP is the owner after physical provider drain.
        ot_hbm_accel_su_parent_exec #(.ENABLE(SU_ENABLE),.IMW(IMW)) u_su_exec(
         .clk(clk_sm),.rst_n(rst_sm_n),.owned(su_owned),.config_idle(db_rdy[d]),
         .loader_we(SU_ENABLE && im_we[d*NSM] && im_addr[IMW-1]),.loader_addr(im_addr),.loader_data(im_data),
         .selected_pc(su_pc),.job_id(cpl_job),.req_v(su_req_v),.req_rdy(su_req_rdy),.req(su_request),
         .rsp_v(su_rsp_v),.rsp_rdy(su_rsp_rdy),.rsp(su_response),.done(su_exec_done),.fault(su_exec_fault),
         .virtual_edges(),.read_requests(),.write_requests(),.publication_requests(),.retired_original_ops());
        genvar u;
        for(u=1;u<NCL;u=u+1) begin:g_prior
         assign c_req_v[u]=a_req_v[u];assign a_req_rdy[u]=c_req_rdy[u];
         assign c_req_we[u]=a_req_we[u];assign c_req_addr[u*32+:32]=a_req_addr[u*32+:32];
         assign c_req_wdata[u*256+:256]=a_req_wdata[u*256+:256];
         assign c_req_wstrb[u*32+:32]=a_req_wstrb[u*32+:32];assign c_req_tag[u*16+:16]=a_req_tag[u*16+:16];
         assign a_rsp_v[u]=c_rsp_v[u];assign c_rsp_rdy[u]=a_rsp_rdy[u];
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
        assign die_fault[d] = (|sm_fault) | (|cdc_f) | mem_fault;
    end
    assign sys_fault = (|die_fault) | coll_fault;
end endgenerate
endmodule
