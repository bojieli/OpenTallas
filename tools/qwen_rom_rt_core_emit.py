#!/usr/bin/env python3
"""Emit ot_qwen_rom_core: the O4 ROM die core with its matrix engine built as the W12 array.

Text of rtl/hdc/ot_hdc_core_vector_weight.sv with u_me replaced by the array's
spine (rtl/hdc/ot_qwen_me_array.sv ot_qwen_me_spine: the engine top, the
instruction broadcast and the x network) and the G-wide engine memory ports
replaced by the spine's:

  removed  int8_wrom_q, kv_raddr, kv_q (the tiles read their own ROM banks and
           KV), vx_re/vx_addr/vx_q (G per-group x ports), me_oaddr/omask/odata
  added    vx_re/vx_addr/vx_q over 2^SMAX x chunks (the vector memory's x port),
           tgo/tb/xl_d/t_lvl/fab_fault (the tile fabric: 1,280 tile elements
           and the upper tree nodes, composed by the simulation host)

Everything else is the production core, including the vector stream unit
(SU_VEC = 1).  The emitter refuses to run if an anchor is missing.  The
emitted file is the die core of the runtime composition; the RTL array
(ot_qwen_me_array) is the same spine plus the same tile logic in one module.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv"
VSTREAM = ROOT / "rtl/hdc/ot_hdc_vstream.sv"
REMOVE = ("int8_wrom_q", "kv_raddr", "kv_q", "vx_re", "vx_addr", "vx_q", "me_oaddr", "me_omask", "me_odata")
SPINE_PARAMS = ("SMIN", "SMAX", "TCUT", "BD", "XVM", "NWS", "TWS", "ORD", "SCALE_LOCAL")


def emit(text: str) -> str:
    def sub1(pattern, repl, s, flags=0):
        out, n = re.subn(pattern, repl, s, count=1, flags=flags)
        if n != 1:
            raise SystemExit(f"anchor not found: {pattern}")
        return out

    text = sub1(r"module ot_hdc_core_vector_weight #\(", "module ot_qwen_rom_core #(", text)
    text = sub1(r"ot_hdc_vstream #\(", "ot_hdc_vstream_rt #(", text)
    # The stream unit's weight-ROM port serves only the BF16 embedding read, which the O4 die does not use
    # (INT8 matrices; the embedding row is preloaded).  The simulation copy gives it one ROM word of W
    # lanes (WR = W) instead of G*W, so the 1,024 lanes do not each elaborate a 98,304-way select; the
    # host fails closed if the stream unit ever reads the weight ROM (die output wrom_re).
    text = sub1(r"ot_hdc_vstream_rt #\(\.SW\(SW\), \.LV\(LV\), \.WR\(G \* W\),",
                "ot_hdc_vstream_rt #(.SW(SW), .LV(LV), .WR(W),", text)
    text = sub1(r"(\.wrom_re\(su_wrom_re\), \.wrom_addr\(su_wrom_addr\), )\.wrom_q\(wrom_q\),",
                r"\1.wrom_q(wrom_q[W*16-1:0]),", text)
    text = sub1(r"(    parameter integer EMB_ADDR_BASE = 0)( //[^\n]*)\n\) \(",
                r"\1,\2\n" + ",\n".join(f"    parameter integer {p} = 0" for p in SPINE_PARAMS) + "\n) (", text)
    for name in REMOVE:
        text = sub1(rf"\n    (input|output)\s+wire\s+\[[^\]]*\]\s+{name},[^\n]*", "", text)
    ports = ("\n    // W12 array spine: the vector memory's x chunk port and the tile fabric"
             "\n    output wire [(1<<SMAX)-1:0]    vx_re,"
             "\n    output wire [(1<<SMAX)*AW-1:0] vx_addr,"
             "\n    input  wire [(1<<SMAX)*32-1:0] vx_q,"
             "\n    output wire              tgo,"
             "\n    output wire [3*NW+13*AW+13-1:0] tb,"
             "\n    output wire [(1<<SMAX)*32-1:0] xl_d,"
             "\n    input  wire [(G >> TCUT)*W*32-1:0] t_lvl,"
             "\n    input  wire              fab_fault,")
    text = sub1(r"\n    input  wire              w_ok, emb_ok,", ports + "\n    input  wire              w_ok, emb_ok,", text)
    text = sub1(r"\n    wire \[G\*W\*\(\(INT8_WEIGHT != 0\) \? 8 : 16\)-1:0\] me_wrom_q;\n    generate if .*?end endgenerate",
                "", text, flags=re.S)
    start = text.index("    ot_hdc_matvec #(")
    end = text.index(");", start) + 2
    inst = text[start:end]
    inst = inst.replace("ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW),\n                    .INT8_WEIGHT(INT8_WEIGHT), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE)) u_me (",
                        "ot_qwen_me_spine #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE),\n"
                        "                    .GT(G), .TG(4), " + ", ".join(f".{p}({p})" for p in SPINE_PARAMS) + ") u_me (", 1)
    if "ot_qwen_me_spine" not in inst:
        raise SystemExit("u_me header anchor")
    for old, new in ((".wrom_q(me_wrom_q),", ""),
                     (".kv_re(kv_re), .kv_addr(kv_raddr), .kv_q(kv_q),", ".kv_re(kv_re),"),
                     (".x_re(vx_re), .x_addr(vx_addr), .x_q(vx_q),",
                      ".x_re(vx_re), .x_addr(vx_addr), .x_q(vx_q),\n        .tgo(tgo), .tb(tb), .xl_d(xl_d), .t_lvl(t_lvl), .fab_fault(fab_fault),")):
        if inst.count(old) != 1:
            raise SystemExit(f"u_me port anchor: {old}")
        inst = inst.replace(old, new)
    text = text[:start] + inst + text[end:]
    text = sub1(r"\n    assign me_oaddr = vw_me_addr;\n    assign me_omask = vw_me_mask;\n    assign me_odata = vw_me_data;", "", text)
    # the engine's result and scale ports serve only the G >> SMIN result-port groups
    for pat, rep in ((r"output wire \[G-1:0\]      scale_gre,", "output wire [(G >> SMIN)-1:0] scale_gre,"),
                     (r"output wire \[G\*AW-1:0\]   scale_addr,", "output wire [(G >> SMIN)*AW-1:0] scale_addr,"),
                     (r"input  wire \[G\*W\*16-1:0\] scale_q,", "input  wire [(G >> SMIN)*W*16-1:0] scale_q,"),
                     (r"output wire \[G-1:0\]      vw_me_we,", "output wire [(G >> SMIN)-1:0] vw_me_we,"),
                     (r"output wire \[G\*AW-1:0\]   vw_me_addr,", "output wire [(G >> SMIN)*AW-1:0] vw_me_addr,"),
                     (r"output wire \[G\*W-1:0\]    vw_me_mask,", "output wire [(G >> SMIN)*W-1:0] vw_me_mask,"),
                     (r"output wire \[G\*W\*32-1:0\] vw_me_data,", "output wire [(G >> SMIN)*W*32-1:0] vw_me_data,"),
                     (r"wire \[G-1:0\] me_o_we;", "wire [(G >> SMIN)-1:0] me_o_we;"),
                     (r"assign vw_me_we = me_o_we & \{G\{me_en\}\};", "assign vw_me_we = me_o_we & {(G >> SMIN){me_en}};")):
        text = sub1(pat, rep, text)
    for name in ("int8_wrom_q", "kv_raddr", "me_oaddr", "me_omask", "me_odata", "me_wrom_q"):
        if re.search(rf"\b{name}\b", text):
            raise SystemExit(f"removed net {name} still referenced")
    return ("// GENERATED by tools/qwen_rom_rt_core_emit.py from rtl/hdc/ot_hdc_core_vector_weight.sv "
            f"(sha256 {hashlib.sha256(CORE.read_bytes()).hexdigest()}).\n" + text)


def emit_vstream(text: str) -> str:
    """ot_hdc_vstream with every lane instance parameter-identical (LANE = 0), the lane's address offset
    LANE x stride added by the parent instead: cura0 + l*asi (same AW-bit sum), so a simulator can
    compile the lane once (Verilator hier_block).  Simulation only; algebraically the same module."""
    old = "ot_hdc_vstream_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE(l), .KV_FP8(KV_FP8)) u_lane ("
    if text.count(old) != 1:
        raise SystemExit("vstream lane anchor")
    text = text.replace(old, "ot_hdc_vstream_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE(0), .KV_FP8(KV_FP8)) u_lane (")
    for a, st in (("cura", "asi"), ("curb", "bsi"), ("curc", "csi"), ("curd", "dsi")):
        pat = f".{a}0({a}),"
        if text.count(pat) != 1:
            raise SystemExit(f"vstream anchor {pat}")
        text = text.replace(pat, f".{a}0({a} + l * {st}),")
    text = text.replace("module ot_hdc_vstream #(", "module ot_hdc_vstream_rt #(", 1)
    return ("// GENERATED by tools/qwen_rom_rt_core_emit.py from rtl/hdc/ot_hdc_vstream.sv "
            f"(sha256 {hashlib.sha256(VSTREAM.read_bytes()).hexdigest()}). SIMULATION ONLY.\n" + text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(emit(CORE.read_text()))
    print(args.out)


if __name__ == "__main__":
    main()
