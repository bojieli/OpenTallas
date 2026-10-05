#!/usr/bin/env python3
"""Zero-latency issue-loop fallbacks over the final DEC_LA core (results/rtl/qwen_core_decode_closure_20261004/
CODEX_HANDOFF.md), behind parameter DEC_LA_ISSUE_FB (default 0 = the DEC_LA core unchanged).

FB >= 1 (fallback 1): `issue` is duplicated per consumer group, each copy specialised to its unit so the copies are
  distinct functions (no synthesis merge): me_go (d_unit 1: chase on the SU's rows/progress, ME ready/enable, KV and
  weight gates), su_go (d_unit 2: chase on ME progress, SU ready/drain, embedding gate), unit 3 (no go; SU-side
  conditions, as the original), the NEXT/FIFO advance (load, pc, nx_v: OR of the three) and the lm_head argmax update
  (its own ME copy).  The original `unit_ready`/`kv_gate`/`w_gate`/`chased` muxes on d_unit leave the issue path.
FB >= 2 (fallback 2): the unit / barrier / chase-source selection is registered one-hot with the NEXT control fields
  at LOAD (same edge, same enable), so each comparator result feeds an AND-OR instead of a d_unit / d_chase_rows mux.

Each level is cycle-identical to the DEC_LA core (same issue on the same edge; no added edge, the issue loop stays one
cycle)."""


def _rep(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new)


FB_CORE = r"""
    // ---- DEC_LA_ISSUE_FB (tools/qwen_rom_core_issue_fallback_w12.py) ---------------------------------------
    wire fb_kvg_me = (KV_HBM == 0) || !me_wsrc || (kv_ok && !kvd_v);
    wire fb_wg_me = (W_HBM == 0) || me_wsrc || (w_ok && !wd_v);
    wire fb_wg_su = (W_HBM == 0) || !a_src || emb_ok;
    wire fb_rdy_su = su_ready && (!KV_VEC_WRITE_BRIDGE || (su_idle && kv_write_drained));
    wire fb_waits = (!d_wait_me || me_idle) && (!d_wait_su || su_idle);
    wire fb_cond_me, fb_cond_su, fb_is_me, fb_is_su, fb_is_s3;
    wire fb_load;                                   // = load (declared below)
    generate if (DEC_LA_ISSUE_FB >= 2) begin : g_fb_oh
        // one-hot selection, registered with d_unit / d_barrier / d_chase / d_chase_rows (same LOAD edge)
        reg oh_me, oh_su, oh_s3, oh_bar, oh_me_rows, oh_me_prog, oh_su_chase;
        always @(posedge clk) if (fb_load) begin
            oh_me <= fqd_d_unit[la_rd] == 2'd1;
            oh_su <= fqd_d_unit[la_rd] == 2'd2;
            oh_s3 <= fqd_d_unit[la_rd] == 2'd3;
            oh_bar <= fqd_d_barrier[la_rd];
            oh_me_rows <= fqd_d_unit[la_rd] == 2'd1 && fqd_d_chase[la_rd] && fqd_d_chase_rows[la_rd];
            oh_me_prog <= fqd_d_unit[la_rd] == 2'd1 && fqd_d_chase[la_rd] && !fqd_d_chase_rows[la_rd];
            oh_su_chase <= fqd_d_unit[la_rd] != 2'd1 && fqd_d_chase[la_rd];
        end
        assign fb_is_me = oh_me; assign fb_is_su = oh_su; assign fb_is_s3 = oh_s3;
        assign fb_cond_me = oh_bar ? drained
                                   : ((!oh_me_rows || ge_su_rows) && (!oh_me_prog || ge_su_prog) && fb_waits);
        assign fb_cond_su = oh_bar ? drained : ((!oh_su_chase || ge_me_prog) && fb_waits);
    end else begin : g_fb_mux
        assign fb_is_me = d_unit == 2'd1; assign fb_is_su = d_unit == 2'd2; assign fb_is_s3 = d_unit == 2'd3;
        assign fb_cond_me = d_barrier ? drained
                                      : ((!d_chase || (d_chase_rows ? ge_su_rows : ge_su_prog)) && fb_waits);
        assign fb_cond_su = d_barrier ? drained : ((!d_chase || ge_me_prog) && fb_waits);
    end endgenerate
    wire fb_run = (st == S_RUN) && nx_v;
    (* keep *) wire fb_me_go = fb_run && fb_is_me && fb_cond_me && me_ready && me_en && fb_kvg_me && fb_wg_me;
    (* keep *) wire fb_am_go = fb_run && fb_is_me && fb_cond_me && me_ready && me_en && fb_kvg_me && fb_wg_me;
    (* keep *) wire fb_su_go = fb_run && fb_is_su && fb_cond_su && fb_rdy_su && fb_wg_su;
    (* keep *) wire fb_s3_go = fb_run && fb_is_s3 && fb_cond_su && fb_rdy_su && fb_wg_su;
    wire issue_ld = (DEC_LA_ISSUE_FB != 0) ? (fb_me_go || fb_su_go || fb_s3_go) : issue;
"""


