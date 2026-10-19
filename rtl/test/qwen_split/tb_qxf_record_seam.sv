`timescale 1ns/1ps
// QXF-SEAMC 10-18: slice bench of the Qwen compute die RECORD-BUNDLE seams (TOKEN-XDIE-QWEN F5 + LAYERBENCH-QWEN G-C2).
// DUT = the seam slice qxf_seam (tools/qwen_split/record_bundles.py slice): the d2d_rom -> native59 rx record bundle
// {native_rx_v, native_rx_slot, native_rx_slot_kind, native_rx_slot_beat, rx_payload} and the d2d_rom -> sys_face rx record
// bundle {rx_payload (fan-out leg), prog_rx_v, prog_auth_slot, prog_context_slot, prog_witness_slot, emb_rx_v, emb_rx_slot},
// each member on the forwarded lane / landing the die GEN builds (real RTL: gen_relay_rtl.py wrappers over
// rtl/qwen_split/qfd_fwd_lane.sv, the cells, frame counts and K straps of the GEN netlist or of the fixed GEN form),
// between the d2d_rom pin registers (source root src_ck, lane gate = the source's released reset) and REAL consumers on
// their own mesochronous roots:
//   native59 side  qfd_native59_record_endpoint (qkd_native_attention_record codec: rx_event / slot / kind / beat / payload
//                  checked on one edge) -- 12 RESULT beats (8 spaced, 4 back-to-back)
//   sys_face side  qfd_sys_face_record_port (slot_fault if rx_v !== auth | context; BEGIN / AUTH decoded on rx_v && slot;
//                  witness TX on its slot) + the sys_face EMB face rule (emb_rx_v === emb_rx_slot, payload on emb_rx_v,
//                  qfd_sys_face.sv:477-480) -- BEGIN, AUTH, a witness slot, an embedding word
// Checks: every record decoded bit-exact, no consumer fault, no landing fault, every arrival on the compiled edge
// (source edge + bundle lane cycles EXP_C / EXP_SF (+1 consumer register)), the same latency for every record.
// Static schedule: no ready, no credit; the source launches on compiled edges only.
module tb;
    parameter integer EXP_C  = 3;          // C.rx_record lane cycles of the slice (record_bundles.py slice: K + 1)
    parameter integer EXP_SF = 3;          // SF.rx_record lane cycles
    parameter integer G = 10, R0 = 10;     // source / receiver reset release edges (K = E + G - R0)
    localparam [15:0] EP = 16'h5a3c;
    localparam [5:0]  LAYER = 6'd7;
    localparam [58:0] TAG = {EP, LAYER + 6'd1, 37'h0_1234_5678};
    localparam [63:0] DIG = 64'hfeed_c0de_1357_9bdf;
    reg src_ck = 0, n59_ck = 0, sf_ck = 0;
    always #5 src_ck = ~src_ck;
    initial begin #3.3; forever #5 n59_ck = ~n59_ck; end      // receiving roots: same frequency, own phase
    initial begin #6.7; forever #5 sf_ck = ~sf_ck; end
    integer es = 0, en_ = 0, ef = 0;
    reg src_en = 0, n59_rs = 0, sf_rs = 0;
    always @(posedge src_ck) begin src_en <= (es >= G); es <= es + 1; end
    always @(posedge n59_ck) begin n59_rs <= (en_ >= R0); en_ <= en_ + 1; end
    always @(posedge sf_ck) begin sf_rs <= (ef >= R0); ef <= ef + 1; end

    // ---------------------------------------------------------------- d2d_rom pin registers (compiled source schedule)
    reg q_nrv = 0, q_nrs = 0, q_prv = 0, q_pas = 0, q_pcs = 0, q_pws = 0, q_erv = 0, q_ers = 0;
    reg [3:0] q_nrk = 0; reg [4:0] q_nrb = 0; reg [547:0] q_pay = 0;
    function automatic [511:0] rdata(input integer b);
        rdata = {16{b[7:0] ^ 8'h3c, 24'h00a5c3 + 24'(b)}};
    endfunction
    function automatic integer c_beat_at(input integer e);   // RESULT beat launched at source edge e, or -1
        if (e >= 40 && e < 64 && (e - 40) % 3 == 0) c_beat_at = (e - 40) / 3;
        else if (e >= 80 && e < 84) c_beat_at = 8 + (e - 80);
        else c_beat_at = -1;
    endfunction
    localparam integer E_BEGIN = 100, E_AUTH = 101, E_WIT = 110, E_EMB = 120;
    localparam [511:0] EMBW = {8{64'h0123_4567_89ab_cdef}};
    always @(posedge src_ck) begin
        integer b;
        b = c_beat_at(es);
        q_nrv <= b >= 0; q_nrs <= b >= 0; q_nrk <= b >= 0 ? 4'd3 : 4'd0; q_nrb <= b >= 0 ? 5'(b) : 5'd0;
        q_prv <= es == E_BEGIN || es == E_AUTH; q_pas <= es == E_BEGIN || es == E_AUTH; q_pcs <= 1'b0;
        q_pws <= es == E_WIT; q_erv <= es == E_EMB; q_ers <= es == E_EMB;
        if (b >= 0)              q_pay <= {5'd0, 4'd3, LAYER, EP, 5'(b), rdata(b)};
        else if (es == E_BEGIN)  q_pay <= {5'd0, 4'd13, 6'd63, EP, 5'd0, 495'd0, 4'd8, 11'd1024, 2'd1};
        else if (es == E_AUTH)   q_pay <= {5'd0, 4'd13, 6'd63, EP, 5'd0, 446'd0, DIG, 2'd2};
        else if (es == E_EMB)    q_pay <= {5'd0, 4'd5, 6'd0, EP, 5'd0, EMBW};
        else                     q_pay <= 548'd0;
    end
    // pin clock-to-out (the gated hop-0 clock is a delta later than src_ck in simulation; a real flop has a c->q)
    wire w_nrv, w_nrs, w_prv, w_pas, w_pcs, w_pws, w_erv, w_ers; wire [3:0] w_nrk; wire [4:0] w_nrb; wire [547:0] w_pay;
    assign #0.2 {w_nrv, w_nrs, w_prv, w_pas, w_pcs, w_pws, w_erv, w_ers} = {q_nrv, q_nrs, q_prv, q_pas, q_pcs, q_pws, q_erv, q_ers};
    assign #0.2 w_nrk = q_nrk;
    assign #0.2 w_nrb = q_nrb;
    assign #0.2 w_pay = q_pay;

    wire lane_fault;
    wire d_nrv, d_nrs, d_prv, d_pas, d_pcs, d_pws, d_erv, d_ers; wire [3:0] d_nrk; wire [4:0] d_nrb;
    wire [547:0] d_pay_n, d_pay_s;
    qxf_seam u_seam (.src_ck(src_ck), .src_en(src_en), .n59_ck(n59_ck), .n59_rs(n59_rs), .sf_ck(sf_ck), .sf_rs(sf_rs),
        .d2d_ck(src_ck), .d2d_rs(src_en), .lane_fault(lane_fault),
        .s_lnk_native_rx_v(w_nrv), .d_lnk_native_rx_v(d_nrv), .s_lnk_native_rx_slot(w_nrs), .d_lnk_native_rx_slot(d_nrs),
        .s_lnk_native_rx_slot_kind(w_nrk), .d_lnk_native_rx_slot_kind(d_nrk),
        .s_lnk_native_rx_slot_beat(w_nrb), .d_lnk_native_rx_slot_beat(d_nrb),
        .s_lnk_rx_payload(w_pay), .d_lnk_rx_payload(d_pay_n), .s_lnk_rx_payload__fo1(w_pay), .d_lnk_rx_payload__fo1(d_pay_s),
        .s_sf_prog_rx_v(w_prv), .d_sf_prog_rx_v(d_prv), .s_sf_prog_auth_slot(w_pas), .d_sf_prog_auth_slot(d_pas),
        .s_sf_prog_context_slot(w_pcs), .d_sf_prog_context_slot(d_pcs), .s_sf_prog_witness_slot(w_pws),
        .d_sf_prog_witness_slot(d_pws), .s_sf_emb_rx_v(w_erv), .d_sf_emb_rx_v(d_erv), .s_sf_emb_rx_slot(w_ers),
        .d_sf_emb_rx_slot(d_ers));

    // ---------------------------------------------------------------- consumers (real RTL)
    wire ep_rv, ep_slot, ep_done, ep_fault, ep_txv; wire [4:0] ep_rb, ep_slot_beat; wire [58:0] ep_rtag, ep_dtag;
    wire [511:0] ep_rd; wire [547:0] ep_txp;
    qfd_native59_record_endpoint u_ep (.ck(n59_ck), .rst_n(n59_rs), .operation_tag(TAG),
        .kernel_request_v(1'b0), .kernel_request_tag(59'd0), .kernel_q_v(1'b0), .kernel_q_beat(5'd0), .kernel_q_tag(59'd0),
        .kernel_q_data(512'd0), .tx_slot(1'b0), .tx_slot_kind(4'd0), .tx_slot_beat(5'd0), .tx_valid(ep_txv), .tx_payload(ep_txp),
        .rx_event(d_nrv), .rx_payload(d_pay_n), .rx_slot(d_nrs), .rx_slot_kind(d_nrk), .rx_slot_beat(d_nrb),
        .result_v(ep_rv), .result_beat(ep_rb), .result_tag(ep_rtag), .result_data(ep_rd), .result_slot(ep_slot),
        .result_slot_beat(ep_slot_beat), .kernel_done(ep_done), .kernel_done_tag(ep_dtag), .fault(ep_fault));
    wire rp_begin, rp_auth, rp_ready, rp_cap, rp_commit, rp_hev, rp_txv, rp_txo, rp_fault;
    wire [15:0] rp_bep, rp_aep, rp_pep, rp_hep; wire [10:0] rp_pw; wire [3:0] rp_dw; wire [63:0] rp_adig, rp_pdig;
    wire [58:0] rp_htag; wire [1:0] rp_hgen; wire [547:0] rp_txr;
    qfd_sys_face_record_port u_rp (.ck(sf_ck), .rst_rn({6{sf_rs}}), .auth_slot(d_pas), .context_slot(d_pcs),
        .witness_slot(d_pws), .rx_v(d_prv), .rx_record(d_pay_s), .execution_active(1'b0), .program_obs2(152'd0),
        .descriptor_obs(69'd0), .cfg_image_ready(2'b00), .head_context_v(1'b0), .head_stage(6'd0), .head_token(18'd0),
        .head_position(18'd0), .begin_v(rp_begin), .auth_v(rp_auth), .begin_epoch(rp_bep), .auth_epoch(rp_aep),
        .expected_pw(rp_pw), .expected_dw(rp_dw), .auth_digest(rp_adig), .program_ready(rp_ready),
        .installed_fusedcap(rp_cap), .commit_v(rp_commit), .program_epoch(rp_pep), .program_digest(rp_pdig),
        .host_epoch_valid(rp_hev), .host_epoch(rp_hep), .host_tag(rp_htag), .host_gen(rp_hgen), .tx_v(rp_txv),
        .tx_observed_v(rp_txo), .tx_record(rp_txr), .fault(rp_fault));

    // ---------------------------------------------------------------- checks
    integer errs = 0, chk = 0, n_res = 0, n_beg = 0, n_aut = 0, n_wit = 0, n_emb = 0;
    integer lat_c = -1, lat_sf = -1;
    reg [8*200-1:0] first_err = "";
    task automatic err(input [8*200-1:0] s);
        begin if (errs == 0) first_err = s; errs = errs + 1; $display("QXF_ERR t=%0t %0s", $time, s); end
    endtask
    // native59: a RESULT beat sampled at receiver edge k is visible after edge k-1 = source edge e + EXP_C + 1
    always @(posedge n59_ck) if (n59_rs) begin
        chk = chk + 1;
        if (ep_fault) err("native59 record endpoint fault (rx_record / rx_time: the C.rx_record bundle is torn)");
        if (ep_rv) begin : g_r
            integer want_b, lat;
            want_b = n_res;
            if (ep_rb != 5'(want_b) || ep_rd != rdata(want_b)) err("native59 RESULT beat / data not bit-exact");
            lat = (en_ - 1) - (want_b < 8 ? 40 + 3 * want_b : 80 + want_b - 8);
            if (lat_c < 0) lat_c = lat; else if (lat != lat_c) err("native59 RESULT latency differs between records");
            if (lat != EXP_C + 1) err("native59 RESULT not on its compiled edge (source + C lane cycles + 1)");
            n_res = n_res + 1;
        end
    end
    always @(posedge sf_ck) if (sf_rs) begin
        chk = chk + 1;
        if (u_rp.slot_fault) err("sys_face record port slot_fault (rx_v !== auth | context: SF.rx_record torn)");
        if (u_rp.af) err("sys_face program auth RX fault");
        if (u_rp.cf) err("sys_face host context RX fault");
        if (d_erv !== d_ers) err("sys_face EMB face rule: emb_rx_v !== emb_rx_slot");
        if (d_erv) begin
            if (d_pay_s[511:0] != EMBW) err("sys_face EMB word not on the emb_rx_v edge");
            if ((ef - 1) - E_EMB != EXP_SF) err("sys_face EMB not on its compiled edge");
            n_emb = n_emb + 1;
        end
        if (rp_begin) begin
            if (rp_bep != EP || rp_pw != 11'd1024 || rp_dw != 4'd8) err("sys_face BEGIN fields wrong");
            if ((ef - 1) - E_BEGIN != EXP_SF + 1) err("sys_face BEGIN not on its compiled edge");
            lat_sf = (ef - 1) - E_BEGIN;
            n_beg = n_beg + 1;
        end
        if (rp_auth) begin
            if (rp_aep != EP || rp_adig != DIG) err("sys_face AUTH fields wrong");
            if ((ef - 1) - E_AUTH != EXP_SF + 1) err("sys_face AUTH not on its compiled edge");
            n_aut = n_aut + 1;
        end
        if (rp_txv) begin
            if ((ef - 1) - E_WIT != EXP_SF + 1) err("sys_face witness TX not on its compiled edge (witness slot age)");
            n_wit = n_wit + 1;
        end
    end
    always @(posedge src_ck) if (lane_fault === 1'b1 && es > 30) err("landing ring fault (L6)");
    initial begin
        wait (es == 170);
        if (n_res != 12) err("native59: not every RESULT beat decoded");
        if (n_beg != 1 || n_aut != 1) err("sys_face: BEGIN / AUTH not decoded exactly once");
        if (n_wit != 1) err("sys_face: witness TX not exactly once");
        if (n_emb != 1) err("sys_face: EMB word not seen exactly once");
        $display("QXF_CFG EXP_C=%0d EXP_SF=%0d results=%0d begin=%0d auth=%0d witness=%0d emb=%0d lat_c=%0d lat_sf=%0d jf=%0b wf=%0b",
                 EXP_C, EXP_SF, n_res, n_beg, n_aut, n_wit, n_emb, lat_c, lat_sf, u_rp.jf, u_rp.wf);
        if (errs == 0) $display("QXF_SEAM PASS 0 errors in %0d checks", chk);
        else $display("QXF_SEAM FAIL %0d errors in %0d checks; first: %0s", errs, chk, first_err);
        $finish;
    end
endmodule
