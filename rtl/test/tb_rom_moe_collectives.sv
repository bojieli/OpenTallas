`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Multi-package bench of the MoE dispatch / combine engines (Verilator).
//
// Five packages of the reduced DeepSeek-V4.1 array (dim 160, 12 routed
// experts, top-6, one shared expert), connected by ot_rom_pkg_link instances:
//
//   package 0 (home): router output -> ot_hdc_actquant -> ot_rom_moe_dispatch
//                     -> fabric -> 4 down links;  4 up links -> merge ->
//                     ot_rom_moe_combine;  the shared expert lives here, on
//                     ot_rom_moe_expert_port SELF=0, reached without a link;
//   packages 1..4:    ot_rom_moe_expert_port behind one down and one up link,
//                     routed expert e on package 1 + (e mod 4).
//
// The "fabric" is this bench's own: a multicast demultiplexer (a flit moves
// when every package in its dst_mask can take it) and a packet-atomic
// round-robin merge; the RTL fabric router is not used.  The expert COMPUTE
// is a behavioural model: it checks that every received activation, expert
// id, routing weight and rank equals the golden's, then returns the golden's
// expert output after a random latency and in a random order, so results
// reach the combine out of order.  The combine's BF16 output is checked
// against tools/hdc_golden_v41's MoE output for every chunk of every token.
//
// Vectors (written by tools/rtl_rom_collectives_campaign.py) under +VEC=dir:
//   x.mem     5 blocks x 32 binary32 per token (the MoE input, BF16 values)
//   desc.mem  one descriptor per token: six (id, weight) items, router order
//   act.mem   3 flits per token: the golden's quant_fp8 codes and exponents
//   out.mem   7 ranks x 5 flits per token: each expert's golden output, BF16
//   meta.mem  7 per token: {id, weight} at each rank
//   moe.mem   5 flits per token: the golden's MoE output, BF16
// Plusargs: +N tokens, +SEED, +BP back-pressure percent, +ELAT maximum expert
// latency, +GAP producer gap percent, +SERIAL one token in flight.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module tb_rom_moe_collectives #(
    parameter integer MCAST   = 1,
    parameter integer TAGS    = 8,
    parameter integer MB      = 4,
    parameter integer CREDITS = 128,
    parameter integer CH      = 60
) (
    input wire clk
);
    localparam integer FW = 512, NP = 5, ACT = 3, VF = 5, NB = 5, NR = 7, MAXT = 4096, J = 64;
    localparam [51:0] PLACE = 52'h0_4321_4321_4321;

    reg [3:0] rcnt = 4'd0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (rcnt != 4'hF) rcnt <= rcnt + 4'd1;
    reg [63:0] now = 64'd0;
    always @(posedge clk) now <= now + 64'd1;

    function [31:0] xs(input [31:0] s);            // xorshift32
        reg [31:0] v;
        begin v = s ^ (s << 13); v = v ^ (v >> 17); xs = v ^ (v << 5); end
    endfunction

    // -- vectors ----------------------------------------------------------------------------
    reg [1023:0] vx   [0:MAXT*NB-1];
    reg [FW-1:0] vdesc[0:MAXT-1];
    reg [FW-1:0] vact [0:MAXT*ACT-1];
    reg [FW-1:0] vout [0:MAXT*NR*VF-1];
    reg [63:0]   vmeta[0:MAXT*NR-1];
    reg [FW-1:0] vmoe [0:MAXT*VF-1];
    string dir;
    integer N, SEED, BP, ELAT, GAP, SERIAL;
    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("N=%d", N)) N = 16;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("BP=%d", BP)) BP = 0;
        if (!$value$plusargs("ELAT=%d", ELAT)) ELAT = 0;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("SERIAL=%d", SERIAL)) SERIAL = 0;
        $readmemh({dir, "/x.mem"}, vx);
        $readmemh({dir, "/desc.mem"}, vdesc);
        $readmemh({dir, "/act.mem"}, vact);
        $readmemh({dir, "/out.mem"}, vout);
        $readmemh({dir, "/meta.mem"}, vmeta);
        $readmemh({dir, "/moe.mem"}, vmoe);
    end

    // -- home: tag pool, activation quantiser, record assembly ------------------------------------
    reg  [TAGS-1:0] tfree;
    reg  [31:0]     tagmap [0:TAGS-1];
    reg  [63:0]     t_issue [0:TAGS-1];
    integer n_issue = 0, fb = 0, n_feed = 0, t_feed = 0, batch_n = 0;
    reg  feed_eob = 1'b0;
    reg  [31:0] r_prod = 32'h1234_5678;
    // actquant
    reg          aq_v;
    reg [1023:0] aq_x;
    wire         aq_vo, aq_fault;
    wire [255:0] aq_q;
    wire signed [9:0] aq_e;
    wire [511:0] aq_y;
    ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_n), .v(aq_v), .fp4(1'b0), .x(aq_x),
                          .vo(aq_vo), .q(aq_q), .e(aq_e), .y(aq_y), .fault(aq_fault));
    // tokens whose blocks are in the quantiser, in order
    reg [31:0] pq_n [0:15]; reg [7:0] pq_t [0:15]; reg pq_eob [0:15];
    integer pq_w = 0, pq_r = 0, ob = 0;
    reg [1535:0] pay;
    // the dispatch input queue, in flits
    reg [FW:0] iq [0:255];
    reg [31:0] iq_w = 0, iq_r = 0;
    integer aq_errors = 0, aq_faults = 0;
    integer k, p, c, i;
    reg [7:0] pick_t;
    reg       pick_ok;
    reg [FW-1:0] d;
    integer done_n = 0;
    always @* begin
        pick_ok = 1'b0; pick_t = 8'd0;
        for (k = TAGS - 1; k >= 0; k = k - 1) if (tfree[k]) begin pick_ok = 1'b1; pick_t = k; end
    end
    wire cmb_free_v;
    wire [7:0] cmb_free_t;
    always @(posedge clk) begin
        if (!rst_n) begin
            tfree <= {TAGS{1'b1}}; aq_v <= 1'b0; r_prod <= 32'h1234_5678 ^ SEED;
        end else begin
            r_prod <= xs(r_prod);
            aq_v <= 1'b0;
            if (fb != 0) begin                             // feeding the blocks of token n_feed
                aq_v <= 1'b1; aq_x <= vx[n_feed * NB + (NB - fb)]; fb = fb - 1;
            end else if (n_issue < N && pick_ok && (r_prod % 100) >= GAP
                         && (SERIAL == 0 || tfree == {TAGS{1'b1}}) && (iq_w - iq_r) < 200) begin
                tagmap[pick_t] <= n_issue;
                n_feed = n_issue; t_feed = pick_t;
                batch_n = batch_n + 1;
                // close the micro-batch when full, when no other tag is free, or at the end
                feed_eob = (batch_n == MB) || ((tfree & ~(1 << pick_t)) == 0) || (n_issue == N - 1) || SERIAL != 0;
                if (feed_eob) batch_n = 0;
                pq_n[pq_w % 16] <= n_issue; pq_t[pq_w % 16] <= pick_t; pq_eob[pq_w % 16] <= feed_eob;
                pq_w = pq_w + 1;
                aq_v <= 1'b1; aq_x <= vx[n_issue * NB]; fb = NB - 1;
                n_issue = n_issue + 1;
                tfree[pick_t] <= 1'b0;
            end
            if (cmb_free_v) tfree[cmb_free_t] <= 1'b1;
            // quantiser output: assemble codes, then exponents after the last code
            if (aq_vo) begin
                if (aq_fault) aq_faults = aq_faults + 1;
                pay[256 * ob +: 256] = aq_q;
                pay[8 * (32 * NB + ob) +: 8] = aq_e[7:0];
                if (aq_e > 127 || aq_e < -128) aq_faults = aq_faults + 1;
                ob = ob + 1;
                if (ob == NB) begin
                    ob = 0;
                    for (k = 32 * NB + NB; k < 192; k = k + 1) pay[8 * k +: 8] = 8'd0;
                    d = vdesc[pq_n[pq_r % 16]];
                    d[H_TAG +: 8] = pq_t[pq_r % 16];
                    d[H_EOB] = pq_eob[pq_r % 16];
                    iq[iq_w % 256] = {1'b0, d};
                    for (k = 0; k < ACT; k = k + 1) begin
                        iq[(iq_w + 1 + k) % 256] = {k == ACT - 1, pay[FW * k +: FW]};
                        if (pay[FW * k +: FW] !== vact[pq_n[pq_r % 16] * ACT + k]) aq_errors = aq_errors + 1;
                    end
                    iq_w <= iq_w + 1 + ACT;
                    pq_r = pq_r + 1;
                end
            end
        end
    end

    // -- dispatch ----------------------------------------------------------------------------------
    wire          dsp_in_valid = rst_n && (iq_w != iq_r) && ((r_prod >> 8) % 100 >= GAP);
    wire          dsp_in_ready;
    wire [FW-1:0] dsp_out_data;
    wire          dsp_out_valid, dsp_out_last;
    wire          dsp_out_ready;
    wire [31:0]   dsp_tokens, dsp_records, dsp_flits;
    wire          dsp_fault;
    ot_rom_moe_dispatch #(.FLIT_W(FW), .NPKG(NP), .SELF(0), .N_EXP(12), .ACT_FLITS(ACT), .MCAST(MCAST),
                          .TAGS(MB), .PLACE(PLACE)) u_dsp (
        .clk(clk), .rst_n(rst_n), .in_valid(dsp_in_valid), .in_ready(dsp_in_ready),
        .in_data(iq[iq_r % 256][FW-1:0]), .in_last(iq[iq_r % 256][FW]),
        .out_valid(dsp_out_valid), .out_ready(dsp_out_ready), .out_data(dsp_out_data), .out_last(dsp_out_last),
        .tokens_in(dsp_tokens), .records_out(dsp_records), .flits_out(dsp_flits), .fault(dsp_fault));
    // per-message control latency of the dispatch: a token's descriptor in -> its first record out
    reg [63:0] d_in_t [0:TAGS-1];
    reg [TAGS-1:0] d_seen;
    integer dsp_lat_min = 1 << 30, dsp_lat_max = 0;
    integer in_pos = 0, out_pos = 0;
    reg [7:0] otag;
    always @(posedge clk) begin
        if (!rst_n) d_seen <= {TAGS{1'b0}};
        else begin
            if (dsp_in_valid && dsp_in_ready) begin
                if (in_pos == 0) begin
                    t_issue[iq[iq_r % 256][H_TAG +: 8]] <= now;
                    d_in_t[iq[iq_r % 256][H_TAG +: 8]] <= now;
                    d_seen[iq[iq_r % 256][H_TAG +: 8]] <= 1'b0;
                end
                in_pos = (in_pos == ACT) ? 0 : in_pos + 1;
                iq_r <= iq_r + 1;
            end
            if (dsp_out_valid && dsp_out_ready) begin
                if (out_pos == 0) begin
                    otag = dsp_out_data[H_TAG +: 8];
                    if (!d_seen[otag]) begin
                        d_seen[otag] <= 1'b1;
                        if (now - d_in_t[otag] < dsp_lat_min) dsp_lat_min = now - d_in_t[otag];
                        if (now - d_in_t[otag] > dsp_lat_max) dsp_lat_max = now - d_in_t[otag];
                    end
                end
                out_pos = (out_pos == ACT) ? 0 : out_pos + 1;
            end
        end
    end
    // -- fabric: multicast demultiplexer to package 0 (direct) and down links 1..4 -------------------
    reg  [NP-1:0] fmask;
    reg           fbusy = 1'b0;
    wire [NP-1:0] m_now = fbusy ? fmask : dsp_out_data[H_MASK +: NP];
    wire [NP-1:0] tgt_ready;
    wire          all_ready = &(tgt_ready | ~m_now);
    assign dsp_out_ready = all_ready;
    always @(posedge clk) begin
        if (!rst_n) fbusy <= 1'b0;
        else if (dsp_out_valid && all_ready) begin fbusy <= !dsp_out_last; fmask <= m_now; end
    end
    integer fab_copies = 0, dest_errors = 0;
    // the fabric id every record carries: the multicast group GROUP_BASE + set, or the one package
    always @(posedge clk) if (rst_n && dsp_out_valid && all_ready && !fbusy)
        if (dsp_out_data[H_DST +: 8] != ((MCAST != 0) ? GROUP_BASE + dsp_out_data[H_MASK +: NP]
                                                       : $clog2(dsp_out_data[H_MASK +: NP])) ||
            dsp_out_data[H_LEN +: 8] != ACT || dsp_out_data[H_KIND +: 4] != K_DISPATCH)
            dest_errors = dest_errors + 1;
    always @(posedge clk) if (rst_n && dsp_out_valid && all_ready) for (k = 0; k < NP; k = k + 1) if (m_now[k]) fab_copies = fab_copies + 1;
    // dispatch control bubbles: cycles it refuses offered input although its output is not held
    // (its ready is registered, so the cycle after a release of back-pressure is counted apart)
    integer dsp_in_stall = 0, dsp_out_held = 0, dsp_bubble = 0;
    reg     held_prev = 1'b0;
    always @(posedge clk) if (rst_n) begin
        if (dsp_in_valid && !dsp_in_ready) dsp_in_stall = dsp_in_stall + 1;
        if (dsp_out_valid && !dsp_out_ready) dsp_out_held = dsp_out_held + 1;
        if (dsp_in_valid && !dsp_in_ready && !(dsp_out_valid && !dsp_out_ready) && !held_prev) dsp_bubble = dsp_bubble + 1;
        held_prev <= dsp_out_valid && !dsp_out_ready;
    end

    // -- packages -------------------------------------------------------------------------------------
    wire [NP-1:0]  pin_ready;
    wire [NP-1:0]  po_valid, po_ready, po_last;
    wire [FW-1:0]  po_data [0:NP-1];
    wire [31:0]    p_rdrop [0:NP-1];
    wire [NP-1:0]  p_fault;
    // merge side of each package: what the merge sees (package 0 direct, others through up links)
    wire [NP-1:0]  mg_valid, mg_last;
    wire [NP-1:0]  mg_ready;
    wire [FW-1:0]  mg_data [0:NP-1];
    wire [31:0]    dstall [0:NP-1], ustall [0:NP-1];
    wire [31:0]    pk_err [0:NP-1], pk_place [0:NP-1], pk_jobs [0:NP-1], pk_full [0:NP-1];

    genvar g;
    generate for (g = 0; g < NP; g = g + 1) begin : g_pkg
        // random back-pressure at this package's link endpoints and work port
        reg  [31:0] r_bp;
        reg         stall_in, stall_wk, stall_mg;
        always @(posedge clk) begin
            if (!rst_n) r_bp <= (32'h9E37_79B9 * (g + 1)) ^ SEED;
            else r_bp <= xs(r_bp);
            stall_in <= (r_bp % 100) < BP;
            stall_wk <= ((r_bp >> 7) % 100) < BP;
            stall_mg <= ((r_bp >> 14) % 100) < BP;
        end
        wire          pin_valid, pin_last;
        wire [FW-1:0] pin_data;
        if (g == 0) begin : g_local
            assign tgt_ready[g] = pin_ready[g];
            assign pin_valid = dsp_out_valid && m_now[g] && all_ready;
            assign pin_data  = dsp_out_data;
            assign pin_last  = dsp_out_last;
            assign mg_valid[g] = po_valid[g] && !stall_mg;
            assign mg_data[g]  = po_data[g];
            assign mg_last[g]  = po_last[g];
            assign po_ready[g] = mg_ready[g] && !stall_mg;
            assign dstall[g] = 32'd0; assign ustall[g] = 32'd0;
        end else begin : g_remote
            wire          dl_out_valid, dl_out_last;
            wire [FW-1:0] dl_out_data;
            ot_rom_pkg_link #(.FLIT_BYTES(FW / 8), .CHANNEL_CYCLES(CH), .CREDITS(CREDITS)) u_down (
                .clk(clk), .rst_n(rst_n), .in_valid(dsp_out_valid && m_now[g] && all_ready), .in_ready(tgt_ready[g]),
                .in_data(dsp_out_data), .in_last(dsp_out_last),
                .out_valid(dl_out_valid), .out_ready(pin_ready[g] && !stall_in), .out_data(dl_out_data),
                .out_last(dl_out_last), .credit_stalls(dstall[g]));
            assign pin_valid = dl_out_valid && !stall_in;
            assign pin_data  = dl_out_data;
            assign pin_last  = dl_out_last;
            wire ul_out_valid;
            ot_rom_pkg_link #(.FLIT_BYTES(FW / 8), .CHANNEL_CYCLES(CH), .CREDITS(CREDITS)) u_up (
                .clk(clk), .rst_n(rst_n), .in_valid(po_valid[g]), .in_ready(po_ready[g]),
                .in_data(po_data[g]), .in_last(po_last[g]),
                .out_valid(ul_out_valid), .out_ready(mg_ready[g] && !stall_mg), .out_data(mg_data[g]),
                .out_last(mg_last[g]), .credit_stalls(ustall[g]));
            assign mg_valid[g] = ul_out_valid && !stall_mg;
        end
        wire          wk_valid, wk_last;
        wire [FW-1:0] wk_data;
        wire          wk_ready = !stall_wk;
        reg           rs_valid, rs_last;
        wire          rs_ready;
        reg  [FW-1:0] rs_data;
        reg  [7:0]    rs_tag;
        reg  [2:0]    rs_rank;
        wire [31:0]   p_rin, p_rout;
        ot_rom_moe_expert_port #(.FLIT_W(FW), .SELF(g), .ACT_FLITS(ACT)) u_port (
            .clk(clk), .rst_n(rst_n),
            .in_valid(pin_valid), .in_ready(pin_ready[g]), .in_data(pin_data), .in_last(pin_last),
            .work_valid(wk_valid), .work_ready(wk_ready), .work_data(wk_data), .work_last(wk_last),
            .res_valid(rs_valid), .res_ready(rs_ready), .res_data(rs_data), .res_last(rs_last),
            .res_tag(rs_tag), .res_rank(rs_rank), .res_home(4'd0),
            .out_valid(po_valid[g]), .out_ready(po_ready[g]), .out_data(po_data[g]), .out_last(po_last[g]),
            .records_in(p_rin), .records_dropped(p_rdrop[g]), .results_out(p_rout), .fault(p_fault[g]));

        // -- behavioural expert compute: check what arrived, answer later and out of order -------------
        reg          jb_v    [0:J-1];
        reg [31:0]   jb_n    [0:J-1];
        reg [7:0]    jb_tag  [0:J-1];
        reg [2:0]    jb_rank [0:J-1];
        reg [63:0]   jb_t    [0:J-1];
        integer      wpos, snd_j, snd_c, nn, rk, jj, st, found, ii;
        integer      e_err = 0, e_place = 0, e_jobs = 0, e_full = 0;
        reg [FW-1:0] wdesc;
        reg [31:0]   r_ex;
        reg [63:0]   meta;
        assign pk_err[g] = e_err; assign pk_place[g] = e_place; assign pk_jobs[g] = e_jobs; assign pk_full[g] = e_full;
        always @(posedge clk) begin
            if (!rst_n) begin
                wpos = 0; snd_j = -1; snd_c = 0; r_ex = (32'hC2B2_AE35 * (g + 3)) ^ SEED;
                rs_valid <= 1'b0;
                for (jj = 0; jj < J; jj = jj + 1) jb_v[jj] = 1'b0;
            end else begin
                r_ex = xs(r_ex);
                // receive work: the descriptor (owned items only), then the activation flits
                if (wk_valid && wk_ready) begin
                    if (wpos == 0) wdesc = wk_data;
                    else begin
                        nn = tagmap[wdesc[H_TAG +: 8]];
                        if (wk_data !== vact[nn * ACT + wpos - 1]) e_err = e_err + 1;
                    end
                    if (wpos == ACT) begin
                        nn = tagmap[wdesc[H_TAG +: 8]];
                        for (ii = 0; ii < N_ITEMS; ii = ii + 1) if (wdesc[H_IVAL + ii]) begin
                            rk = wdesc[H_ITEM + ITEM_W * ii + I_RANK +: 3];
                            meta = vmeta[nn * NR + rk];
                            if (wdesc[H_ITEM + ITEM_W * ii + I_ID +: 9] != meta[40:32]) e_err = e_err + 1;
                            if (ii != N_ITEMS - 1 && wdesc[H_ITEM + ITEM_W * ii + I_WGT +: 32] != meta[31:0])
                                e_err = e_err + 1;
                            if (PLACE[4 * meta[40:32] +: 4] != g) e_place = e_place + 1;
                            if (wdesc[H_SRC +: 8] != 0) e_err = e_err + 1;
                            found = 0;
                            for (jj = 0; jj < J; jj = jj + 1) if (found == 0 && !jb_v[jj]) begin
                                found = 1;
                                jb_v[jj] = 1'b1; jb_n[jj] = nn; jb_tag[jj] = wdesc[H_TAG +: 8];
                                jb_rank[jj] = rk; jb_t[jj] = now + (ELAT > 0 ? (r_ex % (ELAT + 1)) : 0);
                                e_jobs = e_jobs + 1;
                            end
                            if (found == 0) e_full = e_full + 1;
                        end
                    end
                    if (wk_last && wpos != ACT) e_err = e_err + 1;
                    wpos = (wpos == ACT) ? 0 : wpos + 1;
                end
                // results: one at a time, flit by flit; the next job is a random ready one
                if (rs_valid && rs_ready) begin
                    snd_c = snd_c + 1;
                    if (snd_c == VF) begin jb_v[snd_j] = 1'b0; snd_j = -1; end
                end
                if (snd_j < 0) begin
                    st = (r_ex >> 5) % J;
                    for (jj = 0; jj < J; jj = jj + 1)
                        if (snd_j < 0 && jb_v[(st + jj) % J] && jb_t[(st + jj) % J] <= now) begin
                            snd_j = (st + jj) % J; snd_c = 0;
                        end
                end
                // (re-)offer the current flit unless back-pressure withholds it this cycle
                if (snd_j >= 0 && ((r_ex >> 12) % 100) >= BP) begin
                    rs_valid <= 1'b1;
                    rs_data  <= vout[(jb_n[snd_j] * NR + jb_rank[snd_j]) * VF + snd_c];
                    rs_last  <= (snd_c == VF - 1);
                    rs_tag   <= jb_tag[snd_j];
                    rs_rank  <= jb_rank[snd_j];
                end else rs_valid <= 1'b0;
            end
        end
    end endgenerate

    // -- merge: packet-atomic round-robin into the combine -----------------------------------------------
    integer owner = -1, rrp = 0;
    reg [NP-1:0] grant;
    integer ret_flits = 0;
    always @* begin
        grant = {NP{1'b0}};
        if (owner >= 0) grant[owner] = 1'b1;
        else for (k = NP - 1; k >= 0; k = k - 1) if (mg_valid[(rrp + k) % NP]) begin grant = 0; grant[(rrp + k) % NP] = 1'b1; end
    end
    assign mg_ready = grant;
    reg          cb_valid, cb_last;
    reg [FW-1:0] cb_data;
    always @* begin
        cb_valid = 1'b0; cb_last = 1'b0; cb_data = {FW{1'b0}};
        for (k = 0; k < NP; k = k + 1) if (grant[k] && mg_valid[k]) begin
            cb_valid = 1'b1; cb_last = mg_last[k]; cb_data = mg_data[k];
        end
    end
    always @(posedge clk) begin
        if (!rst_n) begin owner = -1; rrp = 0; end
        else for (k = 0; k < NP; k = k + 1) if (grant[k] && mg_valid[k]) begin
            owner = mg_last[k] ? -1 : k;
            if (mg_last[k]) rrp = (k + 1) % NP;
            ret_flits = ret_flits + 1;
        end
    end

    // -- combine and the check ------------------------------------------------------------------------------
    wire          cmb_ready, cmb_out_valid, cmb_out_last, cmb_fault;
    wire [7:0]    cmb_out_tag, cmb_out_chunk;
    wire [FW-1:0] cmb_out_data;
    wire [31:0]   cmb_results, cmb_issued, cmb_waits;
    ot_rom_moe_combine #(.FLIT_W(FW), .TAGS(TAGS), .NRANK(NR), .VEC_FLITS(VF)) u_cmb (
        .clk(clk), .rst_n(rst_n), .in_valid(cb_valid), .in_ready(cmb_ready), .in_data(cb_data), .in_last(cb_last),
        .out_valid(cmb_out_valid), .out_tag(cmb_out_tag), .out_chunk(cmb_out_chunk), .out_data(cmb_out_data),
        .out_last(cmb_out_last), .tag_free_valid(cmb_free_v), .tag_free(cmb_free_t),
        .results_in(cmb_results), .chunks_issued(cmb_issued), .walker_waits(cmb_waits), .fault(cmb_fault));
    // combine control latency: the token's last input flit -> its out_last
    reg [63:0] last_in_t [0:TAGS-1], first_in_t [0:TAGS-1];
    integer    nres [0:TAGS-1];
    initial for (k = 0; k < TAGS; k = k + 1) nres[k] = 0;
    integer cb_pos = 0;
    reg [7:0] cb_tag;
    always @(posedge clk) if (rst_n && cb_valid) begin
        if (cb_pos == 0) begin
            cb_tag = cb_data[H_TAG +: 8];
            if (cb_data[H_SRC +: 8] != 0 && nres[cb_tag] == 0) first_in_t[cb_tag] <= now;   // first REMOTE result
            if (cb_data[H_SRC +: 8] != 0) nres[cb_tag] = (nres[cb_tag] == NR - 2) ? 0 : nres[cb_tag] + 1;
        end
        if (cb_pos == VF) last_in_t[cb_tag] <= now;
        cb_pos = (cb_pos == VF) ? 0 : cb_pos + 1;
    end
    integer chunks_checked = 0, moe_errors = 0, order_errors = 0, nn;
    integer lat_min = 1 << 30, lat_max = 0, cmb_lat_min = 1 << 30, cmb_lat_max = 0;
    integer out_min = 1 << 30, span_min = 1 << 30, span_max = 0;   // issue -> first return; first -> last return
    reg [63:0] lat_sum = 0, first_issue = 0, last_done = 0, q1_t = 0, q3_t = 0;
    integer next_chunk [0:TAGS-1];
    initial for (k = 0; k < TAGS; k = k + 1) next_chunk[k] = 0;
    always @(posedge clk) begin
        if (rst_n && cmb_out_valid) begin
            nn = tagmap[cmb_out_tag];
            chunks_checked = chunks_checked + 1;
            if (cmb_out_data !== vmoe[nn * VF + cmb_out_chunk]) begin
                moe_errors = moe_errors + 1;
                if (moe_errors <= 5) $display("MISMATCH token=%0d chunk=%0d got=%h want=%h", nn, cmb_out_chunk,
                                              cmb_out_data[63:0], vmoe[nn * VF + cmb_out_chunk][63:0]);
            end
            if (cmb_out_chunk != next_chunk[cmb_out_tag]) order_errors = order_errors + 1;
            next_chunk[cmb_out_tag] = (cmb_out_chunk == VF - 1) ? 0 : cmb_out_chunk + 1;
            if (cmb_out_last) begin
                if (done_n == 0) first_issue = t_issue[cmb_out_tag];
                if (now - t_issue[cmb_out_tag] < lat_min) lat_min = now - t_issue[cmb_out_tag];
                if (now - t_issue[cmb_out_tag] > lat_max) lat_max = now - t_issue[cmb_out_tag];
                if (now - last_in_t[cmb_out_tag] < cmb_lat_min) cmb_lat_min = now - last_in_t[cmb_out_tag];
                if (now - last_in_t[cmb_out_tag] > cmb_lat_max) cmb_lat_max = now - last_in_t[cmb_out_tag];
                lat_sum = lat_sum + (now - t_issue[cmb_out_tag]);
                if (first_in_t[cmb_out_tag] - t_issue[cmb_out_tag] < out_min) out_min = first_in_t[cmb_out_tag] - t_issue[cmb_out_tag];
                if (last_in_t[cmb_out_tag] - first_in_t[cmb_out_tag] < span_min) span_min = last_in_t[cmb_out_tag] - first_in_t[cmb_out_tag];
                if (last_in_t[cmb_out_tag] - first_in_t[cmb_out_tag] > span_max) span_max = last_in_t[cmb_out_tag] - first_in_t[cmb_out_tag];
                done_n = done_n + 1;
                if (done_n == N / 4) q1_t = now;
                if (done_n == (3 * N) / 4) q3_t = now;
                last_done = now;
            end
        end
    end

    // -- end of run -------------------------------------------------------------------------------------
    integer ds_total, us_total, e_total, pl_total, jb_total, fl_total;
    always @(posedge clk) begin
        if (rst_n && (done_n == N || now > 64'd200 + 64'd4000 * N)) begin
            ds_total = 0; us_total = 0;
            e_total = 0; pl_total = 0; jb_total = 0; fl_total = 0;
            for (k = 1; k < NP; k = k + 1) begin ds_total = ds_total + dstall[k]; us_total = us_total + ustall[k]; end
            for (k = 0; k < NP; k = k + 1) begin
                e_total = e_total + pk_err[k]; pl_total = pl_total + pk_place[k];
                jb_total = jb_total + pk_jobs[k]; fl_total = fl_total + pk_full[k];
            end
            $display("MOE tokens=%0d done=%0d chunks=%0d errors=%0d order_errors=%0d exp_errors=%0d place_errors=%0d aq_errors=%0d aq_faults=%0d faults=%0d%0d%0d jobs=%0d jobs_full=%0d",
                     N, done_n, chunks_checked, moe_errors, order_errors, e_total, pl_total, aq_errors, aq_faults,
                     dsp_fault, cmb_fault, |p_fault, jb_total, fl_total);
            $display("MOESTAT cycles=%0d first_issue=%0d last_done=%0d lat_min=%0d lat_max=%0d lat_sum=%0d q1=%0d q3=%0d dsp_lat_min=%0d dsp_lat_max=%0d cmb_lat_min=%0d cmb_lat_max=%0d round_trip_min=%0d ingest_span_min=%0d ingest_span_max=%0d",
                     now, first_issue, last_done, lat_min, lat_max, lat_sum, q1_t, q3_t, dsp_lat_min, dsp_lat_max,
                     cmb_lat_min, cmb_lat_max, out_min, span_min, span_max);
            $display("MOEDSP dsp_in_stall=%0d dsp_out_held=%0d dsp_bubble=%0d dest_errors=%0d", dsp_in_stall, dsp_out_held, dsp_bubble, dest_errors);
            $display("MOEFLITS dsp_tokens=%0d dsp_records=%0d dsp_flits=%0d fabric_copies=%0d ret_flits=%0d cmb_results=%0d cmb_chunks=%0d cmb_waits=%0d down_credit_stalls=%0d up_credit_stalls=%0d dropped=%0d",
                     dsp_tokens, dsp_records, dsp_flits, fab_copies, ret_flits, cmb_results, cmb_issued, cmb_waits,
                     ds_total, us_total, p_rdrop[0] + p_rdrop[1] + p_rdrop[2] + p_rdrop[3] + p_rdrop[4]);
            $finish;
        end
    end
endmodule
