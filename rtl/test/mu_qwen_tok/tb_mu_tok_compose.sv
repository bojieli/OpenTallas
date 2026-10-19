`timescale 1ns/1ps
// MU-ADOPT-TOK 2026-10-19: MU.TOK.QW command-plane smoke -- the three MU RTL blocks composed and driven by the compiled
// 4-user calendar (tools/qwen_static_schedule/mu_tok_cases.py):
//   qfd_dv_cmd_cal_mu (NU 4)  the DV compute die's static command calendar with NU playheads (R1/R5)
//   qfd_dv_amax_mu    (NU 4)  the per-user chunked LM-head running argmax (R4), fed by the calendar's issued STN / AMAX
//                             words; the user fields are the ADOPTION GLUE this bench defines: STN cmd[52:51] and AMAX
//                             cmd[9:8] = cmd_user (the image leaves them 0, as for the XC tag)
//   qkd_kv_mu_wrow / _rrow    the KV die's per-user row insertion (R6), applied to the q record of every attention op
//                             (the loc_seg entry) with the issuing user and that user's layer (its last stage - 1)
// Station results: behavioural (an amax STN returns RW result words of 16 logits, the first STN_LAT edges after its
// issue, then one every RW_GAP edges; logit = hash(user, token, row) -- the same function in mu_tok_smoke.py; two
// words on one edge = "RCOL", a station result-bus clash the calendar must exclude).  Event file (+EV, sorted "cycle kind hex", applied before posedge):
//   0 PW {addr10, data64}  1 DW {addr3, data64}  2 START {user2, stage6}  3 AMAX PRIME (open user's first head)
// Log (+LOG): "c CMD u hex", "c SUI u pidx", "c XCI u", "c EMB u", "c SEG u base", "c DONE u", "c FAULT code",
//   "c AM u tok idx val" (argmax emitted), "c KV u layer rrow wrow_xa wrow_es", "c MUF" (amax fault rise),
//   "c RF" (KV range fault), "c RCOL" (station result-bus clash), "c EMPTY u" (emit of an empty run), "c END fault code mism".
// GLUE_MUT (bench-side mutants of the adoption glue): 1 = the KV row user taken from the LAST START's user instead of
//   the issuing playhead (cmd_user);  2 = STN user field left 0 (glue not applied).
module tb_mu_tok_compose;
    parameter integer NU = 4, MUT = 0, AMUT = 0, GLUE_MUT = 0, UVM_STRIDE = 16384, PIDX_STRIDE = 64, STN_LAT = 40,
              RW = 16, RW_GAP = 20;
    localparam integer UB = 2;
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst_n = 1'b0;
    reg pw_v = 0, dw_v = 0, start = 0; reg [9:0] pw_addr = 0; reg [63:0] pw_data = 0, dw_data = 0; reg [2:0] dw_addr = 0;
    reg [5:0] stage = 0; reg [UB-1:0] start_user = 0;
    wire [115:0] cmd; wire [UB-1:0] cmd_user, done_user;
    wire loc_emb, loc_seg, su_issue, xc_issue, image_ready, running, done, fault;
    wire [11:0] loc_base; wire [8:0] su_pidx; wire [75:0] pobs; wire [68:0] dobs; wire [NU-1:0] running_u; wire [5:0] fcode;
    qfd_dv_cmd_cal_mu #(.MUT(MUT), .NU(NU), .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE)) u_cal (.ck(ck), .rst_n(rst_n),
        .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data), .dw_v(dw_v), .dw_addr(dw_addr), .dw_data(dw_data),
        .start(start), .stage(stage), .start_user(start_user), .start_rng(1'b0), .start_first(10'd0), .start_cnt(10'd0), .cmd(cmd), .cmd_user(cmd_user), .loc_emb(loc_emb),
        .loc_seg(loc_seg), .loc_base(loc_base), .su_issue(su_issue), .su_pidx(su_pidx), .xc_issue(xc_issue),
        .program_obs(pobs), .descriptor_obs(dobs), .image_ready(image_ready), .running(running), .running_u(running_u),
        .done(done), .done_user(done_user), .fault(fault), .fault_code(fcode));

    // ---------------------------------------------------------------- argmax (R4) on the issued command stream
    wire       is_stn = cmd[0] && cmd[3:1] == 3'd2;
    wire       is_am  = cmd[0] && cmd[3:1] == 3'd6;
    reg        prime_v = 0; reg [1:0] prime_u = 0;
    wire [1:0] stn_user = (GLUE_MUT == 2) ? 2'd0 : cmd_user;          // glue: STN cmd[52:51] = cmd_user
    wire       c_am = is_am || prime_v;
    wire       am_clr = prime_v ? 1'b1 : cmd[4];
    wire       am_emit_cmd = prime_v ? 1'b0 : cmd[5];
    wire [1:0] am_user = prime_v ? prime_u : cmd_user;                  // glue: AMAX cmd[9:8] = cmd_user
    reg        r_v = 0; reg [23:0] r_addr = 0; reg [511:0] r_d = 0;
    wire       am_v, emit_empty, mu_fault; wire [23:0] am_idx; wire [31:0] am_val;
    qfd_dv_amax_mu #(.NU(NU), .MUT(AMUT)) u_am (.ck(ck), .rst(rst_n), .c_stn(is_stn), .stn_amax_bit(cmd[50]),
        .stn_user(stn_user), .r_v(r_v), .r_addr(r_addr), .r_d(r_d), .c_am(c_am), .am_clr(am_clr),
        .am_emit_cmd(am_emit_cmd), .am_user(am_user), .am_v(am_v), .am_idx(am_idx), .am_val(am_val),
        .emit_empty(emit_empty), .mu_fault(mu_fault));

    // ---------------------------------------------------------------- KV row insertion (R6) on the q record
    reg  [1:0]  last_su = 0;                                             // last START's user (GLUE_MUT 1)
    reg  [5:0]  ustage [0:3];
    wire [1:0]  kv_u = (GLUE_MUT == 1) ? last_su : cmd_user;
    wire [5:0]  kv_l = ustage[cmd_user] - 6'd1;
    wire [18:0] kv_row = 19'd64 + {13'd0, kv_l};
    wire [42:0] rr_i = {10'd0, 2'd0, 11'd1, kv_row, 1'b0};
    wire [42:0] rr_o;
    wire [28:0] xa_o; wire [287:0] es_o; wire range_fault;
    wire [287:0] es_i = {12'd0, kv_row, 256'd0, 1'b1};                   // lane {.., row19 [275:257], data256, w_v=1}
    qkd_kv_mu_rrow #(.MU(1)) u_rr (.user(kv_u), .cmd_i(rr_i), .cmd_o(rr_o));
    qkd_kv_mu_wrow #(.MU(1), .NL(1)) u_wr (.user(kv_u), .es_i(es_i), .xa_i({kv_row, 10'd0}), .es_o(es_o), .xa_o(xa_o),
        .range_fault(range_fault));

    // ---------------------------------------------------------------- station result model (behavioural)
    function automatic [31:0] logit(input integer u, input integer tok, input integer idx);
        reg [31:0] h;
        begin
            h = 32'(u) * 32'h9E3779B1 ^ 32'(tok) * 32'h85EBCA77 ^ 32'(idx) * 32'hC2B2AE3D;
            h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; h = h ^ (h >> 12);
            logit = {1'b0, 24'h3f0000, h[6:0]};                  // small positive range: many exact ties
        end
    endfunction
    integer tok [0:3], chunk [0:3];
    reg     rq_v [0:4095]; integer rq_u [0:4095], rq_tok [0:4095], rq_row [0:4095]; integer slot, rk;
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0, i;
    reg [127:0] ev; reg have; reg [1023:0] evf, lgf; reg flt_l = 0, muf_l = 0;
    reg [1:0] emit_u = 0; reg emit_pend = 0;
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        for (i = 0; i < 4; i = i + 1) begin tok[i] = 0; chunk[i] = 0; ustage[i] = 6'd1; end
        for (i = 0; i < 4096; i = i + 1) rq_v[i] = 1'b0;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w"); cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            // -------- observe the edge just taken (label cyc)
            if (cmd != 116'd0) $fdisplay(lg, "%0d CMD %0d %h", cyc, cmd_user, cmd);
            if (su_issue) $fdisplay(lg, "%0d SUI %0d %h", cyc, cmd_user, su_pidx);
            if (xc_issue) $fdisplay(lg, "%0d XCI %0d", cyc, cmd_user);
            if (loc_emb) $fdisplay(lg, "%0d EMB %0d", cyc, cmd_user);
            if (loc_seg) begin
                $fdisplay(lg, "%0d SEG %0d %h", cyc, cmd_user, loc_base);
                $fdisplay(lg, "%0d KV %0d %0d %0d %0d %0d", cyc, cmd_user, kv_l, rr_o[19:1], xa_o[28:10], es_o[275:257]);
                if (range_fault) $fdisplay(lg, "%0d RF", cyc);
            end
            if (done) $fdisplay(lg, "%0d DONE %0d", cyc, done_user);
            if (fault && !flt_l) $fdisplay(lg, "%0d FAULT %b", cyc, fcode);
            flt_l = fault;
            if (mu_fault && !muf_l) $fdisplay(lg, "%0d MUF", cyc);
            muf_l = mu_fault;
            if (am_v) $fdisplay(lg, "%0d AM %0d %0d %0d %h", cyc, emit_u, tok[emit_u] - 1, am_idx, am_val);
            if (emit_empty) $fdisplay(lg, "%0d EMPTY %0d", cyc, emit_u);
            // the station: an amax STN issued on this edge returns its 16 logits STN_LAT edges later
            if (is_stn && cmd[50]) begin
                for (rk = 0; rk < RW; rk = rk + 1) begin
                    slot = (cyc + STN_LAT + RW_GAP * rk) % 4096;
                    if (rq_v[slot]) $fdisplay(lg, "%0d RCOL", cyc + STN_LAT + RW_GAP * rk);
                    rq_v[slot] = 1'b1; rq_u[slot] = cmd_user; rq_tok[slot] = tok[cmd_user];
                    rq_row[slot] = chunk[cmd_user] * 16 * RW + 16 * rk;
                end
                chunk[cmd_user] = chunk[cmd_user] + 1;
            end
            if (is_am && cmd[5]) begin emit_u = cmd_user; tok[cmd_user] = tok[cmd_user] + 1; end
            if (is_am && cmd[4]) chunk[cmd_user] = 0;
            // -------- inputs for the next posedge (cyc + 1)
            r_v = 1'b0; r_d = 512'd0; r_addr = 24'd0;
            slot = (cyc + 1) % 4096;
            if (rq_v[slot]) begin
                r_v = 1'b1; r_addr = 24'(rq_row[slot]);
                for (i = 0; i < 16; i = i + 1) r_d[32*i +: 32] = logit(rq_u[slot], rq_tok[slot], rq_row[slot] + i);
                rq_v[slot] = 1'b0;
            end
            pw_v = 1'b0; dw_v = 1'b0; start = 1'b0; prime_v = 1'b0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw_v = 1'b1; pw_addr = ev[73:64]; pw_data = ev[63:0]; end
                    1: begin dw_v = 1'b1; dw_addr = ev[66:64]; dw_data = ev[63:0]; end
                    2: begin start = 1'b1; stage = ev[5:0]; start_user = ev[7:6]; last_su = ev[7:6];
                             ustage[ev[7:6]] = (ev[5:0] >= 6'd1 && ev[5:0] <= 6'd36) ? ev[5:0] : ustage[ev[7:6]]; end
                    3: begin prime_v = 1'b1; prime_u = ev[1:0]; end
                    default: $fatal(1, "bad kind %0d", ek);
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (have && ec <= cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END %0d %b %0d", cyc, fault, fcode, mu_fault);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