def apply(text: str, level: int, default: int = 0) -> str:
    """Patch for levels <= `level`; the parameter's default is `default` (0: opt-in by parameter)."""
    if "    parameter integer DEC_LA = 0\n) (" in text:
        text = _rep(text, "    parameter integer DEC_LA = 0\n) (",
                    f"    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_ISSUE_FB = {default}\n) (")
    else:   # another default-off DEC_LA_* parameter follows (e.g. DEC_LA_BOUND)
        text = _rep(text, "    parameter integer DEC_LA = 0,\n",
                    f"    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_ISSUE_FB = {default},\n")
    if level == 0:
        return text
    assert level in (1, 2, 3)
    # consumers of `issue` -> their copies (DEC_LA_ISSUE_FB = 0 keeps the original nets)
    text = _rep(text, "    assign me_go = issue && (d_unit == 2'd1);\n", FB_CORE +
                "    assign me_go = (DEC_LA_ISSUE_FB != 0) ? fb_me_go : (issue && (d_unit == 2'd1));\n")
    text = _rep(text, "    wire la_me_go_am = (DEC_LA != 0) ? (la_issue_am && (d_unit == 2'd1)) : me_go;\n",
                "    wire la_me_go_am = (DEC_LA_ISSUE_FB != 0) ? fb_am_go\n"
                "                     : (DEC_LA != 0) ? (la_issue_am && (d_unit == 2'd1)) : me_go;\n")
    text = _rep(text, "    assign su_go = issue && (d_unit == 2'd2);\n",
                "    assign su_go = (DEC_LA_ISSUE_FB != 0) ? fb_su_go : (issue && (d_unit == 2'd2));\n")
    text = _rep(text, "    wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue);\n",
                "    wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue_ld);\n    assign fb_load = load;\n")
    text = _rep(text, "                    if (issue) pc <= pc + 1'b1;\n",
                "                    if (issue_ld) pc <= pc + 1'b1;\n")
    text = _rep(text, "                    else if (issue) nx_v <= 1'b0;\n",
                "                    else if (issue_ld) nx_v <= 1'b0;\n")
    # fqd_d_chase / fqd_d_chase_rows / fqd_d_barrier / fqd_d_unit must exist (DEC_LA decoded FIFO)
    for n in ("fqd_d_unit", "fqd_d_barrier", "fqd_d_chase ", "fqd_d_chase_rows"):
        assert ("reg " in text) and (n.strip() + " [0:7]" in text), n
    return text


AMQ_REGS = r"""
    // ---- DEC_LA_AMQ (tools/qwen_rom_core_issue_fallback_w12.py): the engine's argmax result (am_idx / am_val /
    // am_any, unit registers) is registered at the core boundary; the lm_head chunk fold and the END fold read the
    // registered copy one edge later (the fold's NEXT fields are captured with its trigger), and done / next_token /
    // next_val are written one edge after fin.  Values identical; +1 cycle per core program END only.
    reg [NW-1:0] amq_idx; reg [31:0] amq_val; reg amq_any;
    reg amf_v, amf_amc; reg [NW-1:0] amf_row0;
    always @(posedge clk) begin amq_idx <= am_idx; amq_val <= am_val; amq_any <= am_any; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) amf_v <= 1'b0;
        else amf_v <= (DEC_LA_AMQ != 0) && la_me_go_am && me_amax;
    always @(posedge clk) begin amf_amc <= me_amc; amf_row0 <= me_row0; end
    wire [NW-1:0] amv_idx = (DEC_LA_AMQ != 0) ? amq_idx : am_idx;
    wire [31:0] amv_val = (DEC_LA_AMQ != 0) ? amq_val : am_val;
    wire amv_any = (DEC_LA_AMQ != 0) ? amq_any : am_any;
    wire am_trig = (DEC_LA_AMQ != 0) ? amf_v : (la_me_go_am && me_amax);
    wire am_trig_amc = (DEC_LA_AMQ != 0) ? amf_amc : me_amc;
    wire [NW-1:0] am_trig_row0 = (DEC_LA_AMQ != 0) ? amf_row0 : me_row0;
"""


