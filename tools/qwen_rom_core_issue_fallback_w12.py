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


def apply_nxreg(text: str) -> str:
    """DEC_LA_NXREG (default 0; owner margin rule 2026-10-06): the issued instruction's data fields leave the core from
    registers.  In the DEC_LA core every output field is fqd_<f>[la_nx], an 8:1 read of the decoded-field FIFO behind
    the NEXT pointer (r5b_f3ba: every endpoint within 60 ps of SS sign-off is la_nx -> such a field -> output port).
    Here each field is copied into nx_<f> on the LOAD edge that makes its entry NEXT (la_nx <= la_rd), from
    fqd_<f>[la_rd], or from the entry's write data when that write lands on the same edge (data fields: la_we[la_rd];
    control fields: pend1 && la_wr == la_rd).  The NEXT entry is never written while it is NEXT (FIFO depth 8), so
    nx_<f> == fqd_<f>[la_nx] on every cycle after the first LOAD: cycle-identical, 0 added cycles."""
    import re
    text = _rep(text, "    parameter integer DEC_LA = 0,\n",
                "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_NXREG = 0,\n") \
        if "    parameter integer DEC_LA = 0,\n" in text else \
        _rep(text, "    parameter integer DEC_LA = 0\n) (", "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_NXREG = 0\n) (")
    fields = sorted(set(re.findall(r"fqd_(\w+)\[la_nx\]", text)))
    assert fields, "no fqd_*[la_nx] reads"
    regs, upd = [], []
    for f in fields:
        m = re.search(r"\n    reg\s+(\[[^\]]*\]\s*)?fqd_%s\s*\[0:7\];" % re.escape(f), text)
        assert m, f
        w = (m.group(1) or "").strip()
        dm = re.findall(r"if \(la_we\[lw\]\) fqd_%s\[lw\] <= (.*);\n" % re.escape(f), text)
        cm = re.findall(r"\n\s+fqd_%s\[la_wr\]\s*<= (.*);" % re.escape(f), text)
        assert len(dm) + len(cm) == 1, (f, dm, cm)
        regs.append(f"    reg {w + ' ' if w else ''}nx_{f};")
        if dm:
            upd.append(f"            nx_{f} <= la_we[la_rd] ? ({dm[0]}) : fqd_{f}[la_rd];")
        else:
            upd.append(f"            nx_{f} <= (pend1 && la_wr == la_rd) ? ({cm[0]}) : fqd_{f}[la_rd];")
    block = ("    // ---- DEC_LA_NXREG (tools/qwen_rom_core_issue_fallback_w12.py apply_nxreg): NEXT fields registered ----\n"
             + "\n".join(regs) + "\n"
             + "    always @(posedge clk) if (DEC_LA != 0 && DEC_LA_NXREG != 0 && load) begin\n"
             + "\n".join(upd) + "\n    end\n")
    text = _rep(text, "    `undef FP\n", block + "    `undef FP\n")
    for f in fields:
        text = text.replace(f"fqd_{f}[la_nx]", f"((DEC_LA_NXREG != 0) ? nx_{f} : fqd_{f}[la_nx])")
    return text


