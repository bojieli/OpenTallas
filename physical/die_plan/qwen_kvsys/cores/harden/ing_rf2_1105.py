#!/usr/bin/env python3
"""DIE-KV-73/ING 11-05 qkd_hr_ingest_eng cut form r2, on the ING1 form results/kv_ing_rf_1104 (usage: repo root, no args).
Writes results/kv_ing_rf2_1105/rtl/qkd_hr_ingest_eng: engine qkd_host_native_engine_ing2 (cuts in its header), wrapper, core json.
Routed ING1 census: fq_rp -> w_data/rf_oh_w_data 40 ep to -69.4; ra_rp -> sh_r 119 ep to -40.6; ra_rp -> write data 6 ep to -12.5;
TT slew 646: i1_code to 16 banks, fq_rp, ra_rp."""
import json, re
from pathlib import Path
S = Path("results/kv_ing_rf_1104/rtl/qkd_hr_ingest_eng"); O = Path("results/kv_ing_rf2_1105/rtl/qkd_hr_ingest_eng")
O.mkdir(parents=True, exist_ok=True)
def rep(t, a, b, n=1):
    assert t.count(a) == n, (a, t.count(a)); return t.replace(a, b)
t = (S / "qkd_host_native_engine_ing1.sv").read_text()
t = rep(t, "module qkd_host_native_engine_ing1 (", """// DIE-KV-73/ING 11-05 r2 cuts on the ING1 form (census of the routed ING1 build):
// 12 Exact     FIFO read: fq_rp replaced by one-hot read pointers, one kept copy per w_data byte, 2 for address, 1 for tag; each rotates itself on fq_pop.
//              qk_wv registered (fq_n != 0), a kept copy per slice selects FIFO vs stream.  No edge added.
// 13 V/R safe  I1B: one copy of the code beat per macro quadrant ({gb[3], gb[1]}); a code bit drives 4 flops, a quadrant copy 4 banks.  +1 edge beat to bank write.
// 14 V/R safe  stream read: word registers wq0, wq1 after the 8:1 word mux, kept per-byte copies of the word pointer (next state, no edge) and of the byte offset.
//              RAW: wq0 is a valid-qualified read stage (rawq_v), ra advances on its load, 1 sector a cycle kept, +1 edge beat to write.
//              ROWS / IKEY: second bubble (ok0) after each step and after new data: one step per 3 edges instead of 2.
// TOK-VERIFY cycle list on top of ING1: QKV beat -> bank write +1 (cut 13), drain, FIFO +0; RAW write +1 (cut 14), rate kept; ROWS / IKEY 1 step per 3 edges (was 2).  Ports unchanged.
module qkd_host_native_engine_ing2 (""")
t = rep(t, "// DIE-KV-70/ING 11-04 RE-FORM of qkd_host_native_engine", "// DIE-KV-70/ING 11-04, DIE-KV-73/ING 11-05 RE-FORM of qkd_host_native_engine")
# ---- cut 13 I1B
t = rep(t, "    always @(posedge clk) begin i1_slot <= q1_slot; i1_last <= q1_last; i1_isv <= q1_isv; i1_a <= {q1_slot, q1_t}; end\n",
"""    always @(posedge clk) begin i1_slot <= q1_slot; i1_last <= q1_last; i1_isv <= q1_isv; i1_a <= {q1_slot, q1_t}; end
    // -- I1B: per-quadrant copy of the beat (cut 13) ---------------------------------------------------------------------
    wire [511:0] ib_code [0:3];
    reg  [15:0]  ib_sel0, ib_sel1, ib_sel2, ib_sel3;
    reg          ib_v, ib_slot, ib_last, ib_isv;
    reg  [4:0]   ib_a;
    genvar gq1;
    generate for (gq1 = 0; gq1 < 4; gq1 = gq1 + 1) begin : g_ibq
        (* keep = 1 *) reg [511:0] code;
        always @(posedge clk) code <= i1_code;
        assign ib_code[gq1] = code;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ib_v <= 1'b0; ib_sel0 <= 16'd0; ib_sel1 <= 16'd0; ib_sel2 <= 16'd0; ib_sel3 <= 16'd0; end
        else begin ib_v <= i1_v; ib_sel0 <= i1_sel0; ib_sel1 <= i1_sel1; ib_sel2 <= i1_sel2; ib_sel3 <= i1_sel3; end
    always @(posedge clk) begin ib_slot <= i1_slot; ib_last <= i1_last; ib_isv <= i1_isv; ib_a <= i1_a; end
""")
t = rep(t, """                    wk_v <= !i1_isv && (i1_sel0[gb] || i1_sel1[gb] || i1_sel2[gb] || i1_sel3[gb]);
                    wv_v <=  i1_isv && (i1_sel0[gb] || i1_sel1[gb] || i1_sel2[gb] || i1_sel3[gb]);
""", """                    wk_v <= !ib_isv && (ib_sel0[gb] || ib_sel1[gb] || ib_sel2[gb] || ib_sel3[gb]);
                    wv_v <=  ib_isv && (ib_sel0[gb] || ib_sel1[gb] || ib_sel2[gb] || ib_sel3[gb]);
""")
t = rep(t, """                w_d <= ({128{i1_sel0[gb]}} & i1_code[127:0])   | ({128{i1_sel1[gb]}} & i1_code[255:128]) |
                       ({128{i1_sel2[gb]}} & i1_code[383:256]) | ({128{i1_sel3[gb]}} & i1_code[511:384]);
""", """                w_d <= ({128{ib_sel0[gb]}} & w_code[127:0])   | ({128{ib_sel1[gb]}} & w_code[255:128]) |
                       ({128{ib_sel2[gb]}} & w_code[383:256]) | ({128{ib_sel3[gb]}} & w_code[511:384]);
""")
t = rep(t, "            reg          wk_v, wv_v;\n", "            reg          wk_v, wv_v;\n            wire [511:0] w_code = ib_code[{gb[3], gb[1]}];\n")
t = rep(t, "fset_r <= i1_v && i1_last; i2_v <= i1_v;", "fset_r <= ib_v && ib_last; i2_v <= ib_v;")
t = rep(t, "w_a <= i1_a; fslot_r <= i1_slot; r_a", "w_a <= ib_a; fslot_r <= ib_slot; r_a")
t = rep(t, "wire qp_busy = i0_v || q1_v || i1_v || i2_v", "wire qp_busy = i0_v || q1_v || i1_v || ib_v || i2_v")
# ---- cut 12 FIFO read
t = rep(t, """    reg  [2:0]   fq_wp, fq_rp;
    reg  [3:0]   fq_n;
    wire         qk_wv = fq_n != 4'd0;
    wire         fq_pop = qk_wv && w_rdy;
    wire [22:0]  fa = fq_a[fq_rp];
    wire [31:0]  qp_wa = {8'd0, fa[22:14], 1'b0, fa[13:0]};
    wire [255:0] qp_wd = fq_d[fq_rp];
    wire [8:0]   ft = fq_t[fq_rp];
""", """    reg  [2:0]   fq_wp;
    reg  [3:0]   fq_n;
    reg          qk_wv;                         // fq_n != 0 (cut 12)
    wire         fq_pop = qk_wv && w_rdy;
    wire [3:0]   fq_n_n = fq_n + (e1_v ? 4'd1 : 4'd0) - (fq_pop ? 4'd1 : 4'd0);
    wire         fq_ne_n = fq_n_n != 4'd0;
    wire [2047:0] fd_all = {fq_d[7], fq_d[6], fq_d[5], fq_d[4], fq_d[3], fq_d[2], fq_d[1], fq_d[0]};
    wire [183:0] fa_all = {fq_a[7], fq_a[6], fq_a[5], fq_a[4], fq_a[3], fq_a[2], fq_a[1], fq_a[0]};
    wire [71:0]  ft_all = {fq_t[7], fq_t[6], fq_t[5], fq_t[4], fq_t[3], fq_t[2], fq_t[1], fq_t[0]};
    wire [34:0]  qk_s;                          // per-slice qk_wv
    wire [255:0] qp_wd;
    wire [22:0]  fa;
    wire [8:0]   ft;
    genvar gs, gk;
    generate for (gs = 0; gs < 35; gs = gs + 1) begin : g_rs
        localparam integer W = (gs < 32) ? 8 : (gs == 32) ? 12 : (gs == 33) ? 11 : 9;
        (* keep = 1 *) reg [7:0] oh;
        (* keep = 1 *) reg       qk_c;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin oh <= 8'd1; qk_c <= 1'b0; end
            else begin if (fq_pop) oh <= {oh[6:0], oh[7]}; qk_c <= fq_ne_n; end
        assign qk_s[gs] = qk_c;
        wire [W-1:0] t_or [0:8];
        assign t_or[0] = {W{1'b0}};
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_k
            wire [W-1:0] w_k;
            if (gs < 32) begin : gd assign w_k = fd_all[gk*256 + gs*8 +: 8]; end
            else if (gs == 32) begin : ga0 assign w_k = fa_all[gk*23 +: 12]; end
            else if (gs == 33) begin : ga1 assign w_k = fa_all[gk*23 + 12 +: 11]; end
            else begin : gt assign w_k = ft_all[gk*9 +: 9]; end
            assign t_or[gk+1] = t_or[gk] | ({W{oh[gk]}} & w_k);
        end
        if (gs < 32) begin : gd assign qp_wd[gs*8 +: 8] = t_or[8]; end
        else if (gs == 32) begin : ga0 assign fa[11:0] = t_or[8]; end
        else if (gs == 33) begin : ga1 assign fa[22:12] = t_or[8]; end
        else begin : gt assign ft = t_or[8]; end
    end endgenerate
    wire [31:0]  qp_wa = {8'd0, fa[22:14], 1'b0, fa[13:0]};
""")
t = rep(t, "if (!rst_n) begin fq_wp <= 3'd0; fq_rp <= 3'd0; fq_n <= 4'd0; cred <= 4'd0; end", "if (!rst_n) begin fq_wp <= 3'd0; fq_n <= 4'd0; qk_wv <= 1'b0; cred <= 4'd0; end")
t = rep(t, """            if (fq_pop) fq_rp <= fq_rp + 3'd1;
            fq_n <= fq_n + (e1_v ? 4'd1 : 4'd0) - (fq_pop ? 4'd1 : 4'd0);
""", """            fq_n <= fq_n_n; qk_wv <= fq_ne_n;
""")
# ---- cut 14 stream read
t = rep(t, """    wire [2:0]   ra_w0 = ra_rp[7:5];
    wire [2:0]   ra_w1 = ra_w0 + 3'd1;
""", "")
t = rep(t, """    wire [255:0] ra_word = ra[ra_w0];
    wire [255:0] ra_wnext = ra[ra_w1];
    wire [511:0] ra_sh = {ra_wnext, ra_word} >> {ra_rp[4:0], 3'b000};
    reg  [255:0] sh_r;                          // the next 32 bytes, ROWS / IKEY (cut 10)
""", """    wire [2047:0] ra_all = {ra[7], ra[6], ra[5], ra[4], ra[3], ra[2], ra[1], ra[0]};
    wire [7:0]   ra_rp_n;                       // ra_rp next state
    reg  [255:0] wq0, wq1;                      // word registers (cut 14)
    wire [255:0] ra_word, ra_wnext;
    wire [255:0] ra_sh;
    wire [511:0] wq_all = {wq1, wq0};
    genvar gy;
    generate for (gy = 0; gy < 32; gy = gy + 1) begin : g_ry
        (* keep = 1 *) reg [2:0] w0, w1;
        (* keep = 1 *) reg [4:0] off;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin w0 <= 3'd0; w1 <= 3'd1; end
            else begin w0 <= ra_rp_n[7:5]; w1 <= ra_rp_n[7:5] + 3'd1; end
        always @(posedge clk) off <= ra_rp[4:0];
        wire [63:0] by0, by1;
        assign ra_word[gy*8 +: 8]  = ra_all[{w0, 8'd0} + gy*8 +: 8];
        assign ra_wnext[gy*8 +: 8] = ra_all[{w1, 8'd0} + gy*8 +: 8];
        wire [255:0] win = wq_all[gy*8 +: 256];
        assign ra_sh[gy*8 +: 8] = win[{off, 3'b000} +: 8];
    end endgenerate
    reg  [255:0] sh_r;                          // the next 32 bytes, ROWS / IKEY (cut 10)
""")
t = rep(t, "wire         raw_ok = st_run && is_raw && ra_n[8:5] != 4'd0;\n",
"""wire         raw_have = st_run && is_raw && ra_n[8:5] != 4'd0;
    reg          rawq_v;                        // wq0 holds the next RAW word (cut 14)
    reg          ok0;                           // second bubble (cut 14)
    wire         raw_ok = st_run && is_raw && rawq_v;
""")
t = rep(t, "    wire         st_go  = st_adv && (!st_wv || w_rdy);\n",
"""    wire         st_go  = st_adv && (!st_wv || w_rdy);
    wire         raw_load = raw_have && (!rawq_v || st_go);
    wire         ra_adv = is_raw ? raw_load : st_go;
    always @(posedge clk) begin
        if (!is_raw || raw_load) wq0 <= ra_word;
        wq1 <= ra_wnext;
    end
""")
t = rep(t, "is_raw ? ra_word : (is_ikey && ik_sc)", "is_raw ? wq0 : (is_ikey && ik_sc)")
t = rep(t, """    assign w_addr = qk_wv ? qp_wa : st_wa;
    assign w_data = qk_wv ? qp_wd : st_wd;
""", """    assign w_addr = {qk_s[33] ? qp_wa[31:14] : st_wa[31:14], qk_s[32] ? qp_wa[13:0] : st_wa[13:0]};
    genvar gw;
    generate for (gw = 0; gw < 32; gw = gw + 1) begin : g_wd
        assign w_data[gw*8 +: 8] = qk_s[gw] ? qp_wd[gw*8 +: 8] : st_wd[gw*8 +: 8];
    end endgenerate
    assign ra_rp_n = st_pad ? 8'd0 : ra_adv ? ra_rp + {2'd0, st_pop} : ra_rp;
""")
t = rep(t, "st_act <= 1'b0; st_pad <= 1'b0; ra_n <= 9'd0; ra_rp <= 8'd0; ra_wp <= 3'd0; push_q <= 1'b0;", "st_act <= 1'b0; st_pad <= 1'b0; ra_n <= 9'd0; ra_rp <= 8'd0; ra_wp <= 3'd0; push_q <= 1'b0; rawq_v <= 1'b0; ok0 <= 1'b0;")
t = rep(t, """                ra_n <= 9'd0; ra_rp <= 8'd0; ra_wp <= 3'd0;
""", """                ra_n <= 9'd0; ra_rp <= 8'd0; ra_wp <= 3'd0; rawq_v <= 1'b0;
""")
t = rep(t, """                ra_n <= ra_n + (push_q ? 9'd64 : 9'd0) - (st_go ? {3'd0, st_pop} : 9'd0);
                if (st_go) ra_rp <= ra_rp + {2'd0, st_pop};
""", """                ra_n <= ra_n + (push_q ? 9'd64 : 9'd0) - (ra_adv ? {3'd0, st_pop} : 9'd0);
                ra_rp <= ra_rp_n;
                rawq_v <= raw_load || (rawq_v && !st_go);
""")
t = rep(t, "            st_ok_r <= st_run && !is_raw && ap_go && !st_go && need_ok;\n",
"""            ok0 <= st_run && !is_raw && ap_go && !st_go && need_ok;
            st_ok_r <= ok0 && st_run && !is_raw && ap_go && !st_go && need_ok;
""")
(O / "qkd_host_native_engine_ing2.sv").write_text(t)
(O / "ot_hdc_ingest_fp8q_s.sv").write_text((S / "ot_hdc_ingest_fp8q_s.sv").read_text())
w = (S / "qkd_hr_ingest_eng.sv").read_text()
w = rep(w, "qkd_host_native_engine_ing1", "qkd_host_native_engine_ing2", w.count("qkd_host_native_engine_ing1"))
w = rep(w, "do not edit.", "do not edit. DIE-KV-73/ING 11-05 r2.", 1)
(O / "qkd_hr_ingest_eng.sv").write_text(w)
cj = json.load(open(S / "qkd_hr_ingest_eng_core.json"))
cj["files"] = [f.replace("results/kv_ing_rf_1104/", "results/kv_ing_rf2_1105/").replace("qkd_host_native_engine_ing1", "qkd_host_native_engine_ing2") for f in cj["files"]]
cj["member_modules"] = {"u_eng": "qkd_host_native_engine_ing2"}
cj["rf_1105"] = {"transform": "physical/die_plan/qwen_kvsys/cores/harden/ing_rf2_1105.py", "form": "DIE-KV-73/ING r2: cuts 12-14 in the engine header"}
(O / "qkd_hr_ingest_eng_core.json").write_text(json.dumps(cj, indent=1) + "\n")
B = Path("results/kv_ing_rf2_1105/bench"); B.mkdir(parents=True, exist_ok=True)
SB = Path("results/kv_ing_rf_1104/bench")
tb = (SB / "tb_ing1.sv").read_text().replace("qkd_host_native_engine_ing1", "qkd_host_native_engine_ing2").replace("$random(seed)", "rr()")
tb = rep(tb, "  reg [31:0] seed;\n", "  reg [31:0] seed;\n  // DIE-KV-73/ING: Verilator $random(seed) did not follow +seed (36 ING1 seeds were 3 distinct runs); own xorshift, seed really varies\n  function automatic [31:0] rr(); seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5); rr = seed; endfunction\n")
tb = rep(tb, '    if (!$value$plusargs("seed=%d", seed)) seed = 1;\n', '    if (!$value$plusargs("seed=%d", seed)) seed = 1;\n    seed = seed * 32\'d2654435761 + 32\'d12345;\n')
(B / "tb_ing2.sv").write_text(tb)
(B / "tb_fp8q.sv").write_text((SB / "tb_fp8q.sv").read_text())
r = (SB / "run_ing.sh").read_text()
r = r.replace("results/kv_ing_rf_1104", "results/kv_ing_rf2_1105").replace("qkd_host_native_engine_ing1", "qkd_host_native_engine_ing2").replace("tb_ing1", "tb_ing2")
r = rep(r, """ m_nowait) sub $E "st_ok_r <= st_run && !is_raw && ap_go && !st_go && need_ok;" "st_ok_r <= st_run && !is_raw && ap_go && need_ok;";;""",
""" m_nowait) sub $E "st_ok_r <= ok0 && st_run && !is_raw && ap_go && !st_go && need_ok;" "st_ok_r <= ok0 && st_run && !is_raw && ap_go && need_ok;";;
 m_ok0) sub $E "st_ok_r <= ok0 && st_run" "st_ok_r <= st_run";;
 m_oh) sub $E "else begin if (fq_pop) oh <= {oh[6:0], oh[7]}; qk_c <= fq_ne_n; end" "else begin if (fq_pop) oh <= (gs == 7) ? {oh[3:0], oh[7:4]} : {oh[6:0], oh[7]}; qk_c <= fq_ne_n; end";;
 m_qkc) sub $E "qk_c <= fq_ne_n; end" "qk_c <= qk_wv; end";;
 m_rawclr) sub $E "ra_wp <= 3'd0; rawq_v <= 1'b0;" "ra_wp <= 3'd0;";;
 m_rawq) sub $E "rawq_v <= raw_load || (rawq_v && !st_go);" "rawq_v <= raw_load;";;
 m_w1) sub $E "w1 <= ra_rp_n[7:5] + 3'd1;" "w1 <= ra_rp_n[7:5];";;
 m_off) sub $E "always @(posedge clk) off <= ra_rp[4:0];" "always @(posedge clk) off <= (gy == 3) ? ra_rp[4:0] ^ 5'd1 : ra_rp[4:0];";;
 m_ibq) sub $E "wire [511:0] w_code = ib_code[{gb[3], gb[1]}];" "wire [511:0] w_code = (gb == 13) ? i1_code : ib_code[{gb[3], gb[1]}];";;
 m_ibsel) sub $E "ib_sel1 <= i1_sel1;" "ib_sel1 <= i1_sel0;";;""")
(B / "run_ing.sh").write_text(r)
print("ok", len(t.splitlines()))
