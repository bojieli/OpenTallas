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
    parameter integer SINK_PIN = 1
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
    input  wire [264:0]  f_hr
);
    localparam integer NSLOT = 8, SLW = 3, IDW = ENG_ID_W;
    reg [1:0] rs_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];

    // ---------------- command endpoint
    wire j_v, j_new; wire [83:0] j_d, j_new_d; wire ep_fault;
    reg  j_done, jf;
    ot_s81_slab_ep #(.QD(8), .JQ(8), .MUT(EPMUT)) u_ep (.c_clk(ck[0]), .c_rst_n(rst[0]), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck[0]), .e_rst_n(rn), .j_v(j_v), .j_d(j_d), .j_new(j_new), .j_new_d(j_new_d),
        .j_present(1'b1), .j_done(j_done), .slab_fault(jf | pf_fault), .ep_fault(ep_fault));
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
    wire       rel_w = (hn != 2'd0) && (in_ != 4'd0) && (lc != 2'd0);
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
    dsfd_engram_lkp #(.PIPE(PIPE), .NSLOT(NSLOT), .HQ_CRED(8), .O_CRED(16), .SLW(SLW)) u_lkp (
        .ck(ck[0]), .rst_n(rn), .cfg_layer(f_cfg[0]), .cfg_rank(f_cfg[2:1]),
        .win_v(lk_wv), .win_ids(lk_wid), .win_cred(lk_wcred), .rel(rel_q),
        .hq_v(lk_hqv), .hq_atom(lk_hqa), .hq_tag(lk_hqt), .hq_cred(f_hr[0]),
        .hr_v(f_hr[1]), .hr_tag(f_hr[4:2]), .hr_idx(f_hr[8:5]), .hr_d(f_hr[264:9]),
        .o_v(lk_ov), .o_col(lk_oc), .o_beat(lk_ob), .o_slot(lk_os), .o_d(lk_od), .o_cred(f_agc[0]),
        .st_v(lk_stv), .st_slot(lk_sts), .st_bad(lk_stb), .fault(lk_fault));
    assign t_hq = {lk_hqt, lk_hqa, lk_hqv};
    assign t_ag = {lk_fault, lk_stb, lk_sts, lk_stv, lk_od, lk_os, lk_ob, lk_oc, lk_ov};

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
