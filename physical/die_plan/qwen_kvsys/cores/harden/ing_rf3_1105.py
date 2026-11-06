#!/usr/bin/env python3
"""KV-ING-1 11-05 qkd_hr_ingest_eng vB (safe-by-construction form r3) on the r2 form results/kv_ing_rf2_1105 (usage: repo root, no args).
Writes results/kv_ing_rf3_1105/{rtl/qkd_hr_ingest_eng,bench}: engine qkd_host_native_engine_ing3, wrapper, core json, bench.
Routed r2 sign-off (intel1 dkv73/ing, 14:54): TT -6.18/4 (st_ph -> rf_oh_w_data, in_rdy out port), slew TT 636 / FF 453,
top TT slew pins = ib_all D (one i1_code bit -> 4 quadrant copies across the core).  Reset recovery +84 ps (no reset cut needed).
r3 cuts on r2 (OWNER 19:3x version B: registered faces, short reach):
 15 V/R safe  I1H: i1_code -> 2 kept half copies (ih_all) -> 4 quadrant copies (ib_all): a bit drives 2 flops a stage.  +1 edge beat to bank write.
 16 V/R safe  input faces registered: in_v/in_data and d_v/d_data land in 2-entry FIFOs at the pins; in_rdy, d_rdy are flops
              (not full, next state).  +1 edge port -> engine for beats and descriptors; full rate kept (2 entries).
 17 V/R safe  busy is a flop: engine busy, either FIFO non-empty now or next, or a push this edge.  Falls 1 edge later.
PIN CYCLES on top of r2: QKV beat -> bank write +1 (cut 15), port -> engine +1 for in and d (cut 16), busy fall +1 (cut 17)."""
import json, re
from pathlib import Path
S = Path("results/kv_ing_rf2_1105"); O = Path("results/kv_ing_rf3_1105")
OR = O / "rtl/qkd_hr_ingest_eng"; SR = S / "rtl/qkd_hr_ingest_eng"
OR.mkdir(parents=True, exist_ok=True)
def rep(t, a, b, n=1):
    assert t.count(a) == n, (a, t.count(a)); return t.replace(a, b)
