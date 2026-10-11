`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kit_seq / dsfd_sp_seq / dsfd_sp_seq_h (mtp-lead/kitseq, 2026-10-11; MAIN DECISION option A: the WFC kit is
// the single stage controller of the S81 die; ot_s81_ctrl's hop_tx / pkg_ctrl handoff retired; ot_s81_stage_seq and
// the engine adapters kept).  The binding of the kit's stage START / DONE to the stage sequencer:
//
//   VM slab  dsfd_vm_wfc_ep t_ks {start, user, token, pos} (53 b, serial 0.9 GHz pulse, raised when the START doorbell
//            leaves the endpoint's op pipe, i.e. after every payload write of the job is at the VM pins)
//     --(KS hub relay stations: plain flops; a pulse net with no back-pressure)-->
//   f_ks pin flop (ckv) -> ot_s81_pulse_cdc (ckv -> ck, KQ entries) -> job_v / job_rdy of ot_s81_stage_seq (ck 1.2 GHz)
//   ot_s81_stage_seq: program memory (pw_*), engine commands / completions to the slab masters' ot_s81_engine_adapter
//            (physical/s81_ctrl/ADAPTER_CONTRACT_1011.json: 84-b command, 8-b tag, QD 8 done-credit)
//   KIT HAND-OFF (engine port 7, served HERE: hop_tx is retired): the program's hop entry (arg {has_pred, pred_op})
//            fires when its predecessor's completion has been seen for the job's slot; it pushes the kit DONE
//            {done, next_token, next_val} -> ot_s81_pulse_cdc (ck -> ckv) -> t_kd, and returns the hop completion to the
//            sequencer.  A job with no hop entry raises the DONE at job_done.  So the kit's outbound prefetch starts at
//            the composition's hand-off point; jobs after the hop in the program keep running (S029 cand.*), and the
//            sequencer's second job slot lets the kit START the next job meanwhile.
//     --(KD hub relay stations)--> WFC slab kit f_kd (dsfd_wfc_vmx k_done).
//
// Job-port mapping (the kit's one-shot START against job_rdy): the START enters a KQ-deep CDC queue whose read side
// is the sequencer's valid / ready job port (job_v = queue non-empty, popped on job_v && job_rdy): a START that arrives
// while both sequencer slots are held waits in the queue, never dropped.  The WFC core contract keeps <= 1 job between
// START and DONE; a START that finds the queue full is a sticky fault (fvec[0]).
// next_token / next_val: layer die (dsfd_sp_seq): the kit's STG tokpipe has SEND_RESULT 0 / COMBINE_IN 0 and does not
// consume them; they return the job's own {token, 11'b0, pos} from the hop descriptor (identity, checkable).  Head-root
// die (dsfd_sp_seq_h): the head slab's argmax {am_tok, am_val} of the job (latched on am_v; a hand-off without an
// argmax since the previous one is fvec[2]).
// Die lanes (10): engine ports {0 fld, 1 su, 2 hc, 3 coll, 4 svc, 5 sel, 6 col, 8 head, 9 emb, 10 eng} -> lanes 0..9
// (lane = port < 7 ? port : port - 1).  Port 7 (hop) is internal; port 11 (spare) has no lane: a descriptor to it is
// fvec[3] (the compiler never emits one: tools/s81_ctrl/kit_programs.py).
// Timing: every die input lands in a pin flop, every die output leaves a flop.
// MUT (bench negative controls): 1 = drop the 3rd START (dropped start); 2 = DONE at the job's accept (early done).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kit_seq #(
    parameter integer HEAD   = 0,
    parameter integer NOPS   = 128,
    parameter integer QD     = 8,           // engine credits (ADAPTER_CONTRACT_1011 QD 8)
    parameter integer KQ     = 4,           // START / DONE CDC queue entries
    parameter integer USER_W = 10,
    parameter integer NW     = 21,
    parameter integer ARGW   = 24,
    parameter integer MUT    = 0,
    parameter integer OPW    = $clog2(NOPS),
    parameter integer CMDW   = 1 + USER_W + 2 * NW + ARGW + OPW,
    parameter integer TAGW   = 1 + OPW,
    parameter integer NL     = 10           // die lanes
) (
    input  wire                   ck, rst,          // stream 1.2 GHz (sequencer, engine lanes)
    input  wire                   ckv, rsv,         // serial 0.9 GHz (kit / VM endpoint side)
    input  wire                   pw_v, input wire [OPW-1:0] pw_a, input wire [4+ARGW-1:0] pw_d, input wire [OPW:0] prog_len,
    input  wire [USER_W+2*NW:0]   f_ks,             // {start, user, token, pos} (ckv)
    output reg  [NW+32:0]         t_kd,             // {done, next_token, next_val} (ckv)
    output wire [NL-1:0]          cv,
    output wire [NL*CMDW-1:0]     cd,
    input  wire [NL-1:0]          dv,
    input  wire [NL*TAGW-1:0]     dt,
    input  wire                   am_v, input wire [NW-1:0] am_tok, input wire [31:0] am_val,   // HEAD only
    output reg                    flt,
    output reg  [7:0]             fvec,             // {seq code[3:0], spare-cmd, head-no-argmax, done-queue, start-queue}
    output wire                   busy,
    output wire [31:0]            st_jobs
);
    localparam integer SP = USER_W + 2 * NW;        // {user, token, pos}
    localparam integer NENG = 12, HOP = 7, SPARE = 11;
    wire c_run, v_run;
    ot_reset_sync u_rc (.clk(ck),  .async_rst_n(rst && rsv), .sync_rst_n(c_run));
    ot_reset_sync u_rv (.clk(ckv), .async_rst_n(rst && rsv), .sync_rst_n(v_run));

    // ---- START: pin flop (ckv) -> CDC queue -> job port ------------------------------------------------------------
    reg ks_v; reg [SP-1:0] ks_d; reg [1:0] ks_n;
    always @(posedge ckv or negedge v_run)
        if (!v_run) begin ks_v <= 1'b0; ks_n <= 2'd0; end
        else begin
            ks_v <= f_ks[SP] && !(MUT == 1 && ks_n == 2'd2);
            if (f_ks[SP] && ks_n != 2'd3) ks_n <= ks_n + 1'b1;
        end
    always @(posedge ckv) ks_d <= f_ks[SP-1:0];
    wire ks_acc, ks_flt, j_v, j_rdy; wire [SP-1:0] j_d;
    ot_s81_pulse_cdc #(.W(SP), .QD(KQ)) u_ks (.s_clk(ckv), .s_rst_n(v_run), .i_v(ks_v), .i_d(ks_d), .i_accept(ks_acc),
        .fault(ks_flt), .d_clk(ck), .d_rst_n(c_run), .o_v(j_v), .o_r(j_rdy), .o_d(j_d));

    // ---- the stage sequencer (12 engine ports) ----------------------------------------------------------------------
    wire [NENG-1:0] s_cv; wire [NENG*CMDW-1:0] s_cd; wire [NENG-1:0] s_dv; wire [NENG*TAGW-1:0] s_dt;
    wire job_done, s_flt; wire [3:0] s_code; wire [31:0] st_cmds, st_cs;
    ot_s81_stage_seq #(.NOPS(NOPS), .NENG(NENG), .ARGW(ARGW), .USER_W(USER_W), .NW(NW), .QD(QD)) u_seq (
        .clk(ck), .rst_n(c_run), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len),
        .job_v(j_v), .job_rdy(j_rdy), .job_user(j_d[SP-1 -: USER_W]), .job_pos(j_d[NW-1:0]), .job_tok(j_d[NW +: NW]),
        .job_done(job_done), .cmd_v(s_cv), .cmd_d(s_cd), .dn_v(s_dv), .dn_tag(s_dt), .busy(busy), .fault(s_flt),
        .fault_code(s_code), .st_jobs(st_jobs), .st_cmds(st_cmds), .st_credit_stall(st_cs));

    // ---- die lanes <-> engine ports ---------------------------------------------------------------------------------
    reg hop_dv; reg [TAGW-1:0] hop_dt;
    genvar g;
    generate for (g = 0; g < NL; g = g + 1) begin : g_lane
        localparam integer P = (g < HOP) ? g : g + 1;
        assign cv[g] = s_cv[P];
        assign cd[g*CMDW +: CMDW] = s_cd[P*CMDW +: CMDW];
        assign s_dv[P] = dv[g];
        assign s_dt[P*TAGW +: TAGW] = dt[g*TAGW +: TAGW];
    end endgenerate
    assign s_dv[HOP] = hop_dv;  assign s_dt[HOP*TAGW +: TAGW] = hop_dt;
    assign s_dv[SPARE] = 1'b0;  assign s_dt[SPARE*TAGW +: TAGW] = {TAGW{1'b0}};

    // ---- completion snoop: per-slot op-done bitmap (own pin flops on the die completions) ---------------------------
    reg [NL-1:0] dv_q; reg [NL*TAGW-1:0] dt_q;
    always @(posedge ck or negedge c_run) if (!c_run) dv_q <= {NL{1'b0}}; else dv_q <= dv;
    always @(posedge ck) dt_q <= dt;
    wire acc = j_v && j_rdy;
    reg ns;                                          // slot the next accepted job takes (mirrors the sequencer)
    reg [NOPS-1:0] dn [0:1];
    integer e;
    always @(posedge ck or negedge c_run)
        if (!c_run) begin ns <= 1'b0; dn[0] <= {NOPS{1'b0}}; dn[1] <= {NOPS{1'b0}}; end
        else begin
            if (acc) begin ns <= ~ns; dn[ns] <= {NOPS{1'b0}}; end
            for (e = 0; e < NL; e = e + 1)
                if (dv_q[e]) dn[dt_q[e*TAGW + OPW]][dt_q[e*TAGW +: OPW]] <= 1'b1;
        end

    // ---- kit hand-off (port 7): 2-entry queue of hop descriptors, fired in order when the predecessor is done -------
    wire [CMDW-1:0] hc = s_cd[HOP*CMDW +: CMDW];
    reg [CMDW-1:0] hq [0:1]; reg hq_r, hq_w; reg [1:0] hq_n;
    wire [CMDW-1:0] hh = hq[hq_r];
    wire hh_s = hh[CMDW-1];
    wire [ARGW-1:0] hh_arg = hh[OPW +: ARGW];
    wire hh_ok = !hh_arg[7] || dn[hh_s][hh_arg[OPW-1:0]];
    wire h_fire = (hq_n != 0) && hh_ok;
    reg [1:0] h_fired;                               // per slot: the job's hand-off has fired
    reg am_seen; reg [NW-1:0] am_t; reg [31:0] am_x; reg no_am, sp_cmd;
    always @(posedge ck or negedge c_run)
        if (!c_run) begin
            hq_r <= 1'b0; hq_w <= 1'b0; hq_n <= 2'd0; hop_dv <= 1'b0; hop_dt <= {TAGW{1'b0}}; h_fired <= 2'b00;
            am_seen <= 1'b0; no_am <= 1'b0; sp_cmd <= 1'b0;
        end else begin
            if (s_cv[HOP]) begin hq[hq_w] <= hc; hq_w <= ~hq_w; end
            if (h_fire) hq_r <= ~hq_r;
            hq_n <= hq_n + (s_cv[HOP] ? 2'd1 : 2'd0) - (h_fire ? 2'd1 : 2'd0);
            hop_dv <= h_fire;
            hop_dt <= {hh_s, hh[OPW-1:0]};
            if (acc) h_fired[ns] <= 1'b0;
            if (h_fire) h_fired[hh_s] <= 1'b1;
            if (HEAD) begin
                if (am_v) am_seen <= 1'b1; else if (h_fire) am_seen <= 1'b0;
                if (h_fire && !am_seen) no_am <= 1'b1;
            end
            if (s_cv[SPARE]) sp_cmd <= 1'b1;
        end
    always @(posedge ck) if (am_v) begin am_t <= am_tok; am_x <= am_val; end

    // ---- job_done of a job without a hand-off: its context in accept order ------------------------------------------
    reg [2*NW-1:0] cx [0:1]; reg cx_r; reg old;      // old = the sequencer's oldest slot
    always @(posedge ck or negedge c_run)
        if (!c_run) begin cx_r <= 1'b0; old <= 1'b0; end
        else begin
            if (job_done) old <= ~old;
        end
    always @(posedge ck) if (acc) cx[ns] <= {j_d[NW +: NW], j_d[NW-1:0]};
    wire jd_ev = job_done && !h_fired[old];
    // DONE event and payload
    wire d_ev = (MUT == 2) ? acc : (h_fire || jd_ev);
    wire [2*NW-1:0] d_id = h_fire ? {hh[CMDW-2-USER_W-NW -: NW], hh[CMDW-2-USER_W -: NW]} : cx[old];   // {tok, pos}
    wire [NW+31:0] d_pl = HEAD ? {am_t, am_x} : {d_id[2*NW-1:NW], 11'd0, d_id[NW-1:0]};
    wire kd_acc, kd_flt, kd_v; wire [NW+31:0] kd_d;
    ot_s81_pulse_cdc #(.W(NW + 32), .QD(KQ)) u_kd (.s_clk(ck), .s_rst_n(c_run), .i_v(d_ev), .i_d(d_pl), .i_accept(kd_acc),
        .fault(kd_flt), .d_clk(ckv), .d_rst_n(v_run), .o_v(kd_v), .o_r(1'b1), .o_d(kd_d));
    always @(posedge ckv or negedge v_run)
        if (!v_run) t_kd <= '0;
        else t_kd <= {kd_v, kd_v ? kd_d : {(NW + 32){1'b0}}};

    // ---- sticky status (ck) --------------------------------------------------------------------------------------
    reg ksf_c1, ksf_c2;
    always @(posedge ck or negedge c_run)
        if (!c_run) begin ksf_c1 <= 1'b0; ksf_c2 <= 1'b0; flt <= 1'b0; fvec <= 8'd0; end
        else begin
            ksf_c1 <= ks_flt; ksf_c2 <= ksf_c1;
            fvec <= {s_code, sp_cmd, no_am, kd_flt, ksf_c2};
            flt <= s_flt || sp_cmd || no_am || kd_flt || ksf_c2;
        end
endmodule

// S81 layer die: the stage controller slab master (10 engine lanes of 84-b commands / 8-b tags, ADAPTER_CONTRACT_1011)
module dsfd_sp_seq #(parameter integer MUT = 0) (
    input  wire [0:0] ck, rst, ckv, rsv,
    input  wire pw_v, input wire [6:0] pw_a, input wire [27:0] pw_d, input wire [7:0] prog_len,
    input  wire [52:0] f_ks, output wire [53:0] t_kd,
    output wire [9:0] cv, output wire [10*84-1:0] cd, input wire [9:0] dv, input wire [10*8-1:0] dt,
    output wire flt, output wire [7:0] fvec
);
    wire busy_u; wire [31:0] jobs_u;
    ot_s81_kit_seq #(.HEAD(0), .MUT(MUT)) u (.ck(ck[0]), .rst(rst[0]), .ckv(ckv[0]), .rsv(rsv[0]),
        .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len), .f_ks(f_ks), .t_kd(t_kd),
        .cv(cv), .cd(cd), .dv(dv), .dt(dt), .am_v(1'b0), .am_tok(21'd0), .am_val(32'd0),
        .flt(flt), .fvec(fvec), .busy(busy_u), .st_jobs(jobs_u));
endmodule

// S81 head-root die: + the head slab's argmax {am_tok, am_val} returned in the DONE word
module dsfd_sp_seq_h #(parameter integer MUT = 0) (
    input  wire [0:0] ck, rst, ckv, rsv,
    input  wire pw_v, input wire [6:0] pw_a, input wire [27:0] pw_d, input wire [7:0] prog_len,
    input  wire [52:0] f_ks, output wire [53:0] t_kd,
    output wire [9:0] cv, output wire [10*84-1:0] cd, input wire [9:0] dv, input wire [10*8-1:0] dt,
    input  wire am_v, input wire [20:0] am_tok, input wire [31:0] am_val,
    output wire flt, output wire [7:0] fvec
);
    reg av_q; reg [20:0] at_q; reg [31:0] ax_q;     // pin flops on the head slab's argmax
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) av_q <= 1'b0; else av_q <= am_v;
    always @(posedge ck[0]) begin at_q <= am_tok; ax_q <= am_val; end
    wire busy_u; wire [31:0] jobs_u;
    ot_s81_kit_seq #(.HEAD(1), .MUT(MUT)) u (.ck(ck[0]), .rst(rst[0]), .ckv(ckv[0]), .rsv(rsv[0]),
        .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len), .f_ks(f_ks), .t_kd(t_kd),
        .cv(cv), .cd(cd), .dv(dv), .dt(dt), .am_v(av_q), .am_tok(at_q), .am_val(ax_q),
        .flt(flt), .fvec(fvec), .busy(busy_u), .st_jobs(jobs_u));
endmodule
