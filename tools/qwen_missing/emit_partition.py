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
    body = ["    // ---- vector stream unit (die master qfd_sp_su64_sfu): ports (SU_VEC = 1 only) ----"]
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
    t = t.replace(anchor, anchor[:-3].replace("me_clk_en       //", "me_clk_en,      //") + "\n    // -- partition ports (tools/qwen_missing/emit_partition.py) --\n" + ",\n".join(extra) + "\n);", 1)
    if re.search(r"\bu_me\b|\bu_su\b", re.sub(r"//[^\n]*", "", t.split("// -- partition ports")[1])):
        raise SystemExit("a reference to u_me / u_su remains in the controller")
    return ("// GENERATED by tools/qwen_missing/emit_partition.py from the emitted ot_qwen_rom_core "
            "(tools/qwen_rom_rt_core_emit_w12.py). The core minus its matrix-engine spine and stream unit.\n" + t)


def emit_part(core: str) -> str:
    params, port_text = header(core)
    ports = ports_of(port_text)
    names = [n for _, _, n in ports]
    for need in ("clk", "me_clk_en", "scale_q", "vb_q", "crom_q", "kv_we"):
        if need not in names:
            raise SystemExit(f"part: core port {need} not parsed")
    pnames = re.findall(r"parameter\s+integer\s+(\w+)", params)
    L = ["// GENERATED by tools/qwen_missing/emit_partition.py: ot_qwen_rom_core re-wired across the die-master partition",
         "// (qfd_sp_constants_sequencer = ot_qwen_rom_core_ctrl, qfd_sp_tree_top = ot_qwen_me_spine_w12,",
         "// qfd_sp_su64_sfu = ot_hdc_vstream_rt).  Same parameters and ports as ot_qwen_rom_core.",
         params.replace("module ot_qwen_rom_core #(", "module ot_qwen_rom_core_part #(", 1), ") (", port_text, ");"]
    dir_ports = {ex.split("[")[0] for _, ex, k, _ in ME + SU if k in ("dir_o", "dir_i")}
    for unit, table in (("me", ME), ("su", SU)):
        for p, ex, k, w in table:
            if k == "out":
                L.append(f"    wire [{w}-1:0] {unit}_{p};")
            elif k in ("in",):
                L.append(f"    wire [{w}-1:0] {unit}_{p};")
    L.append("    wire [SW-1:0] su_kv_we;")
    # controller
    cc = [f".{n}({n})" if n not in dir_ports else f".{n}()" for n in names if n not in ("kv_we",)]
    cc = [c for c in cc]
    # inputs only a unit reads: tie at the controller
    for _, ex, k, _ in ME + SU:
        if k == "dir_i":
            n = ex.split("[")[0]
            cc = [c if c != f".{n}()" else f".{n}('0)" for c in cc]
    cc.append(".kv_we()")
    for unit, table in (("me", ME), ("su", SU)):
        for p, ex, k, w in table:
            if k == "out":
                cc.append(f".po_{unit}_{p}({unit}_{p})")
            elif k == "in":
                cc.append(f".pi_{unit}_{p}({unit}_{p})")
            elif k == "dir_ok":
                cc.append(f".pi_{unit}_{p}(su_kv_we)")
    L.append("    ot_qwen_rom_core_ctrl #(" + ", ".join(f".{p}({p})" for p in pnames) + ") u_ctrl (\n        "
             + ",\n        ".join(cc) + ");")
    # spine
    sp = []
    for p, ex, k, w in ME:
        if k in ("out", "in"):
            sp.append(f".{p}(me_{p})")
        elif k == "rst":
            sp.append(f".{p}(rst_n)")
        else:
            sp.append(f".{p}({ex})")
    L.append("    ot_qwen_me_spine_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE),\n"
             "        .GT(G), .TG(4), " + ", ".join(f".{p}({p})" for p in EMIT.SPINE_PARAMS) + ") u_me (\n        "
             + ",\n        ".join(sp) + ");")
    su = []
    for p, ex, k, w in SU:
        if k in ("out", "in"):
            su.append(f".{p}(su_{p})")
        elif k in ("rst", "clk"):
            su.append(f".{p}({ex})")
        elif k == "dir_ok":
            su.append(f".{p}(su_kv_we)")
        else:
            su.append(f".{p}({ex})")
    L.append("    ot_hdc_vstream_rt #(.SW(SW), .LV(LV), .WR(W), .AW(AW), .NW(NW), .KV_FP8(KV_FP8)) u_su (\n        "
             + ",\n        ".join(su) + ");")
    L.append("    assign kv_we = su_kv_we;")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    core = EMIT.emit(EMIT.CORE.read_text())
    (a.out_dir / "ot_qwen_rom_core.sv").write_text(core)
    (a.out_dir / "ot_qwen_rom_core_ctrl.sv").write_text(emit_ctrl(core))
    (a.out_dir / "ot_qwen_rom_core_part.sv").write_text(emit_part(core))
    (a.out_dir / "ot_hdc_vstream_rt.sv").write_text(EMIT.emit_vstream(EMIT.VSTREAM.read_text()))
    print(a.out_dir)


if __name__ == "__main__":
    main()
