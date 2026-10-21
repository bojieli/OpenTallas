`timescale 1ns/1ps
// Explicit opt-in STATUS kind15 extension. Legacy codec modules and DATA[155:0] are unchanged.
// DATA[511:304] = {v1, ctx_seen,ctx_user2,ctx_tag59,res_seen,res_user2,res_dh44,
//                 native_seen,overflow,count32,last_optag59,2'b0}; DATA[303:156] stays zero.
(* keep_hierarchy = "yes" *)
module ot_qwen_status_obs_v1_valid(input wire [207:0] x, output wire good);
    wire ctx_bad = x[203] ? (x[202:201] == 0 || x[202:201] != x[186:185]) : |x[202:142];
    wire res_bad = x[141] ? !x[137] : |x[140:95];
    wire nat_bad = x[94] ? (x[92:61] == 0 || (x[93] && x[92:61] != 32'hffffffff)) : |x[93:2];
    assign good = x[207:204] == 4'd1 && x[1:0] == 0 && !ctx_bad && !res_bad && !nat_bad;
endmodule

(* keep_hierarchy = "yes" *)
module ot_qwen_status_obs_full32(input wire [15:0] lo,hi, output wire full);
    assign full = (&lo) && (&hi);
endmodule

module ot_qwen_status_obs_v1_state(
    input wire ck, input wire [2:0] rst_n, input wire [15:0] epoch16,
    input wire [61:0] obs_ctx, input wire [46:0] obs_res, input wire [59:0] obs_native,
    output wire [207:0] snapshot, output wire fault
);
    // Cold reset only. Link epoch_begin does not clear a count in the same STATUS receipt epoch.
    (* keep = "true", dont_touch = "true" *) reg [15:0] ep_lo,ep_hi,ep_id;
    reg [15:0] count_lo,count_hi;
    (* keep = "true", dont_touch = "true" *) reg [3:0] ctx_seen,nat_seen;
    (* keep = "true", dont_touch = "true" *) reg [2:0] res_seen;
    reg overflow, bad_q;
    wire ch_lo=ep_lo!=epoch16, ch_hi=ep_hi!=epoch16, ch_id=ep_id!=epoch16;
    wire [15:0] base_lo=ch_lo?16'd0:count_lo, base_hi=ch_hi?16'd0:count_hi;
    wire full_lo,full_hi;
    ot_qwen_status_obs_full32 u_full_lo(.lo(base_lo),.hi(base_hi),.full(full_lo));
    ot_qwen_status_obs_full32 u_full_hi(.lo(base_lo),.hi(base_hi),.full(full_hi));
    wire [15:0] next_lo=(obs_native[59]&&full_lo)?16'hffff:base_lo+{15'd0,obs_native[59]};
    wire [15:0] next_hi=(obs_native[59]&&full_hi)?16'hffff:base_hi+{15'd0,(obs_native[59]&&(&base_lo))};
    wire overflow_now=(!ch_id&&overflow)||(obs_native[59]&&full_lo);
    always @(posedge ck or negedge rst_n[0])
        if(!rst_n[0]) begin ep_lo<=0;count_lo<=0;end
        else begin ep_lo<=epoch16;count_lo<=next_lo;end
    always @(posedge ck or negedge rst_n[1])
        if(!rst_n[1]) begin ep_hi<=0;count_hi<=0;end
        else begin ep_hi<=epoch16;count_hi<=next_hi;end
    wire input_bad=(obs_ctx[61]&&(obs_ctx[60:59]==0||obs_ctx[60:59]!=obs_ctx[44:43])) ||
                   (obs_res[46]&&!obs_res[42]);
    always @(posedge ck or negedge rst_n[2])
        if(!rst_n[2]) begin ep_id<=0;ctx_seen<=0;res_seen<=0;nat_seen<=0;overflow<=0;bad_q<=0;end
        else begin
            ep_id<=epoch16;
            ctx_seen<={4{obs_ctx[61]}} | (ch_id?4'd0:ctx_seen);
            res_seen<={3{obs_res[46]}} | (ch_id?3'd0:res_seen);
            nat_seen<={4{obs_native[59]}} | (ch_id?4'd0:nat_seen);
            overflow<=overflow_now;
            bad_q<=(ch_id?1'b0:bad_q)||input_bad||(ch_lo!=ch_hi)||(ch_hi!=ch_id)||overflow_now;
        end
    wire [3:0] ctx_v=ctx_seen&{4{!ch_id}} | {4{obs_ctx[61]}};
    wire [2:0] res_v=res_seen&{3{!ch_id}} | {3{obs_res[46]}};
    wire [3:0] nat_v=nat_seen&{4{!ch_id}} | {4{obs_native[59]}};
    wire [60:0] cx; wire [45:0] rr; wire [58:0] nn;
    genvar g;
    for(g=0;g<4;g=g+1) begin:g_ctx_mask
        localparam integer LO=16*g, W=(LO+16<=61)?16:61-LO;
        assign cx[LO+:W]=obs_ctx[LO+:W]&{W{ctx_v[g]}};
    end
    for(g=0;g<3;g=g+1) begin:g_res_mask
        localparam integer LO=16*g, W=(LO+16<=46)?16:46-LO;
        assign rr[LO+:W]=obs_res[LO+:W]&{W{res_v[g]}};
    end
    for(g=0;g<4;g=g+1) begin:g_native_mask
        localparam integer LO=16*g, W=(LO+16<=59)?16:59-LO;
        assign nn[LO+:W]=obs_native[LO+:W]&{W{nat_v[g]}};
    end
    // Include same-edge events in the actual STATUS capture, with true held operation identities.
    assign snapshot={4'd1,ctx_v[0],cx,res_v[0],rr,nat_v[0],overflow_now,next_hi,next_lo,nn,2'd0};
    assign fault=bad_q||input_bad||overflow_now;
endmodule

module ot_qwen_d2d_status_tx_s7_obs1 #(parameter integer SFMUT = 0) (
    input wire [2:0] obs_rst_n,
    input wire [61:0] obs_ctx, input wire [46:0] obs_res, input wire [59:0] obs_native,
    input  wire         ck,
    input  wire [5:0]   rst_h_k,        // held result: [0] pend + slices 0..3, [g] slices 4g..4g+3 (g 1..5)
    input  wire         rst_t,          // TX register (tx_valid, fault)
    input  wire [15:0]  epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire [21:0]  result_v_k,     // KEPT pin-flop copies of result_v
    input  wire         result_done, result_fault,
    input  wire [3:0]   result_cause,
    input  wire [58:0]  result_tag,
    input  wire [1:0]   result_gen,
    input  wire [17:0]  result_token,
    input  wire [31:0]  result_value, result_cycles,
    input  wire         status_event_valid, status_port_match, tx_slot_canonical,
    input  wire [3:0]   tx_kind,
    output wire          tx_valid,
    output wire  [547:0] tx_payload,
    output wire          fault
);
    wire [547:0] base_payload; wire base_fault; wire [207:0] obs_snapshot; reg [207:0] held_obs; wire obs_fault;
    ot_qwen_d2d_status_tx_s7 #(.SFMUT(SFMUT)) u_base (
        .ck(ck),
        .rst_h_k(rst_h_k),
        .rst_t(rst_t),
        .epoch16(epoch16),
        .vm_drained(vm_drained),
        .collective_drained(collective_drained),
        .collective_busy(collective_busy),
        .crom_fault(crom_fault),
        .execution_active(execution_active),
        .admit_ready(admit_ready),
        .result_v_k(result_v_k),
        .result_done(result_done),
        .result_fault(result_fault),
        .result_cause(result_cause),
        .result_tag(result_tag),
        .result_gen(result_gen),
        .result_token(result_token),
        .result_value(result_value),
        .result_cycles(result_cycles),
        .status_event_valid(status_event_valid),
        .status_port_match(status_port_match),
        .tx_slot_canonical(tx_slot_canonical),
        .tx_kind(tx_kind),
        .tx_valid(tx_valid),
        .tx_payload(base_payload),
        .fault(base_fault));
    ot_qwen_status_obs_v1_state u_obs(.ck(ck),.rst_n(obs_rst_n),.epoch16(epoch16),.obs_ctx(obs_ctx),.obs_res(obs_res),.obs_native(obs_native),.snapshot(obs_snapshot),.fault(obs_fault));
    genvar og;
    for(og=0;og<13;og=og+1) begin:g_obs_capture
        wire local_slot;
        ot_d2d_status_and_s7 u_slot(.valid(status_event_valid),.port_match(status_port_match),.slot(local_slot));
        always @(posedge ck) if(local_slot) held_obs[16*og+:16]<=obs_snapshot[16*og+:16];
    end
    assign tx_payload={base_payload[547:512],held_obs,148'd0,base_payload[155:0]};
    assign fault=base_fault|obs_fault;
endmodule

module qfd_d2d_static_core_s7_obs1 #(parameter [31:0] TXDP = {8'd2, 8'd1, 8'd2, 8'd1}, parameter integer SFMUT = 0, parameter integer HEAD_CONTEXT = 0) (
    input wire [61:0] obs_ctx, input wire [46:0] obs_res, input wire [59:0] obs_native,
    input  wire         ck,
    input  wire         por_n, rst_n,
    input  wire         cfg_tx_we, cfg_rx_we, input wire [5:0] cfg_addr,
    input  wire [31:0]  cfg_data_t, cfg_data_r, input wire [4:0] cfg_seg_t, cfg_seg_r,
    input  wire [6:0]   cal_start_k, cal_start_rx_k,
    input  wire [5:0]   cal_seg_k, cal_seg_rx_k,
    input  wire [1:0]   cal_user_tx, cal_user_rx,
    output wire [1:0]   tx_user, rx_user,
    input  wire         fwd_epoch,
    input  wire         fwd_link_rst_n,
    output wire         native_tx_slot, output wire [3:0] native_tx_slot_kind, output wire [4:0] native_tx_slot_beat,
    input  wire         native_tx_v, input wire [547:0] native_tx_payload,
    output wire [547:0] rx_payload,
    output wire         native_rx_v,
    output wire         native_rx_slot, output wire [3:0] native_rx_slot_kind, output wire [4:0] native_rx_slot_beat,
    output wire         prog_witness_slot, output wire prog_auth_slot, output wire prog_context_slot,
    output wire         prog_head_context_slot,
    input  wire         prog_tx_observed_v, input wire [547:0] prog_tx_record,
    output wire         prog_rx_v,
    output wire         emb_rx_v, output wire emb_rx_slot,
    output wire         kv_x3_slot,
    input  wire [523:0] x3, input wire [58:0] x3_identity, input wire [1:0] x3_generation,
    input  wire [15:0]  status_epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire [21:0]  result_v_k,
    input  wire         result_done, result_fault, input wire [3:0] result_cause, input wire [58:0] result_tag,
    input  wire [1:0]   result_gen, input wire [17:0] result_token, input wire [31:0] result_value, result_cycles,
    input  wire         fdi_tx_up, output wire fdi_tx_v, output wire [582:0] fdi_tx_flit,
    input  wire         fdi_rx_v, input wire [582:0] fdi_rx_flit,
    output wire         phy_rst_n,
    output wire         epoch_abort, output wire [7:0] transport_fault, output wire fault
);
    localparam integer NRST = 39, NEB = 25;
    wire [NRST-1:0] lr;
    wire [0:0] local_por_n;
    ot_d2d_rst_tree_s7 #(.NR(NRST)) u_reset_regions (.clk(ck), .rst_n_in(rst_n), .rst_n(lr));
    ot_rst_pipe #(.REGIONS(1), .STAGES(2)) u_por_region (.clk(ck), .rst_n_in(por_n), .rst_n(local_por_n));
    localparam integer FW = 548;
    wire [3:0] txs, rxe, rxs; wire [3:0] tk, rk; wire [4:0] tb, rb; wire [FW-1:0] rxp;
    wire [3:0] tv; wire [4*FW-1:0] tp;
    wire eb, ab, endf, own_rst_n, rec; wire [7:0] ep, fc;
    wire st_f, kvn_f;
    wire status_event_valid, status_port_match;
    ot_qwen_d2d_recovery #(.MASTER(0)) u_rec (.ck(ck), .por_n(local_por_n[0]), .rst_n(lr[0]), .abort(ab | endf),
        .fault_cause(fc), .end_fault(endf), .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_rx_v(fdi_rx_v),
        .reset_req(1'b0), .recovery_clear(1'b0), .boot_begin(1'b0), .fwd_epoch_i(fwd_epoch), .fwd_epoch_o(),
        .fwd_link_rst_n(), .phy_rst_n(own_rst_n), .epoch_begin(eb), .epoch(ep), .link_up(), .links_drained(),
        .link_reset_seen(), .retrained(), .transport_fault(transport_fault), .recovering(rec), .recovery_cycles());
    // epoch_begin copies: copy of the follower strobe capture chain (same D / reset depth as u_rec.fq) and KEPT copies
    reg [2:0] fq_c;
    always @(posedge ck or negedge lr[1]) if (!lr[1]) fq_c <= 3'd0; else fq_c <= {fq_c[1:0], fwd_epoch};
    wire [NEB-1:0] eb_k;
    genvar e;
    for (e = 0; e < NEB; e = e + 1) begin : g_eb
        ot_d2d_kffr u_eb (.ck(ck), .rst_n(lr[1]), .d(fq_c[2]), .q(eb_k[e]));
    end
    assign phy_rst_n = own_rst_n & fwd_link_rst_n;
    ot_qwen_d2d_static_end_s7 #(.TXD(TXDP), .SFMUT(SFMUT)) u_end (
        .ck({5{ck}}), .rst_n(lr[27:2]), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr),
        .cfg_data_t(cfg_data_t), .cfg_data_r(cfg_data_r), .cfg_seg_t(cfg_seg_t), .cfg_seg_r(cfg_seg_r),
        .eb_k(eb_k[17:0]), .epoch(ep), .cal_start_k(cal_start_k), .cal_seg_k(cal_seg_k),
        .cal_start_rx_k(cal_start_rx_k), .cal_seg_rx_k(cal_seg_rx_k), .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx),
        .tx_user(tx_user), .rx_user(rx_user),
        .tx_slot(txs), .tx_kind(tk), .tx_beat(tb), .tx_valid(tv), .tx_payload(tp),
        .rx_event(rxe), .rx_slot(rxs), .rx_kind(rk), .rx_beat(rb), .rx_payload(rxp),
        .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_tx_flit(fdi_tx_flit), .p_rx_v(fdi_rx_v), .p_rx_flit(fdi_rx_flit),
        .epoch_abort(ab), .fault_cause(fc), .end_fault(endf), .cal_running(),
        .status_event_valid(status_event_valid), .status_port_match(status_port_match));
    assign epoch_abort = ab;
    assign native_tx_slot = txs[0]; assign native_tx_slot_kind = tk; assign native_tx_slot_beat = tb;
    assign tv[0] = native_tx_v; assign tp[0 +: FW] = native_tx_payload;
    assign rx_payload = rxp;
    assign native_rx_v = rxe[0];
    assign native_rx_slot = rxs[0]; assign native_rx_slot_kind = rk; assign native_rx_slot_beat = rb;
    assign prog_witness_slot = txs[1] && (HEAD_CONTEXT == 0 || tk == 4'd14);
    assign prog_head_context_slot = HEAD_CONTEXT != 0 && txs[1] && tk == 4'd12;
    assign tv[1] = prog_tx_observed_v; assign tp[FW +: FW] = prog_tx_record;
    assign prog_rx_v = rxe[1];
    assign emb_rx_v = rxe[2]; assign emb_rx_slot = rxs[2];
    assign prog_auth_slot = rxs[1] && rk == 4'd13;
    assign prog_context_slot = rxs[1] && rk == 4'd12;
    // STATUS resets: held-result groups and TX register, each = region copy & ~epoch_begin copy (as rst_n & ~eb)
    wire [5:0] st_rh;
    for (e = 0; e < 6; e = e + 1) begin : g_strh
        ot_d2d_kandn_s7 u_r (.a(lr[28 + e]), .bn(eb_k[18 + e]), .y(st_rh[e]));
    end
    wire st_rt;
    ot_d2d_kandn_s7 u_strt (.a(lr[34]), .bn(eb_k[23]), .y(st_rt));
    ot_qwen_d2d_status_tx_s7_obs1 #(.SFMUT(SFMUT)) u_st (.obs_ctx(obs_ctx),.obs_res(obs_res),.obs_native(obs_native),.obs_rst_n(lr[38:36]),.ck(ck), .rst_h_k(st_rh), .rst_t(st_rt), .epoch16(status_epoch16),
        .vm_drained(vm_drained), .collective_drained(collective_drained), .collective_busy(collective_busy),
        .crom_fault(crom_fault), .execution_active(execution_active), .admit_ready(admit_ready),
        .result_v_k(result_v_k), .result_done(result_done), .result_fault(result_fault), .result_cause(result_cause),
        .result_tag(result_tag), .result_gen(result_gen), .result_token(result_token), .result_value(result_value),
        .result_cycles(result_cycles), .tx_slot_canonical(txs[2]), .status_event_valid(status_event_valid),
        .status_port_match(status_port_match), .tx_kind(tk), .tx_valid(tv[2]), .tx_payload(tp[2*FW +: FW]),
        .fault(st_f));
    assign kv_x3_slot = txs[3];
    ot_qwen_d2d_kvn_tx u_kvn (.ck(ck), .rst_n(lr[35] & ~eb_k[24]), .x3(x3), .x3_identity(x3_identity),
        .x3_generation(x3_generation), .tx_valid(tv[3]), .tx_payload(tp[3*FW +: FW]), .fault(kvn_f));
    assign fault = endf | st_f | kvn_f;
endmodule
module qfd_d2d_static_ovl_sf7_obs1 #(parameter integer MUT = 0, parameter integer PR = 1, parameter [31:0] TXDP = 32'd0,
    parameter integer SFMUT = 0, parameter integer HEAD_CONTEXT = 0) (
    input wire [61:0] obs_ctx, input wire [46:0] obs_res, input wire [59:0] obs_native,
    input  wire ck,
    input  wire por_n,
    input  wire rst_n,
    input  wire cfg_tx_we,
    input  wire cfg_rx_we,
    input  wire [5:0] cfg_addr,
    input  wire [31:0] cfg_data,
    input  wire cal_start,
    input  wire cal_seg,
    input  wire cal_start_rx,
    input  wire cal_seg_rx,
    input  wire [1:0] cal_user_tx,
    input  wire [1:0] cal_user_rx,
    output wire [1:0] tx_user,
    output wire [1:0] rx_user,
    input  wire fwd_epoch,
    input  wire fwd_link_rst_n,
    output wire native_tx_slot,
    output wire [3:0] native_tx_slot_kind,
    output wire [4:0] native_tx_slot_beat,
    input  wire native_tx_v,
    input  wire [547:0] native_tx_payload,
    output wire [547:0] rx_payload,
    output wire native_rx_v,
    output wire native_rx_slot,
    output wire [3:0] native_rx_slot_kind,
    output wire [4:0] native_rx_slot_beat,
    output wire prog_witness_slot,
    output wire prog_head_context_slot,
    output wire prog_auth_slot,
    output wire prog_context_slot,
    input  wire prog_tx_observed_v,
    input  wire [547:0] prog_tx_record,
    output wire prog_rx_v,
    output wire emb_rx_v,
    output wire emb_rx_slot,
    output wire kv_x3_slot,
    input  wire [523:0] x3,
    input  wire [58:0] x3_identity,
    input  wire [1:0] x3_generation,
    input  wire [15:0] status_epoch16,
    input  wire vm_drained,
    input  wire collective_drained,
    input  wire collective_busy,
    input  wire crom_fault,
    input  wire execution_active,
    input  wire admit_ready,
    input  wire result_v,
    input  wire result_done,
    input  wire result_fault,
    input  wire [3:0] result_cause,
    input  wire [58:0] result_tag,
    input  wire [1:0] result_gen,
    input  wire [17:0] result_token,
    input  wire [31:0] result_value,
    input  wire [31:0] result_cycles,
    input  wire fdi_tx_up,
    output wire fdi_tx_v,
    output wire [582:0] fdi_tx_flit,
    input  wire fdi_rx_v,
    input  wire [582:0] fdi_rx_flit,
    output wire phy_rst_n,
    output wire epoch_abort,
    output wire [7:0] transport_fault,
    output wire fault
);
    // TXDP = the compiler's per-TX-port producer capture latency (port p = byte p, 1..255 edges), set by the die GEN
    // from d2d_cal_image.svh (D2D_TXDP_C / D2D_TXDP_K, tools/qwen_split/d2d_cal_seq_image.py) or txdp.svh
    // (tools/qwen_split/d2d_link_calendar.py).  No production default exists: PR = 1 with an uncompiled (zero) port
    // byte does not elaborate (QXF-LINK 2026-10-18, TOKEN-XDIE-QWEN F4; the r4..r9 masters hard-wired the
    // component-bench codec latencies).
    generate if (PR != 0 && (TXDP[7:0] == 8'd0 || TXDP[15:8] == 8'd0 || TXDP[23:16] == 8'd0 || TXDP[31:24] == 8'd0)) begin : g_txdp_uncompiled
        D2D_TXDP_NOT_COMPILED__set_TXDP_from_the_compiler u_txdp_uncompiled ();
    end endgenerate
    generate if (PR == 0) begin : g_sf_needs_pr
        D2D_SF_REQUIRES_PR_1 u_sf_needs_pr ();
    end endgenerate
    reg [61:0] q_obs_ctx; reg [46:0] q_obs_res; reg [59:0] q_obs_native;
    always @(posedge ck) begin q_obs_ctx<=obs_ctx;q_obs_res<=obs_res;q_obs_native<=obs_native;end
    wire [61:0] c_obs_ctx=PR?q_obs_ctx:obs_ctx;
    wire [46:0] c_obs_res=PR?q_obs_res:obs_res;
    wire [59:0] c_obs_native=PR?q_obs_native:obs_native;
    genvar gi;   // SAFE5: KEPT pin-flop copies (ot_d2d_kff, route.synth_keep_modules), one per <= ~32 loads
    wire c_cfg_tx_we;
    reg q_cfg_tx_we;
    always @(posedge ck) q_cfg_tx_we <= cfg_tx_we;
    assign c_cfg_tx_we = PR ? q_cfg_tx_we : cfg_tx_we;
    wire c_cfg_rx_we;
    reg q_cfg_rx_we;
    always @(posedge ck) q_cfg_rx_we <= cfg_rx_we;
    assign c_cfg_rx_we = PR ? q_cfg_rx_we : cfg_rx_we;
    wire [5:0] c_cfg_addr;
    reg [5:0] q_cfg_addr;
    always @(posedge ck) q_cfg_addr <= cfg_addr;
    assign c_cfg_addr = PR ? q_cfg_addr : cfg_addr;
    wire [31:0] k_cfg_data_t;
    for (gi = 0; gi < 32; gi = gi + 1) begin : g_cfg_data_t
        ot_d2d_kff u_k (.ck(ck), .d(cfg_data[gi]), .q(k_cfg_data_t[gi]));
    end
    wire [31:0] k_cfg_data_r;
    for (gi = 0; gi < 32; gi = gi + 1) begin : g_cfg_data_r
        ot_d2d_kff u_k (.ck(ck), .d(cfg_data[gi]), .q(k_cfg_data_r[gi]));
    end
    wire [4:0] k_cfg_seg_t;
    for (gi = 0; gi < 5; gi = gi + 1) begin : g_cfg_seg_t
        ot_d2d_kff u_k (.ck(ck), .d(cfg_data[gi]), .q(k_cfg_seg_t[gi]));
    end
    wire [4:0] k_cfg_seg_r;
    for (gi = 0; gi < 5; gi = gi + 1) begin : g_cfg_seg_r
        ot_d2d_kff u_k (.ck(ck), .d(cfg_data[gi]), .q(k_cfg_seg_r[gi]));
    end
    wire [6:0] k_cal_start_rx_k;
    for (gi = 0; gi < 7; gi = gi + 1) begin : g_cal_start_rx_k
        ot_d2d_kff u_k (.ck(ck), .d(cal_start_rx), .q(k_cal_start_rx_k[gi]));
    end
    wire [5:0] k_cal_seg_rx_k;
    for (gi = 0; gi < 6; gi = gi + 1) begin : g_cal_seg_rx_k
        ot_d2d_kff u_k (.ck(ck), .d(cal_seg_rx), .q(k_cal_seg_rx_k[gi]));
    end
    wire [1:0] c_cal_user_tx;
    reg [1:0] q_cal_user_tx;
    always @(posedge ck) q_cal_user_tx <= cal_user_tx;
    assign c_cal_user_tx = PR ? q_cal_user_tx : cal_user_tx;
    wire [1:0] c_cal_user_rx;
    reg [1:0] q_cal_user_rx;
    always @(posedge ck) q_cal_user_rx <= cal_user_rx;
    assign c_cal_user_rx = PR ? q_cal_user_rx : cal_user_rx;
    wire [1:0] c_tx_user;
    reg [1:0] q_tx_user;
    always @(posedge ck) q_tx_user <= c_tx_user;
    assign tx_user = PR ? q_tx_user : c_tx_user;
    wire [1:0] c_rx_user;
    reg [1:0] q_rx_user;
    always @(posedge ck) q_rx_user <= c_rx_user;
    assign rx_user = PR ? q_rx_user : c_rx_user;
    wire [6:0] k_cal_start_k;
    for (gi = 0; gi < 7; gi = gi + 1) begin : g_cal_start_k
        ot_d2d_kff u_k (.ck(ck), .d(cal_start), .q(k_cal_start_k[gi]));
    end
    wire [5:0] k_cal_seg_k;
    for (gi = 0; gi < 6; gi = gi + 1) begin : g_cal_seg_k
        ot_d2d_kff u_k (.ck(ck), .d(cal_seg), .q(k_cal_seg_k[gi]));
    end
    wire c_fwd_epoch;
    reg q_fwd_epoch;
    always @(posedge ck) q_fwd_epoch <= fwd_epoch;
    assign c_fwd_epoch = PR ? q_fwd_epoch : fwd_epoch;
    wire c_fwd_link_rst_n;
    reg q_fwd_link_rst_n;
    always @(posedge ck) q_fwd_link_rst_n <= fwd_link_rst_n;
    assign c_fwd_link_rst_n = PR ? q_fwd_link_rst_n : fwd_link_rst_n;
    wire c_native_tx_slot;
    reg q_native_tx_slot;
    always @(posedge ck) q_native_tx_slot <= c_native_tx_slot;
    assign native_tx_slot = PR ? q_native_tx_slot : c_native_tx_slot;
    wire [3:0] c_native_tx_slot_kind;
    reg [3:0] q_native_tx_slot_kind;
    always @(posedge ck) q_native_tx_slot_kind <= c_native_tx_slot_kind;
    assign native_tx_slot_kind = PR ? q_native_tx_slot_kind : c_native_tx_slot_kind;
    wire [4:0] c_native_tx_slot_beat;
    reg [4:0] q_native_tx_slot_beat;
    always @(posedge ck) q_native_tx_slot_beat <= c_native_tx_slot_beat;
    assign native_tx_slot_beat = PR ? q_native_tx_slot_beat : c_native_tx_slot_beat;
    wire c_native_tx_v;
    reg q_native_tx_v;
    always @(posedge ck) q_native_tx_v <= native_tx_v;
    assign c_native_tx_v = PR ? q_native_tx_v : native_tx_v;
    wire [547:0] c_native_tx_payload;
    reg [547:0] q_native_tx_payload;
    always @(posedge ck) q_native_tx_payload <= native_tx_payload;
    assign c_native_tx_payload = PR ? q_native_tx_payload : native_tx_payload;
    wire [547:0] c_rx_payload;
    reg [547:0] q_rx_payload;
    always @(posedge ck) q_rx_payload <= c_rx_payload;
    assign rx_payload = PR ? q_rx_payload : c_rx_payload;
    wire c_native_rx_v;
    reg q_native_rx_v;
    always @(posedge ck) q_native_rx_v <= c_native_rx_v;
    assign native_rx_v = PR ? q_native_rx_v : c_native_rx_v;
    wire c_native_rx_slot;
    reg q_native_rx_slot;
    always @(posedge ck) q_native_rx_slot <= c_native_rx_slot;
    assign native_rx_slot = PR ? q_native_rx_slot : c_native_rx_slot;
    wire [3:0] c_native_rx_slot_kind;
    reg [3:0] q_native_rx_slot_kind;
    always @(posedge ck) q_native_rx_slot_kind <= c_native_rx_slot_kind;
    assign native_rx_slot_kind = PR ? q_native_rx_slot_kind : c_native_rx_slot_kind;
    wire [4:0] c_native_rx_slot_beat;
    reg [4:0] q_native_rx_slot_beat;
    always @(posedge ck) q_native_rx_slot_beat <= c_native_rx_slot_beat;
    assign native_rx_slot_beat = PR ? q_native_rx_slot_beat : c_native_rx_slot_beat;
    wire c_prog_head_context_slot;
    reg q_prog_head_context_slot;
    always @(posedge ck) q_prog_head_context_slot <= c_prog_head_context_slot;
    assign prog_head_context_slot = PR ? q_prog_head_context_slot : c_prog_head_context_slot;
    wire c_prog_witness_slot;
    reg q_prog_witness_slot;
    always @(posedge ck) q_prog_witness_slot <= c_prog_witness_slot;
    assign prog_witness_slot = PR ? q_prog_witness_slot : c_prog_witness_slot;
    wire c_prog_auth_slot;
    reg q_prog_auth_slot;
    always @(posedge ck) q_prog_auth_slot <= c_prog_auth_slot;
    assign prog_auth_slot = PR ? q_prog_auth_slot : c_prog_auth_slot;
    wire c_prog_context_slot;
    reg q_prog_context_slot;
    always @(posedge ck) q_prog_context_slot <= c_prog_context_slot;
    assign prog_context_slot = PR ? q_prog_context_slot : c_prog_context_slot;
    wire c_prog_tx_observed_v;
    reg q_prog_tx_observed_v;
    always @(posedge ck) q_prog_tx_observed_v <= prog_tx_observed_v;
    assign c_prog_tx_observed_v = PR ? q_prog_tx_observed_v : prog_tx_observed_v;
    wire [547:0] c_prog_tx_record;
    reg [547:0] q_prog_tx_record;
    always @(posedge ck) q_prog_tx_record <= prog_tx_record;
    assign c_prog_tx_record = PR ? q_prog_tx_record : prog_tx_record;
    wire c_prog_rx_v;
    reg q_prog_rx_v;
    always @(posedge ck) q_prog_rx_v <= c_prog_rx_v;
    assign prog_rx_v = PR ? q_prog_rx_v : c_prog_rx_v;
    wire c_emb_rx_v;
    reg q_emb_rx_v;
    always @(posedge ck) q_emb_rx_v <= c_emb_rx_v;
    assign emb_rx_v = PR ? q_emb_rx_v : c_emb_rx_v;
    wire c_emb_rx_slot;
    reg q_emb_rx_slot;
    always @(posedge ck) q_emb_rx_slot <= c_emb_rx_slot;
    assign emb_rx_slot = PR ? q_emb_rx_slot : c_emb_rx_slot;
    wire c_kv_x3_slot;
    reg q_kv_x3_slot;
    always @(posedge ck) q_kv_x3_slot <= c_kv_x3_slot;
    assign kv_x3_slot = PR ? q_kv_x3_slot : c_kv_x3_slot;
    wire [523:0] c_x3;
    reg [523:0] q_x3;
    always @(posedge ck) q_x3 <= x3;
    assign c_x3 = PR ? q_x3 : x3;
    wire [58:0] c_x3_identity;
    reg [58:0] q_x3_identity;
    always @(posedge ck) q_x3_identity <= x3_identity;
    assign c_x3_identity = PR ? q_x3_identity : x3_identity;
    wire [1:0] c_x3_generation;
    reg [1:0] q_x3_generation;
    always @(posedge ck) q_x3_generation <= x3_generation;
    assign c_x3_generation = PR ? q_x3_generation : x3_generation;
    wire [15:0] c_status_epoch16;
    reg [15:0] q_status_epoch16;
    always @(posedge ck) q_status_epoch16 <= status_epoch16;
    assign c_status_epoch16 = PR ? q_status_epoch16 : status_epoch16;
    wire c_vm_drained;
    reg q_vm_drained;
    always @(posedge ck) q_vm_drained <= vm_drained;
    assign c_vm_drained = PR ? q_vm_drained : vm_drained;
    wire c_collective_drained;
    reg q_collective_drained;
    always @(posedge ck) q_collective_drained <= collective_drained;
    assign c_collective_drained = PR ? q_collective_drained : collective_drained;
    wire c_collective_busy;
    reg q_collective_busy;
    always @(posedge ck) q_collective_busy <= collective_busy;
    assign c_collective_busy = PR ? q_collective_busy : collective_busy;
    wire c_crom_fault;
    reg q_crom_fault;
    always @(posedge ck) q_crom_fault <= crom_fault;
    assign c_crom_fault = PR ? q_crom_fault : crom_fault;
    wire c_execution_active;
    reg q_execution_active;
    always @(posedge ck) q_execution_active <= execution_active;
    assign c_execution_active = PR ? q_execution_active : execution_active;
    wire c_admit_ready;
    reg q_admit_ready;
    always @(posedge ck) q_admit_ready <= admit_ready;
    assign c_admit_ready = PR ? q_admit_ready : admit_ready;
    wire [21:0] k_result_v_k;
    for (gi = 0; gi < 22; gi = gi + 1) begin : g_result_v_k
        ot_d2d_kff u_k (.ck(ck), .d(result_v), .q(k_result_v_k[gi]));
    end
    wire c_result_done;
    reg q_result_done;
    always @(posedge ck) q_result_done <= result_done;
    assign c_result_done = PR ? q_result_done : result_done;
    wire c_result_fault;
    reg q_result_fault;
    always @(posedge ck) q_result_fault <= result_fault;
    assign c_result_fault = PR ? q_result_fault : result_fault;
    wire [3:0] c_result_cause;
    reg [3:0] q_result_cause;
    always @(posedge ck) q_result_cause <= result_cause;
    assign c_result_cause = PR ? q_result_cause : result_cause;
    wire [58:0] c_result_tag;
    reg [58:0] q_result_tag;
    always @(posedge ck) q_result_tag <= result_tag;
    assign c_result_tag = PR ? q_result_tag : result_tag;
    wire [1:0] c_result_gen;
    reg [1:0] q_result_gen;
    always @(posedge ck) q_result_gen <= result_gen;
    assign c_result_gen = PR ? q_result_gen : result_gen;
    wire [17:0] c_result_token;
    reg [17:0] q_result_token;
    always @(posedge ck) q_result_token <= result_token;
    assign c_result_token = PR ? q_result_token : result_token;
    wire [31:0] c_result_value;
    reg [31:0] q_result_value;
    always @(posedge ck) q_result_value <= result_value;
    assign c_result_value = PR ? q_result_value : result_value;
    wire [31:0] c_result_cycles;
    reg [31:0] q_result_cycles;
    always @(posedge ck) q_result_cycles <= result_cycles;
    assign c_result_cycles = PR ? q_result_cycles : result_cycles;
    wire c_fdi_tx_up;
    reg q_fdi_tx_up;
    always @(posedge ck) q_fdi_tx_up <= fdi_tx_up;
    assign c_fdi_tx_up = PR ? q_fdi_tx_up : fdi_tx_up;
    wire c_fdi_tx_v;
    reg q_fdi_tx_v;
    always @(posedge ck) q_fdi_tx_v <= c_fdi_tx_v;
    assign fdi_tx_v = PR ? q_fdi_tx_v : c_fdi_tx_v;
    wire [582:0] c_fdi_tx_flit;
    reg [582:0] q_fdi_tx_flit;
    always @(posedge ck) q_fdi_tx_flit <= c_fdi_tx_flit;
    assign fdi_tx_flit = PR ? q_fdi_tx_flit : c_fdi_tx_flit;
    wire c_fdi_rx_v;
    reg q_fdi_rx_v;
    always @(posedge ck) q_fdi_rx_v <= fdi_rx_v;
    assign c_fdi_rx_v = PR ? q_fdi_rx_v : fdi_rx_v;
    wire [582:0] c_fdi_rx_flit;
    reg [582:0] q_fdi_rx_flit;
    always @(posedge ck) q_fdi_rx_flit <= fdi_rx_flit;
    assign c_fdi_rx_flit = PR ? q_fdi_rx_flit : fdi_rx_flit;
    wire c_phy_rst_n;
    reg q_phy_rst_n;
    always @(posedge ck) q_phy_rst_n <= c_phy_rst_n;
    assign phy_rst_n = PR ? q_phy_rst_n : c_phy_rst_n;
    wire c_epoch_abort;
    reg q_epoch_abort;
    always @(posedge ck) q_epoch_abort <= c_epoch_abort;
    assign epoch_abort = PR ? q_epoch_abort : c_epoch_abort;
    wire [7:0] c_transport_fault;
    reg [7:0] q_transport_fault;
    always @(posedge ck) q_transport_fault <= c_transport_fault;
    assign transport_fault = PR ? q_transport_fault : c_transport_fault;
    wire c_fault;
    reg q_fault;
    always @(posedge ck) q_fault <= c_fault;
    assign fault = PR ? q_fault : c_fault;
    qfd_d2d_static_core_s7_obs1 #(.TXDP(PR ? TXDP : {8'd2, 8'd1, 8'd2, 8'd1}), .SFMUT(SFMUT), .HEAD_CONTEXT(HEAD_CONTEXT)) u_core (.obs_ctx(c_obs_ctx),.obs_res(c_obs_res),.obs_native(c_obs_native),.ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(c_cfg_tx_we), .cfg_rx_we(c_cfg_rx_we), .cfg_addr(c_cfg_addr), .cfg_data_t(k_cfg_data_t), .cfg_data_r(k_cfg_data_r), .cfg_seg_t(k_cfg_seg_t), .cfg_seg_r(k_cfg_seg_r), .cal_start_k(k_cal_start_k), .cal_seg_k(k_cal_seg_k), .cal_start_rx_k(k_cal_start_rx_k), .cal_seg_rx_k(k_cal_seg_rx_k), .cal_user_tx(c_cal_user_tx), .cal_user_rx(c_cal_user_rx), .tx_user(c_tx_user), .rx_user(c_rx_user), .fwd_epoch(c_fwd_epoch), .fwd_link_rst_n(c_fwd_link_rst_n), .native_tx_slot(c_native_tx_slot), .native_tx_slot_kind(c_native_tx_slot_kind), .native_tx_slot_beat(c_native_tx_slot_beat), .native_tx_v(c_native_tx_v), .native_tx_payload(c_native_tx_payload), .rx_payload(c_rx_payload), .native_rx_v(c_native_rx_v), .native_rx_slot(c_native_rx_slot), .native_rx_slot_kind(c_native_rx_slot_kind), .native_rx_slot_beat(c_native_rx_slot_beat), .prog_witness_slot(c_prog_witness_slot), .prog_head_context_slot(c_prog_head_context_slot), .prog_auth_slot(c_prog_auth_slot), .prog_context_slot(c_prog_context_slot), .prog_tx_observed_v(c_prog_tx_observed_v), .prog_tx_record(c_prog_tx_record), .prog_rx_v(c_prog_rx_v), .emb_rx_v(c_emb_rx_v), .emb_rx_slot(c_emb_rx_slot), .kv_x3_slot(c_kv_x3_slot), .x3(c_x3), .x3_identity(c_x3_identity), .x3_generation(c_x3_generation), .status_epoch16(c_status_epoch16), .vm_drained(c_vm_drained), .collective_drained(c_collective_drained), .collective_busy(c_collective_busy), .crom_fault(c_crom_fault), .execution_active(c_execution_active), .admit_ready(c_admit_ready), .result_v_k(k_result_v_k), .result_done(c_result_done), .result_fault(c_result_fault), .result_cause(c_result_cause), .result_tag(c_result_tag), .result_gen(c_result_gen), .result_token(c_result_token), .result_value(c_result_value), .result_cycles(c_result_cycles), .fdi_tx_up(c_fdi_tx_up), .fdi_tx_v(c_fdi_tx_v), .fdi_tx_flit(c_fdi_tx_flit), .fdi_rx_v(c_fdi_rx_v), .fdi_rx_flit(c_fdi_rx_flit), .phy_rst_n(c_phy_rst_n), .epoch_abort(c_epoch_abort), .transport_fault(c_transport_fault), .fault(c_fault));
endmodule
// Each kept leaf owns its grammar decision and <=16 payload capture bits.
// Caller supplies same-phase regional reset copies; no data/event edge is added.
(* keep_hierarchy = "yes" *)
module ot_qwen_status_obs_rx_chunk #(parameter integer W=16)(
 input wire ck,rst_n,ev,rs,hk,fc,
 input wire [15:0] he,epoch16,
 input wire [511:0] d,
 input wire [W-1:0] capture_d,
 output reg [W-1:0] q
);
 wire good;
 ot_qwen_status_obs_v1_valid u_check(.x(d[511:304]),.good(good));
 wire en=ev && rs && hk && he==epoch16 && good && !(|d[303:156]) && !fc;
 always @(posedge ck or negedge rst_n)
  if(!rst_n) q<=0; else if(en) q<=capture_d;
endmodule
module ot_qwen_d2d_status_rx_sfm3_obs1 #(parameter integer NG = 24) (
    input wire [NG+1:0] rst_k, // 0..NG-1 payload chunks, NG fault copies, NG+1 metadata
    input  wire         ck, rst_n,
    input  wire [15:0]  epoch16,
    input  wire         rx_event, rx_slot,
    input  wire [NG-1:0] ev_c, rs_c,
    input  wire [NG-1:0] hk_c,          // KV-D2D3: per-group static header predicate copies (rx_payload edge)
    input  wire [16*NG-1:0] he_c,       // KV-D2D3: per-group copies of rx_payload[532:517]
    input  wire [547:0] rx_payload,
    output wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    output reg          status_fresh,
    output reg          result_v,
    output wire         result_done, result_fault,
    output wire [3:0]   result_cause,
    output wire [58:0]  result_tag,
    output wire [1:0]   result_gen,
    output wire [17:0]  result_token,
    output wire [31:0]  result_value, result_cycles,
    input  wire         epoch_begin,
    output reg status_obs_v, output reg [15:0] status_obs_epoch16,
    output wire [207:0] status_obs_payload,
    output wire         fault
);
    wire [511:0] d = rx_payload[511:0];
    // KV-D2D3: as-built bad_hdr = rx_payload[547:543] != 0 || [542:539] != 15 || [538:533] != 63 || [532:517] != epoch16
    // || [516:512] != 0 || d[511:156] != 0, evaluated per capture group from its own registered copies (hk_c, he_c), so
    // no shared header net reaches more than one group (ABC folded the single bad_hdr into all 156 capture bits)
    wire extension_good;
    ot_qwen_status_obs_v1_valid u_ext_check(.x(rx_payload[511:304]),.good(extension_good));
    wire [NG-1:0] bad_g;
    genvar gh;
    for (gh = 0; gh < NG; gh = gh + 1) begin : g_bad
        assign bad_g[gh] = !hk_c[gh] || he_c[16*gh +: 16] != epoch16 || !extension_good || |rx_payload[303:156];
    end
    wire bad_hdr = bad_g[0];
    // sticky fault: master + NG copies on one D net
    (* keep = "true", dont_touch = "true" *) reg [NG:0] fc;      // fc[0] = master
    wire fault_d = (rx_event != rx_slot || (rx_event && bad_hdr)) ? 1'b1 : fc[0];
    (* keep = "true", dont_touch = "true" *) always @(posedge ck or negedge rst_k[NG])
        if (!rst_k[NG]) fc <= {(NG+1){1'b0}}; else fc <= {(NG+1){fault_d}};
    assign fault = rst_n && fc[0];
    // captured image: cap[5:0] = d[5:0] (status levels), cap[155:7] = d[155:7] (result fields); bit 6 unused (result_v)
    wire [363:0] cap;
    wire [363:0] capture_d={d[511:304],d[155:0]};
    assign status_obs_payload=cap[363:156];
    localparam integer GB = (364 + NG - 1) / NG;
    genvar g;
    for (g = 0; g < NG; g = g + 1) begin : g_cap
        localparam integer LO = (364 * g) / NG;
        localparam integer WG = (364 * (g + 1)) / NG - LO;
        ot_qwen_status_obs_rx_chunk #(.W(WG)) u_cap(
            .ck(ck),.rst_n(rst_k[g]),.ev(ev_c[g]),.rs(rs_c[g]),.hk(hk_c[g]),
            .fc(fc[g+1]),.he(he_c[16*g+:16]),.epoch16(epoch16),.d(d),
            .capture_d(capture_d[LO+:WG]),.q(cap[LO+:WG]));
    end
    wire en0 = ev_c[0] && rs_c[0] && !bad_hdr && !fc[1];
    always @(posedge ck or negedge rst_k[NG+1])
        if (!rst_k[NG+1]) begin status_fresh <= 1'b0; result_v <= 1'b0;status_obs_v<=0;status_obs_epoch16<=0; end
        else begin
            result_v <= en0 && d[6];
            status_obs_v<=en0;
            if(en0)status_obs_epoch16<=epoch16;
            if (en0) status_fresh <= 1'b1;
            else if (epoch_begin) status_fresh <= 1'b0;
        end
    assign {admit_ready, execution_active, crom_fault, collective_busy, collective_drained, vm_drained} = cap[5:0];
    assign {result_cycles, result_value, result_token, result_gen, result_tag, result_cause, result_fault, result_done} =
        cap[155:7];
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (fc !== {(NG+1){fc[0]}} || ev_c !== {NG{rx_event}} || rs_c !== {NG{rx_slot}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule
