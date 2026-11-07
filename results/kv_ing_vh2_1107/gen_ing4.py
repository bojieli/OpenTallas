#!/usr/bin/env python3
"""KV-ING-8 11-07 qkd_hr_ingest_eng vH2 (conservative form) on r3 + cut 19 (usage: repo root, no args).
Writes results/kv_ing_vh2_1107/rtl/: engine qkd_host_native_engine_ing4 and the wrapper qkd_hr_ingest_eng.
Cuts on r3+19 (classes as in the engine header; bench/tb_ing4.sv is the lock-step proof against the source engine):
 20 V/R safe  free-running face flop on every in_data, d_data pin; in_v / d_v land in one flop each.  in FIFO 3 entries, descriptor FIFO gone
              (face flop writes dq directly).  rdy flops do not look at the pins.  +1 edge port -> engine, full rate kept.
 21 V/R safe  write face: engine -> 2-entry skid -> port register.  The engine sees only ready flops (next state from the skid count, no w_rdy cone).
              w_rdy reaches only the port register band.  +1 edge engine -> port, full rate kept.
 22 V/R safe  done travels with its write through the skid; a stream done waits for the face to drain and blocks the next dispatch.
              n_sectors and done reach the top-left pins through one mid hop (+1 edge), same relation done <-> count as the source.
 23 Exact     write mux selects: per-slice registered copies from the next state of st_mode / st_ph / take (was one decode net with 256 loads).
 24 Exact     RAW write address: counter loaded at dispatch instead of base + st_row.
 26 V/R safe  sec_q, e2_*: one stage between the macro read registers and the output FIFO (rule 2 distance budget), +1 edge.
 25 Exact     st_row in two halves with a registered low-all-ones flag; st_left 24 bits (it is loaded with 24 bits and only counts down)."""
from pathlib import Path
S = Path("results/kv_ing_rf3_1105/rtl/qkd_hr_ingest_eng"); O = Path("results/kv_ing_vh2_1107/rtl"); O.mkdir(parents=True, exist_ok=True)
def rep(t, a, b, n=1):
    assert t.count(a) == n, (a, t.count(a)); return t.replace(a, b)
t = (S / "qkd_host_native_engine_ing3.sv").read_text()
t = rep(t, "module qkd_host_native_engine_ing3 (", """// KV-ING-8 11-07 vH2 (conservative) on r3 + cut 19, faces live in the wrapper qkd_hr_ingest_eng:
// 20 V/R safe  p_in_* / p_d_* come from free-running face flops.  in FIFO 3 entries, rdy next state = count + rdy <= 2 (no pin in the cone); dq written directly, rdy = count + rdy <= 3.
// 21 V/R safe  e_rdy copies: er_m (FIFO, credit), er_s (per slice one-hot read pointer), er_st (stream step), all from er_n, which has no w_rdy in its cone.
// 22 V/R safe  e_last, e_tag: fenced last sector's done travels with its write.  Stream done: sd_pend until face_idle, blocks dispatch.  done_r/done_q/wf_q/n_sectors move to the wrapper.
// 23 Exact     per-slice sl_raw, sl_sc, sl_p0, mb_q from next state.
// 24 Exact     RAW address ra_lo/ra_hi counter.
// 25 Exact     st_row = {row_hi, row_lo}, registered low-all-ones flag; st_left 24 bits.
// TOK-VERIFY on top of r3: port -> engine +1 (in, d), engine -> w port +1, done/n_sectors +1 more, stream done after the face drains; rates kept.
module qkd_host_native_engine_ing4 (""")
# ---- ports
a = t.index("    input  wire         p_d_v,"); b = t.index(");\n    localparam [3:0] M_RAW")
t = t[:a] + """    input  wire         p_d_v,                 // face flop: a descriptor was accepted at the port on the previous edge
    output wire         p_d_rdy,
    input  wire [255:0] p_d_data,
    input  wire         p_in_v,
    output wire         p_in_rdy,
    input  wire [511:0] p_in_data,
    output wire         e_wv,
    input  wire         er_n,                  // next state of the write-face ready
    output wire [31:0]  w_addr,
    output wire [255:0] w_data,
    output wire         e_last,
    output wire [7:0]   e_tag,
    input  wire         face_idle,
    output wire         sd_fire,
    output wire [7:0]   sd_tag,
    output wire         p_busy
""" + t[b:]
# ---- input faces
a = t.index("    // -- registered input faces (cuts 16, 17)"); b = t.index("    // -- descriptor queue ---")
t = t[:a] + """    // -- input FIFO behind the face flops (cut 20) ------------------------------------------------------------------------
    wire         in_v, in_rdy, busy;
    wire [511:0] in_data;
    reg  [511:0] fi_d0, fi_d1, fi_d2;
    reg  [1:0]   fi_n;
    reg  [2:0]   fi_rp, fi_wp;                 // one-hot
    reg          fi_rdy;
    wire         fi_push = p_in_v, fi_pop = in_v && in_rdy;
    wire [1:0]   fi_n_n = fi_n + {1'b0, fi_push} - {1'b0, fi_pop};
    assign p_in_rdy = fi_rdy;
    assign in_v = fi_n != 2'd0;
    assign in_data = ({512{fi_rp[0]}} & fi_d0) | ({512{fi_rp[1]}} & fi_d1) | ({512{fi_rp[2]}} & fi_d2);
    assign p_busy = busy || fi_n != 2'd0 || fi_n_n != 2'd0;
    always @(posedge clk) begin
        if (fi_push && fi_wp[0]) fi_d0 <= p_in_data;
        if (fi_push && fi_wp[1]) fi_d1 <= p_in_data;
        if (fi_push && fi_wp[2]) fi_d2 <= p_in_data;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            fi_n <= 2'd0; fi_rp <= 3'b001; fi_wp <= 3'b001; fi_rdy <= 1'b0;
        end else begin
            fi_n <= fi_n_n; fi_rdy <= {1'b0, fi_n_n} + {2'd0, fi_rdy} <= 3'd2;
            if (fi_push) fi_wp <= {fi_wp[1:0], fi_wp[2]};
            if (fi_pop) fi_rp <= {fi_rp[1:0], fi_rp[2]};
        end
    // write-face ready copies (cut 21): identical flops, each with its own loads
    (* keep = 1 *) reg er_m;
    (* keep = 1 *) reg er_st;
    (* keep = 1 *) reg [34:0] er_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin er_m <= 1'b0; er_st <= 1'b0; er_s <= 35'd0; end
        else begin er_m <= er_n; er_st <= er_n; er_s <= {35{er_n}}; end

""" + t[b:]
# ---- descriptor queue
t = rep(t, "    assign d_rdy = !dq_n[2];\n", """    reg          dq_rdy;
    wire         d_pop;
    wire [2:0]   dq_n_n = dq_n + {2'd0, p_d_v} - {2'd0, d_pop};
    assign p_d_rdy = dq_rdy;
""")
t = rep(t, "    wire d_pop = q_disp || s_disp;\n", "    assign d_pop = q_disp || s_disp;\n")
t = rep(t, """            if (d_v && d_rdy) dq_wr <= dq_wr + 2'd1;
""", """            dq_rdy <= {1'b0, dq_n_n} + {3'd0, dq_rdy} <= 4'd3;
            if (p_d_v) dq_wr <= dq_wr + 2'd1;
""")
t = rep(t, "            dq_n <= dq_n + ((d_v && d_rdy) ? 3'd1 : 3'd0) - (d_pop ? 3'd1 : 3'd0);\n", "            dq_n <= dq_n_n;\n")
t = rep(t, "        if (d_v && d_rdy) dq[dq_wr] <= d_data;\n", "        if (p_d_v) dq[dq_wr] <= p_d_data;\n")
t = rep(t, "            dq_n <= 3'd0; dq_rd <= 2'd0; dq_wr <= 2'd0;\n", "            dq_n <= 3'd0; dq_rd <= 2'd0; dq_wr <= 2'd0; dq_rdy <= 1'b0;\n")
# ---- FIFO read side, per slice pop (cut 21)
t = rep(t, "    wire         fq_pop = qk_wv && w_rdy;\n", "    wire         fq_pop = qk_wv && er_m;\n")
t = rep(t, "            else if (fq_pop) oh <= {oh[6:0], oh[7]};\n", "            else if (qk_s[gs] && er_s[gs]) oh <= {oh[6:0], oh[7]};\n")
t = rep(t, "    wire         qp_dv = fq_pop && ft[8];\n", "    assign       e_last = qk_s[34] && ft[8];\n    assign       e_tag = ft[7:0];\n")
# ---- stream step
t = rep(t, "    wire         st_go  = st_adv && (!st_wv || w_rdy);\n", "    wire         st_go  = st_adv && (!st_wv || er_st);\n")
# ---- st_row / st_left (cut 25), raw address (cut 24)
t = rep(t, "    reg  [31:0]  st_row, st_left;\n", """    reg  [15:0]  row_lo, row_hi;
    reg          row_lf;                       // row_lo == 16'hffff (cut 25)
    wire [31:0]  st_row = {row_hi, row_lo};
    reg  [23:0]  st_left;
    reg  [15:0]  ra_lo, ra_hi;                 // RAW write address (cut 24)
    reg          ra_lf;
""")
# ---- cut 22: stream done
t = rep(t, "                    if (st_d[7]) begin done_r <= 1'b1; dtag_r <= st_d[15:8]; end\n", "                    if (st_d[7]) sd_pend <= 1'b1;\n")
t = rep(t, """            done_r <= 1'b0;
            if (qp_dv) begin done_r <= 1'b1; dtag_r <= ft[7:0]; end
            if (wf_q) begin nsec_lo <= nsec_lo + 16'd1; nsec_lf <= nsec_lo == 16'hfffe; if (nsec_lf) nsec_hi <= nsec_hi + 16'd1; end
""", """            if (sd_fire) sd_pend <= 1'b0;
""")
t = rep(t, """            done_r <= 1'b0; dtag_r <= 8'd0; nsec_lo <= 16'd0; nsec_hi <= 16'd0; nsec_lf <= 1'b0;
""", """            sd_pend <= 1'b0;
""")
a = t.index("    wire   w_fire = w_v && w_rdy;"); b = t.index("    wire   ra_room = ra_n <= 9'd192;")
t = t[:a] + """    reg    sd_pend;                             // a stream descriptor's done, waits for the face to drain (cut 22)
    assign sd_fire = sd_pend && face_idle;
    assign sd_tag = st_d[15:8];
""" + t[b:]
t = rep(t, "qp_busy || done_r || done_q || wf_q;", "qp_busy || sd_pend;")
t = rep(t, "    wire q_disp = dh_v && dh_mode == M_QKV && !qi_act && !st_act && !nfull", "    assign q_disp = dh_v && !sd_pend && dh_mode == M_QKV && !qi_act && !st_act && !nfull")
t = rep(t, "    wire s_disp = dh_v && dh_mode != M_QKV && !qi_act", "    assign s_disp = dh_v && !sd_pend && dh_mode != M_QKV && !qi_act")
t = rep(t, "    reg  [255:0] ra [0:7];\n", "    wire         q_disp, s_disp;\n    reg  [255:0] ra [0:7];\n")
# remove done_q etc. from the reset block
t = rep(t, "            done_q <= 1'b0; dtag_q <= 8'd0; wf_q <= 1'b0;\n", "")
t = rep(t, "            done_q <= done_r; dtag_q <= dtag_r; wf_q <= w_fire;\n", "")
# row / left assignments
t = rep(t, "st_ph <= 3'd0; st_beats <= 16'd0; st_row <= 32'd0; st_left <= 32'd0; st_rem <= 16'd0; st_sec <= 5'd0;", "st_ph <= 3'd0; st_beats <= 16'd0; row_lo <= 16'd0; row_hi <= 16'd0; row_lf <= 1'b0; st_left <= 24'd0; st_rem <= 16'd0; st_sec <= 5'd0;")
t = rep(t, """                st_row <= (dh_mode == M_RAW) ? 32'd0 : {8'd0, dh[167:144]};
                st_left <= (dh_mode == M_RAW) ? {8'd0, dh[167:144]} : {16'd0, dh[199:184]};
""", """                row_lo <= (dh_mode == M_RAW) ? 16'd0 : dh[159:144];
                row_hi <= (dh_mode == M_RAW) ? 16'd0 : {8'd0, dh[167:160]};
                row_lf <= (dh_mode != M_RAW) && dh[159:144] == 16'hffff;
                st_left <= (dh_mode == M_RAW) ? dh[167:144] : {8'd0, dh[199:184]};
""")
t = rep(t, "                    st_row <= st_row + 32'd1; st_left <= st_left - 32'd1;\n                    if (st_left == 32'd1) st_pad <= 1'b1;\n", "                    `ROW_STEP\n                    if (st_left == 24'd1) st_pad <= 1'b1;\n")
t = rep(t, "st_sec <= 5'd0; st_rem <= s_rb; st_row <= st_row + 32'd1; st_left <= st_left - 32'd1;\n                        if (st_left == 32'd1) st_pad <= 1'b1;", "st_sec <= 5'd0; st_rem <= s_rb; `ROW_STEP\n                        if (st_left == 24'd1) st_pad <= 1'b1;")
t = rep(t, "else begin st_ph <= 3'd0; st_row <= st_row + 32'd1; st_left <= st_left - 32'd1; end", "else begin st_ph <= 3'd0; `ROW_STEP end")
t = rep(t, "                        st_ph <= 3'd0; st_row <= st_row + 32'd1; st_left <= st_left - 32'd1;\n                        if (st_left == 32'd1) st_pad <= 1'b1;", "                        st_ph <= 3'd0; `ROW_STEP\n                        if (st_left == 24'd1) st_pad <= 1'b1;")
t = rep(t, "if (st_run && st_left == 32'd0 && !s_disp)", "if (st_run && st_left == 24'd0 && !s_disp)")
t = rep(t, "module qkd_host_native_engine_ing4 (", """`define ROW_STEP begin row_lo <= row_lo + 16'd1; row_lf <= row_lo == 16'hfffe; if (row_lf) row_hi <= row_hi + 16'd1; st_left <= st_left - 24'd1; end
module qkd_host_native_engine_ing4 (""")
# ---- raw address counter: data register without reset, in the valid-qualified block
t = rep(t, "        if (s_disp) begin st_mode <= dh_mode; st_d <= dh; end\n", """        if (s_disp) begin st_mode <= dh_mode; st_d <= dh; ra_lo <= dh[31:16]; ra_hi <= dh[47:32]; ra_lf <= dh[31:16] == 16'hffff; end
        if (st_go && is_raw) begin ra_lo <= ra_lo + 16'd1; ra_lf <= ra_lo == 16'hfffe; if (ra_lf) ra_hi <= ra_hi + 16'd1; end
""")
# ---- selects (cut 23), next states
t = rep(t, "    wire [255:0] st_wd = is_raw ? wq0 : (is_ikey && ik_sc) ? (st_ph[0] ? sc0 : sc1) : (sh_r & m_byte);\n    wire [31:0]  st_wa = is_raw ? (st_d[47:16] + st_row) : st_wa_r;\n", """    // cut 23: next states of the select inputs, one registered copy per slice
    wire [3:0]   st_mode_n = s_disp ? dh_mode : st_mode;
    wire [2:0]   st_ph_n = (st_go && is_ikey) ? (st_ph == 3'd2 ? (st_row[3:0] == 4'd15 ? 3'd3 : 3'd0) : st_ph == 3'd4 ? 3'd0 : st_ph + 3'd1) : s_disp ? 3'd0 : st_ph;
    wire [5:0]   take_n = (st_run && !is_raw) ? (is_rows ? k_take : ik_low ? 6'd32 : st_ph == 3'd2 ? 6'd4 : 6'd0) : take_r;
    wire         raw_n = st_mode_n == M_RAW, sc_n = st_mode_n == M_IKEY && st_ph_n >= 3'd3;
    wire [255:0] st_wd;
    wire [31:0]  st_wa;
    (* keep = 1 *) reg [33:0] sl_raw;
    (* keep = 1 *) reg [31:0] sl_sc, sl_p0;
    (* keep = 1 *) reg [31:0] mb_q;
    always @(posedge clk) begin sl_raw <= {34{raw_n}}; sl_sc <= {32{sc_n}}; sl_p0 <= {32{st_ph_n[0]}}; end
    generate for (mb = 0; mb < 32; mb = mb + 1) begin : g_sw
        always @(posedge clk) mb_q[mb] <= take_n[5] || (5'(mb) < take_n[4:0]);
        assign st_wd[mb*8 +: 8] = sl_raw[mb] ? wq0[mb*8 +: 8] : sl_sc[mb] ? (sl_p0[mb] ? sc0[mb*8 +: 8] : sc1[mb*8 +: 8]) : (sh_r[mb*8 +: 8] & {8{mb_q[mb]}});
    end endgenerate
    assign st_wa = {sl_raw[33] ? {ra_hi, ra_lo[15:14]} : st_wa_r[31:14], sl_raw[32] ? ra_lo[13:0] : st_wa_r[13:0]};
""")
t = rep(t, """    wire [255:0] m_byte;                        // ROWS: bytes below take_r
    genvar mb;
    generate for (mb = 0; mb < 32; mb = mb + 1) begin : g_mask
        assign m_byte[mb*8 +: 8] = {8{take_r[5] || (5'(mb) < take_r[4:0])}};
    end endgenerate
""", "    genvar mb;\n")
t = rep(t, "            take_r <= is_rows ? k_take : ik_low ? 6'd32 : st_ph == 3'd2 ? 6'd4 : 6'd0;\n", "            take_r <= take_n;\n")
# ---- ports
t = rep(t, "    assign w_v    = qk_wv || st_wv;\n", "    assign e_wv   = qk_wv || st_wv;\n")
# ---- cut 26: a stage between the macro read registers (top) and the output FIFO (bottom)
t = rep(t, "    wire [3:0]   fq_n_n = fq_n + (e1_v ? 4'd1 : 4'd0) - (fq_pop ? 4'd1 : 4'd0);\n", "    reg          e2_v, e2_last;\n    reg  [7:0]   e2_tag;\n    reg  [22:0]  e2_a;\n    reg  [255:0] sec_q;\n    wire [3:0]   fq_n_n = fq_n + (e2_v ? 4'd1 : 4'd0) - (fq_pop ? 4'd1 : 4'd0);\n")
t = rep(t, "    always @(posedge clk) if (e1_v) begin fq_d[fq_wp] <= sec; fq_a[fq_wp] <= e1_a; fq_t[fq_wp] <= {e1_last, e1_tag}; end\n", "    always @(posedge clk) begin sec_q <= sec; e2_a <= e1_a; e2_last <= e1_last; e2_tag <= e1_tag; end\n    always @(posedge clk) if (e2_v) begin fq_d[fq_wp] <= sec_q; fq_a[fq_wp] <= e2_a; fq_t[fq_wp] <= {e2_last, e2_tag}; end\n")
t = rep(t, "if (!rst_n) begin fq_wp <= 3'd0; fq_n <= 4'd0; qk_wv <= 1'b0; qk_s <= 35'd0; cred <= 4'd0; end", "if (!rst_n) begin fq_wp <= 3'd0; fq_n <= 4'd0; qk_wv <= 1'b0; qk_s <= 35'd0; cred <= 4'd0; e2_v <= 1'b0; end")
t = rep(t, "            if (e1_v) fq_wp <= fq_wp + 3'd1;\n", "            e2_v <= e1_v;\n            if (e2_v) fq_wp <= fq_wp + 3'd1;\n")
t = rep(t, "// TOK-VERIFY on top of r3: port -> engine +1 (in, d), engine -> w port +1,", "// 26 V/R safe  sec_q, e2_*: read registers -> mid stage -> output FIFO (distance budget: macro block at the top edge, FIFO at the w pins at the bottom).  +1 edge QKV read to FIFO.\n// TOK-VERIFY on top of r3: QKV read -> FIFO +1, port -> engine +1 (in, d), engine -> w port +1,")
(O / "qkd_host_native_engine_ing4.sv").write_text(t)
(O / "ot_hdc_ingest_fp8q_s.sv").write_text((S / "ot_hdc_ingest_fp8q_s.sv").read_text())
w = r"""`timescale 1ns/1ps
// KV-ING-8 11-07 vH2 conservative wrapper of qkd_hr_ingest_eng.  Same ports as r3.  PIN CYCLES (declared): in_v/in_data, d_v/d_data -> engine +1; engine -> w_* +1;
// done_v, done_tag, n_sectors +1 on top of that (mid hop towards the top-left pins); stream done additionally waits for the write face to drain; busy falls later accordingly.
// Faces: every in_data/d_data pin = one free-running flop.  w_rdy reaches only the port register band and the skid count.  Reset: one relay flop, as RF-KV1; the flow's reset replicas fan it out.
module qkd_hr_ingest_eng (
    input  wire [0:0]   ck,
    output wire [0:0]   busy,
    input  wire [255:0] d_data,
    output wire [0:0]   d_rdy,
    input  wire [0:0]   d_v,
    output wire [7:0]   done_tag,
    output wire [0:0]   done_v,
    input  wire [511:0] in_data,
    output wire [0:0]   in_rdy,
    input  wire [0:0]   in_v,
    output wire [31:0]  n_sectors,
    output wire [31:0]  r_addr,
    output wire [0:0]   r_v,
    input  wire [255:0] rd_data,
    input  wire [0:0]   rd_v,
    input  wire [0:0]   rst_n,
    output wire [31:0]  w_addr,
    output wire [255:0] w_data,
    input  wire [0:0]   w_rdy,
    output wire [0:0]   w_v
);
    assign r_v = 1'b0;
    assign r_addr = 32'd0;
    (* keep = 1 *) reg rf_rst_q__rst_n;
    always @(posedge ck or negedge rst_n) if (!rst_n) rf_rst_q__rst_n <= 1'b0; else rf_rst_q__rst_n <= 1'b1;
    wire rq = rf_rst_q__rst_n;

    // -- input face flops -------------------------------------------------------------------------------------------
    (* keep = 1 *) reg [511:0] fc_in;
    (* keep = 1 *) reg [255:0] fc_d;
    reg fc_in_v, fc_d_v;
    wire e_in_rdy, e_d_rdy;
    assign in_rdy = e_in_rdy;
    assign d_rdy = e_d_rdy;
    wire in_acc = in_v && e_in_rdy, d_acc = d_v && e_d_rdy;
    always @(posedge ck) begin fc_in <= in_data; fc_d <= d_data; end
    always @(posedge ck or negedge rq)
        if (!rq) begin fc_in_v <= 1'b0; fc_d_v <= 1'b0; end
        else begin fc_in_v <= in_acc; fc_d_v <= d_acc; end

    // -- engine -----------------------------------------------------------------------------------------------------
    wire         e_wv, e_last, e_busy, sd_fire, er_n;
    wire [7:0]   e_tag, sd_tag;
    wire [31:0]  e_addr;
    wire [255:0] e_data;
    wire         face_idle;
    qkd_host_native_engine_ing4 u_eng (.clk(ck), .rst_n(rq),
        .p_d_v(fc_d_v), .p_d_rdy(e_d_rdy), .p_d_data(fc_d),
        .p_in_v(fc_in_v), .p_in_rdy(e_in_rdy), .p_in_data(fc_in),
        .e_wv(e_wv), .er_n(er_n), .w_addr(e_addr), .w_data(e_data), .e_last(e_last), .e_tag(e_tag),
        .face_idle(face_idle), .sd_fire(sd_fire), .sd_tag(sd_tag), .p_busy(e_busy));

    // -- write face: skid S[0:1] + port register ----------------------------------------------------------------------
    // S data is written on every accepted beat and needs no w_rdy; the count and pointers decide whether it counts.
    localparam integer FW = 297;
    reg          er_w;                          // same D as the engine's copies
    wire [FW-1:0] e_all = {e_last, e_tag, e_addr, e_data};
    reg  [FW-1:0] s0, s1;
    (* keep = 1 *) reg [287:0] o_pin;           // {w_addr, w_data}: reaches only the pins
    (* keep = 1 *) reg [287:0] o_h;             // the same value, holds the register (face guard: a port flop has no internal load)
    reg  [8:0]   o_dn;                          // {last, tag}
    (* keep = 1 *) reg o_vn;                    // internal copy of the port flop o_vp, inverted so synthesis cannot fold them
    reg o_vp;                                   // port flop, no keep: a kept scalar name leaves an alias buffer on the port net
    wire o_v = !o_vn;
    reg          s_wp, s_rp;
    reg  [1:0]   s_n;
    wire         push = e_wv && er_w;
    wire         ld_o = !o_v || w_rdy;
    wire         s_nz = s_n != 2'd0;
    wire         s_keep = push && !(ld_o && !s_nz);
    wire         s_take = ld_o && s_nz;
    wire [FW-1:0] s_h = s_rp ? s1 : s0;
    wire [FW-1:0] o_n = s_nz ? s_h : e_all;
    assign er_n = ({2'd0, o_v} + {1'b0, s_n} + {2'd0, push}) <= 3'd2;
    assign face_idle = !o_v && !s_nz;
    assign w_v = o_vp;
    assign w_addr = o_pin[287:256];
    assign w_data = o_pin[255:0];
    always @(posedge ck) begin
        if (push && !s_wp) s0 <= e_all;
        if (push && s_wp) s1 <= e_all;
        o_pin <= ld_o ? o_n[287:0] : o_h;
        o_h <= ld_o ? o_n[287:0] : o_h;
        if (ld_o) o_dn <= o_n[296:288];
    end
    wire         fire = o_v && w_rdy;
    always @(posedge ck or negedge rq)
        if (!rq) begin o_vn <= 1'b1; o_vp <= 1'b0; s_wp <= 1'b0; s_rp <= 1'b0; s_n <= 2'd0; er_w <= 1'b0; end
        else begin
            er_w <= er_n;
            if (ld_o) o_vn <= !(s_nz || push);
            o_vp <= ld_o ? (s_nz || push) : o_v;   // holds from the twin: the port flop has no internal load
            if (s_keep) s_wp <= !s_wp;
            if (s_take) s_rp <= !s_rp;
            s_n <= s_n + {1'b0, s_keep} - {1'b0, s_take};
        end

    // -- done, n_sectors: one hop towards the top-left pins ----------------------------------------------------------
    reg  wf_a, wf_b, dn_a, dn_b, dn_q;
    reg  [7:0] tg_a, tg_b, tg_q;
    (* keep = 1 *) reg [15:0] nsec_lo, nsec_hi;  // internal twin of the port flops nsec_o
    (* keep = 1 *) reg [31:0] nsec_o;           // port flops, same D as the counter
    reg  nsec_lf;
    wire [15:0] nsec_lo_n = wf_b ? nsec_lo + 16'd1 : nsec_lo;
    wire [15:0] nsec_hi_n = (wf_b && nsec_lf) ? nsec_hi + 16'd1 : nsec_hi;
    assign done_v = dn_q;
    assign done_tag = tg_q;
    assign n_sectors = nsec_o;
    always @(posedge ck) begin
        tg_a <= (fire && o_dn[8]) ? o_dn[7:0] : sd_tag;
        tg_b <= tg_a; tg_q <= tg_b;
    end
    always @(posedge ck or negedge rq)
        if (!rq) begin
            wf_a <= 1'b0; wf_b <= 1'b0; dn_a <= 1'b0; dn_b <= 1'b0; dn_q <= 1'b0;
            nsec_lo <= 16'd0; nsec_hi <= 16'd0; nsec_lf <= 1'b0; nsec_o <= 32'd0;
        end else begin
            wf_a <= fire; wf_b <= wf_a;
            dn_a <= (fire && o_dn[8]) || sd_fire; dn_b <= dn_a; dn_q <= dn_b;
            nsec_lo <= nsec_lo_n; nsec_hi <= nsec_hi_n; nsec_o <= {nsec_hi_n, nsec_lo_n};
            if (wf_b) nsec_lf <= nsec_lo == 16'hfffe;
        end

    // -- busy ---------------------------------------------------------------------------------------------------------
    reg  busy_q;
    assign busy = busy_q;
    always @(posedge ck or negedge rq)
        if (!rq) busy_q <= 1'b0;
        else busy_q <= e_busy || in_acc || d_acc || fc_in_v || fc_d_v || o_v || s_nz || push || wf_a || wf_b || dn_a || dn_b;
endmodule
"""
(O / "qkd_hr_ingest_eng.sv").write_text(w)
