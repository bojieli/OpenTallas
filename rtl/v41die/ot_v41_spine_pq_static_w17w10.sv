// Additive immutable provider join; STATIC_CONTROLS defaults off. No host array patch on static path.
// Additive default-off address-cone repair. Original source remains byte-identical.
// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_spine_pq_w17w10: SUCCESSOR of ot_v41_spine_w17w10 (DS-ROM recovery lever "field", 2026-10-04): the ROM-
// field front end with PIPELINED PHASES, for the PQ field (ot_v41_field_pq_w17w10 / ot_v41_pair_pq_w17w10 /
// ot_v41_rom_elem_pq_w10).  Same phase ROM, stream ROM, broadcast and vector-memory ports as the pinned spine;
// the broadcast carries one more field, the op's 2-bit tag.
//
// The pinned spine runs one phase at a time: the next phase's configuration is broadcast only when every region
// has written every row of the current one, so configuration, x fill, element pipeline, return tree and root are
// paid again each phase.  Here up to four ops are in flight (tags 0..3, accepted back to back while `ready`):
//
//   LOAD    the x of op t is read into buffer parity t[0] as soon as that buffer's previous op (t - 2) has sent
//           its last beat -- i.e. while op t - 1 still streams (prefetch);
//   CFG     op t's configuration is broadcast right after op t - 1's go: the elements load it into their
//           configuration SHADOW while op t - 1 streams (an element holds the load while its shadow is full or the
//           output-tag bank it would write still drains);
//   GO      op t's go is broadcast >= CW + 1 + GSLACK cycles after its configuration, >= GAP cycles after op t - 1's
//           last beat (the elements' walkers finish op t - 1, copy the shadow into the live configuration and let
//           it settle) and >= GUARD cycles after op t - 2's last beat (the tag bank op t reuses has drained and op
//           t's load completed: GUARD >= walker lag + the element's DRAIN + CW + 2 + settle).  A go that finds an
//           element not ready is a fault;
//   STREAM  as the pinned spine, from op t's stream ROM entries and buffer t[0];
//   RETURN  a row's [15:14] is its op tag: it is written at that op's base, in that op's row format, and counted
//           against that op; an op retires when its stream is sent and all its rows are written.
//
// A multi-position (MTP, np > 0) op runs ALONE, as in the pinned spine: its configuration waits until no other op is
// in flight and the next op's configuration waits until it has retired; its positions alternate the x buffers
// (parity tag[0] ^ position[0]) and its rows go to obase + row + position * ops.  PQ = 0 keeps one op in flight
// (the pinned sequencing: the next configuration only after every row of the previous op is written).
// Debug outputs ev_go / ev_end pulse when an op's go is broadcast and when its last beat is sent (tag ev_tag).
// ---------------------------------------------------------------------------
module ot_v41_spine_pq_static_w17w10 #(
    parameter integer PHW = 10,
    parameter integer SAW = 14,
    parameter integer R = 2,
    parameter integer VAW = 19,
    parameter integer VRD = 64,
    parameter integer KMAX = 6144,
    parameter integer BST = 2,
    parameter integer NSEG = 8,
    parameter integer PQ = 0,
    parameter integer ADDR_LOOKAHEAD = 0,
    parameter integer STATIC_CONTROLS = 0,
    parameter integer CONTROL_STAGE = 37,
    parameter integer GAP = 12,
    parameter integer GUARD = 180,
    parameter integer GSLACK = 6,
    parameter integer BW = 1 + PHW + 3 + 1 + 1 + 2 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [PHW-1:0]    i_ph,
    input  wire [2:0]        i_np,
    input  wire [VAW-1:0]    i_xbase,
    input  wire [VAW-1:0]    i_xps,
    input  wire [VAW-1:0]    i_obase,
    input  wire [VAW-1:0]    i_ops,
    input  wire [1:0]        i_fmt,
    output wire              ready,
    output wire              idle,
    output reg               x_re,
    output reg  [VAW-1:0]    x_addr,
    input  wire [VRD*32-1:0] x_q,
    output reg  [R-1:0]      w_we,
    output reg  [R*VAW-1:0]  w_addr,
    output reg  [R*32-1:0]   w_data,
    output wire              f_cfg_go,
    output wire [PHW-1:0]    f_cfg_ph,
    output wire [2:0]        f_cfg_np,
    output wire              f_go,
    output wire              f_go_bf,
    output wire [1:0]        f_go_tag,
    output wire              f_xs_v,
    output wire [7:0]        f_xs_p,
    output wire [2:0]        f_xs_b,
    output wire [1:0]        f_xs_sv,
    output wire [255:0]      f_xs_q0,
    output wire [9:0]        f_xs_e0,
    output wire [255:0]      f_xs_q1,
    output wire [9:0]        f_xs_e1,
    output wire [2:0]        f_xs_pos,
    output wire [2:0]        f_xb_pos,
    output wire              f_xb_v,
    output wire [2:0]        f_xb_b,
    output wire [3:0]        f_xb_sv,
    output wire [31:0]       f_xb_u,
    output wire [1023:0]     f_xb_d,
    output wire [BW-1:0]     f_bus,
    input  wire [R-1:0]      r_v,
    input  wire [16*R-1:0]   r_row,
    input  wire [3*R-1:0]    r_pos,
    input  wire [32*R-1:0]   r_fp32,
    input  wire [16*R-1:0]   r_bf16,
    input  wire [R-1:0]      r_e,
    input  wire              f_fault,
    output reg               fault,
    output reg  [31:0]       phase_cycles,    // cycles from the first accepted op to idle (last node)
    output reg               ev_go,
    output reg               ev_end,
    output reg  [1:0]        ev_tag