def apply_meif(text: str) -> str:
    """DEC_LA_MEIF (default 0; coordinator decision 2026-10-06): every core <-> ME-spine handshake crosses a register.
    The ME spine is a separate die element (the tree / spine datapath), so its interface leaves the core's hardened
    block through flops: go and the issued fields are registered at the core's output pins (mq_*: captured on the issue
    edge, held until the next ME issue; go stays raised until the ME's clock enable takes it), and ready / idle /
    progress are registered at the input pins.  For the two cycles in which the registered status still predates
    the ME's acceptance (go pending, then the acceptance edge), the core sees the ME as not ready, not idle and with
    progress 0, so it never issues twice, never passes a wait / barrier / chase on stale status.  Values unchanged;
    each ME handshake gains its register latency (measured on the token benches)."""
    import re
    text = _rep(text, "    parameter integer DEC_LA = 0,\n",
                "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_MEIF = 0,\n") \
        if "    parameter integer DEC_LA = 0,\n" in text else \
        _rep(text, "    parameter integer DEC_LA = 0\n) (", "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_MEIF = 0\n) (")
    i = text.index(" u_me (")
    j = text.index(");", i)
    inst = text[i:j]
    fields = re.findall(r"\.(i_\w+)\((me_\w+)\)", inst)
    widths = {}
    for _, n in fields:
        m = re.search(r"\n\s*(?:output\s+)?(?:wire|reg)\s*(\[[^\]]+\])?\s*[^;\n]*\b%s\b[^;]*;" % n, text)
        assert m, n
        widths[n] = m.group(1) or ""
    new = inst
    for p, n in fields:
        new = new.replace(f".{p}({n})", f".{p}(mq_{n[3:]})")
    new = new.replace(".go(me_go)", ".go(me_go_pin)").replace(".ready(me_ready)", ".ready(me_ready_pin)") \
             .replace(".idle(me_idle)", ".idle(me_idle_pin)").replace(".progress(me_progress)", ".progress(me_progress_pin)")
    text = text[:i] + new + text[j:]
    regs = "\n".join(f"    reg {widths[n] + ' ' if widths[n] else ''}mq_{n[3:]};" for _, n in fields)
    caps = "\n".join(f"            mq_{n[3:]} <= {n};" for _, n in fields)
    block = f"""    // ---- DEC_LA_MEIF (tools/qwen_rom_core_issue_fallback_w12.py apply_meif): registered ME interface ----
    wire me_go_pin, me_ready_pin, me_idle_pin;
    wire [15:0] me_progress_pin;
{regs}
    reg me_gop, me_tk_d, me_rdy_q, me_idl_q;
    reg [15:0] me_prg_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin me_gop <= 1'b0; me_tk_d <= 1'b0; me_rdy_q <= 1'b0; me_idl_q <= 1'b1; me_prg_q <= 16'd0; end
        else begin
            me_gop <= me_go ? 1'b1 : (me_en ? 1'b0 : me_gop);       // raised until the ME's enabled clock takes it
            me_tk_d <= me_gop && me_en;                              // the acceptance edge
            me_rdy_q <= me_ready_pin; me_idl_q <= me_idle_pin; me_prg_q <= me_progress_pin;
        end
    always @(posedge clk) if (me_go) begin
{caps}
    end
    wire me_ifhold = (DEC_LA_MEIF == 2) ? 1'b0 : (me_gop || me_tk_d);   // 2 = NEGATIVE CONTROL: stale status unmasked
    generate if (DEC_LA_MEIF != 0) begin : g_meif
        assign me_go_pin = me_gop;
        assign me_ready = me_rdy_q && !me_ifhold;
        assign me_idle = me_idl_q && !me_ifhold;
        assign me_progress = me_ifhold ? 16'd0 : me_prg_q;
    end else begin : g_nomeif
        assign me_go_pin = me_go;
        assign me_ready = me_ready_pin;
        assign me_idle = me_idle_pin;
        assign me_progress = me_progress_pin;
    end endgenerate
"""
    # the original field nets keep driving mq_* only through the capture (MEIF) or directly (no MEIF): wire them through
    passthru = "\n".join(f"    wire {widths[n] + ' ' if widths[n] else ''}mqw_{n[3:]} = (DEC_LA_MEIF != 0) ? mq_{n[3:]} : {n};"
                         for _, n in fields)
    # insert the block just before the u_me instance statement (after every declaration it needs)
    k = text.rindex("\n", 0, text.rindex("\n", 0, i)) if False else text.rfind("\n    ", 0, i)
    stmt_start = text.rfind(";", 0, i)
    stmt_start = text.index("\n", stmt_start) + 1
    text = text[:stmt_start] + block + passthru + "\n" + text[stmt_start:]
    for _, n in fields:
        text = text.replace(f"(mq_{n[3:]})", f"(mqw_{n[3:]})")
    return text