t = (SR / "qkd_host_native_engine_ing2.sv").read_text()
t = rep(t, "module qkd_host_native_engine_ing2 (", """// KV-ING-1 11-05 r3 (version B, safe by construction) on r2:
// 15 V/R safe  I1H: i1_code -> 2 kept half copies ih_all -> 4 quadrant copies ib_all; a bit drives 2 flops per stage.  +1 edge beat to bank write.
// 16 V/R safe  input faces registered: in_* and d_* land in 2-entry FIFOs at the pins; in_rdy / d_rdy are flops.  +1 edge port -> engine.
// 17 V/R safe  busy is a flop (engine busy | FIFO non-empty now or next | push this edge); falls 1 edge later.
// TOK-VERIFY on top of r2: QKV beat -> bank write +1 (15), port -> engine +1 for beats and descriptors (16), busy fall +1 (17); rates kept.
module qkd_host_native_engine_ing3 (""")
# ---- cut 16/17: rename the faces, the old names become engine-side wires
t = rep(t, """    input  wire         d_v,
    output wire         d_rdy,
    input  wire [255:0] d_data,
    input  wire         in_v,
    output wire         in_rdy,
    input  wire [511:0] in_data,
""", """    input  wire         p_d_v,
    output wire         p_d_rdy,
    input  wire [255:0] p_d_data,
    input  wire         p_in_v,
    output wire         p_in_rdy,
    input  wire [511:0] p_in_data,
""")
t = rep(t, "    output wire         busy,\n", "    output wire         p_busy,\n")
t = rep(t, "    localparam [3:0] M_RAW = 4'd0, M_QKV = 4'd1, M_ROWS = 4'd2, M_IKEY = 4'd3;\n", """    localparam [3:0] M_RAW = 4'd0, M_QKV = 4'd1, M_ROWS = 4'd2, M_IKEY = 4'd3;

    // -- registered input faces (cuts 16, 17): 2-entry FIFOs at the pins, ready from flops ------------------------------
    wire         d_v, d_rdy, in_v, in_rdy, busy;
    wire [255:0] d_data;
    wire [511:0] in_data;
    reg  [511:0] fi_d0, fi_d1;
    reg  [1:0]   fi_n;
    reg          fi_rp, fi_wp, fi_rdy;
    reg  [255:0] fd_d0, fd_d1;
    reg  [1:0]   fd_n;
    reg          fd_rp, fd_wp, fd_rdy;
    reg          busy_q;
    wire         fi_push = p_in_v && fi_rdy, fi_pop = in_v && in_rdy;
    wire         fd_push = p_d_v && fd_rdy, fd_pop = d_v && d_rdy;
    wire [1:0]   fi_n_n = fi_n + {1'b0, fi_push} - {1'b0, fi_pop};
    wire [1:0]   fd_n_n = fd_n + {1'b0, fd_push} - {1'b0, fd_pop};
    assign p_in_rdy = fi_rdy;
    assign p_d_rdy = fd_rdy;
    assign in_v = fi_n != 2'd0;
    assign d_v = fd_n != 2'd0;
    assign in_data = fi_rp ? fi_d1 : fi_d0;
    assign d_data = fd_rp ? fd_d1 : fd_d0;
    assign p_busy = busy_q;
    always @(posedge clk) begin
        if (fi_push && !fi_wp) fi_d0 <= p_in_data;
        if (fi_push && fi_wp) fi_d1 <= p_in_data;
        if (fd_push && !fd_wp) fd_d0 <= p_d_data;
        if (fd_push && fd_wp) fd_d1 <= p_d_data;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            fi_n <= 2'd0; fi_rp <= 1'b0; fi_wp <= 1'b0; fi_rdy <= 1'b0;
            fd_n <= 2'd0; fd_rp <= 1'b0; fd_wp <= 1'b0; fd_rdy <= 1'b0; busy_q <= 1'b0;
        end else begin
            fi_n <= fi_n_n; fi_rdy <= fi_n_n != 2'd2;
            if (fi_push) fi_wp <= !fi_wp;
            if (fi_pop) fi_rp <= !fi_rp;
            fd_n <= fd_n_n; fd_rdy <= fd_n_n != 2'd2;
            if (fd_push) fd_wp <= !fd_wp;
            if (fd_pop) fd_rp <= !fd_rp;
            busy_q <= busy || fi_n != 2'd0 || fd_n != 2'd0 || fi_n_n != 2'd0 || fd_n_n != 2'd0;
        end
""")
# ---- cut 15: I1H half copies between i1 and the quadrant copies
t = rep(t, "    always @(posedge clk) ib_all <= {4{i1_code}};\n", """    // I1H (cut 15): two kept half copies; quadrants 0, 1 (banks 0..7) read half 0, quadrants 2, 3 (banks 8..15) half 1
    (* keep = 1 *) reg [1023:0] ih_all;
    reg  [15:0]  ih_sel0, ih_sel1, ih_sel2, ih_sel3;
    reg          ih_v, ih_slot, ih_last, ih_isv;
    reg  [4:0]   ih_a;
    always @(posedge clk) ih_all <= {2{i1_code}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ih_v <= 1'b0; ih_sel0 <= 16'd0; ih_sel1 <= 16'd0; ih_sel2 <= 16'd0; ih_sel3 <= 16'd0; end
        else begin ih_v <= i1_v; ih_sel0 <= i1_sel0; ih_sel1 <= i1_sel1; ih_sel2 <= i1_sel2; ih_sel3 <= i1_sel3; end
    always @(posedge clk) begin ih_slot <= i1_slot; ih_last <= i1_last; ih_isv <= i1_isv; ih_a <= i1_a; end
    always @(posedge clk) ib_all <= {ih_all[1023:512], ih_all[1023:512], ih_all[511:0], ih_all[511:0]};
""")
t = rep(t, "else begin ib_v <= i1_v; ib_sel0 <= i1_sel0; ib_sel1 <= i1_sel1; ib_sel2 <= i1_sel2; ib_sel3 <= i1_sel3; end",
           "else begin ib_v <= ih_v; ib_sel0 <= ih_sel0; ib_sel1 <= ih_sel1; ib_sel2 <= ih_sel2; ib_sel3 <= ih_sel3; end")
