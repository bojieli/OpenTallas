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
    assert level in (1, 2)
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