`ifdef OT_PQ_ROM_PORTS
    // physical screen only: the phase and stream ROMs as macro ports (address out, word in)
    ,
    output wire [PHW:0]      rom_pa0,
    output wire [PHW:0]      rom_pa1,
    input  wire [63:0]       rom_pq0,
    input  wire [63:0]       rom_pq1,
    output wire [SAW-1:0]    rom_sa,
    input  wire [47:0]       rom_sq
`endif
);
    localparam integer CW = 3 * NSEG + 1;
    localparam integer NBLK = KMAX / 32;
    localparam integer BAW = $clog2(NBLK);
`ifndef OT_PQ_ROM_PORTS
    // ------------------------------------------------------------------ ROMs
    reg [63:0] phrom [0:(2 << PHW)-1] /*verilator public_flat_rw*/;
    reg [47:0] strom [0:(1 << SAW)-1] /*verilator public_flat_rw*/;
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial if (STATIC_CONTROLS == 0) begin
        for (ii = 0; ii < (2 << PHW); ii = ii + 1) phrom[ii] = 64'd0;
        for (ii = 0; ii < (1 << SAW); ii = ii + 1) strom[ii] = 48'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) begin
            $readmemh({rom_dir, "/spine_phase.hex"}, phrom);
            $readmemh({rom_dir, "/spine_stream.hex"}, strom);
        end
    end
`endif
    // ------------------------------------------------------------------ op slots (tag = slot)
    reg           sv [0:3];          // accepted, not retired
    reg           si [0:3];          // configuration issued
    reg           sd [0:3];          // last beat sent
    reg [PHW-1:0] s_ph [0:3];
    reg [VAW-1:0] s_xb [0:3];
    reg [VAW-1:0] s_ob [0:3];
    reg [1:0]     s_fm [0:3];
    reg [63:0]    s_pw [0:3];
    reg [15:0]    s_rs [0:3];
    reg [18:0]    s_rl [0:3];        // rows left
    reg [2:0]     s_np [0:3];        // positions - 1
    reg [VAW-1:0] s_xps [0:3];
    reg [VAW-1:0] s_ops [0:3];
    reg [1:0]     acc, ldt, ist;     // next tag to accept / load / issue
    reg [31:0]    cyc;
    reg           any_v;
    always @* any_v = sv[0] | sv[1] | sv[2] | sv[3];
    assign ready = !sv[acc];
    assign idle = !any_v;
    // ------------------------------------------------------------------ loader
    reg        ld_run, ld_more;
    reg [1:0]  ld_tag;
    reg [2:0]  ld_pos;
    reg [13:0] ld_k, ld_kk;
    reg        ld_fam;
    reg        rq_v, rq_par, rq_fam;
    reg [13:0] rq_k, is_k;
    reg        is_par, is_fam;
    reg        bufbusy [0:1];        // buffer parity holds an op's x not yet fully streamed
    wire [1:0] aq_vo, aq_f;
    wire [511:0] aq_q;
    wire [19:0]  aq_e;
    genvar gq;
    generate for (gq = 0; gq < 2; gq = gq + 1) begin : g_aq
        wire [511:0] unused_y;
        wire signed [9:0] e1;
        ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_n), .v(rq_v && !rq_fam), .fp4(1'b0),
            .x(x_q[1024*gq +: 1024]), .vo(aq_vo[gq]), .q(aq_q[256*gq +: 256]), .e(e1), .y(unused_y),
            .fault(aq_f[gq]));
        assign aq_e[10*gq +: 10] = e1;
    end endgenerate
    wire [BAW-1:0] aq_blk;
    wire           aq_par;
    ot_hdc_delay #(.W(BAW + 1), .D(13)) u_aqi (.clk(clk), .rst_n(rst_n), .d({rq_k[BAW+4:5], rq_par}),
                                              .q({aq_blk, aq_par}));
    reg [255:0] qb [0:2*NBLK-1];
    reg [9:0]   eb [0:2*NBLK-1];
    reg [15:0]  bb [0:2*KMAX-1];
    reg [14:0]  have [0:1];
    // ------------------------------------------------------------------ issuer / streamer
    localparam [1:0] I_IDLE = 2'd0, I_CFG = 2'd1;
    reg [1:0]  ist_st;
    reg [5:0]  cfg_cnt;
    reg        sm_run;
    reg [1:0]  sm_tag;
    reg [2:0]  sm_pos;
    reg [15:0] sm_i;
    reg [47:0] sw;
    reg        sw_v;
    reg [15:0] since1, since2;       // cycles since the last / the previous last beat (saturating)
    wire [63:0] spw = s_pw[sm_tag];
    // Payload is qualified by existing sm_run/sw_v, reset by the original control.
    // Captured on the SAME can_go edge: no new valid, pipeline stage or clock domain.
    reg active_fam;
    reg [15:0] active_nbeat, active_base;
    reg [SAW-1:0] active_addr;
    wire        fam = ADDR_LOOKAHEAD != 0 ? active_fam : spw[0];
    wire [15:0] nbeat = ADDR_LOOKAHEAD != 0 ? active_nbeat : spw[29:14];
    wire [15:0] sbase = ADDR_LOOKAHEAD != 0 ? active_base : spw[45:30];
    wire        spar = sm_tag[0] ^ sm_pos[0];
    wire [7:0] u  = sw[8:1];
    wire [2:0] b  = sw[11:9];
    wire [1:0] sv2 = sw[13:12];
    reg [7:0] umax;
    integer kb;
    always @* begin
        umax = 8'd0;
        for (kb = 0; kb < 4; kb = kb + 1) if (sw[4 + kb] && sw[8 + 8*kb +: 8] > umax) umax = sw[8 + 8*kb +: 8];
    end
    wire [14:0] need_q = sv2[1] ? ({u, 1'b1, b, 5'd0} + 15'd32) : ({u, 1'b0, b, 5'd0} + 15'd32);
    wire [14:0] need_b = {umax, 7'd0} + 15'd128;
    wire        s_ok = !sw[0] || ((fam ? need_b : need_q) <= have[spar]);
    wire        s_adv = sm_run && sw_v && s_ok;
    wire        s_last = sm_i + 16'd1 == nbeat;
    // ROM reads: the phase ROM at accept (two words), the stream ROM at the streamer's next beat
    wire [SAW-1:0] legacy_st_a = SAW'(sbase) + SAW'(!sw_v ? sm_i : (s_last ? 16'd0 : sm_i + 16'd1));
    wire [SAW-1:0] st_a = ADDR_LOOKAHEAD != 0 ? active_addr : legacy_st_a;
    // The lookahead predicts the NEXT state of the original combinational address.
    // Last-beat sw still captures beat zero; the following cycle addresses beat one.
    wire [15:0] ahead_i = sm_i + 16'd2;
    generate if (ADDR_LOOKAHEAD != 0) begin : g_addr_lookahead
        always @(posedge clk) begin
            if (rst_n) begin
                if (can_go) begin
                    active_fam <= s_pw[ist][0];
                    active_nbeat <= s_pw[ist][29:14];
                    active_base <= s_pw[ist][45:30];
                    active_addr <= SAW'(s_pw[ist][45:30]);
                end else if (sm_run && (!sw_v || s_ok)) begin
                    if (!sw_v || s_last)
                        active_addr <= SAW'(active_base) + SAW'(active_nbeat == 16'd1 ? 16'd0 : 16'd1);
                    else
                        active_addr <= SAW'(active_base) + SAW'(ahead_i == active_nbeat ? 16'd0 : ahead_i);
                end
            end
        end
    end endgenerate
    wire [63:0] ph_q0, ph_q1;
    wire [47:0] st_q;
`ifdef OT_PQ_ROM_PORTS
    assign rom_pa0 = {i_ph, 1'b0}; assign rom_pa1 = {i_ph, 1'b1}; assign rom_sa = st_a;
    assign ph_q0 = rom_pq0; assign ph_q1 = rom_pq1; assign st_q = rom_sq;
`else
    generate if (STATIC_CONTROLS != 0) begin : g_static_controls
        if (PHW != 10 || SAW != 14) begin : g_bad_shape
            initial $fatal(1,"Static canonical field controls require PHW10 SAW14");
        end
        if (CONTROL_STAGE == 37) begin : g_stage37
            ot_v41_stage37_control_rom u_controls(.phase(i_ph),.stream_addr(st_a),.pq0(ph_q0),.pq1(ph_q1),.sq(st_q));
        end else if (CONTROL_STAGE == 38) begin : g_stage38
            ot_v41_stage38_control_rom u_controls(.phase(i_ph),.stream_addr(st_a),.pq0(ph_q0),.pq1(ph_q1),.sq(st_q));
        end else begin : g_bad_stage
            initial $fatal(1,"Static canonical stage not source-bound");
        end
    end else begin : g_runtime_controls
        assign ph_q0 = phrom[{i_ph, 1'b0}]; assign ph_q1 = phrom[{i_ph, 1'b1}]; assign st_q = strom[st_a];
    end endgenerate
`endif
    // issue condition for op ist
    reg inflight;                    // PQ = 0: an issued op not yet retired
    always @* inflight = (sv[0] && si[0]) | (sv[1] && si[1]) | (sv[2] && si[2]) | (sv[3] && si[3]);
    reg inflight_mtp;                // an issued multi-position op not yet retired (it runs alone)
    always @* inflight_mtp = (sv[0] && si[0] && s_np[0] != 3'd0) | (sv[1] && si[1] && s_np[1] != 3'd0) |
                             (sv[2] && si[2] && s_np[2] != 3'd0) | (sv[3] && si[3] && s_np[3] != 3'd0);
    wire can_issue = sv[ist] && !si[ist] && ist_st == I_IDLE &&
                     ((PQ != 0 && s_np[ist] == 3'd0 && !inflight_mtp) ? 1'b1 : (!inflight && !sm_run));
    wire can_go = ist_st == I_CFG && cfg_cnt >= 6'(CW + 1 + GSLACK) && !sm_run &&
                  ((PQ != 0) ? (since1 >= 16'(GAP) && since2 >= 16'(GUARD)) : 1'b1);
    // beat assembly
    reg         bt_xs_v, bt_xb_v;
    reg [7:0]   bt_p;
    reg [2:0]   bt_b;
    reg [1:0]   bt_sv;
    reg [255:0] bt_q0, bt_q1;
    reg [9:0]   bt_e0, bt_e1;
    reg [3:0]   bt_bsv;
    reg [31:0]  bt_u;
    reg [1023:0] bt_d;
    reg         bt_go, bt_gobf, bt_cfg;
    reg [1:0]   bt_tag;
    reg [2:0]   bt_np, bt_pos;
    reg [PHW-1:0] bt_ph;
    wire [15:0] blk0 = (spar ? 16'(NBLK) : 16'd0) + {5'd0, u, 1'b0, b};
    wire [15:0] blk1 = (spar ? 16'(NBLK) : 16'd0) + {5'd0, u, 1'b1, b};
    integer kl, ku;
    always @(posedge clk) begin
        bt_p <= u; bt_b <= fam ? sw[3:1] : b; bt_sv <= sv2; bt_pos <= sm_pos;
        bt_q0 <= sv2[0] ? qb[blk0] : 256'd0; bt_e0 <= sv2[0] ? eb[blk0] : 10'd0;
        bt_q1 <= sv2[1] ? qb[blk1] : 256'd0; bt_e1 <= sv2[1] ? eb[blk1] : 10'd0;
        bt_bsv <= sw[7:4];
        bt_u <= sw[39:8];
        for (ku = 0; ku < 4; ku = ku + 1)
            for (kl = 0; kl < 16; kl = kl + 1)
                bt_d[256*ku + 16*kl +: 16] <= sw[4 + ku] ?
                    bb[(spar ? 16'(KMAX) : 16'd0) + {1'b0, sw[8 + 8*ku +: 8], 7'd0} + 16'(kl * 8) + {13'd0, sw[3:1]}] : 16'd0;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin bt_xs_v <= 1'b0; bt_xb_v <= 1'b0; end
        else begin
            bt_xs_v <= s_adv && sw[0] && !fam;
            bt_xb_v <= s_adv && sw[0] && fam;
        end
    end
    // ------------------------------------------------------------------ broadcast wire stages
    wire [BW-1:0] bc_in = {bt_cfg, bt_ph, bt_np, bt_go, bt_gobf, bt_tag, bt_xs_v, bt_p, bt_b, bt_sv, bt_q0, bt_e0, bt_q1,
                           bt_e1, bt_pos, bt_pos, bt_xb_v, bt_b, bt_bsv, bt_u, bt_d};
    wire [BW-1:0] bc;
    generate if (BST > 0) begin : g_bst
        ot_hdc_delay #(.W(BW), .D(BST), .RESET(1)) u_bst (.clk(clk), .rst_n(rst_n), .d(bc_in), .q(bc));
    end else begin : g_nobst
        assign bc = bc_in;
    end endgenerate
    assign {f_cfg_go, f_cfg_ph, f_cfg_np, f_go, f_go_bf, f_go_tag, f_xs_v, f_xs_p, f_xs_b, f_xs_sv, f_xs_q0, f_xs_e0,
            f_xs_q1, f_xs_e1, f_xs_pos, f_xb_pos, f_xb_v, f_xb_b, f_xb_sv, f_xb_u, f_xb_d} = bc;
    assign f_bus = bc;

    // ------------------------------------------------------------------ rows: per-tag counts, a registered tree
    // stage A: per group of 16 region roots, per tag (5 bits); stage B: the groups summed (8 bits).  An op's rows-left
    // count is reduced two cycles after its rows are written; it retires only when the count reaches zero, so the
    // delay only postpones the retirement.
    localparam integer NGR = (R + 15) / 16;
    reg [4:0] ga [0:NGR-1][0:3];
    reg [7:0] rc [0:3];
    reg [15:0] gm [0:3];
    reg [7:0] racc;
    integer kr, kt, kg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (kt = 0; kt < 4; kt = kt + 1) begin
                rc[kt] <= 8'd0;
                for (kg = 0; kg < NGR; kg = kg + 1) ga[kg][kt] <= 5'd0;
            end
        end else begin
            // stage A: per group of 16 roots and per tag, a one-hot mask and its population count (balanced)
            for (kg = 0; kg < NGR; kg = kg + 1)
                for (kt = 0; kt < 4; kt = kt + 1) begin
                    gm[kt] = 16'd0;
                    for (kr = 0; kr < 16; kr = kr + 1)
                        if (16 * kg + kr < R)
                            gm[kt][kr] = r_v[16 * kg + kr] && r_row[16 * (16 * kg + kr) + 14 +: 2] == 2'(kt);
                    ga[kg][kt] <= 5'($countones(gm[kt]));
                end
            for (kt = 0; kt < 4; kt = kt + 1) begin
                racc = 8'd0;
                for (kg = 0; kg < NGR; kg = kg + 1) racc = racc + 8'(ga[kg][kt]);
                rc[kt] <= racc;
            end
        end
    end
    // ------------------------------------------------------------------ control
    integer ks;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ld_more <= 1'b0; bt_np <= 3'd0;
            fault <= 1'b0; bt_go <= 1'b0; bt_gobf <= 1'b0; bt_cfg <= 1'b0; bt_tag <= 2'd0; bt_ph <= '0;
            ld_run <= 1'b0; rq_v <= 1'b0; sm_run <= 1'b0; sw_v <= 1'b0; x_re <= 1'b0;
            have[0] <= 15'd0; have[1] <= 15'd0; w_we <= {R{1'b0}}; phase_cycles <= 32'd0; cyc <= 32'd0;
            acc <= 2'd0; ldt <= 2'd0; ist <= 2'd0; ist_st <= I_IDLE; since1 <= 16'hFFFF; since2 <= 16'hFFFF;
            bufbusy[0] <= 1'b0; bufbusy[1] <= 1'b0; ev_go <= 1'b0; ev_end <= 1'b0; ev_tag <= 2'd0;
            for (ks = 0; ks < 4; ks = ks + 1) begin sv[ks] <= 1'b0; si[ks] <= 1'b0; sd[ks] <= 1'b0; s_rl[ks] <= 19'd0; end
        end else begin
            bt_go <= 1'b0; bt_gobf <= 1'b0; bt_cfg <= 1'b0; ev_go <= 1'b0; ev_end <= 1'b0;
            cyc <= any_v ? cyc + 32'd1 : 32'd0;
            if (f_fault || (|aq_f)) fault <= 1'b1;
            if (since1 != 16'hFFFF) since1 <= since1 + 16'd1;
            if (since2 != 16'hFFFF) since2 <= since2 + 16'd1;
            // accept
            if (go && !sv[acc]) begin
                sv[acc] <= 1'b1; si[acc] <= 1'b0; sd[acc] <= 1'b0;
                s_ph[acc] <= i_ph; s_xb[acc] <= i_xbase; s_ob[acc] <= i_obase; s_fm[acc] <= i_fmt;
                s_pw[acc] <= ph_q0; s_rs[acc] <= ph_q1[15:0];
                s_np[acc] <= i_np; s_xps[acc] <= i_xps; s_ops[acc] <= i_ops;
                acc <= acc + 2'd1;
            end
            // issue: configuration, then go
            case (ist_st)
                I_IDLE: if (can_issue) begin
                    bt_cfg <= 1'b1; bt_ph <= s_ph[ist]; bt_np <= s_np[ist]; cfg_cnt <= 6'd0; ist_st <= I_CFG;
                    si[ist] <= 1'b1;
                    s_rl[ist] <= 19'(s_pw[ist][61:46]) * (19'(s_np[ist]) + 19'd1);
                end
                I_CFG: begin
                    if (cfg_cnt != 6'h3F) cfg_cnt <= cfg_cnt + 6'd1;
                    if (can_go) begin
                        bt_go <= 1'b1; bt_gobf <= s_pw[ist][0]; bt_tag <= ist; ist_st <= I_IDLE;
                        ev_go <= 1'b1; ev_tag <= ist;
                        sm_run <= 1'b1; sm_tag <= ist; sm_pos <= 3'd0; sm_i <= 16'd0; sw_v <= 1'b0;
                        ist <= ist + 2'd1;
                    end
                end
                default: ist_st <= I_IDLE;
            endcase
            // loader: (op, position) into buffer tag[0] ^ position[0] once that buffer's previous user has sent its
            // last beat
            x_re <= 1'b0; rq_v <= x_re; rq_k <= is_k; rq_par <= is_par; rq_fam <= is_fam;
            if (!ld_run && !ld_more && sv[ldt] && !bufbusy[ldt[0]]) begin
                ld_run <= 1'b1; ld_tag <= ldt; ld_pos <= 3'd0; ld_k <= 14'd0; ld_kk <= {1'b0, s_pw[ldt][13:1]};
                ld_fam <= s_pw[ldt][0]; ld_more <= s_np[ldt] != 3'd0;
                bufbusy[ldt[0]] <= 1'b1; have[ldt[0]] <= 15'd0;
                ldt <= ldt + 2'd1;
            end else if (!ld_run && ld_more && !bufbusy[ld_tag[0] ^ ~ld_pos[0]]) begin
                ld_run <= 1'b1; ld_pos <= ld_pos + 3'd1; ld_k <= 14'd0; ld_more <= ld_pos + 3'd1 != s_np[ld_tag];
                bufbusy[ld_tag[0] ^ ~ld_pos[0]] <= 1'b1; have[ld_tag[0] ^ ~ld_pos[0]] <= 15'd0;
            end else if (ld_run) begin
                x_re <= 1'b1; is_k <= ld_k; is_par <= ld_tag[0] ^ ld_pos[0]; is_fam <= ld_fam;
                x_addr <= s_xb[ld_tag] + VAW'(ld_pos) * s_xps[ld_tag] + VAW'(ld_k);
                if (ld_k + 14'(VRD) >= ld_kk) ld_run <= 1'b0;
                else ld_k <= ld_k + 14'(VRD);
            end
            if (rq_v && rq_fam) have[rq_par] <= 15'(rq_k) + 15'(VRD);
            if (aq_vo[0]) have[aq_par] <= {aq_blk, 5'd0} + 15'd64;
            // streamer
            if (sm_run) begin
                if (!sw_v) begin
                    sw <= st_q; sw_v <= 1'b1;
                end else if (s_ok) begin
                    if (s_last) begin
                        sm_i <= 16'd0; bufbusy[spar] <= 1'b0;
                        if (sm_pos != s_np[sm_tag]) sm_pos <= sm_pos + 3'd1;
                        else begin
                            sm_run <= 1'b0;
                            sd[sm_tag] <= 1'b1;
                            since2 <= since1; since1 <= 16'd0;
                            ev_end <= 1'b1; ev_tag <= sm_tag;
                        end
                    end else sm_i <= sm_i + 16'd1;
                    sw <= st_q;
                end
            end
            // rows: each written at its op's base and format, counted against its op
            w_we <= {R{1'b0}};
            for (kr = 0; kr < R; kr = kr + 1) if (r_v[kr]) begin
                w_we[kr] <= 1'b1;
                w_addr[VAW*kr +: VAW] <= s_ob[r_row[16*kr + 14 +: 2]] + VAW'(r_row[16*kr +: 14])
                                         + VAW'(r_pos[3*kr +: 3]) * s_ops[r_row[16*kr + 14 +: 2]];
                w_data[32*kr +: 32] <= ((s_fm[r_row[16*kr + 14 +: 2]] == 2'd1) || (s_fm[r_row[16*kr + 14 +: 2]] == 2'd0 &&
                                        ((r_row[16*kr +: 14] < s_rs[r_row[16*kr + 14 +: 2]][13:0])
                                         ? s_pw[r_row[16*kr + 14 +: 2]][62] : s_pw[r_row[16*kr + 14 +: 2]][63])))
                                       ? r_fp32[32*kr +: 32] : {r_bf16[16*kr +: 16], 16'd0};
                if (r_e[kr]) fault <= 1'b1;
                if (!sv[r_row[16*kr + 14 +: 2]] || !si[r_row[16*kr + 14 +: 2]]) fault <= 1'b1;   // row of no live op
            end
            for (ks = 0; ks < 4; ks = ks + 1) begin
                if (!(ist_st == I_IDLE && can_issue && ist == 2'(ks)))
                    s_rl[ks] <= s_rl[ks] - 19'(rc[ks]);
                // retire: stream sent and every row written
                if (sv[ks] && si[ks] && sd[ks] && s_rl[ks] == 19'(rc[ks]) && !(go && !sv[acc] && acc == 2'(ks))) begin
                    sv[ks] <= 1'b0; si[ks] <= 1'b0; sd[ks] <= 1'b0;
                end
            end
            if (any_v) phase_cycles <= cyc + 32'd1;
        end
    end
    // buffers
    integer kw;
    always @(posedge clk) begin
        if (aq_vo[0]) begin
            qb[(aq_par ? NBLK : 0) + 32'(aq_blk)] <= aq_q[255:0];       eb[(aq_par ? NBLK : 0) + 32'(aq_blk)] <= aq_e[9:0];
            qb[(aq_par ? NBLK : 0) + 32'(aq_blk) + 1] <= aq_q[511:256]; eb[(aq_par ? NBLK : 0) + 32'(aq_blk) + 1] <= aq_e[19:10];
        end
        if (rq_v && rq_fam)
            for (kw = 0; kw < VRD; kw = kw + 1)
                bb[(rq_par ? KMAX : 0) + 32'(rq_k) + kw] <= x_q[32*kw + 16 +: 16] +
                    {15'd0, x_q[32*kw + 15] & ((x_q[32*kw +: 15] != 15'd0) | x_q[32*kw + 16])};
    end
endmodule
