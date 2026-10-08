#!/usr/bin/env python3
"""Emit the Qwen ROM die core as three physical partitions (qwen-missing 2026-10-07).

From the runtime core text (tools/qwen_rom_rt_core_emit_w12.py emit(): ot_qwen_rom_core) this writes:

  ot_qwen_rom_core_ctrl  the core WITHOUT its two units: fetch / decode / DYN / issue, the chunked-argmax fold,
                         the engine clock gate and the INT8 embedding decode -- the logic of die master
                         qfd_sp_constants_sequencer.  The matrix engine spine (u_me, ot_qwen_me_spine_w12: die master
                         qfd_sp_tree_top) and the vector stream unit (u_su, ot_hdc_vstream_rt: die master
                         qfd_sp_su64_sfu) become ports: po_me_* / po_su_* (instruction fields, go, the engine's gated
                         clock, the embedding-decoded va data) and pi_me_* / pi_su_* (ready, idle, progress, faults,
                         argmax, the strobes the controller combines).  Core outputs that only a unit drives are tied
                         to zero in the controller (the partition wrapper takes them from the unit); core inputs only
                         a unit reads are unused there.
  ot_qwen_rom_core_part  the SAME module interface as ot_qwen_rom_core (parameters and ports), built from
                         ot_qwen_rom_core_ctrl + ot_qwen_me_spine_w12 + ot_hdc_vstream_rt.  With STN = 0 it is
                         the core re-wired across the partition boundary, cycle- and bit-identical; it replaces
                         ot_qwen_rom_core in the token bench (tools/qwen_missing/partition_token.py) to prove that
                         the boundary carries everything (no hidden net crosses it).

The emitter refuses to run if an anchor or a connection of the removed instances is not covered.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_rt_core_emit_w12 as EMIT  # noqa: E402

# --- the spine (u_me) and stream unit (u_su) interfaces ----------------------------------------------------
# (sub port, ctrl expression, kind, width): kind 'out' = ctrl drives the unit (port po_<unit>_<sub port>),
# 'in' = the unit drives a ctrl net (port pi_<unit>_<sub port>), 'dir_o' = the unit drives a core OUTPUT port
# (ctrl ties it to 0), 'dir_i' = a core INPUT port read only by the unit.
ME = [("clk", "me_clk", "out", "1"), ("rst_n", "rst_n", "rst", "1"), ("go", "me_go", "out", "1"),
      ("ready", "me_ready", "in", "1"), ("idle", "me_idle", "in", "1"),
      ("i_nout", "me_nout", "out", "NW"), ("i_tiles", "me_tiles", "out", "NW"), ("i_k", "me_k", "out", "NW"),
      ("i_wsrc", "me_wsrc", "out", "1"), ("i_wbase", "me_wbase", "out", "AW"), ("i_ts", "me_ts", "out", "AW"),
      ("i_ks", "me_ks", "out", "AW"), ("i_js", "me_js", "out", "AW"), ("i_xbase", "me_xbase", "out", "AW"),
      ("i_xks", "me_xks", "out", "AW"), ("i_xjs", "me_xjs", "out", "AW"), ("i_xcs", "me_xcs", "out", "AW"),
      ("i_jsh", "me_jsh", "out", "3"), ("i_split", "me_split", "out", "4"), ("i_wcs", "me_wcs", "out", "AW"),
      ("i_round", "me_round", "out", "1"), ("i_obase", "me_obase", "out", "AW"), ("i_ots", "me_ots", "out", "AW"),
      ("i_ojs", "me_ojs", "out", "AW"), ("i_mmode", "me_mmode", "out", "1"), ("i_oen", "me_oen", "out", "1"),
      ("i_amax", "me_amax", "out", "1"), ("i_rmax", "me_rmax", "out", "1"), ("i_mbase", "me_mbase", "out", "AW"),
      ("mx_we", "me_mx_we", "in", "1"), ("mx_addr", "vw_mx_addr", "dir_o", None), ("mx_mask", "vw_mx_mask", "dir_o", None),
      ("mx_data", "vw_mx_data", "dir_o", None), ("wrom_re", "me_wrom_re", "in", "1"),
      ("wrom_addr", "me_wrom_addr", "in", "AW"), ("scale_re", "scale_re", "dir_o", None),
      ("scale_gre", "scale_gre", "dir_o", None), ("scale_addr", "scale_addr", "dir_o", None),
      ("scale_q", "scale_q", "dir_i", None), ("kv_re", "kv_re", "dir_o", None), ("x_re", "vx_re", "dir_o", None),
      ("x_addr", "vx_addr", "dir_o", None), ("x_q", "vx_q", "dir_i", None), ("tgo", "tgo", "dir_o", None),
      ("tb", "tb", "dir_o", None), ("xl_d", "xl_d", "dir_o", None), ("t_lvl", "t_lvl", "dir_i", None),
      ("fab_fault", "fab_fault", "dir_i", None), ("ov", "me_ov", "dir_o", None), ("o_we", "me_o_we", "in", "(G >> SMIN)"),
      ("o_addr", "vw_me_addr", "dir_o", None), ("o_mask", "vw_me_mask", "dir_o", None),
      ("o_data", "vw_me_data", "dir_o", None), ("am_idx", "am_idx", "in", "NW"), ("am_val", "am_val", "in", "32"),
      ("am_any", "am_any", "in", "1"), ("progress", "me_progress", "in", "16"), ("fault", "me_fault", "in", "1")]
SU = [("clk", "clk", "clk", "1"), ("rt_active", "su_active", "in", "1"), ("rt_inflight", "su_inflight", "in", "8"),
      ("rst_n", "rst_n", "rst", "1"), ("go", "su_go", "out", "1"), ("ready", "su_ready", "in", "1"),
      ("idle", "su_idle", "in", "1"), ("i_nout", "su_nout", "out", "NW"), ("i_nin", "su_nin", "out", "NW"),
      ("i_asrc", "(INT8_EMBED != 0) ? 1'b0 : a_src", "out", "1"), ("i_abase", "a_base", "out", "AW"),
      ("i_aso", "a_so", "out", "AW"), ("i_asi", "a_si", "out", "AW"), ("i_bsrc", "b_src", "out", "1"),
      ("i_bbase", "b_base", "out", "AW"), ("i_bso", "b_so", "out", "AW"), ("i_bsi", "b_si", "out", "AW"),
      ("i_csrc", "c_src", "out", "1"), ("i_cbase", "c_base", "out", "AW"), ("i_cso", "c_so", "out", "AW"),
      ("i_csi", "c_si", "out", "AW"), ("i_ma", "ma", "out", "2"), ("i_mb", "mb", "out", "2"), ("i_ad", "ad", "out", "3"),
      ("i_sfu", "sfu", "out", "3"), ("i_mc", "mc", "out", "1"), ("i_md", "md", "out", "1"), ("i_dst", "dst", "out", "2"),
      ("i_dbase", "d_base", "out", "AW"), ("i_dso", "d_so", "out", "AW"), ("i_dsi", "d_si", "out", "AW"),
      ("i_red", "red", "out", "2"), ("i_redsq", "redsq", "out", "1"), ("i_rbase", "r_base", "out", "AW"),
      ("i_rso", "r_so", "out", "AW"), ("i_imm1", "imm1", "out", "32"), ("i_imm2", "imm2", "out", "32"),
      ("va_re", "su_va_re", "in", "SW"), ("va_addr", "su_va_addr", "in", "SW*AW"), ("va_q", "su_va_q", "out", "SW*32"),
      ("vb_re", "vb_re", "dir_o", None), ("vb_addr", "vb_addr", "dir_o", None), ("vb_q", "vb_q", "dir_i", None),
      ("vc_re", "vc_re", "dir_o", None), ("vc_addr", "vc_addr", "dir_o", None), ("vc_q", "vc_q", "dir_i", None),
      ("wrom_re", "su_wrom_re", "in", "1"), ("wrom_addr", "su_wrom_addr", "in", "AW"),
      ("wrom_q", "wrom_q[W*16-1:0]", "dir_i", None), ("crom_re", "crom_re", "dir_o", None),
      ("crom_addr", "crom_addr", "dir_o", None), ("crom_q", "crom_q", "dir_i", None),
      ("vm_we", "vw_su_we", "dir_o", None), ("vm_waddr", "vw_su_addr", "dir_o", None),
      ("vm_wdata", "vw_su_data", "dir_o", None), ("kv_we", "kv_we", "dir_ok", "SW"),
      ("kv_waddr", "kv_waddr", "dir_o", None), ("kv_wdata", "kv_wdata", "dir_o", None),
      ("red_we", "vw_rd_we", "dir_o", None), ("red_addr", "vw_rd_addr", "dir_o", None),
      ("red_data", "vw_rd_data", "dir_o", None), ("progress", "su_progress", "in", "16"),
      ("progress_rows", "su_rows", "in", "16"), ("fault", "su_fault", "in", "1")]


def conns(inst: str):
    """(port, expression) of an instance's named connections (balanced parentheses), after its ') u_xx (' head."""
    m = re.search(r"\)\s*u_\w+\s*\(", inst)
    if not m:
        raise SystemExit("instance head")
    s, out, i = inst[m.end():], [], 0
    while True:
        j = s.find(".", i)
        if j < 0:
            return out
        k = s.index("(", j)
        name = s[j + 1:k].strip()
        d, q = 0, k
        while True:
            if s[q] == "(":
                d += 1
            elif s[q] == ")":
                d -= 1
                if d == 0:
                    break
            q += 1
        out.append((name, s[k + 1:q].strip()))
        i = q + 1


def cut(text: str, start_pat: str, end_pat: str):
    s = text.find(start_pat)
    if s < 0 or text.count(start_pat) != 1:
        raise SystemExit(f"anchor: {start_pat!r}")
    e = text.find(end_pat, s)
    if e < 0:
        raise SystemExit(f"end anchor: {end_pat!r}")
    return s, e + len(end_pat)


def check(table, inst, who):
    got = conns(inst)
    want = [(p, e) for p, e, _, _ in table]
    if [g[0] for g in got] != [w[0] for w in want]:
        raise SystemExit(f"{who}: port list changed\n got  {[g[0] for g in got]}\n want {[w[0] for w in want]}")
    for (gp, ge), (wp, we) in zip(got, want):
        if re.sub(r"\s+", "", ge) != re.sub(r"\s+", "", we):
            raise SystemExit(f"{who}.{gp}: connection {ge!r} != {we!r}")


def header(text: str):
    s = text.index("module ot_qwen_rom_core #(")
    e = text.index("\n) (\n", s)
    pe = text.index("\n);\n", e)
    return text[s:e], text[e + 5:pe]


def ports_of(port_text: str):
    out = []
    for line in port_text.splitlines():
        m = re.match(r"\s*(input|output)\s+(?:wire|reg)?\s*(\[[^\]]*\])?\s*([\w\s,]+?),?\s*(//.*)?$", line)
        if m:
            for n in m.group(3).split(","):
                if n.strip():
                    out.append((m.group(1), m.group(2) or "", n.strip()))
    return out


def emit_ctrl(core: str) -> str:
    t = core.replace("module ot_qwen_rom_core #(", "module ot_qwen_rom_core_ctrl #(", 1)
    s, e = cut(t, "    ot_qwen_me_spine_w12 #(", "fault(me_fault));\n")
    me_inst = t[s:e]
    check(ME, me_inst, "u_me")
    body = ["    // ---- matrix engine spine (die master qfd_sp_tree_top): ports ----"]
    for p, ex, k, w in ME:
        if k == "out":
            body.append(f"    assign po_me_{p} = {ex};")
        elif k == "in":
            body.append(f"    assign {ex} = pi_me_{p};")
        elif k == "dir_o":
            body.append(f"    assign {ex} = '0;   // driven by the spine in ot_qwen_rom_core_part")
    t = t[:s] + "\n".join(body) + "\n" + t[e:]
    s, e = cut(t, "    generate if (SU_VEC != 0) begin : g_vsu", "    end endgenerate\n")
    su_inst = t[s:e]
    i0, i1 = cut(su_inst, "    ot_hdc_vstream_rt #(", "fault(su_fault));\n")
    check(SU, su_inst[i0:i1], "u_su")
    body = ["    // ---- vector stream unit (die master qfd_sp_su64_sfu): ports (SU_VEC = 1 only) ----",
            "    assign po_su_asrc_raw = a_src;   // split-exact: the embedding selector travels with the go"]
    for p, ex, k, w in SU:
        if k == "out":
            body.append(f"    assign po_su_{p} = {ex};")
        elif k == "in":
            body.append(f"    assign {ex} = pi_su_{p};")
        elif k == "dir_ok":
            body.append(f"    assign {ex} = pi_su_{p};   // also read by the controller (kv_write_flush)")
        elif k == "dir_o":
            body.append(f"    assign {ex} = '0;   // driven by the stream unit in ot_qwen_rom_core_part")
    t = t[:s] + "\n".join(body) + "\n" + t[e:]
    # the extra ports go after the last core port
    anchor = "    output wire              me_clk_en       // ME_STALL: this edge clocks the engine (pre-edge value)\n);"
    if t.count(anchor) != 1:
        raise SystemExit("ctrl port anchor")
    extra = []
    for unit, table in (("me", ME), ("su", SU)):
        for p, ex, k, w in table:
            if k == "out":
                extra.append(f"    output wire [{w}-1:0] po_{unit}_{p}")
            elif k in ("in", "dir_ok"):
                extra.append(f"    input  wire [{w}-1:0] pi_{unit}_{p}")
    extra.append("    output wire [1-1:0] po_su_asrc_raw")
    t = t.replace(anchor, anchor[:-3].replace("me_clk_en       //", "me_clk_en,      //") + "\n    // -- partition ports (tools/qwen_missing/emit_partition.py) --\n" + ",\n".join(extra) + "\n);", 1)
    if re.search(r"\bu_me\b|\bu_su\b", re.sub(r"//[^\n]*", "", t.split("// -- partition ports")[1])):
        raise SystemExit("a reference to u_me / u_su remains in the controller")
    return ("// GENERATED by tools/qwen_missing/emit_partition.py from the emitted ot_qwen_rom_core "
            "(tools/qwen_rom_rt_core_emit_w12.py). The core minus its matrix-engine spine and stream unit.\n" + t)


# Split-exact (qwen-split-exact 2026-10-07): ctrl -> unit nets cross DCU stations, unit -> ctrl nets DUC; the
# controller sees the units through ot_qfd_issue_shell (rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv,
# crossing classes A-F there).  Unit -> ctrl nets the controller must NOT take stationed (they leave the controller):
ME_LOCAL = {"mx_we", "o_we"}               # class E: VM write enables gated with me_en on the engine side
SU_LOCAL = {"va_re", "va_addr"}            # class D: the va read loop stays on the stream-unit side (ot_qfd_su_embed)
SHELL_ME = {"ready", "idle", "progress"}   # classes A / B
SHELL_SU = {"ready", "idle", "progress", "progress_rows"}


def _rst(w: str) -> str:
    return ", .RESET(1)" if w in ("1", "8", "16") else ""


def emit_part(core: str, dcu: int = 0, duc: int = 0, comp: int = 1, su_ml: int = 0) -> str:
    """ot_qwen_rom_core_part: the core re-wired across the three die masters with DCU / DUC pin stations and the
    split-exact compensation.  DCU = DUC = 0 (any COMP) is cycle-identical to ot_qwen_rom_core."""
    params, port_text = header(core)
    ports = ports_of(port_text)
    names = [n for _, _, n in ports]
    for need in ("clk", "me_clk_en", "scale_q", "vb_q", "crom_q", "kv_we", "va_re", "embed_code_re", "vw_me_we"):
        if need not in names:
            raise SystemExit(f"part: core port {need} not parsed")
    pnames = re.findall(r"parameter\s+integer\s+(\w+)", params)
    L = ["// GENERATED by tools/qwen_missing/emit_partition.py: ot_qwen_rom_core re-wired across the die-master partition",
         "// (qfd_sp_constants_sequencer = ot_qwen_rom_core_ctrl, qfd_sp_tree_top = ot_qwen_me_spine_w12,",
         "// qfd_sp_su64_sfu = ot_hdc_vstream_rt) with DCU / DUC pin stations and the split-exact compensation",
         "// (ot_qfd_split_exact.sv).  Same ports as ot_qwen_rom_core.",
         params.replace("module ot_qwen_rom_core #(", "module ot_qwen_rom_core_part #(", 1)
         + f",\n    parameter integer DCU = {dcu},\n    parameter integer DUC = {duc},\n    parameter integer COMP = {comp}",
         ") (", port_text, ");",
         "    localparam integer RT = DCU + DUC;   // c_me_clk = the controller's po_me_clk: the engine's gated clock"]
    dir_ports = {ex.split("[")[0] for _, ex, k, _ in ME + SU if k in ("dir_o", "dir_i")}
    for unit, table in (("me", ME), ("su", SU)):
        for p, ex, k, w in table:
            if k in ("out", "in"):
                L.append(f"    wire [{w}-1:0] c_{unit}_{p}, u_{unit}_{p};")
    L += ["    wire [SW-1:0] su_kv_we, d_su_kv_we;", "    wire c_su_asrc_raw, u_su_asrc_raw;",
          "    wire [NW-1:0] c_tok, u_tok; wire [15:0] c_escale, u_escale;", "    wire u_su_efault;"]
    # ---- controller
    own = {"kv_we", "va_re", "va_addr", "embed_code_re", "embed_code_addr", "vw_me_we", "vw_mx_we"}
    cc = []
    for n in names:
        if n in own:
            cc.append(f".{n}()")
        elif n in dir_ports:
            cc.append(f".{n}()")
        else:
            cc.append(f".{n}({n})")
    for _, ex, k, _ in ME + SU:
        if k == "dir_i":
            n = ex.split("[")[0]
            cc = [c if c != f".{n}()" else f".{n}('0)" for c in cc]
    for unit, table, local, shell in (("me", ME, ME_LOCAL, SHELL_ME), ("su", SU, SU_LOCAL, SHELL_SU)):
        for p, ex, k, w in table:
            if k == "out":
                cc.append(f".po_{unit}_{p}(c_{unit}_{p})")
            elif k == "in":
                if p in local:
                    cc.append(f".pi_{unit}_{p}('0)")
                elif p in shell:
                    cc.append(f".pi_{unit}_{p}(s_{unit}_{p})")
                else:
                    cc.append(f".pi_{unit}_{p}(c_{unit}_{p})")
            elif k == "dir_ok":
                cc.append(f".pi_{unit}_{p}(d_su_kv_we)")
    cc.append(".po_su_asrc_raw(c_su_asrc_raw)")
    L += ["    wire s_me_ready, s_me_idle, s_su_ready, s_su_idle;", "    wire [15:0] s_me_progress, s_su_progress, s_su_progress_rows;"]
    L.append("    ot_qwen_rom_core_ctrl #(" + ", ".join(f".{p}({p})" for p in pnames) + ") u_ctrl (\n        "
             + ",\n        ".join(cc) + ");")
    L += ["    ot_qfd_issue_shell #(.RT_ME(RT), .RT_SU(RT), .COMP(COMP)) u_shell (.clk(clk), .rst_n(rst_n),",
          "        .me_go(c_me_go), .su_go(c_su_go), .me_en(me_clk_en), .su_sfu(c_su_i_sfu), .me_amax(c_me_i_amax),",
          "        .d_me_ready(c_me_ready), .d_me_idle(c_me_idle), .d_me_progress(c_me_progress),",
          "        .d_su_ready(c_su_ready), .d_su_idle(c_su_idle), .d_su_active(c_su_rt_active), .d_su_inflight(c_su_rt_inflight),",
          "        .d_su_progress(c_su_progress), .d_su_rows(c_su_progress_rows),",
          "        .c_me_ready(s_me_ready), .c_me_idle(s_me_idle), .c_me_progress(s_me_progress),",
          "        .c_su_ready(s_su_ready), .c_su_idle(s_su_idle), .c_su_progress(s_su_progress), .c_su_rows(s_su_progress_rows));"]
    # ---- per-token constants for the stream-unit side embedding decode (static from the token start)
    L += ["    reg es_pend; reg [15:0] es_hold; reg [NW-1:0] tok_l;",
          "    always @(posedge clk or negedge rst_n) if (!rst_n) es_pend <= 1'b0; else es_pend <= embed_scale_re;",
          "    always @(posedge clk) begin if (es_pend) es_hold <= embed_scale_q; if (embed_scale_re) tok_l <= token; end",
          "    assign c_tok = tok_l; assign c_escale = es_hold;"]
    # ---- stations
    def stn(name, w, d, clk, src, dst, rst=""):
        L.append(f"    ot_hdc_delay #(.W({w}), .D({d}){rst}) u_{name} (.clk({clk}), .rst_n(rst_n), .d({src}), .q({dst}));")
    for p, ex, k, w in ME:
        if k == "out" and p != "clk":
            stn(f"sd_me_{p}", w, "DCU", "c_me_clk", f"c_me_{p}", f"u_me_{p}", ", .RESET(1)" if p == "go" else "")
        elif k == "in" and p not in ME_LOCAL:
            stn(f"su_me_{p}", w, "DUC", "c_me_clk", f"u_me_{p}", f"c_me_{p}", _rst(w))
    for p, ex, k, w in SU:
        if k == "out" and p != "va_q":
            stn(f"sd_su_{p}", w, "DCU", "clk", f"c_su_{p}", f"u_su_{p}", ", .RESET(1)" if p == "go" else "")
        elif k == "in" and p not in SU_LOCAL:
            src = "u_su_fault | u_su_efault" if p == "fault" else f"u_su_{p}"
            stn(f"su_su_{p}", w, "DUC", "clk", src, f"c_su_{p}", _rst(w))
    stn("sd_asrc", "1", "DCU", "clk", "c_su_asrc_raw", "u_su_asrc_raw")
    stn("sd_tok", "NW", "DCU", "clk", "c_tok", "u_tok")
    stn("sd_escale", "16", "DCU", "clk", "c_escale", "u_escale")
    stn("su_kvwe", "SW", "DUC", "clk", "su_kv_we", "d_su_kv_we", ", .RESET(1)")
    # ---- engine side: VM write enables with the ICG enable (class E)
    L += ["    assign vw_me_we = u_me_o_we & {(G >> SMIN){me_clk_en}};",
          "    assign vw_mx_we = u_me_mx_we & me_clk_en;"]
    sp = []
    for p, ex, k, w in ME:
        if p == "clk":
            sp.append(".clk(c_me_clk)")
        elif k in ("out", "in"):
            sp.append(f".{p}(u_me_{p})")
        elif k == "rst":
            sp.append(f".{p}(rst_n)")
        else:
            sp.append(f".{p}({ex})")
    L.append("    ot_qwen_me_spine_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE),\n"
             "        .GT(G), .TG(4), " + ", ".join(f".{p}({p})" for p in EMIT.SPINE_PARAMS) + ") u_me (\n        "
             + ",\n        ".join(sp) + ");")
    # ---- stream-unit side: embedding decode on the va loop (class D)
    L += ["    ot_qfd_su_embed #(.SW(SW), .AW(AW), .NW(NW), .HID(HID), .EMB_CODE_LANES(EMB_CODE_LANES),",
          "        .EMB_ADDR_BASE(EMB_ADDR_BASE), .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .INT8_EMBED(INT8_EMBED)) u_emb (",
          "        .clk(clk), .rst_n(rst_n), .go(u_su_go), .a_src(u_su_asrc_raw), .tok(u_tok), .scale(u_escale),",
          "        .su_va_re(u_su_va_re), .su_va_addr(u_su_va_addr), .su_va_q(u_su_va_q), .va_re(va_re), .va_addr(va_addr),",
          "        .va_q(va_q), .embed_code_re(embed_code_re), .embed_code_addr(embed_code_addr), .embed_code_q(embed_code_q),",
          "        .fault(u_su_efault));"]
    # qwen-rtl-finish: SU_ML > 0 models the re-cut SU master (ot_qfd_sp_su64_sfu_ab): every memory answers the lanes
    # 1 + SU_ML edges after the strobe (the far constant / weight ROM; the abutted VM's answers delayed inside the master)
    SU_MEM = {"va_q": "SW*32", "vb_q": "SW*32", "vc_q": "SW*32", "wrom_q": "W*16", "crom_q": "SW*64"}
    su = []
    for p, ex, k, w in SU:
        if su_ml and p in SU_MEM:
            src = f"u_su_{p}" if k in ("out", "in") else ex
            L.append(f"    wire [{SU_MEM[p]}-1:0] ml_{p};")
            L.append(f"    ot_hdc_delay #(.W({SU_MEM[p]}), .D({su_ml})) u_ml_{p} (.clk(clk), .rst_n(rst_n), .d({src}), .q(ml_{p}));")
            su.append(f".{p}(ml_{p})")
        elif k in ("out", "in"):
            su.append(f".{p}(u_su_{p})")
        elif k in ("rst", "clk"):
            su.append(f".{p}({ex})")
        elif k == "dir_ok":
            su.append(f".{p}(su_kv_we)")
        else:
            su.append(f".{p}({ex})")
    L.append(f"    ot_hdc_vstream_rt #(.SW(SW), .LV(LV), .WR(W), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML({su_ml})) u_su (\n        "
             + ",\n        ".join(su) + ");")
    L.append("    assign kv_we = su_kv_we;")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--committed", action="store_true", help="(re)write rtl/qwen_sys/missing_masters_20261007/gen")
    ap.add_argument("--check", action="store_true", help="fail if the committed generated masters are stale")
    a = ap.parse_args()
    gen = ROOT / "rtl/qwen_sys/missing_masters_20261007/gen"
    if a.committed:
        write_committed(gen)
        print(gen)
        return
    if a.check:
        check_committed(gen)
        return
    a.out_dir.mkdir(parents=True, exist_ok=True)
    core = EMIT.emit(EMIT.CORE.read_text())
    (a.out_dir / "ot_qwen_rom_core.sv").write_text(core)
    (a.out_dir / "ot_qwen_rom_core_ctrl.sv").write_text(emit_ctrl(core))
    (a.out_dir / "ot_qwen_rom_core_part.sv").write_text(emit_part(core))
    (a.out_dir / "ot_hdc_vstream_rt.sv").write_text(EMIT.emit_vstream(EMIT.VSTREAM.read_text()))
    print(a.out_dir)



# --------------------------------------------------------------------------------------------------------------
# die master qfd_sp_constants_sequencer: the controller + TP sequencer + program / descriptor stores, stationed
SEQ_IN = [("h_start", "1"), ("tp_token", "NW"), ("tp_pos", "NW"), ("embed_code_q", "512"), ("embed_scale_q", "16"),
          ("va_q", "SW*32"), ("kv_write_drained", "1"), ("kv_ok", "1"), ("me_mem_ok", "1"),
          ("vm_rq", "512"), ("c_ready", "1"), ("r_valid", "1"), ("r_data", "512"), ("r_last", "1"), ("r_rank", "2"),
          ("r_err", "1"), ("pw_v", "1"), ("pw_addr", "10"), ("pw_data", "64"), ("dw_v", "1"), ("dw_addr", "3"),
          ("dw_data", "64")]
SEQ_OUT = [("s_done", "1"), ("seq_ntok", "NW"), ("seq_nval", "32"), ("s_fault", "1"), ("core_fault", "1"),
           ("coll_busy", "1"), ("embed_code_re", "1"), ("embed_code_addr", "AW"), ("embed_scale_re", "1"),
           ("embed_scale_addr", "NW"), ("va_re", "SW"), ("va_addr", "SW*AW"), ("kv_write_flush", "1"), ("kvd_v", "1"),
           ("kvd_wbase", "AW"), ("kvd_ts", "AW"), ("kvd_ks", "AW"), ("kvd_js", "AW"), ("kvd_wcs", "AW"),
           ("kvd_split", "4"), ("kvd_jsh", "3"), ("kvd_tiles", "NW"), ("kvd_k", "NW"), ("kvd_nout", "NW"),
           ("kvd_kindk", "1"), ("kvd_pos", "NW"), ("me_clk_en", "1"), ("vm_re", "1"), ("vm_raddr", "8"), ("vm_we", "1"),
           ("vm_waddr", "8"), ("vm_wdata", "512"), ("c_valid", "1"), ("c_data", "512"), ("c_last", "1"), ("c_mode", "1"),
           ("c_tag", "32"), ("rom_fault", "1")]
SEQ_PARAMS = dict(G=6144, NW=18, SW=64, LV=7, D=4, ENABLE_AR256=1, QWEN_FULLSHAPE=1, SMIN=7, SMAX=11, TCUT=7)


# qwen-rtl-finish 2026-10-07 (re-cut from the split-exact partition): the embedding decode and its code / scale reads
# live on the stream-unit side (ot_qfd_sp_su64_sfu_ab: row buffer), so the sequencer master drops the va loop and the
# embedding ports and sends the token and the per-op selector instead; the engine-local VM write enables (ME_LOCAL) and
# the SU-local va loop (SU_LOCAL) are not controller pins; me_mem_ok / me_clk_en form the engine clock-gate enable path
# (split-exact class E) and are NOT stationed; the issue shell (classes A-C) sits inside the master.
SEQ_DROP = {"embed_code_q", "embed_scale_q", "va_q", "embed_code_re", "embed_code_addr", "embed_scale_re",
            "embed_scale_addr", "va_re", "va_addr"}
SEQ_UNSTN = {"me_mem_ok", "me_clk_en"}
SEQ_EXTRA_OUT = [("su_asrc", "1"), ("su_tok", "NW")]


def _local(u, p):
    return (u == "me" and p in ME_LOCAL) or (u == "su" and p in SU_LOCAL)


def _shell(u, p):
    return (u == "me" and p in SHELL_ME) or (u == "su" and p in SHELL_SU)


def seq_ports():
    ins = [x for x in SEQ_IN if x[0] not in SEQ_DROP] + \
          [(f"pi_{u}_{p}", w) for u, tab in (("me", ME), ("su", SU)) for p, _, k, w in tab
           if k in ("in", "dir_ok") and not _local(u, p)]
    outs = [x for x in SEQ_OUT if x[0] not in SEQ_DROP] + SEQ_EXTRA_OUT + \
           [(f"po_{u}_{p}", w) for u, tab in (("me", ME), ("su", SU)) for p, _, k, w in tab
            if k == "out" and not (u == "me" and p == "clk") and not (u == "su" and p == "va_q")]
    return ins, outs


def _shell_text(pfx, qin, rt="RT"):
    """the controller-side issue shell (ot_qfd_split_exact.sv) and the token latch, for the master (q_) / bench (ref)"""
    return [f"    wire {pfx}s_me_ready, {pfx}s_me_idle, {pfx}s_su_ready, {pfx}s_su_idle;",
            f"    wire [15:0] {pfx}s_me_progress, {pfx}s_su_progress, {pfx}s_su_progress_rows;",
            f"    wire {pfx}me_go_w, {pfx}su_go_w, {pfx}me_amax_w, {pfx}me_en_w, {pfx}es_re_w; wire [2:0] {pfx}su_sfu_w;",
            f"    ot_qfd_issue_shell #(.RT_ME({rt}), .RT_SU({rt}), .COMP(1)) {pfx}u_shell (.clk(clk), .rst_n({pfx}rs_w),",
            f"        .me_go({pfx}me_go_w), .su_go({pfx}su_go_w), .me_en({pfx}me_en_w), .su_sfu({pfx}su_sfu_w), .me_amax({pfx}me_amax_w),",
            f"        .d_me_ready({qin}pi_me_ready), .d_me_idle({qin}pi_me_idle), .d_me_progress({qin}pi_me_progress),",
            f"        .d_su_ready({qin}pi_su_ready), .d_su_idle({qin}pi_su_idle), .d_su_active({qin}pi_su_rt_active),",
            f"        .d_su_inflight({qin}pi_su_rt_inflight), .d_su_progress({qin}pi_su_progress), .d_su_rows({qin}pi_su_progress_rows),",
            f"        .c_me_ready({pfx}s_me_ready), .c_me_idle({pfx}s_me_idle), .c_me_progress({pfx}s_me_progress),",
            f"        .c_su_ready({pfx}s_su_ready), .c_su_idle({pfx}s_su_idle), .c_su_progress({pfx}s_su_progress),",
            f"        .c_su_rows({pfx}s_su_progress_rows));",
            f"    reg [NW-1:0] {pfx}tok_l;",
            f"    always @(posedge clk) if ({pfx}es_re_w) {pfx}tok_l <= {pfx}core_tok_w;"]


def _unit_conns(pfx, src_pref, out_pref):
    cc = []
    for u, tab in (("me", ME), ("su", SU)):
        for p, _, k, w in tab:
            if k == "out" and not (u == "me" and p == "clk"):
                if u == "su" and p == "va_q":
                    cc.append(".po_su_va_q()")
                else:
                    cc.append(f".po_{u}_{p}({out_pref}po_{u}_{p})")
            elif k in ("in", "dir_ok"):
                if _local(u, p):
                    cc.append(f".pi_{u}_{p}('0)")
                elif _shell(u, p):
                    cc.append(f".pi_{u}_{p}({pfx}s_{u}_{p})")
                else:
                    cc.append(f".pi_{u}_{p}({src_pref}pi_{u}_{p})")
    return cc


def emit_seq_master() -> str:
    ins, outs = seq_ports()
    P = SEQ_PARAMS
    L = ["`timescale 1ns/1ps",
         "// GENERATED by tools/qwen_missing/emit_partition.py: die master qfd_sp_constants_sequencer (qwen-missing",
         "// 2026-10-07).  ot_qwen_rom_core_ctrl (the core without its spine and stream unit) + ot_qwen_tp_seq_w12 + the",
         "// program store (64 x 1,024 b) and segment-descriptor store (8 x 64 b) of the runtime die (configuration",
         "// flops written through pw_* / dw_*, read with the die's registered-response semantics), every port through",
         "// IS input / OS output stations (ot_hdc_delay; one-bit ports on reset lines) except po_me_clk, the engine's",
         "// gated clock (ICG output, a clock pin of the spine master), and the ICG enable path me_mem_ok -> me_clk_en",
         "// (split-exact class E).  qwen-rtl-finish re-cut: the issue shell (ot_qfd_issue_shell, RT) sits here; the INT8",
         "// embedding decode and its ROM reads moved to the stream unit (su_asrc / su_tok leave instead).  The constant",
         "// ROM is not in this master.",
         "module ot_qfd_sp_constants_sequencer #(",
         "    parameter integer W = 16, parameter integer G = %d, parameter integer AW = 24, parameter integer NW = %d," % (P["G"], P["NW"]),
         "    parameter integer PAW = 12, parameter integer SW = %d, parameter integer LV = %d, parameter integer D = %d," % (P["SW"], P["LV"], P["D"]),
         "    parameter integer SMIN = %d, parameter integer SMAX = %d, parameter integer TCUT = %d," % (P["SMIN"], P["SMAX"], P["TCUT"]),
         "    parameter integer IS = 1, parameter integer OS = 1, parameter integer MUT = 0,",
         "    parameter integer RT = 4    // engine / unit edges from a go to post-accept status (DCU + DUC, ot_qfd_issue_shell)",
         ") (", "    input  wire clk,", "    input  wire rst_n,", "    output wire po_me_clk,"]
    L += [f"    input  wire [{w}-1:0] {n}," for n, w in ins]
    L += [f"    output wire [{w}-1:0] {n}," for n, w in outs]
    L[-1] = L[-1].rstrip(",")
    L += [");"]
    L += ["    wire rs;", "    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));"]
    # input stations
    for n, w in ins:
        L.append(f"    wire [{w}-1:0] q_{n};")
        rst = ", .RESET(1)" if w == "1" else ""
        src = f"{n} ^ (MUT != 0 ? 1 : 0)" if n == "pi_me_ready" else n
        if n in SEQ_UNSTN:
            L.append(f"    assign q_{n} = {n};   // not stationed (ICG enable path)")
        else:
            L.append(f"    ot_hdc_delay #(.W({w}), .D(IS){rst}) u_i_{n} (.clk(clk), .rst_n(rst_n), .d({src}), .q(q_{n}));")
    for n, w in outs:
        L.append(f"    wire [{w}-1:0] b_{n};")
        rst = ", .RESET(1)" if w == "1" else ""
        if n in SEQ_UNSTN:
            L.append(f"    assign {n} = b_{n};   // not stationed (ICG enable path)")
        else:
            L.append(f"    ot_hdc_delay #(.W({w}), .D(OS){rst}) u_o_{n} (.clk(clk), .rst_n(rst_n), .d(b_{n}), .q({n}));")
    L += ["    wire rs_w = rs; wire [NW-1:0] core_tok_w;"]
    L += _shell_text("", "q_")
    L += ["    assign me_go_w = b_po_me_go; assign su_go_w = b_po_su_go; assign me_amax_w = b_po_me_i_amax;",
          "    assign su_sfu_w = b_po_su_i_sfu; assign me_en_w = b_me_clk_en; assign b_su_tok = tok_l;"]
    # program / descriptor stores (the runtime die's semantics)
    L += ["    wire core_start, core_done, core_fault_w; wire [NW-1:0] core_tok, core_pos, core_ntok; wire [31:0] core_nval;",
          "    wire prog_re; wire [11:0] prog_addr, prog_base; reg [1023:0] prog_q;",
          "    wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;",
          "    reg [1023:0] prog_mem [0:63];",
          "    reg [63:0] desc_mem [0:7];",
          "    wire [11:0] prog_a = prog_base + prog_addr;",
          "    always @(posedge clk) begin",
          "        if (q_pw_v) prog_mem[q_pw_addr[9:4]][q_pw_addr[3:0]*64 +: 64] <= q_pw_data;",
          "        if (q_dw_v) desc_mem[q_dw_addr] <= q_dw_data;",
          "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;",
          "        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;",
          "    end",
          "    wire wrom_re_w;",
          "    assign b_rom_fault = wrom_re_w;",
          "    assign b_core_fault = core_fault_w;"]
    cpar = ("W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(1), .SW(SW), .LV(LV), .KV_FP8(1), .INT8_WEIGHT(1), "
            ".INT8_SCALE_WCS_BASE(1), .INT8_EMBED(1), .QWEN_FULLSHAPE(%d), .HID(4096), .HALF(64), .HD(128), "
            ".EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .KV_HBM(1), .KV_VEC_WRITE_BRIDGE(1), .ME_STALL(1), "
            ".ME_IDLE_GATE(1), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT)" % P["QWEN_FULLSHAPE"])
    cc = [".clk(clk)", ".rst_n(rs)", ".start(core_start)", ".token(core_tok_w)", ".pos(core_pos)", ".done(core_done)",
          ".next_token(core_ntok)", ".next_val(core_nval)", ".cycles()", ".fault(core_fault_w)",
          ".prog_re(prog_re)", ".prog_addr(prog_addr)", ".prog_q(prog_q)", ".wrom_re(wrom_re_w)", ".wrom_addr()",
          ".wrom_q('0)", ".int8_wrom_re()", ".int8_wrom_addr()", ".scale_re()", ".scale_gre()", ".scale_addr()",
          ".scale_q('0)", ".embed_code_re()", ".embed_code_addr()",
          ".embed_code_q('0)", ".embed_scale_re(es_re_w)", ".embed_scale_addr()",
          ".embed_scale_q('0)", ".crom_re()", ".crom_addr()", ".crom_q('0)", ".kv_re()", ".kv_we()",
          ".kv_waddr()", ".kv_wdata()", ".kv_write_drained(q_kv_write_drained)", ".kv_write_flush(b_kv_write_flush)",
          ".va_re()", ".va_addr()", ".va_q('0)", ".vb_re()", ".vb_addr()", ".vb_q('0)",
          ".vc_re()", ".vc_addr()", ".vc_q('0)", ".vw_me_we()", ".vw_me_addr()", ".vw_me_mask()", ".vw_me_data()",
          ".vw_su_we()", ".vw_su_addr()", ".vw_su_data()", ".vw_rd_we()", ".vw_rd_addr()", ".vw_rd_data()",
          ".vw_mx_we()", ".vw_mx_addr()", ".vw_mx_mask()", ".vw_mx_data()", ".me_ov()", ".kvd_v(b_kvd_v)"]
    cc += [f".kvd_{n}(b_kvd_{n})" for n in ("wbase", "ts", "ks", "js", "wcs", "split", "jsh", "tiles", "k", "nout",
                                           "kindk", "pos")]
    cc += [".kv_ok(q_kv_ok)", ".wrom_su()", ".wd_v()", ".wd_wbase()", ".wd_sbase()", ".wd_tiles()", ".wd_k()",
           ".wd_nout()", ".vx_re()", ".vx_addr()", ".vx_q('0)", ".tgo()", ".tb()", ".xl_d()", ".t_lvl('0)",
           ".fab_fault(1'b0)", ".w_ok(1'b1)", ".emb_ok(1'b1)", ".me_mem_ok(q_me_mem_ok)", ".me_clk_en(b_me_clk_en)",
           ".po_me_clk(po_me_clk)"]
    cc += _unit_conns("", "q_", "b_")
    cc.append(".po_su_asrc_raw(b_su_asrc)")   # split-exact: the SU-side embedding decode's per-op selector
    L.append(f"    ot_qwen_rom_core_ctrl #(.{cpar}) u_ctrl (\n        " + ",\n        ".join(cc) + ");")
    L += ["    ot_qwen_tp_seq_w12 #(.N(D), .NW(NW), .PAW(PAW), .VWA(8), .DAW(6), .FW(512), .TAGW(32),",
          "        .QWEN_FULLSHAPE(%d), .ENABLE_AR256(%d)) u_seq (" % (P["QWEN_FULLSHAPE"], P["ENABLE_AR256"]),
          "        .clk(clk), .rst_n(rs), .start(q_h_start), .token(q_tp_token), .pos(q_tp_pos), .done(b_s_done),",
          "        // (core_tok_w: the token the controller latches at its embedding-scale read)",
          "        .next_token(b_seq_ntok), .next_val(b_seq_nval), .fault(b_s_fault), .coll_busy(b_coll_busy),",
          "        .core_start(core_start), .core_token(core_tok_w), .core_pos(core_pos), .core_done(core_done),",
          "        .core_next_token(core_ntok), .core_next_val(core_nval), .core_fault(core_fault_w), .prog_base(prog_base),",
          "        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(b_vm_re), .vm_raddr(b_vm_raddr),",
          "        .vm_rq(q_vm_rq), .vm_we(b_vm_we), .vm_waddr(b_vm_waddr), .vm_wdata(b_vm_wdata), .c_valid(b_c_valid),",
          "        .c_ready(q_c_ready), .c_data(b_c_data), .c_last(b_c_last), .c_mode(b_c_mode), .c_tag(b_c_tag),",
          "        .r_valid(q_r_valid), .r_data(q_r_data), .r_last(q_r_last), .r_rank(q_r_rank), .r_err(q_r_err));",
          "endmodule"]
    return "\n".join(L) + "\n"


def inline_include(text: str) -> str:
    svh = (ROOT / "rtl/hdc/ot_hdc_isa.svh").read_text()
    if text.count('`include "ot_hdc_isa.svh"') != 1:
        raise SystemExit("isa include anchor")
    return text.replace('`include "ot_hdc_isa.svh"', "// ---- inlined rtl/hdc/ot_hdc_isa.svh ----\n" + svh, 1)


def write_committed(out: Path):
    core = EMIT.emit(EMIT.CORE.read_text())
    out.mkdir(parents=True, exist_ok=True)
    (out / "ot_qwen_rom_core_ctrl.sv").write_text(inline_include(emit_ctrl(core)))
    (out / "ot_qfd_sp_constants_sequencer.sv").write_text(emit_seq_master())
    (ROOT / "rtl/test/tb_qfd_constants_sequencer.sv").write_text(emit_seq_tb())


def check_committed(out: Path):
    core = EMIT.emit(EMIT.CORE.read_text())
    want = {out / "ot_qwen_rom_core_ctrl.sv": inline_include(emit_ctrl(core)),
            out / "ot_qfd_sp_constants_sequencer.sv": emit_seq_master(),
            ROOT / "rtl/test/tb_qfd_constants_sequencer.sv": emit_seq_tb()}
    stale = [str(n) for n, t in want.items() if n.read_text() != t]
    if stale:
        raise SystemExit(f"STALE generated masters (re-run emit_partition.py --committed): {stale}")
    print("generated masters current")



def emit_seq_tb() -> str:
    """rtl/test/tb_qfd_constants_sequencer.sv: the master against an independently wired reference (the runtime
    die's controller + TP sequencer + stores, as rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv wires
    them), open loop: random program / descriptor images, random unit responses and memory data every cycle."""
    ins, outs = seq_ports()
    P = SEQ_PARAMS
    L = ["`timescale 1ns/1ps",
         "// GENERATED by tools/qwen_missing/emit_partition.py --committed (qwen-missing 2026-10-07).  The",
         "// qfd_sp_constants_sequencer master (IS / OS stations) against the bare controller + TP sequencer + stores",
         "// wired as the runtime die wires them; every output of the master must equal the reference's IS + OS cycles",
         "// earlier (4-state).  MUT = 1 inverts one input-station bit (pi_me_ready): must FAIL.",
         "module tb_qfd_constants_sequencer;",
         "    parameter integer IS = 1, OS = 1, MUT = 0, CYCLES = 6000, SEED = 3, RT = 4;",
         "    localparam integer W = 16, G = %d, AW = 24, NW = %d, PAW = 12, SW = %d, LV = %d, D = %d;" % (P["G"], P["NW"], P["SW"], P["LV"], P["D"]),
         "    localparam integer SMIN = %d, SMAX = %d, TCUT = %d, L = IS + OS;" % (P["SMIN"], P["SMAX"], P["TCUT"]),
         "    reg clk = 0, rst_n = 0;", "    always #0.5 clk = ~clk;"]
    for n, w in ins:
        L.append(f"    reg [{w}-1:0] {n};")
    for n, w in outs:
        L.append(f"    wire [{w}-1:0] m_{n}, r_{n};")
    L.append("    wire m_me_clk, r_me_clk;")
    mc = [".clk(clk)", ".rst_n(rst_n)", ".po_me_clk(m_me_clk)"] + [f".{n}({n}_m)" if n in SEQ_UNSTN else f".{n}({n})" for n, _ in ins] + [f".{n}(m_{n})" for n, _ in outs]
    # me_mem_ok enters the master unstationed: the bench presents it IS edges late so the master stays the reference shifted
    L += ["    wire me_mem_ok_m;", "    ot_hdc_delay #(.W(1), .D(IS)) u_mmo (.clk(clk), .rst_n(1'b1), .d(me_mem_ok), .q(me_mem_ok_m));"]
    L.append("    ot_qfd_sp_constants_sequencer #(.IS(IS), .OS(OS), .MUT(MUT), .RT(RT)) dut (\n        " + ",\n        ".join(mc) + ");")
    # reference, wired like the runtime die
    L += ["    // ---- reference: controller + TP sequencer + stores as the runtime die wires them ----",
          "    wire core_start, core_done, core_fault_w; wire [NW-1:0] core_tok, core_pos, core_ntok; wire [31:0] core_nval;",
          "    wire prog_re; wire [11:0] prog_addr, prog_base; reg [1023:0] prog_q; wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;",
          "    reg [1023:0] prog_mem [0:63]; reg [63:0] desc_mem [0:7];",
          "    wire [11:0] prog_a = prog_base + prog_addr;",
          "    always @(posedge clk) begin",
          "        if (pw_v) prog_mem[pw_addr[9:4]][pw_addr[3:0]*64 +: 64] <= pw_data;",
          "        if (dw_v) desc_mem[dw_addr] <= dw_data;",
          "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;",
          "        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;",
          "    end",
          "    assign r_core_fault = core_fault_w;",
          "    wire rrs_w = rst_n; wire [NW-1:0] rcore_tok_w = core_tok;"]
    L += _shell_text("r", "")
    L += ["    assign rme_go_w = r_po_me_go; assign rsu_go_w = r_po_su_go; assign rme_amax_w = r_po_me_i_amax;",
          "    assign rsu_sfu_w = r_po_su_i_sfu; assign rme_en_w = r_me_clk_en; assign r_su_tok = rtok_l;"]
    rc = [".clk(clk)", ".rst_n(rst_n)", ".start(core_start)", ".token(core_tok)", ".pos(core_pos)", ".done(core_done)",
          ".next_token(core_ntok)", ".next_val(core_nval)", ".cycles()", ".fault(core_fault_w)",
          ".prog_re(prog_re)", ".prog_addr(prog_addr)", ".prog_q(prog_q)", ".wrom_re(r_rom_fault)", ".wrom_addr()",
          ".wrom_q('0)", ".int8_wrom_re()", ".int8_wrom_addr()", ".scale_re()", ".scale_gre()", ".scale_addr()",
          ".scale_q('0)", ".embed_code_re()", ".embed_code_addr()",
          ".embed_code_q('0)", ".embed_scale_re(res_re_w)", ".embed_scale_addr()",
          ".embed_scale_q('0)", ".crom_re()", ".crom_addr()", ".crom_q('0)", ".kv_re()", ".kv_we()",
          ".kv_waddr()", ".kv_wdata()", ".kv_write_drained(kv_write_drained)", ".kv_write_flush(r_kv_write_flush)",
          ".va_re()", ".va_addr()", ".va_q('0)", ".vb_re()", ".vb_addr()", ".vb_q('0)",
          ".vc_re()", ".vc_addr()", ".vc_q('0)", ".vw_me_we()", ".vw_me_addr()", ".vw_me_mask()", ".vw_me_data()",
          ".vw_su_we()", ".vw_su_addr()", ".vw_su_data()", ".vw_rd_we()", ".vw_rd_addr()", ".vw_rd_data()",
          ".vw_mx_we()", ".vw_mx_addr()", ".vw_mx_mask()", ".vw_mx_data()", ".me_ov()", ".kvd_v(r_kvd_v)"]
    rc += [f".kvd_{n}(r_kvd_{n})" for n in ("wbase", "ts", "ks", "js", "wcs", "split", "jsh", "tiles", "k", "nout",
                                           "kindk", "pos")]
    rc += [".kv_ok(kv_ok)", ".wrom_su()", ".wd_v()", ".wd_wbase()", ".wd_sbase()", ".wd_tiles()", ".wd_k()",
           ".wd_nout()", ".vx_re()", ".vx_addr()", ".vx_q('0)", ".tgo()", ".tb()", ".xl_d()", ".t_lvl('0)",
           ".fab_fault(1'b0)", ".w_ok(1'b1)", ".emb_ok(1'b1)", ".me_mem_ok(me_mem_ok)", ".me_clk_en(r_me_clk_en)",
           ".po_me_clk(r_me_clk)"]
    rc += _unit_conns("r", "", "r_")
    rc.append(".po_su_asrc_raw(r_su_asrc)")
    cpar = ("W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(1), .SW(SW), .LV(LV), .KV_FP8(1), .INT8_WEIGHT(1), "
            ".INT8_SCALE_WCS_BASE(1), .INT8_EMBED(1), .QWEN_FULLSHAPE(%d), .HID(4096), .HALF(64), .HD(128), "
            ".EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .KV_HBM(1), .KV_VEC_WRITE_BRIDGE(1), .ME_STALL(1), "
            ".ME_IDLE_GATE(1), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT)" % P["QWEN_FULLSHAPE"])
    L.append(f"    ot_qwen_rom_core_ctrl #(.{cpar}) ref_core (\n        " + ",\n        ".join(rc) + ");")
    L += ["    ot_qwen_tp_seq_w12 #(.N(D), .NW(NW), .PAW(PAW), .VWA(8), .DAW(6), .FW(512), .TAGW(32),",
          "        .QWEN_FULLSHAPE(%d), .ENABLE_AR256(%d)) ref_seq (" % (P["QWEN_FULLSHAPE"], P["ENABLE_AR256"]),
          "        .clk(clk), .rst_n(rst_n), .start(h_start), .token(tp_token), .pos(tp_pos), .done(r_s_done),",
          "        .next_token(r_seq_ntok), .next_val(r_seq_nval), .fault(r_s_fault), .coll_busy(r_coll_busy),",
          "        .core_start(core_start), .core_token(core_tok), .core_pos(core_pos), .core_done(core_done),",
          "        .core_next_token(core_ntok), .core_next_val(core_nval), .core_fault(core_fault_w), .prog_base(prog_base),",
          "        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(r_vm_re), .vm_raddr(r_vm_raddr),",
          "        .vm_rq(vm_rq), .vm_we(r_vm_we), .vm_waddr(r_vm_waddr), .vm_wdata(r_vm_wdata), .c_valid(r_c_valid),",
          "        .c_ready(c_ready), .c_data(r_c_data), .c_last(r_c_last), .c_mode(r_c_mode), .c_tag(r_c_tag),",
          "        .r_valid(r_valid), .r_data(r_data), .r_last(r_last), .r_rank(r_rank), .r_err(r_err));"]
    m_all = "{" + ", ".join(f"m_{n}" for n, _ in outs if n not in SEQ_UNSTN) + "}"
    r_all = "{" + ", ".join(f"r_{n}" for n, _ in outs if n not in SEQ_UNSTN) + "}"
    L += [f"    wire [$bits({m_all})-1:0] o_m = {m_all};", f"    wire [$bits({r_all})-1:0] o_r = {r_all};",
          "    reg [$bits(o_r)-1:0] hist [0:L];", "    integer i, k, cyc, bad, first_bad, seed, starts;",
          "    always @(posedge clk) begin for (i = L; i > 0; i = i - 1) hist[i] <= hist[i-1]; hist[0] <= o_r; end",
          "    wire [$bits(o_r)-1:0] o_rd = hist[L-1];",
          "    // the unstationed ICG enable leaves IS edges after the reference's (its inputs are IS late, no output station)",
          "    wire me_en_rd; integer bad_en;",
          "    ot_hdc_delay #(.W(1), .D(IS)) u_men (.clk(clk), .rst_n(1'b1), .d(r_me_clk_en), .q(me_en_rd));",
          "    task rnd_inputs;", "        begin"]
    for n, w in ins:
        if n in ("pw_v", "dw_v", "h_start", "pw_addr", "pw_data", "dw_addr", "dw_data"):
            continue
        L.append(f"            for (k = 0; k < {w}; k = k + 32) {n}[k +: 32] = $random(seed);" if w not in ("1", "2", "3", "8", "10", "16")
                 else f"            {n} = $random(seed);")
    L += ["            pi_me_ready = ($random(seed) & 3) != 0; pi_su_ready = ($random(seed) & 3) != 0;",
          "            kv_ok = ($random(seed) & 7) != 0; kv_write_drained = ($random(seed) & 7) != 0; me_mem_ok = ($random(seed) & 15) != 0;",
          "        end", "    endtask",
          "    initial begin",
          "        seed = SEED; bad = 0; first_bad = -1; starts = 0;",
          "        h_start = 0; pw_v = 0; dw_v = 0; pw_addr = 0; dw_addr = 0; pw_data = 0; dw_data = 0; rnd_inputs;",
          "        for (i = 0; i <= L; i = i + 1) hist[i] = 0;",
          "        repeat (3) @(negedge clk); rst_n = 1;",
          "        // program and descriptor images through the configuration ports (random words; unit field 0..2)",
          "        for (k = 0; k < 1024; k = k + 1) begin @(negedge clk); pw_v = 1; pw_addr = k; pw_data = {$random(seed), $random(seed)}; rnd_inputs; end",
          "        for (k = 0; k < 8; k = k + 1) begin @(negedge clk); pw_v = 0; dw_v = 1; dw_addr = k;",
          "            dw_data = {$random(seed), 8'd0, 6'd0, 2'd0, $random(seed) & 32'h0000ff3c} | (k == 7 ? 64'd3 : 64'd0); rnd_inputs; end",
          "        @(negedge clk); dw_v = 0;",
          "        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin",
          "            @(negedge clk);",
          "            if (cyc > L + 2 && (o_m !== o_rd || m_me_clk_en !== me_en_rd)) begin bad = bad + 1; if (first_bad < 0) first_bad = cyc; end",
          "            rnd_inputs;",
          "            h_start = (cyc % 700) == 5; if (h_start) starts = starts + 1;",
          "        end",
          "        if (bad == 0 && starts > 3) $display(\"PASS qfd_constants_sequencer IS=%0d OS=%0d cycles=%0d starts=%0d outputs=%0d bits latency+%0d\", IS, OS, CYCLES, starts, $bits(o_r), L);",
          "        else $display(\"FAIL qfd_constants_sequencer mismatching cycles=%0d first=%0d\", bad, first_bad);",
          "        $finish;", "    end", "endmodule"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