def apply_amq(text: str) -> str:
    """DEC_LA_AMQ (default 0): argmax boundary register, +1 cycle per program END (not in the issue loop)."""
    text = _rep(text, "    parameter integer DEC_LA = 0,\n",
                "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_AMQ = 0,\n") \
        if "    parameter integer DEC_LA = 0,\n" in text else \
        _rep(text, "    parameter integer DEC_LA = 0\n) (", "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_AMQ = 0\n) (")
    text = _rep(text, "    wire la_am_gt;\n", AMQ_REGS + "    wire la_am_gt;\n")
    text = _rep(text, "ot_qwen_core_key_gt u_la_am_gt (.a(okey(am_val)), .b(run_key), .gt(la_am_gt));",
                "ot_qwen_core_key_gt u_la_am_gt (.a(okey(amv_val)), .b(run_key), .gt(la_am_gt));")
    text = _rep(text, "    wire am_wins = am_any && (!run_any || ((DEC_LA != 0) ? la_am_gt : (okey(am_val) > run_key)));\n",
                "    wire am_wins = amv_any && (!run_any || ((DEC_LA != 0) ? la_am_gt : (okey(amv_val) > run_key)));\n")
    text = _rep(text, "    wire [NW-1:0] fin_idx = am_wins ? am_idx + last_row0 : run_idx;\n    wire [31:0] fin_val = am_wins ? am_val : run_val;\n",
                "    wire [NW-1:0] fin_idx = am_wins ? amv_idx + last_row0 : run_idx;\n    wire [31:0] fin_val = am_wins ? amv_val : run_val;\n")
    old = """        else if (la_me_go_am && me_amax) begin
            last_row0<=me_row0;
            if (!me_amc) run_any<=1'b0;
            else if (am_wins) begin
                run_any<=1'b1; run_key<=okey(am_val);
                run_idx<=am_idx+last_row0; run_val<=am_val;"""
    new = """        else if (am_trig) begin
            last_row0<=am_trig_row0;
            if (!am_trig_amc) run_any<=1'b0;
            else if (am_wins) begin
                run_any<=1'b1; run_key<=okey(amv_val);
                run_idx<=amv_idx+last_row0; run_val<=amv_val;"""
    text = _rep(text, old, new)
    old = """                    if (fin) begin
                        done <= 1'b1; next_token <= fin_idx; next_val <= fin_val; st <= S_IDLE; nx_v <= 1'b0;"""
    new = """                    if (fin) begin
                        if (DEC_LA_AMQ == 0) begin done <= 1'b1; next_token <= fin_idx; next_val <= fin_val; end
                        st <= S_IDLE; nx_v <= 1'b0;"""
    text = _rep(text, old, new)
    # the delayed END write (fin_d), in the FSM block after the state case
    old = """                default: st <= S_IDLE;
            endcase
        end
    end
"""
    assert text.count(old) >= 1
    i = text.index(old)
    new = """                default: st <= S_IDLE;
            endcase
            fin_d <= (DEC_LA_AMQ != 0) && fin;
            if (DEC_LA_AMQ != 0 && fin_d) begin done <= 1'b1; next_token <= fin_idx; next_val <= fin_val; end
        end
    end
"""
    text = text[:i] + new + text[i + len(old):]
    text = _rep(text, "            cycles <= 0; next_token <= 0;\n", "            cycles <= 0; next_token <= 0; fin_d <= 1'b0;\n")
    text = _rep(text, "    wire fin = (st == S_RUN)", "    reg fin_d;\n    wire fin = (st == S_RUN)")
    return text


def apply_start(text: str) -> str:
    """DEC_LA_ISSUE_FB >= 3 (over FB2 + AMQ text): the core's `start` input leaves the data-register enables.
    token / position are captured on every idle edge (the start edge included; they are read only after it), the
    lm_head running max (run_key / run_idx / run_val) and next_val are written from their own trigger without the
    start / reset priority terms (mutually exclusive by construction).  Below 3 every condition is the original one."""
    assert "wire am_trig =" in text, "apply_amq first"
    text = _rep(text, "                    tok_r <= token; pos_r <= pos; pc <= 0;", "                    pc <= 0;")
    text = _rep(text, "    wire [31:0] la_cycles1;\n", """    // DEC_LA_ISSUE_FB >= 3: token and position are captured on every idle edge (the start edge included)
    always @(posedge clk) if (st == S_IDLE && (DEC_LA_ISSUE_FB >= 3 || (rst_n && start))) begin
        tok_r <= token; pos_r <= pos;
    end
    wire [31:0] la_cycles1;
""")
    old = """            else if (am_wins) begin
                run_any<=1'b1; run_key<=okey(amv_val);
                run_idx<=amv_idx+last_row0; run_val<=amv_val;
            end"""
    text = _rep(text, old, "            else if (am_wins) run_any<=1'b1;")
    old = "    // DYN offsets derived once per token.\n"
    text = _rep(text, old, """    // the running max's data registers: their own enable (DEC_LA_ISSUE_FB >= 3 drops the start / reset terms, which
    // never coincide with a fold trigger)
    always @(posedge clk)
        if (am_trig && am_trig_amc && am_wins && (DEC_LA_ISSUE_FB >= 3 || (rst_n && !(start && st == S_IDLE)))) begin
            run_key<=okey(amv_val); run_idx<=amv_idx+last_row0; run_val<=amv_val;
        end
    always @(posedge clk)
        if (((DEC_LA_AMQ != 0) ? fin_d : fin) && (DEC_LA_ISSUE_FB >= 3 || rst_n)) next_val <= fin_val;
""" + old)
    text = _rep(text, "if (DEC_LA_AMQ == 0) begin done <= 1'b1; next_token <= fin_idx; next_val <= fin_val; end",
                "if (DEC_LA_AMQ == 0) begin done <= 1'b1; next_token <= fin_idx; end")
    text = _rep(text, "if (DEC_LA_AMQ != 0 && fin_d) begin done <= 1'b1; next_token <= fin_idx; next_val <= fin_val; end",
                "if (DEC_LA_AMQ != 0 && fin_d) begin done <= 1'b1; next_token <= fin_idx; end")
    return text
