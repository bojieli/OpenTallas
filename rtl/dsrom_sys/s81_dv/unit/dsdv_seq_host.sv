`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SEQ (2026-10-17): dsdv_seq_host -- the S81-DV sequencer / host unit (x1), a stacked unit of 5 leaves on column 4's
// 276-b V rung (p4f..p4h: s_4S <-> bk_sel <-> seqhost <-> s_4N; 680 x 3171 um, leaves ~680 x 634 um, S -> N):
//
//   L0 dsdv_sh_lk  link leaf     host lane port (off-die boundary), host ingest (dsfd_host_native, unchanged) + host
//                                write decode (dsfd_host_sd STATIC = 1, unchanged), svc job / host-write port to the 16
//                                regional service slices, kit (stage start / done) port, regional controller status
//                                fold (the dsfd_ctrl_ctr status merge), the host status / completion word.
//   L1 dsdv_sh_sq  sequencer     ot_dsdv_fixed_issue (= ot_s81_fixed_issue, pipelined seal scan; the compiled calendar {done, issue, engine, arg}, two
//                                job contexts, KIT / END rows, boot seal scan) + the svc completion tag queue.
//   L2 dsdv_sh_vc  middle leaf   ot_dsdv_vstop (the shared V-rung stop, unchanged) + the CTL packer: the calendar's V
//                                commands become CTL beats (template table, 128 x 186 b, boot-loaded) injected N / S;
//                                the gunit cw port (config rows from the host, router / HC jobs from the calendar).
//   L3, L4 dsdv_sh_ft            registered rung hops (one flop a direction a leaf, ~634 um a hop with repeaters).
//
// Engines of the calendar (ENG_PRESENT 5'b10111; any other engine fails the boot seal scan, fixed_issue code 3):
//   0  V north : one CTL beat injected on vo_n (-> s_4N, which applies it if its mask bit is set and re-injects it on
//               the N tier line both ways: one beat reaches the 8 N slices)
//   1  V south : one CTL beat injected on vo_s (-> bk_sel (its vstop may tap CTL) -> s_4S -> the 8 S slices)
//   2  gunit job: cw = {v, a = {2'b10, 7'b0, arg[7]}, d = {214'b0, template[arg[6:0]][41:0]}} on the unit's cw port
//               (dsdv_gunit cw contract, S81U-1 058b17e6e: arg[7] 0 router job, 1 HC job); arg[23:8] = 0 (else fault).
//   4  svc job : s_j = {v, arg 24, tag 8 = {slot, op 7}} to the svc chain (dsfd_svc_c j contract, broadcast to the 16
//               dsdv_svc_rs); the chain's folded completion s_jd {fault, done} completes the oldest posted job.
//   A V command's arg: [6:0] template, [8:7] context (0 none, 1 body[159:108] = {user 10, pos 21, tok 21},
//   2 body[159:139] = pos 21, 3 fault), [23:9] = 0 (else fault).  Its completion is the beat's injection (posted at the
//   CTL beat register, a fixed DONE_V edges after the command pin); the calendar's done row encodes it.
//   CTL beat (ot_s81sl_rstop / ot_s81sl_xr): [0] 1, [3:1] kind 0, [8:4] hops 0 (line default), [12:9] src 4,
//   [20:13] 0, [21 +: 186] payload {body 160, leaf mask 5, target 5, slice mask 16}, upper bits 0.
// Host stream CSR words intercepted in L0 (class 0, never reach the ingest; dsfd_host_c's 0x10 / 0x11 plus 0x13):
//   0x10 calendar word {a = d[102:96], d28 = d[59:32]}   0x11 calendar length d[39:32]   0x13 CTL template
//   {index = d[14:8], payload = d[16 +: 186]}   0x14 gunit table row (boot config: per-layer router bias, HC bases /
//   scales, route scale, eps; set = a[8]) -> cw {1, a = d[17:8] (a[9] must be 0), d = d[32 +: 256]}.  A calendar or template write while a job is held is a sticky fault.
// No credit / ready / arbitration on die: every event is on the compiled timeline; collisions, late / missing
// completions, bad args are sticky faults (assertions, never a reschedule).  The host lane is the only elastic face
// (off-die boundary: the host PHY lane block holds the link-level flow control; the compiler's host slots never exceed
// the ingest's receive FIFO, whose overflow faults).
// Every leaf input lands in a flop, every leaf output leaves a flop.  Single clock ck (stream); per-leaf ot_rst_relay.
// Fixed latencies in edges, counted from the edge that captures an input pin (asserted by tb_dsdv_seq_host): rung
// vi -> vo 6 each way (L0 1, L1 1, vstop 2, L3 1, L4 1); f_ks captured at t -> issuer samples job_v at t + 3 -> the
// command of calendar age a leaves the issuer register at t + 4 + a; V command register -> vo pin + 7; gunit job -> cw
// pin + 3, host 0x14 word captured at e -> cw pin e + 6; svc command
// register -> s_j pin + 2; issuer KIT -> t_kd pin + 3.  Calendar done rows: V / gunit command = issue + 5 (posted);
// svc command = issue + 5 + LS, LS = s_j pin edge -> s_jd capture edge of the svc chain (compiler-priced, p4i).
// MUT (bench negative controls): 1 context splice dropped, 2 svc tag {slot, op} -> {slot, op + 1}, 3 L4 rung hop
// missing (latency 5), 4 V completion one edge late, 5 W svc half dropped from the job-done / status merge, 6 host
// writes routed by the wrong PC bit.
// Two svc halves (RTL-BUILD-S81 10-18, residual bind5 (b)/(c)): s_j is broadcast to both entries (W rsv_05, E rsv_11);
// s_jd_w / s_jd_e merge in L0 (done when both halves reported, at the later half's edge; same pin -> jd_o edge count as
// the one-half unit), s_hw_w / s_hw_e + s_hc_w / s_hc_e are dsfd_host_sd's two stacks (sector -> the half owning its PC,
// markers to both), st_rg_w / st_rg_e fold fault = OR, live = AND into the region status word.
// ---------------------------------------------------------------------------------------------------------------------

// ---------------------------------------------------------------- L3 / L4: registered rung hop (both directions)
module dsdv_sh_ft #(parameter integer V = 276) (
    input  wire         ck,
    input  wire [V-1:0] ni, output reg [V-1:0] no,     // northbound in (S face) / out (N face)
    input  wire [V-1:0] si, output reg [V-1:0] so      // southbound in (N face) / out (S face)
);
    always @(posedge ck) begin no <= ni; so <= si; end
endmodule

// ---------------------------------------------------------------- L0: link leaf
module dsdv_sh_lk #(parameter integer V = 276, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          ck_ih,           // host ingest RX root (ingest clk_h), same stream clock as ck, own CTS root
    input  wire          ck_ic,           // host ingest core root (ingest clk_i), same stream clock as ck, own CTS root
    input  wire          rst_n,
    // unit pins
    input  wire [514:0]  f_host,          // {h_cls 2, h_d 512, h_v}
    output reg  [76:0]   t_host,          // {alive, st 11 = {fault, wf 4, sseq 6}, t_v, t_d 64}
    input  wire [3:0]    f_lf,            // host lane block {fault, live} x 2
    input  wire [52:0]   f_ks,            // {start, user 10, tok 21, pos 21}
    output reg  [53:0]   t_kd,            // {done, tok 21, 32'b0}
    output reg  [32:0]   s_j,             // {v, arg 24, tag 8}
    // per-half svc endpoints (RTL-BUILD-S81 10-18): _w = W entry rsv_05 (columns 0-3), _e = E entry rsv_11 (columns 4-7)
    input  wire [1:0]    s_jd_w, s_jd_e,  // {fault, done} of each half's chain
    output wire [291:0]  s_hw_w, s_hw_e,  // {cls 2, we, addr 32, d 256, v}: sectors routed to the half owning their PC
    input  wire [8:0]    s_hc_w, s_hc_e,  // {ack 8, cr} (one 8-credit contract per half)
    input  wire [1:0]    st_rg_w, st_rg_e,// each half's regional controllers {fault, live} (svc entry st_rg)
    input  wire [V-1:0]  vi_s, output reg [V-1:0] vo_s,      // rung S face (bk_sel)
    // N face (L1)
    output reg  [V-1:0]  rn_o, input wire [V-1:0] rs_i,      // rung hop
    output reg  [35:0]   pw_o,            // {v, a 7, d 28}
    output reg  [8:0]    pl_o,            // {v, len 8}
    output reg  [193:0]  tw_o,            // {v, idx 7, payload 186}
    output reg  [266:0]  cf_o,            // {v, a 10, d 256} gunit config row
    output reg  [52:0]   ks_o,
    input  wire [53:0]   kd_i,
    input  wire [32:0]   j_i,
    output reg  [1:0]    jd_o,
    input  wire [5:0]    sq_i,            // L1 status {fault, code 4, busy}
    input  wire          vf_i             // L2 fault (via L1)
);
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // ---- rung hop
    always @(posedge ck) begin rn_o <= vi_s; vo_s <= rs_i; end
    // ---- pin flops
    reg [514:0] fi; reg [52:0] ks_q; reg [1:0] jdw_q, jde_q, rg_q; reg [3:0] lf_q; reg [53:0] kd_q; reg [32:0] j_q;
    reg [5:0] sq_q; reg vf_q;
    // valid / event bits gated by the relayed reset, payload bits not (S81U-SEQ3: 891 reset loads at gate 8940e10e9)
    always @(posedge ck) begin
        fi <= {f_host[514:1], rn & f_host[0]};
        ks_q <= {rn & f_ks[52], f_ks[51:0]}; jdw_q <= {2{rn}} & s_jd_w; jde_q <= {2{rn}} & s_jd_e; lf_q <= f_lf;
        // region status of both halves: fault = OR, live = AND (MUT 5: the W half is dropped)
        rg_q <= {2{rn}} & ((MUT == 5) ? st_rg_e : {st_rg_w[1] | st_rg_e[1], st_rg_w[0] & st_rg_e[0]});
        kd_q <= {rn & kd_i[53], kd_i[52:0]}; j_q <= {rn & j_i[32], j_i[31:0]}; sq_q <= sq_i; vf_q <= vf_i;
    end
    // ---- to / from L1 and the unit pins (flop-last)
    always @(posedge ck) begin ks_o <= ks_q; t_kd <= kd_q; s_j <= j_q; end
    // ---- job completion merge of the two halves (static: the job broadcast s_j reaches both entries, each half's chain
    // reports its own done at its own compiled latency LS_W / LS_E; the job is done when BOTH halves have reported, in
    // job order, i.e. at the later half's edge -- the calendar's LS is the later one).  Per-half pending counts (jobs
    // done in that half, not yet in the other); a count past 7 = sticky merge fault (a half lost a done).  No handshake.
    reg [2:0] pd_w, pd_e; reg mf;
    wire dw = (MUT == 5) ? jde_q[0] : jdw_q[0], de = jde_q[0];
    wire jb = (pd_w != 3'd0 || dw) && (pd_e != 3'd0 || de);
    always @(posedge ck or negedge rn)
        if (!rn) begin pd_w <= 3'd0; pd_e <= 3'd0; mf <= 1'b0; jd_o <= 2'b00; end
        else begin
            pd_w <= pd_w + {2'b00, dw} - {2'b00, jb}; pd_e <= pd_e + {2'b00, de} - {2'b00, jb};
            if ((pd_w == 3'd7 && dw && !jb) || (pd_e == 3'd7 && de && !jb)) mf <= 1'b1;
            jd_o <= {((MUT == 5) ? 1'b0 : jdw_q[1]) | jde_q[1] | mf, jb};
        end
    // ---- CSR intercept (dsfd_host_c 0x10 / 0x11, plus 0x13 CTL template)
    wire hv = fi[0]; wire [511:0] hd = fi[512:1]; wire [1:0] hcl = fi[514:513];
    wire csr_p = hv && hcl == 2'd0 && hd[7:0] == 8'h10;
    wire csr_l = hv && hcl == 2'd0 && hd[7:0] == 8'h11;
    wire csr_t = hv && hcl == 2'd0 && hd[7:0] == 8'h13;
    wire csr_g = hv && hcl == 2'd0 && hd[7:0] == 8'h14;
    wire to_ing = hv && !csr_p && !csr_l && !csr_t && !csr_g;
    always @(posedge ck) begin
        pw_o <= (rn && csr_p) ? {1'b1, hd[102:96], hd[59:32]} : 36'd0;
        pl_o <= (rn && csr_l) ? {1'b1, hd[39:32]} : 9'd0;
        tw_o <= (rn && csr_t) ? {1'b1, hd[14:8], hd[16 +: 186]} : 194'd0;
        cf_o <= (rn && csr_g) ? {1'b1, hd[17:8], hd[32 +: 256]} : 267'd0;
    end
    // ---- host ingest (clk_h = clk_i = ck, as dsfd_host_c on a layer die) and per-stack decode (NS 1, STATIC)
    wire t_v, ov, owe, ocr, hf, sf; wire [63:0] t_d; wire [31:0] oa; wire [255:0] od; wire [7:0] ack; wire [4:0] crn;
    reg tcr_l;
    // three CTS roots (as dsfd_host_c DSFD_HOST_PQ_BOOT ck_ingest): the ingest's own Gray-FIFO domains clk_h / clk_i
    // get the leaf roots ck_ih / ck_ic (S81U-SEQ3: 24,085 sinks on one root at gate 8940e10e9); APIPE 4 registers the
    // engine's row pitch product (26-level ap1_local -> ap_raddr stage), same values as APIPE 3; APIPE 5 (S81U-SEQ4)
    // also forms the stack x stride partial products in stage A0 (ap1_rbase TT -70 ps at gate4), same values again;
    // APIPE 6 (S81U-SEQ6, gate5 st_sec -> u_ox.mem TT -127.7 ps) registers the request-FIFO write in ot_rom_host_ingest
    // (each host sector enters u_ox one ck_ic edge later; registered free count instead of wfull).
    dsfd_host_native #(.ENABLE(1), .FPIPE(2), .ENG_TRIM(1), .APIPE(6)) u_h (.rst_n(rn), .clk_h(ck_ih), .h_v(to_ing), .h_cls(hcl),
        .h_d(hd), .h_crn(crn), .t_v(t_v), .t_d(t_d), .t_cr(tcr_l), .clk_i(ck_ic), .ck(ck), .o_v(ov), .o_we(owe), .o_addr(oa),
        .o_d(od), .o_cr(ocr), .i_rv(1'b0), .i_rd(256'd0), .host_ack_n(ack), .fault(hf));
    // two host-write stacks = the two svc halves (dsdv_sh_sd = dsfd_host_sd fork, HALF 1: route by the PC owner half; markers to both; MUT 6 = HALF 2)
    dsdv_sh_sd #(.NS(2), .KVS(2'b11), .ENG(-1), .STATIC(1), .HALF((MUT == 6) ? 2 : 1)) u_sd (.ck(ck), .rst_n(rn), .o_v(ov),
        .o_we(owe), .o_addr(oa), .o_d(od), .o_cr(ocr), .hw({s_hw_e, s_hw_w}), .hc({s_hc_e, s_hc_w}), .host_ack_n(ack),
        .fault(sf));
    always @(posedge ck or negedge rn) if (!rn) tcr_l <= 1'b0; else tcr_l <= t_v;
    // ---- status: regional controller fold (dsfd_ctrl_ctr st merge), svc fault, lane faults
    reg rg_up, rg_drop, rg_f, svc_f, lf_f;
    always @(posedge ck or negedge rn)
        if (!rn) begin rg_up <= 1'b0; rg_drop <= 1'b0; rg_f <= 1'b0; svc_f <= 1'b0; lf_f <= 1'b0; end
        else begin
            if (rg_q[0]) rg_up <= 1'b1;
            if (rg_up && !rg_q[0]) rg_drop <= 1'b1;
            if (rg_q[1]) rg_f <= 1'b1;
            if (jdw_q[1] | jde_q[1] | mf) svc_f <= 1'b1;
            if (lf_q[1] | lf_q[3]) lf_f <= 1'b1;
        end
    wire [3:0] wf = {rg_f, rg_drop, svc_f, vf_q};
    always @(posedge ck) t_host <= rn ? {1'b1, hf | sf | lf_f | sq_q[5] | (|wf), wf, sq_q, t_v, t_d} : 77'd0;
endmodule

// ---------------------------------------------------------------- L1: sequencer
module dsdv_sh_sq #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    // S face (L0)
    input  wire [V-1:0]  rn_i, output reg [V-1:0] rs_o,
    input  wire [35:0]   pw_i,
    input  wire [8:0]    pl_i,
    input  wire [193:0]  tw_i,
    input  wire [266:0]  cf_i,
    input  wire [52:0]   ks_i,
    output reg  [53:0]   kd_o,
    output wire [32:0]   j_o,
    input  wire [1:0]    jd_i,
    output reg  [5:0]    sq_o,
    output reg           vf_o,
    // N face (L2)
    output reg  [V-1:0]  rn_o, input wire [V-1:0] rs_i,
    output reg  [193:0]  tw_o,
    output reg  [266:0]  cf_o,
    output wire [84:0]   cn_o,            // V north command {v, cmd 84}
    output wire [84:0]   cs_o,            // V south command
    output wire [84:0]   cg_o,            // gunit job command
    input  wire [26:0]   dn_i,            // {gv, gtag 8, sv, stag 8, nv, ntag 8}
    input  wire          vf_i
);
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    always @(posedge ck) begin rn_o <= rn_i; rs_o <= rs_i; end
    // ---- pin flops
    reg [35:0] pw_q; reg [8:0] pl_q; reg [193:0] tw_q; reg [52:0] ks_q; reg [1:0] jd_q; reg [26:0] dn_q; reg vf_q; reg [266:0] cf_q;
    always @(posedge ck) begin
        pw_q <= {rn & pw_i[35], pw_i[34:0]}; pl_q <= {rn & pl_i[8], pl_i[7:0]}; tw_q <= {rn & tw_i[193], tw_i[192:0]};
        ks_q <= {rn & ks_i[52], ks_i[51:0]}; jd_q <= {2{rn}} & jd_i; vf_q <= vf_i; cf_q <= {rn & cf_i[266], cf_i[265:0]};
        dn_q <= {rn & dn_i[26], dn_i[25:18], rn & dn_i[17], dn_i[16:9], rn & dn_i[8], dn_i[7:0]};
    end
    reg [7:0] plen;
    always @(posedge ck or negedge rn) if (!rn) plen <= 8'd0; else if (pl_q[8]) plen <= pl_q[7:0];
    // ---- the calendar issuer (unchanged)
    localparam integer NE = 5;
    wire [NE-1:0] cv; wire [NE*84-1:0] cd; wire done, kdone, dslot, busy, fault; wire [3:0] code; wire [20:0] ktok;
    reg [NE-1:0] dv; reg [NE*8-1:0] dt;
    ot_dsdv_fixed_issue #(.NOPS(128), .NENG(NE), .STAGE(STAGE), .ENG_PRESENT(5'b10111)) u_iss (.clk(ck), .rst_n(rn),
        .pw_v(pw_q[35]), .pw_a(pw_q[34:28]), .pw_d(pw_q[27:0]), .prog_len(plen),
        .job_v(ks_q[52]), .job_user(ks_q[51:42]), .job_pos(ks_q[20:0]), .job_tok(ks_q[41:21]), .job_rdy(), .busy(busy),
        .job_done(done), .job_kdone(kdone), .done_slot(dslot), .kit_tok(ktok),
        .cmd_v(cv), .cmd_d(cd), .engine_available({NE{1'b1}}), .dn_v(dv), .dn_tag(dt),
        .fault(fault), .fault_code(code), .st_jobs(), .st_cmds(), .phase());
    // command faces: straight from the issuer's command registers (flop-last)
    assign cn_o = {cv[0], cd[0 +: 84]};
    assign cs_o = {cv[1], cd[84 +: 84]};
    assign cg_o = {cv[2], cd[168 +: 84]};
    wire [6:0] jop = (MUT == 2 && cv[4]) ? cd[4*84 +: 7] + 7'd1 : cd[4*84 +: 7];
    assign j_o = {cv[4], cd[4*84 + 7 +: 24], cd[4*84 + 83], jop};
    // ---- svc completion tags: posted jobs complete in order (the chain's folded done)
    reg [7:0] tq [0:7]; reg [2:0] tw_p, tr_p; reg [3:0] tn; reg l1f;
    always @(posedge ck or negedge rn)
        if (!rn) begin tw_p <= 3'd0; tr_p <= 3'd0; tn <= 4'd0; end
        else begin
            if (cv[4]) begin tq[tw_p] <= {cd[4*84 + 83], cd[4*84 +: 7]}; tw_p <= tw_p + 3'd1; end
            if (jd_q[0] && tn != 4'd0) tr_p <= tr_p + 3'd1;
            tn <= tn + (cv[4] ? 4'd1 : 4'd0) - ((jd_q[0] && tn != 4'd0) ? 4'd1 : 4'd0);
        end
    // ---- completions into the issuer (it checks each against its fixed done row)
    always @(*) begin
        dv = {NE{1'b0}}; dt = {NE*8{1'b0}};
        dv[0] = dn_q[8];  dt[0 +: 8] = dn_q[7:0];
        dv[1] = dn_q[17]; dt[8 +: 8] = dn_q[16:9];
        dv[2] = dn_q[26]; dt[16 +: 8] = dn_q[25:18];
        dv[4] = jd_q[0];  dt[32 +: 8] = tq[tr_p];
    end
    // ---- unit faults: tag queue over / underflow, template / calendar write while a job is held
    always @(posedge ck or negedge rn)
        if (!rn) l1f <= 1'b0;
        else if ((jd_q[0] && tn == 4'd0) || (cv[4] && tn == 4'd8) || (tw_q[193] && busy) || (pl_q[8] && busy) ||
                 (cf_q[266] && (busy || cf_q[265]))) l1f <= 1'b1;
    // ---- outputs
    always @(posedge ck) begin
        tw_o <= tw_q; cf_o <= cf_q;
        kd_o <= rn && kdone ? {1'b1, ktok, 32'd0} : 54'd0;
        sq_o <= {fault | l1f, (code != 4'd0) ? code : (l1f ? 4'd12 : 4'd0), busy};
        vf_o <= vf_q;
    end
endmodule

// ---------------------------------------------------------------- L2: middle leaf (V stop + CTL packer)
module dsdv_sh_vc #(parameter integer V = 276, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    // rung (vstop pins)
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_n,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_s,
    // S face (L1)
    input  wire [193:0]  tw_i,
    input  wire [84:0]   cn_i,
    input  wire [84:0]   cs_i,
    input  wire [266:0]  cf_i,
    input  wire [84:0]   cg_i,
    output reg  [26:0]   dn_o,
    output reg           vf_o,
    // gunit configuration / job port (p4i link col 4 -> col 3 gunit)
    output reg           cw_v,
    output reg  [9:0]    cw_a,
    output reg  [255:0]  cw_d
);
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // ---- pin flops
    reg [193:0] tw_q; reg [84:0] cn_q, cs_q;
    reg [266:0] cf_q; reg [84:0] cg_q;
    always @(posedge ck) begin tw_q <= {rn & tw_i[193], tw_i[192:0]}; cn_q <= {rn & cn_i[84], cn_i[83:0]};
        cs_q <= {rn & cs_i[84], cs_i[83:0]}; cf_q <= {rn & cf_i[266], cf_i[265:0]}; cg_q <= {rn & cg_i[84], cg_i[83:0]}; end
    // ---- template table (boot written; registered read): three 1R1W 128 x 256 SRAM macros, one per read port
    //      (N beat, S beat, gunit job), all written by the same boot word.  Same read timing as the former flop
    //      table (address from the pin flop, data after one edge), so cycle-exact; the 23.8k-flop clock root is gone.
    //      Writes are boot-only (a template write while a job is held is a fault), so no read/write collision.
    wire [255:0] rd_n, rd_s, rd_g;
    ot_sram_1r1w_128x256_m1_r2c2 u_ttn (.clk(ck), .r_ce_in(cn_q[84]), .r_addr_in(cn_q[13:7]), .rd_out(rd_n),
        .w_ce_in(tw_q[193]), .w_addr_in(tw_q[192:186]), .wd_in({70'd0, tw_q[185:0]}), .w_mask_in({256{1'b1}}),
        .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    ot_sram_1r1w_128x256_m1_r2c2 u_tts (.clk(ck), .r_ce_in(cs_q[84]), .r_addr_in(cs_q[13:7]), .rd_out(rd_s),
        .w_ce_in(tw_q[193]), .w_addr_in(tw_q[192:186]), .wd_in({70'd0, tw_q[185:0]}), .w_mask_in({256{1'b1}}),
        .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    ot_sram_1r1w_128x256_m1_r2c2 u_ttg (.clk(ck), .r_ce_in(cg_q[84]), .r_addr_in(cg_q[13:7]), .rd_out(rd_g),
        .w_ce_in(tw_q[193]), .w_addr_in(tw_q[192:186]), .wd_in({70'd0, tw_q[185:0]}), .w_mask_in({256{1'b1}}),
        .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    // ---- per direction: read stage, beat register
    // cmd 84 = {slot, user 10, pos 21, tok 21, arg 24, op 7}
    wire [41:0] rg_t = rd_g[41:0]; reg kg, vlg, bag; reg [7:0] tgg; reg [266:0] cf_d;
    wire [185:0] rn_t = rd_n[185:0], rs_t = rd_s[185:0];
    reg [51:0] cxn, cxs; reg [1:0] mdn, mds; reg vln, vls, ban, bas; reg [7:0] tgn, tgs;
    always @(posedge ck) begin
        kg <= cg_q[14]; tgg <= {cg_q[83], cg_q[6:0]};
        cf_d <= cf_q;
        cxn <= cn_q[82:31]; cxs <= cs_q[82:31];
        mdn <= cn_q[15:14]; mds <= cs_q[15:14];
        tgn <= {cn_q[83], cn_q[6:0]}; tgs <= {cs_q[83], cs_q[6:0]};
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin vln <= 1'b0; vls <= 1'b0; ban <= 1'b0; bas <= 1'b0; vlg <= 1'b0; bag <= 1'b0; end
        else begin
            vln <= cn_q[84]; vls <= cs_q[84]; vlg <= cg_q[84];
            bag <= cg_q[84] && cg_q[30:15] != 16'd0;
            ban <= cn_q[84] && (cn_q[30:16] != 15'd0 || cn_q[15:14] == 2'd3);
            bas <= cs_q[84] && (cs_q[30:16] != 15'd0 || cs_q[15:14] == 2'd3);
        end
    function automatic [V-1:0] beat(input [185:0] t, input [51:0] cx, input [1:0] md);
        reg [185:0] p;
        begin
            p = t;
            if (MUT != 1) begin
                if (md == 2'd1) p[26 + 108 +: 52] = cx;              // body[159:108] = {user, pos, tok}
                else if (md == 2'd2) p[26 + 139 +: 21] = cx[41:21];  // body[159:139] = pos
            end
            beat = {V{1'b0}}; beat[0] = 1'b1; beat[3:1] = 3'd0; beat[8:4] = 5'd0; beat[12:9] = 4'd4; beat[21 +: 186] = p;
        end
    endfunction
    reg [V-1:0] bn, bs; reg bnv, bsv; reg [26:0] dn_d; reg cwc;
    always @(posedge ck) begin bn <= beat(rn_t, cxn, mdn); bs <= beat(rs_t, cxs, mds);
        cw_a <= vlg ? {2'b10, 7'd0, kg} : cf_d[265:256];
        cw_d <= vlg ? {214'd0, rg_t} : cf_d[255:0];
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin bnv <= 1'b0; bsv <= 1'b0; dn_o <= 27'd0; dn_d <= 27'd0; cw_v <= 1'b0; cwc <= 1'b0; end
        else begin
            bnv <= vln; bsv <= vls;
            // cw: a calendar gunit job or a host config row (boot only; both in one edge = fault)
            cw_v <= vlg | cf_d[266];
            cwc <= vlg && cf_d[266];
            // completion = the beat posted to the stop (MUT 4: one edge late)
            dn_d <= {vlg, tgg, vls, tgs, vln, tgn};
            dn_o <= (MUT == 4) ? dn_d : {vlg, tgg, vls, tgs, vln, tgn};
        end
    // ---- the shared V-rung stop (unchanged)
    wire vsf;
    ot_dsdv_vstop #(.V(V)) u_vs (.clk(ck), .rst_n(rn), .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_n(vo_n),
        .vi_n(vi_n), .vo_s(vo_s), .dl_nv(), .dl_n(), .dl_sv(), .dl_s(), .in_nv(bnv), .in_n(bn), .in_sv(bsv), .in_s(bs),
        .ra_s(), .ra_n(), .dk_n(), .dk_s(), .fault(vsf));   // ra_* / dk_* = gunit tap observation ports: seqhost taps nothing
    reg arg_f;
    always @(posedge ck or negedge rn) if (!rn) arg_f <= 1'b0; else if (ban || bas || bag || cwc) arg_f <= 1'b1;
    always @(posedge ck) vf_o <= vsf | arg_f;
endmodule

// ---------------------------------------------------------------- the unit
module dsdv_seq_host #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,   // vstop straps (captured pins); seqhost: 0 / 0
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,      // rung S face (bk_sel)
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,      // rung N face (s_4N)
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,     // job broadcast to both halves / per-half done
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e, // per-half host writes / credits + acks
    input  wire [1:0]    st_rg_w, st_rg_e,                               // per-half region status (svc entry st_rg)
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d   // gunit cw port
);
    wire [V-1:0] n01, s10, n12, s21, n23, s32, n34, s43;
    wire [35:0] pw01; wire [8:0] pl01; wire [193:0] tw01, tw12; wire [52:0] ks01; wire [53:0] kd10; wire [32:0] j10;
    wire [1:0] jd01; wire [5:0] sq10; wire vf10, vf21; wire [84:0] cn12, cs12, cg12; wire [26:0] dn21; wire [266:0] cf01, cf12;
    dsdv_sh_lk #(.V(V), .MUT(MUT)) u_l0 (.ck(ck), .ck_ih(ck), .ck_ic(ck), .rst_n(rst_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
        .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .vi_s(vi_s), .vo_s(vo_s),
        .rn_o(n01), .rs_i(s10), .pw_o(pw01), .pl_o(pl01), .tw_o(tw01), .cf_o(cf01), .ks_o(ks01), .kd_i(kd10), .j_i(j10), .jd_o(jd01),
        .sq_i(sq10), .vf_i(vf10));
    dsdv_sh_sq #(.V(V), .STAGE(STAGE), .MUT(MUT)) u_l1 (.ck(ck), .rst_n(rst_n), .rn_i(n01), .rs_o(s10), .pw_i(pw01),
        .pl_i(pl01), .tw_i(tw01), .cf_i(cf01), .ks_i(ks01), .kd_o(kd10), .j_o(j10), .jd_i(jd01), .sq_o(sq10), .vf_o(vf10),
        .rn_o(n12), .rs_i(s21), .tw_o(tw12), .cf_o(cf12), .cn_o(cn12), .cs_o(cs12), .cg_o(cg12), .dn_i(dn21), .vf_i(vf21));
    dsdv_sh_vc #(.V(V), .MUT(MUT)) u_l2 (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .vi_s(n12), .vo_n(n23),
        .vi_n(s32), .vo_s(s21), .tw_i(tw12), .cn_i(cn12), .cs_i(cs12), .cf_i(cf12), .cg_i(cg12), .dn_o(dn21), .vf_o(vf21),
        .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    dsdv_sh_ft #(.V(V)) u_l3 (.ck(ck), .ni(n23), .no(n34), .si(s43), .so(s32));
    generate if (MUT == 3) begin : g_mut3
        assign vo_n = n34; assign s43 = vi_n;                   // negative control: L4 hop missing
    end else begin : g_l4
        dsdv_sh_ft #(.V(V)) u_l4 (.ck(ck), .ni(n34), .no(vo_n), .si(vi_n), .so(s43));
    end endgenerate
endmodule
