`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_engram_c (s81-svceng-1011, 2026-10-11): the Engram slab master of the S81 layer1e die (eng_SE), engine 10 of
// ADAPTER_CONTRACT_1011.  = the pinned command endpoint ot_s81_slab_ep (ot_s81_engine_adapter QD 8, done-credit)
//   + the closed lookup element dsfd_engram_lkp (hash, address, HBM row requests, CRC, row beats)
//   + the closed row sink dsfd_engram_sink (24 columns x 4 ranks -> BF16 rows, slot ready / poison)
//   + the prefetch buffer ot_dsrom_engram_prefetch (8 slots, the existing SECDED words; no new ECC)
// The die buses are ENG_BUSES of tools/dsrom_s81_fulldie.py (names below = the generator's port names).
//
// ENGINE SEMANTICS (one job = one token's Engram lookup on this rank):
//   start = the window: a lead-flit window (f_win) is HELD in a 2-entry queue (the collective's 2 window credits) and
//           released to the lookup only under a queued eng descriptor, in order (one window per descriptor).  A window
//           never reaches the lookup without a command (a dropped command holds it: no rows, no done).
//   done  = the job's prefetch slot became READY on this rank's sink (all 24 rows of the 4 ranks written and their
//           24 statuses counted; a poisoned slot completes too and carries perr on t_vm).  Slot s = n mod 8 of window
//           n; the done of window n is the (n / 8 + 1)-th rising edge of rdy[s] (rdy drops on every release), so a
//           slot still READY from window n - 8 can never complete window n.
//   descriptor arg (compiler schema "eng_job"): arg[15:0] = window sequence number n (mod 2^16), arg[23:16] = 0.
//           A released window whose n differs, or a reserved bit set, is a WRONG DESCRIPTOR: sticky fault (c_st[0]).
// The consumer (VM) reads the slot over f_vm (rd_v / rd_addr {slot, column, beat}, out on t_vm 2 cycles later) after
// the done and releases it (rel_v / rel_slot); the lookup's credit is the 4 ranks' releases (f_win rel, carried by
// the collective ctrl lane).
// HBM: the lookup's request / response credit pair (hq / hr) is the backend port pair t_hq / f_hr (35 / 265 b), the
// SE half of ot_dsrom_engram_hbm_backend binds there (rowstripe read service + boot path; the SW half via svc_SW).
// MUT (negative controls): 5 early done (done when the window is released to the lookup); 6 done on the rdy LEVEL
// (equivalent in every legal flow: slot n - 8 is released before window n is accepted -- kept as a design note).  EPMUT -> ot_s81_slab_ep (2 tag / 3 early start / 4
// dropped done).
// ---------------------------------------------------------------------------------------------------------------
import ot_hdc_engram_tables_shipped_pkg::*;

module dsfd_engram_c #(
    parameter integer MUT = 0,
    parameter integer EPMUT = 0,
    parameter integer PIPE = 0,
    parameter integer SINK_PIN = 1,
    parameter integer BE = 1,              // 1: the stack HBM client (SE half + boot + aperture + router); 0: v1 (t_hq / f_hr = the lookup's port)
    parameter integer EXPECT_SECTORS = 1   // Engram boot image sectors of this die (both stacks; boot dispatcher)
) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,                // async die reset (active low), synchronised here
    // engine 10 die pins (dsfd_stage_seq c<10> / d<10> / s<10>, stream clock)
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st,
    // boot CSR straps (host)
    input  wire [2:0]    f_cfg,              // {cfg_rank 2, cfg_layer}
    // lead-flit window + rank retirements (collective t_eng): {win_v, win_ids 4 x 17, rel 4}
    input  wire [72:0]   f_win,
    output reg  [0:0]    t_collective,       // win_cred
    // all-gather out (to the collective): {fault, st_bad, st_slot 3, st_v, d 264, slot 3, beat 3, col 5, o_v}
    output wire [281:0]  t_ag,
    input  wire [0:0]    f_agc,              // o_cred
    // all-gather in (4 ranks): {st_bad 4, st_slot 12, st_v 4, d 1056, slot 12, beat 12, col 20, in_v 4}
    input  wire [1123:0] f_ai,
    output wire [3:0]    t_air,              // in_r
    // VM: prefetch rows {perr 8, rdy 8, fault, ue, ce, data 512, out_v}; requests {rel_slot 3, rel_v, rd_addr 11, rd_v}
    output wire [531:0]  t_vm,
    input  wire [15:0]   f_vm,
    // HBM backend port pair: {hq_tag 3, hq_atom 31, hq_v} / {hr_d 256, hr_idx 4, hr_tag 3, hr_v, hq_cred}
    output wire [34:0]   t_hq,
    input  wire [264:0]  f_hr,
    // BE = 1: t_hq / f_hr = the SW half's read pair (svc_SW feq / ter); t_eb / f_eb = its boot pair
    //   t_eb {d 256, tag 3, atom 29, type 2, v}: type 1 boot write, 2 aperture CSR word, 3 BOOT READY;  f_eb {tag 3, v}
    output wire [290:0]  t_eb,
    input  wire [3:0]    f_eb,
    // host Engram sectors (dsfd_host_s hw<SE>): {cls 2, we, addr 32, d 256, v};  hc {ack 8, cr}
    input  wire [291:0]  hw,
    output reg  [8:0]    hc,
    // ctrl_SE per-PC faces: rq 32 x 341, wd 32, rd {rv 32, r_beat 32 x 4, r_tag 32 x 17, r_data 32 x 256}
    output wire [32*341-1:0] rq,
    input  wire [31:0]   wd,
    input  wire [8895:0] rd
);
    localparam integer NSLOT = 8, SLW = 3, IDW = ENG_ID_W;
    reg [1:0] rs_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];

    wire m_cred, m_hrv; wire [2:0] m_hrt; wire [3:0] m_hri; wire [255:0] m_hrd; wire pf_fault_be;   // BE router / merge
    // ---------------- command endpoint
    wire j_v, j_new; wire [83:0] j_d, j_new_d; wire ep_fault;
    reg  j_done, jf;
    ot_s81_slab_ep #(.QD(8), .JQ(8), .MUT(EPMUT)) u_ep (.c_clk(ck[0]), .c_rst_n(rst[0]), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck[0]), .e_rst_n(rn), .j_v(j_v), .j_d(j_d), .j_new(j_new), .j_new_d(j_new_d),
        .j_present(1'b1), .j_done(j_done), .slab_fault(jf | pf_fault | pf_fault_be), .ep_fault(ep_fault));
    // (the lookup's sticky fault is a DATA status -- CRC / address / alignment of a row -- carried on t_ag to the
    //  collective and per slot as perr on t_vm; it is not an engine-protocol fault)

    // ---------------- window hold queue (the collective holds 2 window credits)
    reg wv_q; reg [4*IDW-1:0] wid_q; reg [3:0] rel_q;
    always @(posedge ck[0] or negedge rn) if (!rn) begin wv_q <= 1'b0; rel_q <= 4'd0; end
                                         else begin wv_q <= f_win[72]; rel_q <= f_win[3:0]; end
    always @(posedge ck[0]) wid_q <= f_win[71:4];
    reg [4*IDW-1:0] hq_w [0:1]; reg hh, ht; reg [1:0] hn;
    // descriptors not yet matched to a window (issue side runs ahead of the done side)
    reg [16:0] ia [0:7]; reg [2:0] iw, ir; reg [3:0] in_;
    reg [15:0] wn;                         // windows released to the lookup
    reg [15:0] dn;                         // jobs done
    reg [1:0]  lc;                         // credits toward the lookup's 2-entry window FIFO
    wire       lk_wcred;
    wire       be_rdy;                     // BE: the Engram tables are booted (both halves READY)
    wire       rel_w = (hn != 2'd0) && (in_ != 4'd0) && (lc != 2'd0) && (BE == 0 || be_rdy);
    wire       lk_wv = rel_w;
    wire [4*IDW-1:0] lk_wid = hq_w[hh];
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin
            hh <= 1'b0; ht <= 1'b0; hn <= 2'd0; iw <= 0; ir <= 0; in_ <= 0; wn <= 0; lc <= 2'd2; jf <= 1'b0;
            t_collective <= 1'b0;
        end else begin
            if (wv_q) begin hq_w[ht] <= wid_q; ht <= ~ht; if (hn == 2'd2 && !rel_w) jf <= 1'b1; end
            if (rel_w) hh <= ~hh;
            hn <= hn + wv_q - rel_w;
            t_collective <= rel_w;          // the window credit returns when the window leaves the hold queue
            if (j_new) begin ia[iw] <= {(j_new_d[30:23] != 8'd0), j_new_d[22:7]}; iw <= iw + 1'b1; end
            if (rel_w && in_ != 4'd0) begin
                if (ia[ir][16] || ia[ir][15:0] != wn) jf <= 1'b1;      // wrong descriptor
                ir <= ir + 1'b1;
            end
            in_ <= in_ + j_new - (rel_w && in_ != 4'd0);
            if (rel_w) wn <= wn + 1'b1;
            lc <= lc - rel_w + lk_wcred;
        end

    // ---------------- lookup element (closed dsfd_engram_lkp)
    wire lk_fault, lk_ov, lk_stv, lk_stb, lk_hqv; wire [4:0] lk_oc; wire [2:0] lk_ob, lk_os, lk_sts, lk_hqt;
    wire [263:0] lk_od; wire [30:0] lk_hqa;
    dsfd_engram_lkp #(.ROWSTRIPE(BE), .PIPE(PIPE), .NSLOT(NSLOT), .HQ_CRED(8), .O_CRED(16), .SLW(SLW)) u_lkp (
        .ck(ck[0]), .rst_n(rn), .cfg_layer(f_cfg[0]), .cfg_rank(f_cfg[2:1]),
        .win_v(lk_wv), .win_ids(lk_wid), .win_cred(lk_wcred), .rel(rel_q),
        .hq_v(lk_hqv), .hq_atom(lk_hqa), .hq_tag(lk_hqt), .hq_cred(BE ? m_cred : f_hr[0]),
        .hr_v(BE ? m_hrv : f_hr[1]), .hr_tag(BE ? m_hrt : f_hr[4:2]), .hr_idx(BE ? m_hri : f_hr[8:5]), .hr_d(BE ? m_hrd : f_hr[264:9]),
        .o_v(lk_ov), .o_col(lk_oc), .o_beat(lk_ob), .o_slot(lk_os), .o_d(lk_od), .o_cred(f_agc[0]),
        .st_v(lk_stv), .st_slot(lk_sts), .st_bad(lk_stb), .fault(lk_fault));
    assign t_hq = BE ? {lk_hqt, lk_hqa, lk_hqv && !lk_hqa[0]} : {lk_hqt, lk_hqa, lk_hqv};   // BE: even rows = SW
    assign t_ag = {lk_fault, lk_stb, lk_sts, lk_stv, lk_od, lk_os, lk_ob, lk_oc, lk_ov};


    // =============================================================================================================
    // BE = 1: the stack HBM client of the Engram tables (owner GO 2026-10-11).  Row parity = stack (rowstripe
    // req_pc = (row % 2) * 32 + ...; the lookup's ROWSTRIPE atom is 9 x row, so row parity = atom[0]).
    //   router   lookup row request -> SE half (odd rows, local) or t_hq (even rows -> svc_SW's half); the 8 lookup
    //            credits are shared: each half's FIFO is 8 deep, the credit returns of both are merged one a cycle.
    //   merge    the halves' row atoms (pure pushes: each half reserves its row buffers before it issues) into the
    //            lookup's response port: local first, the SW stream through a 64-entry FIFO (<= 6 rows x 9 atoms).
    //   boot     host Engram sectors (hw, class 2) -> ot_dsrom_engram_boot_dispatch (ROWSTRIPE; both stacks, one
    //            sequential image, END marker fingerprint) -> SE writes to the local half, SW writes on t_eb; the true
    //            write completions of both stacks come back to the dispatcher (credits) and to the host as acks.
    //            Aperture CSR words (marker address, d[65:64] = 3, d[255] = 1; d[254:253] kind 1 stack / 2 pc / 3
    //            commit, fields per ot_s81_eng_half) go to both halves, credit returned at once.  When the dispatcher
    //            is loaded, BOOT READY goes to both halves; windows are released to the lookup only after it.
    // =============================================================================================================
    generate if (BE != 0) begin : g_be
        // ---- host face
        reg hv_q; reg [291:1] hd_q;
        always @(posedge ck[0] or negedge rn) if (!rn) hv_q <= 1'b0; else hv_q <= hw[0];
        always @(posedge ck[0]) hd_q <= hw[291:1];
        wire [255:0] h_d = hd_q[256:1]; wire [31:0] h_a = hd_q[288:257]; wire h_we = hd_q[289]; wire [1:0] h_cls = hd_q[291:290];
        wire h_mark = h_a == 32'hffffffff;
        wire h_csr  = hv_q && h_mark && h_d[65:64] == 2'd3 && h_d[255];
        wire h_boot = hv_q && !h_csr;
        reg  hbad;
        // ---- boot dispatcher (both stacks)
        wire dcred, dready, dfault; wire [1:0] wv; wire [28:0] wa; wire [2:0] wt; wire [255:0] wdd;
        wire sw_dv, se_dv; wire [2:0] sw_dt, se_dt;
        ot_dsrom_engram_boot_dispatch #(.ROWSTRIPE(1), .EXPECT_SECTORS(EXPECT_SECTORS)) u_bd (.ck(ck[0]), .rst_n(rn),
            .i_v(h_boot), .i_addr(h_a), .i_d(h_d), .i_cred(dcred), .w_v(wv), .w_atom(wa), .w_tag(wt), .w_d(wdd),
            .done_v({se_dv, sw_dv}), .done_tag({se_dt, sw_dt}), .ready(dready), .fault(dfault));
        reg rsent; reg csr_q; reg [255:0] csr_d;
        // ---- SW pair (t_eb / f_eb): boot writes, CSR words, READY
        reg [290:0] eb_q; reg ebv;
        always @(posedge ck[0] or negedge rn)
            if (!rn) begin ebv <= 1'b0; rsent <= 1'b0; csr_q <= 1'b0; hbad <= 1'b0; hc <= 9'd0; end
            else begin
                csr_q <= h_csr;
                ebv <= wv[0] || h_csr || (dready && !rsent);
                if (dready) rsent <= 1'b1;
                if (hv_q && (h_cls != 2'd2 || !h_we)) hbad <= 1'b1;
                if ((wv[0] && h_csr) || (wv[1] && csr_q)) hbad <= 1'b1;   // aperture CSR words precede the image
                hc <= {8'(sw_dv) + 8'(se_dv) + 8'(h_csr), dcred || h_csr};   // acks: true write completions (+ CSR words)
            end
        always @(posedge ck[0])
            eb_q <= wv[0] ? {wdd, wt, wa, 2'd1} : h_csr ? {h_d, 3'd0, 29'd0, 2'd2} : {256'd0, 3'd0, 29'd0, 2'd3};
        assign t_eb = {eb_q, ebv};
        reg fv_q; reg [2:0] ft_q;
        always @(posedge ck[0] or negedge rn) if (!rn) fv_q <= 1'b0; else fv_q <= f_eb[0];
        always @(posedge ck[0]) ft_q <= f_eb[3:1];
        assign sw_dv = fv_q; assign sw_dt = ft_q;
        // ---- SE half (local)
        wire lq = lk_hqv && lk_hqa[0];
        wire s_cred, s_hrv, h_rdy, h_fault; wire [2:0] s_hrt; wire [3:0] s_hri; wire [255:0] s_hrd;
        ot_s81_eng_half #(.STACK(1)) u_se (.ck(ck[0]), .rst_n(rn),
            .b_v(wv[1] || csr_q || (dready && !rsent)), .b_type(wv[1] ? 2'd1 : csr_q ? 2'd2 : 2'd3),
            .b_atom(wa), .b_tag(wt), .b_d(wv[1] ? wdd : csr_d), .bd_v(se_dv), .bd_tag(se_dt),
            .hq_v(lq), .hq_atom(lk_hqa), .hq_tag(lk_hqt), .hq_cred(s_cred),
            .hr_v(s_hrv), .hr_tag(s_hrt), .hr_idx(s_hri), .hr_d(s_hrd),
            .rq(rq), .wd(wd), .rd(rd), .ready(h_rdy), .fault(h_fault));
        always @(posedge ck[0]) csr_d <= h_d;
        // ---- SW responses (pin flops) + credit merge
        reg rv_q, rc_q; reg [262:0] rh_q;
        always @(posedge ck[0] or negedge rn) if (!rn) begin rv_q <= 1'b0; rc_q <= 1'b0; end
                                             else begin rv_q <= f_hr[1]; rc_q <= f_hr[0]; end
        always @(posedge ck[0]) rh_q <= f_hr[264:2];
        reg [3:0] cpend; reg mcred;
        always @(posedge ck[0] or negedge rn)
            if (!rn) begin cpend <= 0; mcred <= 1'b0; end
            else begin
                mcred <= (cpend + s_cred + rc_q) != 0;
                cpend <= cpend + s_cred + rc_q - (((cpend + s_cred + rc_q) != 0) ? 1'b1 : 1'b0);
            end
        assign m_cred = mcred;
        // ---- response merge: local first, SW through a FIFO
        reg [262:0] rf [0:63]; reg [5:0] rw, rr; reg [6:0] rn_;
        wire take_sw = !s_hrv && rn_ != 0;
        always @(posedge ck[0] or negedge rn)
            if (!rn) begin rw <= 0; rr <= 0; rn_ <= 0; end
            else begin
                if (rv_q) begin rf[rw] <= rh_q; rw <= rw + 1'b1; end
                if (take_sw) rr <= rr + 1'b1;
                rn_ <= rn_ + rv_q - take_sw;
            end
        assign m_hrv = s_hrv || take_sw;
        assign {m_hrd, m_hri, m_hrt} = s_hrv ? {s_hrd, s_hri, s_hrt} : rf[rr];
        assign be_rdy = rsent && h_rdy;
        assign pf_fault_be = hbad | dfault | h_fault | (rn_ == 7'd64 && rv_q && !take_sw);
    end else begin : g_v1
        assign m_cred = 1'b0; assign m_hrv = 1'b0; assign m_hrt = 0; assign m_hri = 0; assign m_hrd = 0;
        assign be_rdy = 1'b1; assign pf_fault_be = 1'b0;
        assign t_eb = 291'd0; assign rq = {32*341{1'b0}};
        always @(posedge ck[0]) hc <= 9'd0;
    end endgenerate

    // ---------------- row sink (closed dsfd_engram_sink) -> prefetch buffer
    wire s_we; wire [10:0] s_wa; wire [511:0] s_wd; wire [7:0] s_rdy, s_perr;
    reg  vrel_q; reg [2:0] vrels_q; reg vrd_q; reg [10:0] vra_q;
    always @(posedge ck[0] or negedge rn) if (!rn) begin vrel_q <= 1'b0; vrd_q <= 1'b0; end
                                         else begin vrel_q <= f_vm[12]; vrd_q <= f_vm[0]; end
    always @(posedge ck[0]) begin vrels_q <= f_vm[15:13]; vra_q <= f_vm[11:1]; end   // f_vm = {rel_slot 3, rel_v, rd_addr 11, rd_v}
    dsfd_engram_sink #(.PIN_CAPTURE(SINK_PIN), .NSLOT(NSLOT), .SLW(SLW)) u_sink (
        .ck(ck[0]), .rst_n(rn), .in_v(f_ai[3:0]), .in_r(t_air), .in_col(f_ai[23:4]), .in_beat(f_ai[35:24]),
        .in_slot(f_ai[47:36]), .in_d(f_ai[1103:48]), .st_v(f_ai[1107:1104]), .st_slot(f_ai[1119:1108]),
        .st_bad(f_ai[1123:1120]), .wr_en(s_we), .wr_addr(s_wa), .wr_data(s_wd), .rdy(s_rdy), .perr(s_perr),
        .rel_v(vrel_q), .rel_slot(vrels_q));
    wire pf_v, pf_ce, pf_ue, pf_fault; wire [511:0] pf_d; wire pf_wp;
    ot_dsrom_engram_prefetch u_pf (.ck(ck[0]), .rst_n(rn), .wr_v(s_we), .wr_addr(s_wa), .wr_data(s_wd), .wr_pending(pf_wp),
        .rd_v(vrd_q), .rd_addr(vra_q), .out_v(pf_v), .out_data(pf_d), .out_ce(pf_ce), .out_ue(pf_ue), .fault(pf_fault));
    // rdy is published two cycles after the sink's (the slot's rows are in the SRAM; a release drops it at once)
    // (the sink's rdy and its last wr_en leave the same register stage; the prefetch commits the write one cycle later)
    reg [7:0] rdy_1, rdy_p, perr_1, perr_p;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin rdy_1 <= 8'd0; rdy_p <= 8'd0; perr_1 <= 8'd0; perr_p <= 8'd0; end
        else begin rdy_1 <= s_rdy; rdy_p <= rdy_1 & s_rdy; perr_1 <= s_perr; perr_p <= perr_1; end
    assign t_vm = {perr_p, rdy_p, pf_fault, pf_ue, pf_ce, pf_d, pf_v};

    // ---------------- done side: the (n / 8 + 1)-th rising edge of rdy[n mod 8]
    reg [7:0] rdy_d; reg [12:0] rise [0:7]; integer s;
    wire [2:0]  dslot = dn[2:0];
    wire [12:0] depo  = dn[15:3] + 1'b1;
    wire        dhit  = (MUT == 6) ? rdy_p[dslot] : (rise[dslot] == depo);
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin rdy_d <= 8'd0; dn <= 0; j_done <= 1'b0; for (s = 0; s < 8; s = s + 1) rise[s] <= 13'd0; end
        else begin
            rdy_d <= rdy_p;
            for (s = 0; s < 8; s = s + 1) if (rdy_p[s] && !rdy_d[s]) rise[s] <= rise[s] + 1'b1;
            j_done <= 1'b0;
            if (j_v && !j_done && dn != wn && (MUT == 5 ? 1'b1 : dhit)) begin j_done <= 1'b1; dn <= dn + 1'b1; end
        end
endmodule