t = rep(t, "    always @(posedge clk) begin ib_slot <= i1_slot; ib_last <= i1_last; ib_isv <= i1_isv; ib_a <= i1_a; end\n",
           "    always @(posedge clk) begin ib_slot <= ih_slot; ib_last <= ih_last; ib_isv <= ih_isv; ib_a <= ih_a; end\n")
t = rep(t, "wire qp_busy = i0_v || q1_v || i1_v || ib_v || i2_v", "wire qp_busy = i0_v || q1_v || i1_v || ih_v || ib_v || i2_v")
(OR / "qkd_host_native_engine_ing3.sv").write_text(t)
(OR / "ot_hdc_ingest_fp8q_s.sv").write_text((SR / "ot_hdc_ingest_fp8q_s.sv").read_text())
w = (SR / "qkd_hr_ingest_eng.sv").read_text()
w = rep(w, "qkd_host_native_engine_ing2 u_eng", "qkd_host_native_engine_ing3 u_eng")
w = rep(w, "engine = qkd_host_native_engine_ing2", "engine = qkd_host_native_engine_ing3")
w = rep(w, "do not edit. DIE-KV-73/ING 11-05 r2.", "do not edit. KV-ING-1 11-05 r3 (vB).")
for a in ("d_v", "d_rdy", "d_data", "in_v", "in_rdy", "in_data", "busy"):
    w = rep(w, f"        .{a}(", f"        .p_{a}(")
(OR / "qkd_hr_ingest_eng.sv").write_text(w)
cj = json.load(open(SR / "qkd_hr_ingest_eng_core.json"))
cj["files"] = [f.replace("results/kv_ing_rf2_1105/", "results/kv_ing_rf3_1105/").replace("qkd_host_native_engine_ing2", "qkd_host_native_engine_ing3") for f in cj["files"]]
cj["member_modules"] = {"u_eng": "qkd_host_native_engine_ing3"}
cj["rf_1105b"] = {"transform": "physical/die_plan/qwen_kvsys/cores/harden/ing_rf3_1105.py", "form": "KV-ING-1 r3 vB: cuts 15-17 in the engine header"}
(OR / "qkd_hr_ingest_eng_core.json").write_text(json.dumps(cj, indent=1) + "\n")
B = O / "bench"; B.mkdir(parents=True, exist_ok=True)
tb = (S / "bench/tb_ing2.sv").read_text()
tb = rep(tb, "  qkd_host_native_engine_ing2 W (.clk(ck), .rst_n(rst_n), .d_v(w_isd), .d_rdy(w_drdy), .d_data(w_head[255:0]),\n    .in_v(w_isp), .in_rdy(w_inrdy), .in_data(w_head),",
              "  qkd_host_native_engine_ing3 W (.clk(ck), .rst_n(rst_n), .p_d_v(w_isd), .p_d_rdy(w_drdy), .p_d_data(w_head[255:0]),\n    .p_in_v(w_isp), .p_in_rdy(w_inrdy), .p_in_data(w_head),")
tb = rep(tb, ".done_v(w_dv), .done_tag(w_tg), .busy(w_busy), .n_sectors(w_ns));", ".done_v(w_dv), .done_tag(w_tg), .p_busy(w_busy), .n_sectors(w_ns));")
tb = rep(tb, "// DIE-KV-70/ING 11-04: transaction co-sim", "// KV-ING-1 11-05: r3 (ing3) on the DIE-KV-70/ING 11-04 transaction co-sim")
# r3 checks: busy contract at the registered face (busy_q covers both input FIFOs and the engine busy, every edge),
# and +pm=3: descriptor bursts (RAW with no sector and no beat on half the descriptors) so the d FIFO and dq fill.
tb = rep(tb, "    if (w_dv) begin\n", """    if (W.fi_n != 2'd0 || W.fd_n != 2'd0 || W.busy) if (!w_busy) begin bad = bad + 1; if (bad < 8) $display("BUSY CONTRACT cyc=%0d fi %0d fd %0d eng %b", cyc, W.fi_n, W.fd_n, W.busy); end
    if (w_dv) begin
""")
tb = rep(tb, "      if (pm == 1) mode = 0; if (pm == 2) mode = 1 + {rr()} % 7;\n",
             "      if (pm == 1) mode = 0; if (pm == 2) mode = 1 + {rr()} % 7; if (pm == 3 && ({rr()} % 2)) mode = 9;\n")