def apply_suif(text: str) -> str:
    """DEC_LA_SUIF (default 0): the DEC_LA_MEIF treatment for the vector stream unit (SU_VEC: ot_hdc_vstream_rt u_su):
    go and the issued fields from output-pin flops, ready / idle / progress / progress_rows registered at the input
    pins and masked for the two stale cycles (the SU's clock is never gated, so go is taken on the next edge).
    Measurement lever for the core re-cut (the cost of an SU kept outside the core block)."""
    import re
    text = _rep(text, "    parameter integer DEC_LA = 0,\n",
                "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_SUIF = 0,\n") \
        if "    parameter integer DEC_LA = 0,\n" in text else \
        _rep(text, "    parameter integer DEC_LA = 0\n) (", "    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_SUIF = 0\n) (")
    gi = text.index("generate if (SU_VEC != 0) begin : g_vsu")
    i = text.index(" u_su (", gi)
    j = text.index(");", i)
    inst = text[i:j]
    conns = re.findall(r"\.(i_\w+)\(((?:[^()]|\([^()]*\))*)\)", inst)
    def width(expr):
        if re.fullmatch(r"\w+", expr):
            m = re.search(r"\n\s*(?:output\s+)?(?:wire|reg)\s*(\[[^\]]+\])?\s*[^;\n]*\b%s\b[^;]*;" % expr, text)
            assert m, expr
            return m.group(1) or ""
        return ""                                                       # the 1-bit i_asrc expression
    regs, caps, new = [], [], inst
    for p, e in conns:
        w = width(e.strip())
        regs.append(f"    reg {w + ' ' if w else ''}sq_{p[2:]};\n    wire {w + ' ' if w else ''}sqw_{p[2:]} = (DEC_LA_SUIF != 0) ? sq_{p[2:]} : ({e});")
        caps.append(f"            sq_{p[2:]} <= {e};")
        new = new.replace(f".{p}({e})", f".{p}(sqw_{p[2:]})", 1)
    new = new.replace(".go(su_go)", ".go(su_go_pin)").replace(".ready(su_ready)", ".ready(su_ready_pin)") \
             .replace(".idle(su_idle)", ".idle(su_idle_pin)").replace(".progress(su_progress)", ".progress(su_progress_pin)") \
             .replace(".progress_rows(su_rows)", ".progress_rows(su_rows_pin)")
    text = text[:i] + new + text[j:]
    block = (f"""    // ---- DEC_LA_SUIF (tools/qwen_rom_core_issue_fallback_w12.py apply_suif): registered SU interface ----
    wire su_go_pin, su_ready_pin, su_idle_pin;
    wire [15:0] su_progress_pin, su_rows_pin;
""" + "\n".join(regs) + f"""
    reg su_gop, su_rdy_q, su_idl_q; reg [15:0] su_prg_q, su_rws_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin su_gop <= 1'b0; su_rdy_q <= 1'b0; su_idl_q <= 1'b1; su_prg_q <= 16'd0; su_rws_q <= 16'd0; end
        else begin su_gop <= su_go; su_rdy_q <= su_ready_pin; su_idl_q <= su_idle_pin; su_prg_q <= su_progress_pin; su_rws_q <= su_rows_pin; end
    reg su_tk_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) su_tk_d <= 1'b0; else su_tk_d <= su_gop;
    always @(posedge clk) if (su_go) begin
""" + "\n".join(caps) + f"""
    end
    wire su_ifhold = (DEC_LA_SUIF == 2) ? 1'b0 : (su_gop || su_tk_d);   // 2 = NEGATIVE CONTROL: stale status unmasked
    if (DEC_LA_SUIF != 0) begin : g_suif
        assign su_go_pin = su_gop;
        assign su_ready = su_rdy_q && !su_ifhold;
        assign su_idle = su_idl_q && !su_ifhold;
        assign su_progress = su_ifhold ? 16'd0 : su_prg_q;
        assign su_rows = su_ifhold ? 16'd0 : su_rws_q;
    end else begin : g_nosuif
        assign su_go_pin = su_go;
        assign su_ready = su_ready_pin;
        assign su_idle = su_idle_pin;
        assign su_progress = su_progress_pin;
        assign su_rows = su_rows_pin;
    end
""")
    # inside the g_vsu generate block, right before the instance statement
    k = text.rfind("\n", 0, text.rfind("ot_hdc_vstream_rt #", 0, i))
    text = text[:k + 1] + block + text[k + 1:]
    return text
