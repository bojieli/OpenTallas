`timescale 1ns/1ps
// tb_s81_ctrl_chain (stream ds-control, 2026-10-08): end-to-end control-plane bench of the S81 die control plane
// (ot_s81_ctrl) on the smallest vehicle that holds every mechanism: three dies -- SOURCE (stage 0, ROLE 1, id 1),
// one layer die (ROLE 0, id 2) and the head root (ROLE 2, id 3) -- joined by three reliable links
// (ot_dsrom_link_ct: CRC-32, go-back-N replay, credits; deterministic bit errors injected on both directions):
//     host -> SOURCE --HIDDEN--> LAYER --SIDE, HIDDEN--> HEAD --RESULT{token, STOP}--> SOURCE -> host completions
// Every die runs a stage program through its ot_s81_stage_seq; the engines are behavioural dataflow ports (a job
// starts when its descriptor is queued and its inputs are present, ends after its duration); the hop jobs are the
// real ot_s81_hop_tx; the vector memories are behavioural.  The head engine's argmax is token(u, p), a fixed
// function with EOS (1) forced at (0,3), (1,0) and (2,1).  The bench checks, against a reference of the stop rule:
//   * run A: CFG {EOS on, max_len 6}, LAUNCH {2 users, prompt 2, gen 8}: user 0 stops on EOS at step 3, user 1 ignores
//     the prompt-phase EOS at step 0 and stops at max_len (6 tokens);
//   * run B: CFG {EOS off, max_len none}, LAUNCH {3 users, prompt 2, gen 3}: every user stops at gen_len (4 tokens),
//     EOS ignored;
//   * a LAUNCH before boot_ok is refused (ERROR cause 8); every TOKEN completion is exact (user, position, token)
//     and in order, DONE closes each run, every payload / SIDE word lands bit-exact, the links replayed under errors,
//     no fault anywhere.
// +forge: a HIDDEN message with a wrong sender id is injected into the layer die's inbound stream once; PASS then
// requires the layer guard to latch F_SRC (2) (the negative control of the identity check).
// MUT=1 (SOURCE ignores STOP): must FAIL.
module tb_s81_ctrl_chain;
    parameter integer MUT = 0;
    localparam integer NW = 21, NENG = 12, NOPS = 16, OPW = 4, ARGW = 24, SUW = 10;
    localparam integer CMDW = 1 + SUW + 2 * NW + ARGW + OPW, TAGW = 1 + OPW;
    localparam integer XW = 8, VWA = 12, RXB = 0, TXB = 1024, SIDE_TXB = 2048, SIDE_BASE = 3072, SIDE_USH = 4;
    localparam integer MAXU = 4, ND = 3, EOS = 1;
    reg clk = 0, rst_n = 0;
    always #0.4166 clk = ~clk;
    integer cyc = 0;

    // ---- programs: per die, per op: port, duration, preds (bitmask), arg ----
    integer np [0:ND-1];
    integer pport [0:ND-1][0:NOPS-1], pdur [0:ND-1][0:NOPS-1], ppred [0:ND-1][0:NOPS-1], parg [0:ND-1][0:NOPS-1];
    task automatic setop(input integer d, input integer o, input integer port, input integer dur, input integer pm, input integer arg);
        begin pport[d][o] = port; pdur[d][o] = dur; ppred[d][o] = pm; parg[d][o] = arg; end
    endtask
    initial begin
        // die 0 = SOURCE: emb -> su -> fld -> hop HIDDEN to die id 2
        np[0] = 4;
        setop(0, 0, 9, 20, 0, 0); setop(0, 1, 1, 15, 1 << 0, 0); setop(0, 2, 0, 30, 1 << 1, 0);
        setop(0, 3, 7, 0, 1 << 2, (2 << 4) | 1);
        // die 1 = layer: su -> {svc, sel} -> fld -> hop SIDE (2 flits) + hop HIDDEN to die id 3
        np[1] = 6;
        setop(1, 0, 1, 10, 0, 0); setop(1, 1, 4, 25, 1 << 0, 0); setop(1, 2, 5, 12, 1 << 0, 0);
        setop(1, 3, 0, 40, (1 << 1) | (1 << 2), 0);
        setop(1, 4, 7, 0, 1 << 3, (2 << 16) | (3 << 4) | 3); setop(1, 5, 7, 0, 1 << 3, (3 << 4) | 1);
        // die 2 = head root: hc -> head (argmax) -> hop RESULT to die id 1 (go from the sampler)
        np[2] = 3;
        setop(2, 0, 2, 8, 0, 0); setop(2, 1, 8, 50, 1 << 0, 0); setop(2, 2, 7, 0, 1 << 1, (1 << 4) | 2);
    end

    // ---- dies ----
    wire [ND-1:0] i_v, i_r, i_l, o_v, o_r, o_l;
    wire [512*ND-1:0] i_d, o_d;
    wire [NENG*ND-1:0] c_v; wire [NENG*CMDW*ND-1:0] c_d;
    reg  [NENG*ND-1:0] d_v = 0; reg [NENG*TAGW*ND-1:0] d_t = 0;
    reg  [ND-1:0] hgo = 0;
    wire [ND-1:0] vwe, vre; wire [VWA*ND-1:0] vwa, vra; wire [512*ND-1:0] vwd; reg [512*ND-1:0] vrq = 0;
    reg  am_v = 0; reg [NW-1:0] am_pos = 0, am_tok = 0; reg [31:0] am_val = 0;
    reg  boot_ok = 0;
    reg  hc_valid = 0; wire hc_ready; reg [1:0] hc_op = 0; reg [7:0] hc_tag = 0, hc_user = 0; reg [NW-1:0] hc_pos = 0, hc_token = 0;
    wire cpl_valid; wire [2+8+8+NW+NW+32-1:0] cpl_data;
    wire [ND-1:0] flt, stk; wire [16*ND-1:0] fvec, snap; wire [32*ND-1:0] sjobs, stoks;
    reg  pw_v = 0; reg [OPW-1:0] pw_a = 0; reg [4+ARGW-1:0] pw_d = 0; reg [ND-1:0] pw_sel = 0;
    // forged-message injection into die 1's inbound stream
    reg  fg_v = 0; reg [511:0] fg_d = 0; wire fg_r;
    wire [ND-1:0] li_v; wire [512*ND-1:0] li_d; wire [ND-1:0] li_l; wire [ND-1:0] li_r;

    genvar g;
    generate for (g = 0; g < ND; g = g + 1) begin : g_die
        localparam integer ROLE = (g == 0) ? 1 : (g == 2) ? 2 : 0;
        localparam integer SLO = (g == 0) ? 3 : (g == 1) ? 1 : 2;
        localparam [15:0] TM = (g == 0) ? 16'h0004 : 16'h000A;
        wire [OPW:0] plen = np[g];
        ot_s81_ctrl #(.ROLE(ROLE), .MY_ID(g + 1), .NW(NW), .MAXU(MAXU), .VWA(VWA), .XW(XW), .RXB(RXB), .TXB(TXB),
            .SIDE_TXB(SIDE_TXB), .SIDE_RXB(0), .SIDE_BASE(SIDE_BASE), .SIDE_USH(SIDE_USH), .NOPS(NOPS), .NENG(NENG),
            .QD(8), .SRC_LO(SLO), .SRC_HI(SLO), .TYPE_MASK(TM), .LEN_SIDE_MAX(4), .PMAX(8), .CQ_DEPTH(64), .WDOG(200000),
            .STUCK(50000), .MUT(MUT)) u (
            .clk(clk), .rst_n(rst_n), .pw_v(pw_v && pw_sel[g]), .pw_a(pw_a), .pw_d(pw_d), .prog_len(plen),
            .cfg_users_static(12'(MAXU)),
            .in_valid(li_v[g]), .in_ready(li_r[g]), .in_data(li_d[g*512 +: 512]), .in_last(li_l[g]),
            .out_valid(o_v[g]), .out_ready(o_r[g]), .out_data(o_d[g*512 +: 512]), .out_last(o_l[g]),
            .cmd_v(c_v[g*NENG +: NENG]), .cmd_d(c_d[g*NENG*CMDW +: NENG*CMDW]),
            .dn_v(d_v[g*NENG +: NENG]), .dn_tag(d_t[g*NENG*TAGW +: NENG*TAGW]), .hop_go(hgo[g]),
            .vm_we(vwe[g]), .vm_waddr(vwa[g*VWA +: VWA]), .vm_wdata(vwd[g*512 +: 512]),
            .vm_re(vre[g]), .vm_raddr(vra[g*VWA +: VWA]), .vm_rq(vrq[g*512 +: 512]),
            .am_v(g == 2 ? am_v : 1'b0), .am_pos(am_pos), .am_tok(am_tok), .am_val(am_val),
            .boot_ok(boot_ok), .hc_valid(g == 0 ? hc_valid : 1'b0), .hc_ready(), .hc_op(hc_op), .hc_tag(hc_tag),
            .hc_user(hc_user), .hc_pos(hc_pos), .hc_token(hc_token), .cpl_valid(), .cpl_ready(1'b1), .cpl_data(),
            .fault(flt[g]), .fault_vec(fvec[g*16 +: 16]), .stuck(stk[g]), .stuck_snap(snap[g*16 +: 16]),
            .st_jobs(sjobs[g*32 +: 32]), .st_tokens(stoks[g*32 +: 32]));
        // links: die g's outbound -> die (g+1)%3's inbound
        localparam integer DST = (g + 1) % ND;
        wire [31:0] cs, sf, s1, s2, s3, s4, s5, s6, s7; wire lf; wire [3:0] lfc;
        ot_dsrom_link_ct #(.FLIT_BYTES(64), .TX_STAGES(2), .CHANNEL_CYCLES(20), .RX_STAGES(2), .CREDITS(16), .SEQW(8),
            .ERR_PERIOD_FWD(13 + g), .ERR_PERIOD_REV(7 + g), .ERR_OFFSET(3)) u_link (
            .clk(clk), .rst_n(rst_n), .channel_cycles(16'd20),
            .in_valid(o_v[g]), .in_ready(o_r[g]), .in_data(o_d[g*512 +: 512]), .in_last(o_l[g]),
            .out_valid(i_v[DST]), .out_ready(i_r[DST]), .out_data(i_d[DST*512 +: 512]), .out_last(i_l[DST]),
            .credit_stalls(cs), .fault(lf), .fault_code(lfc), .st_flits_tx(s1), .st_flits_rx_ok(s2), .st_crc_err(s3),
            .st_naks(s4), .st_replays(s5), .st_timeouts(s6), .st_retx_flits(s7), .st_max_replay_occ(sf));
    end endgenerate
    assign hc_ready = g_die[0].u.hc_ready;
    assign cpl_valid = g_die[0].u.cpl_valid;
    assign cpl_data = g_die[0].u.cpl_data;
    // die 1 inbound: link output, or the forged message while it is offered (between messages)
    reg fg_sel = 0;
    assign li_v = {i_v[2], fg_sel ? fg_v : i_v[1], i_v[0]};
    assign li_d = {i_d[1023+512:1024], fg_sel ? fg_d : i_d[1023:512], i_d[511:0]};
    assign li_l = {i_l[2], fg_sel ? 1'b1 : i_l[1], i_l[0]};
    assign i_r  = {li_r[2], fg_sel ? 1'b0 : li_r[1], li_r[0]};
    assign fg_r = fg_sel && li_r[1];

    // ---- behavioural vector memories ----
    reg [511:0] vm [0:ND-1][0:(1<<VWA)-1];
    integer d, o, e, k;
    integer vd;
    always @(posedge clk) for (vd = 0; vd < ND; vd = vd + 1) begin
        if (vwe[vd]) vm[vd][vwa[vd*VWA +: VWA]] <= vwd[vd*512 +: 512];
        if (vre[vd]) vrq[vd*512 +: 512] <= vm[vd][vra[vd*VWA +: VWA]];
    end
    function automatic [511:0] pat(input integer die, input integer u, input integer p, input integer w);
        pat = {16{32'(die * 1000003 + u * 7919 + p * 104729 + w * 31 + 17)}} ^ {u[7:0], p[7:0], w[7:0], 488'h0};
    endfunction
    function automatic integer tokf(input integer u, input integer p);
        integer t;
        begin
            t = (u * 7919 + p * 104729 + 12345) % 129280;
            if (t == EOS) t = 2;
            if ((u == 0 && p == 3) || (u == 1 && p == 0) || (u == 2 && p == 1)) t = EOS;
            tokf = t;
        end
    endfunction

    // ---- engine models: per die, per slot (2): job context, input-ready time, op state ----
    integer jctx_u [0:ND-1][0:1], jctx_p [0:ND-1][0:1], in_rdy [0:ND-1][0:1];
    integer ost [0:ND-1][0:1][0:NOPS-1], oend [0:ND-1][0:1][0:NOPS-1], ocmd [0:ND-1][0:1][0:NOPS-1];
    integer q [0:ND-1][0:NENG-1][0:63]; integer qh [0:ND-1][0:NENG-1], qt [0:ND-1][0:NENG-1];
    integer dq [0:ND-1][0:NENG-1][0:63]; integer dh [0:ND-1][0:NENG-1], dt2 [0:ND-1][0:NENG-1];
    integer hop_seen [0:ND-1];
    integer errors = 0, pay_ok = 0, side_ok = 0;
    // reference stop model (per run): the expected TOKEN completions per user
    integer exp_n [0:MAXU-1], exp_pos [0:MAXU-1][0:31], exp_tok [0:MAXU-1][0:31], got_n [0:MAXU-1];
    integer run_users, run_plen, run_glen, run_maxl, run_eos, runs_done = 0, dones = 0, errs_cpl = 0, boot_refused = 0;
    integer prompt [0:MAXU-1][0:7];
    task automatic ref_run(input integer users, input integer plen, input integer glen, input integer maxl, input integer eosen);
        integer u, p, t, cont, gen;
        begin
            for (u = 0; u < MAXU; u = u + 1) begin exp_n[u] = 0; got_n[u] = 0; end
            for (u = 0; u < users; u = u + 1) begin
                p = 0; cont = 1;
                while (cont) begin
                    t = tokf(u, p);
                    exp_pos[u][exp_n[u]] = p; exp_tok[u][exp_n[u]] = t; exp_n[u] = exp_n[u] + 1;
                    gen = (p + 1 >= plen);
                    cont = (p + 1 < plen + glen - 1) && !(gen && ((eosen && t == EOS) || (p + 1 >= maxl))) && !(p + 1 >= maxl);
                    p = p + 1;
                end
            end
        end
    endtask

    function automatic integer ready_at(input integer dd, input integer s, input integer op);
        integer r, m;
        begin
            r = in_rdy[dd][s];
            if (r < 0) r = 1 << 30;
            for (m = 0; m < NOPS; m = m + 1)
                if (ppred[dd][op] & (1 << m)) r = (oend[dd][s][m] < 0) ? (1 << 30) : ((oend[dd][s][m] > r) ? oend[dd][s][m] : r);
            ready_at = r;
        end
    endfunction

    // slot of a new job at die dd: track the pkg controller's mirror
    integer nslot [0:ND-1];
    integer i0;
    initial for (i0 = 0; i0 < ND; i0 = i0 + 1) begin nslot[i0] = 0; hop_seen[i0] = 0; end

    task automatic job_reset(input integer dd, input integer s);
        integer m;
        for (m = 0; m < NOPS; m = m + 1) begin ost[dd][s][m] = -1; oend[dd][s][m] = -1; ocmd[dd][s][m] = -1; end
    endtask

    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (cyc % 5000 == 0 && $test$plusargs("trace"))
            $display("T cyc=%0d dones=%0d got=%0d,%0d,%0d jobs=%0d,%0d,%0d flt=%b fvec=%h,%h,%h stuck=%b hc_ready=%b qv=%0d,%0d act=%b users=%0d nu_ok=%b",
                cyc, dones, got_n[0], got_n[1], got_n[2], sjobs[31:0], sjobs[63:32], sjobs[95:64], flt, fvec[15:0], fvec[31:16], fvec[47:32], stk, hc_ready,
                qt[1][1]-qh[1][1], qt[1][0]-qh[1][0], g_die[0].u.g_src.u_hq.active, g_die[0].u.cfg_users, g_die[0].u.u_pkg.nu_ok);
        if (cyc > 400000) begin $display("TB_S81_CTRL_CHAIN TIMEOUT cyc=%0d dones=%0d FAIL", cyc, dones); $finish; end
        hgo = 0; am_v = 0;
        for (d = 0; d < ND; d = d + 1) begin
            // new job accepted by the sequencer (snoop the pkg controller's handshake)
            if (g_die_job_v(d)) begin
                jctx_u[d][nslot[d]] = g_die_job_u(d); jctx_p[d][nslot[d]] = g_die_job_p(d);
                in_rdy[d][nslot[d]] = (d == 0) ? cyc + 1 : -1;
                job_reset(d, nslot[d]);
                nslot[d] = 1 - nslot[d];
            end
            // payload landed (non-SOURCE): the last RX word of a slot written
            if (d != 0 && vwe[d] && (vwa[d*VWA +: VWA] == RXB + XW - 1 || vwa[d*VWA +: VWA] == RXB + 2 * XW - 1)) begin : land
                integer s, w;
                s = (vwa[d*VWA +: VWA] == RXB + XW - 1) ? 0 : 1;
                in_rdy[d][s] = cyc + 1;
            end
            // descriptors
            for (e = 0; e < NENG; e = e + 1) if (c_v[d*NENG + e]) begin : rx
                reg [CMDW-1:0] c; integer s, op;
                c = c_d[(d*NENG + e)*CMDW +: CMDW];
                s = c[CMDW-1]; op = c[OPW-1:0];
                if (pport[d][op] != e || c[OPW +: ARGW] != 24'(parg[d][op]) ||
                    c[CMDW-2 -: SUW] != SUW'(jctx_u[d][s]) || c[CMDW-2-SUW -: NW] != NW'(jctx_p[d][s])) begin
                    errors = errors + 1; $display("ERR desc die %0d port %0d op %0d", d, e, op);
                end
                ocmd[d][s][op] = cyc;
                if ($test$plusargs("dbg")) $display("D cyc=%0d die=%0d slot=%0d op=%0d desc port=%0d", cyc, d, s, op, e);
                q[d][e][qt[d][e] % 64] = s * NOPS + op; qt[d][e] = qt[d][e] + 1;
            end
            // hop descriptors (internal port, snooped)
            if (g_die_hop_cv(d)) begin : hrx
                reg [CMDW-1:0] c; integer s, op;
                c = g_die_hop_cd(d); s = c[CMDW-1]; op = c[OPW-1:0];
                if (pport[d][op] != 7 || c[OPW +: ARGW] != 24'(parg[d][op])) begin errors = errors + 1; $display("ERR hop desc die %0d op %0d", d, op); end
                ocmd[d][s][op] = cyc;
            end
            // engines (not the hop port: it is the real ot_s81_hop_tx)
            for (e = 0; e < NENG; e = e + 1) if (e != 7) begin : eng
                integer x, s, op, go;
                go = 1;
                while (go && qh[d][e] != qt[d][e]) begin
                    x = q[d][e][qh[d][e] % 64]; s = x / NOPS; op = x % NOPS;
                    if (ready_at(d, s, op) <= cyc) begin
                        ost[d][s][op] = cyc; oend[d][s][op] = cyc + pdur[d][op]; qh[d][e] = qh[d][e] + 1;
                        if ($test$plusargs("dbg")) $display("D cyc=%0d die=%0d slot=%0d op=%0d start", cyc, d, s, op);
                    end else go = 0;
                end
            end
            // completions due now; side effects of the producers
            for (k = 0; k < 2; k = k + 1) for (o = 0; o < np[d]; o = o + 1)
                if (oend[d][k][o] == cyc && pport[d][o] != 7) begin : fin
                    integer w;
                    dq[d][pport[d][o]][dt2[d][pport[d][o]] % 64] = k * NOPS + o; dt2[d][pport[d][o]] = dt2[d][pport[d][o]] + 1;
                    // the producer of the hop payload writes the TX region (HIDDEN) / SIDE region
                    if (pport[d][o] == 0) begin
                        for (w = 0; w < XW; w = w + 1) vm[d][TXB + k * XW + w] = pat(d, jctx_u[d][k], jctx_p[d][k], w);
                        for (w = 0; w < 2; w = w + 1) vm[d][SIDE_TXB + k * 256 + w] = pat(d + 10, jctx_u[d][k], jctx_p[d][k], w);
                    end
                    if (d == 2 && pport[d][o] == 8) begin
                        am_v = 1; am_pos = jctx_p[d][k]; am_tok = tokf(jctx_u[d][k], jctx_p[d][k]); am_val = 32'h3f800000;
                    end
                end
            // hop go (SOURCE, layer): one pulse per hop job whose inputs are done, in program order
            if (d != 2) begin : hg
                integer s2, op2, found;
                found = 0;
                for (k = 0; k < 2 && !found; k = k + 1) for (o = 0; o < np[d] && !found; o = o + 1)
                    if (pport[d][o] == 7 && ost[d][k][o] < 0 && ocmd[d][k][o] >= 0 && ready_at(d, k, o) <= cyc) begin
                        ost[d][k][o] = cyc; found = 1;
                    end
                if (found) hgo[d] = 1;
                if (found && $test$plusargs("dbg")) $display("D cyc=%0d die=%0d hop go", cyc, d);
            end
            for (e = 0; e < NENG; e = e + 1) begin
                d_v[d*NENG + e] = 0;
                if (e != 7 && dh[d][e] != dt2[d][e]) begin : rep
                    integer y;
                    y = dq[d][e][dh[d][e] % 64]; dh[d][e] = dh[d][e] + 1;
                    d_v[d*NENG + e] = 1; d_t[(d*NENG + e)*TAGW +: TAGW] = {1'(y / NOPS), OPW'(y % NOPS)};
                end
            end
            // hop completions from the real framer: record ends (for job bookkeeping only)
            if (g_die_hop_dn(d)) begin : hd
                reg [OPW:0] t;
                t = g_die_hop_tag(d);
                oend[d][t[OPW]][t[OPW-1:0]] = cyc;
            end
        end
        // payload checks when a non-SOURCE die's slot input lands
        for (d = 1; d < ND; d = d + 1) for (k = 0; k < 2; k = k + 1)
            if (in_rdy[d][k] == cyc) begin : pc
                integer w, bad;
                bad = 0;
                for (w = 0; w < XW; w = w + 1)
                    if (vm[d][RXB + k * XW + w] !== pat(d - 1, jctx_u[d][k], jctx_p[d][k], w)) bad = 1;
                if (bad) begin errors = errors + 1; $display("ERR payload die %0d slot %0d", d, k); end else pay_ok = pay_ok + 1;
                if (d == 2) begin
                    for (w = 0; w < 2; w = w + 1)
                        if (vm[2][SIDE_BASE + (jctx_u[2][k] << SIDE_USH) + w] !== pat(11, jctx_u[2][k], jctx_p[2][k], w)) bad = 1;
                    if (bad) begin errors = errors + 1; $display("ERR side"); end else side_ok = side_ok + 1;
                end
            end
        // host completions
        if (cpl_valid) begin : cp
            reg [1:0] kd; reg [7:0] u; reg [NW-1:0] p, t;
            kd = cpl_data[2+8+8+NW+NW+32-1 -: 2]; u = cpl_data[NW+NW+32 +: 8];
            p = cpl_data[NW+32 +: NW]; t = cpl_data[32 +: NW];
            if ($test$plusargs("trace")) $display("CPL cyc=%0d kind=%0d user=%0d pos=%0d tok=%0d", cyc, kd, u, p, t);
            if (kd == 1) begin
                if (u >= MAXU || got_n[u] >= exp_n[u] || p != exp_pos[u][got_n[u]] || t != exp_tok[u][got_n[u]]) begin
                    errs_cpl = errs_cpl + 1; $display("ERR cpl user %0d pos %0d tok %0d (expected #%0d pos %0d tok %0d)", u, p, t,
                        got_n[u], exp_pos[u][got_n[u]], exp_tok[u][got_n[u]]);
                end
                if (u < MAXU) got_n[u] = got_n[u] + 1;
            end else if (kd == 2) dones = dones + 1;
            else if (kd == 3 && t == 8) boot_refused = boot_refused + 1;
            else if (kd == 3) begin errs_cpl = errs_cpl + 1; $display("ERR cpl error cause %0d", t); end
        end
    end
    // hierarchical snoops
    function automatic bit g_die_job_v(input integer dd);
        case (dd) 0: g_die_job_v = g_die[0].u.u_pkg.job_v && g_die[0].u.u_pkg.job_rdy;
                  1: g_die_job_v = g_die[1].u.u_pkg.job_v && g_die[1].u.u_pkg.job_rdy;
                  default: g_die_job_v = g_die[2].u.u_pkg.job_v && g_die[2].u.u_pkg.job_rdy; endcase
    endfunction
    function automatic integer g_die_job_u(input integer dd);
        case (dd) 0: g_die_job_u = g_die[0].u.u_pkg.job_user; 1: g_die_job_u = g_die[1].u.u_pkg.job_user;
                  default: g_die_job_u = g_die[2].u.u_pkg.job_user; endcase
    endfunction
    function automatic integer g_die_job_p(input integer dd);
        case (dd) 0: g_die_job_p = g_die[0].u.u_pkg.job_pos; 1: g_die_job_p = g_die[1].u.u_pkg.job_pos;
                  default: g_die_job_p = g_die[2].u.u_pkg.job_pos; endcase
    endfunction
    function automatic bit g_die_hop_cv(input integer dd);
        case (dd) 0: g_die_hop_cv = g_die[0].u.s_cv[7]; 1: g_die_hop_cv = g_die[1].u.s_cv[7]; default: g_die_hop_cv = g_die[2].u.s_cv[7]; endcase
    endfunction
    function automatic [CMDW-1:0] g_die_hop_cd(input integer dd);
        case (dd) 0: g_die_hop_cd = g_die[0].u.s_cd[7*CMDW +: CMDW]; 1: g_die_hop_cd = g_die[1].u.s_cd[7*CMDW +: CMDW];
                  default: g_die_hop_cd = g_die[2].u.s_cd[7*CMDW +: CMDW]; endcase
    endfunction
    function automatic bit g_die_hop_dn(input integer dd);
        case (dd) 0: g_die_hop_dn = g_die[0].u.h_dv; 1: g_die_hop_dn = g_die[1].u.h_dv; default: g_die_hop_dn = g_die[2].u.h_dv; endcase
    endfunction
    function automatic [OPW:0] g_die_hop_tag(input integer dd);
        case (dd) 0: g_die_hop_tag = g_die[0].u.h_dt; 1: g_die_hop_tag = g_die[1].u.h_dt; default: g_die_hop_tag = g_die[2].u.h_dt; endcase
    endfunction

    // ---- host script ----
    task automatic hcmd(input [1:0] op, input [7:0] tag, input [7:0] u, input integer p, input integer t);
        begin
            @(negedge clk); hc_valid = 1; hc_op = op; hc_tag = tag; hc_user = u; hc_pos = p; hc_token = t;
            @(posedge clk); while (!hc_ready) @(posedge clk);
            @(negedge clk); hc_valid = 0;
        end
    endtask
    integer u_, p_, t_end, forge = 0, fg_done = 0, id_, io_, ie_, ik_;
    initial begin
        for (id_ = 0; id_ < ND; id_ = id_ + 1) for (ie_ = 0; ie_ < NENG; ie_ = ie_ + 1) begin qh[id_][ie_] = 0; qt[id_][ie_] = 0; dh[id_][ie_] = 0; dt2[id_][ie_] = 0; end
        for (id_ = 0; id_ < ND; id_ = id_ + 1) for (ik_ = 0; ik_ < 2; ik_ = ik_ + 1) begin in_rdy[id_][ik_] = -1; jctx_u[id_][ik_] = 0; jctx_p[id_][ik_] = 0; job_reset(id_, ik_); end
        if ($test$plusargs("forge")) forge = 1;
        repeat (5) @(posedge clk); rst_n = 1;
        // program load per die
        for (id_ = 0; id_ < ND; id_ = id_ + 1) for (io_ = 0; io_ < np[id_]; io_ = io_ + 1) begin
            @(negedge clk); pw_v = 1; pw_sel = 1 << id_; pw_a = io_; pw_d = {4'(pport[id_][io_]), 24'(parg[id_][io_])};
        end
        @(negedge clk); pw_v = 0; pw_sel = 0;
        for (u_ = 0; u_ < MAXU; u_ = u_ + 1) for (p_ = 0; p_ < 8; p_ = p_ + 1) prompt[u_][p_] = 100 + u_ * 10 + p_;
        // prompts (the prompt tokens are fed at prompt positions; tokf models the head's argmax)
        for (u_ = 0; u_ < 3; u_ = u_ + 1) for (p_ = 0; p_ < 2; p_ = p_ + 1) hcmd(1, 0, u_, p_, prompt[u_][p_]);
        // LAUNCH before boot: refused
        hcmd(2, 8'h0B, 2, 2, 8);
        repeat (20) @(posedge clk);
        boot_ok = 1;
        // run A
        hcmd(3, 8'h01, 1, 6, EOS);          // CFG: EOS on, max_len 6
        ref_run(2, 2, 8, 6, 1);
        run_users = 2;
        hcmd(2, 8'hA0, 2, 2, 8);
        t_end = cyc + 200000;
        while (dones < 1 && cyc < t_end) @(posedge clk);
        for (u_ = 0; u_ < 2; u_ = u_ + 1) if (got_n[u_] != exp_n[u_]) begin errs_cpl = errs_cpl + 1; $display("ERR run A user %0d got %0d exp %0d", u_, got_n[u_], exp_n[u_]); end
        repeat (50) @(posedge clk);
        // run B
        hcmd(3, 8'h02, 0, 0, EOS);          // CFG: EOS off, no max_len
        ref_run(3, 2, 3, 1 << 21, 0);
        hcmd(2, 8'hB0, 3, 2, 3);
        t_end = cyc + 200000;
        while (dones < 2 && cyc < t_end) @(posedge clk);
        for (u_ = 0; u_ < 3; u_ = u_ + 1) if (got_n[u_] != exp_n[u_]) begin errs_cpl = errs_cpl + 1; $display("ERR run B user %0d got %0d exp %0d", u_, got_n[u_], exp_n[u_]); end
        // forged message into the layer die (a wrong sender id), between messages
        if (forge) begin
            @(negedge clk);
            fg_d = 0; fg_d[11:0] = 12'd2; fg_d[23:12] = 12'd7; fg_d[27:24] = 4'd1; fg_d[39:28] = 12'd0;
            fg_sel = 1; fg_v = 1;
            @(posedge clk); while (!fg_r) @(posedge clk);
            @(negedge clk); fg_v = 0; fg_sel = 0;
            repeat (10) @(posedge clk);
        end
        repeat (20) @(posedge clk);
        begin : verdict
            integer pass, gf;
            gf = g_die[1].u.u_guard.fault_code;
            pass = (errors == 0 && errs_cpl == 0 && dones == 2 && boot_refused == 1 && pay_ok > 0 && side_ok > 0);
            if (forge) pass = pass && gf == 2 && !flt[0] && !flt[2];
            else       pass = pass && flt == 0 && stk == 0;
            $display("TB_S81_CTRL_CHAIN mut=%0d forge=%0d cycles=%0d dones=%0d boot_refused=%0d payloads=%0d sides=%0d desc_err=%0d cpl_err=%0d faults=%b fvec=%h,%h,%h guard1=%0d crc_err=%0d,%0d,%0d replays=%0d,%0d,%0d jobs=%0d,%0d,%0d tokens=%0d %s",
                MUT, forge, cyc, dones, boot_refused, pay_ok, side_ok, errors, errs_cpl, flt, fvec[15:0], fvec[31:16], fvec[47:32], gf,
                g_die[0].u_link.st_crc_err, g_die[1].u_link.st_crc_err, g_die[2].u_link.st_crc_err,
                g_die[0].u_link.st_replays, g_die[1].u_link.st_replays, g_die[2].u_link.st_replays,
                sjobs[31:0], sjobs[63:32], sjobs[95:64], stoks[31:0], pass ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