tb = rep(tb, "        n = 2 * (1 + {rr()} % 24); if (({rr()} % 5) == 0) n = 0;\n        b = {rr()} % 2;                 // an extra pad beat sometimes\n",
             "        n = 2 * (1 + {rr()} % 24); if (({rr()} % 5) == 0) n = 0;\n        b = {rr()} % 2;                 // an extra pad beat sometimes\n        if (mode == 9) begin n = 0; b = 0; end   // r3 +pm=3: descriptor only\n")
tb = rep(tb, "      end else if (mode <= 4) begin              // RAW\n", "      end else if (mode <= 4 || mode == 9) begin   // RAW (9: r3 burst, descriptor only)\n")
(B / "tb_ing3.sv").write_text(tb)
(B / "tb_fp8q.sv").write_text((S / "bench/tb_fp8q.sv").read_text())
r = (S / "bench/run_ing.sh").read_text()
r = r.replace("results/kv_ing_rf2_1105", "results/kv_ing_rf3_1105").replace("qkd_host_native_engine_ing2", "qkd_host_native_engine_ing3").replace("tb_ing2", "tb_ing3")
r = rep(r, """ m_ibsel) sub $E "ib_sel1 <= i1_sel1;" "ib_sel1 <= i1_sel0;";;""", """ m_ibsel) sub $E "ib_sel1 <= ih_sel1;" "ib_sel1 <= ih_sel0;";;
 m_ihq) sub $E "ib_all <= {ih_all[1023:512], ih_all[1023:512], ih_all[511:0], ih_all[511:0]};" "ib_all <= {ih_all[1023:512], i1_code, ih_all[511:0], ih_all[511:0]};";;
 m_ihv) sub $E "wire qp_busy = i0_v || q1_v || i1_v || ih_v || ib_v" "wire qp_busy = i0_v || q1_v || i1_v || ib_v";;
 m_ihlast) sub $E "ih_last <= i1_last;" "ih_last <= i1_last || i1_v;";;
 m_fiwp) sub $E "if (fi_push) fi_wp <= !fi_wp;" "fi_wp <= 1'b0;";;
 m_fdrp) sub $E "if (fd_pop) fd_rp <= !fd_rp;" "if (fd_push) fd_rp <= !fd_rp;";;
 m_firdy) sub $E "fi_rdy <= fi_n_n != 2'd2;" "fi_rdy <= 1'b1;";;
 m_fdrdy) sub $E "fd_rdy <= fd_n_n != 2'd2;" "fd_rdy <= 1'b1;";;
 m_busyf) sub $E "busy_q <= busy || fi_n != 2'd0 || fd_n != 2'd0 || fi_n_n != 2'd0 || fd_n_n != 2'd0;" "busy_q <= busy || fi_n != 2'd0 || fi_n_n != 2'd0;";;
 m_busyn) sub $E "busy_q <= busy || fi_n != 2'd0 || fd_n != 2'd0 || fi_n_n != 2'd0 || fd_n_n != 2'd0;" "busy_q <= busy || fi_n_n != 2'd0 || fd_n_n != 2'd0;";;""")
r = rep(r, "# DIE-KV-70/ING 11-04 engine bench.", "# KV-ING-1 11-05 r3 engine bench (DIE-KV-70/ING 11-04 bench).")
(B / "run_ing.sh").write_text(r)
print("ok", len(t.splitlines()))
