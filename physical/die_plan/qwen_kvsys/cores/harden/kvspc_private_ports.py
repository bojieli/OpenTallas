#!/usr/bin/env python3
"""PATH-KV-PC 10-25: kvs_pc / kvs_pc_h_head_p private output ports (kit-copy RTL transform, apply AFTER
kvspc_face_ports.py; gen_core_kit_kv.py --kvspc-private-ports).  Closes the remaining face_guard classes of the
4c6e890d93 recut (pc shared 1085 + ft 1, head_p shared 305 + ft 1) with RTL-level boundary registers:

  P1 o_grp[287:0] (return actual_data/epoch/layer/sector; hold loop on the port flop): private port flop whose next
     state comes from an internal copy act_i (port <= (rs_a && slot) ? new : act_i), the internal copy keeps the hold
     loop.  0 cycles.
  P2 o_grp[288] actual_valid was merged by opt_merge into its internal twin slot_d (both <= slot): both kept.  0 cycles.
  P3 o_grp[296:289] (cal / completion / drain / er[260] / fo / front fault + go flags: sticky observation flags that
     also feed local logic): one wrapper output pin flop each (ot_kvpc_pin_dff, keep_hierarchy).  +1 edge on these
     fault / drain observations only (as the 4c6e fi landing); o_grp[294] is no longer a feedthrough of pc__fo.
  P4 o_prev[779:0] (non-head; chain dout = input capture c, also decoded locally): private outgoing launch flop per bit
     (codex/kv-pc-0719 forward_launch), +1 edge per o_prev chain hop; local decode unchanged.
  P5 pc__pi[0]: the two identical rv_q captures (sched / port, same hclk / h_rn / pi[0]) merge (codex forward).
  P6 ID straps (OWNER option B): pc__pc[4:0] -> strap_pc, pc__cfg_stack[1:0] -> strap_stack; one landing register
     per strap bit (the existing pc_sr / st_sr); the chain station reads the landed copy (+1 settle edge after a strap
     change; straps are constant on the die).
  P7 head_p o_next (embedding return record upo[298:1]): constant bits for the head PC (word index / half from the PC
     parameter) were folded to one TIELO (64 loads): upo[298:1] become kept pin flops (ot_kvpc_pin_dff) with the same
     D.  0 cycles.
"""
import re
from pathlib import Path

FFS = '''`timescale 1ns/1ps
// PATH-KV-PC 10-25: kept single-bit boundary flops (keep_hierarchy: opt_merge / const folding cannot fold them)
(* keep_hierarchy *) module ot_kvpc_pin_dff(input wire ck, input wire d, output reg q);
 always @(posedge ck) q <= d;
endmodule
(* keep_hierarchy *) module ot_kvpc_pin_ar0(input wire ck, input wire rn, input wire d, output reg q);
 always @(posedge ck or negedge rn) if (!rn) q <= 1'b0; else q <= d;
endmodule
'''

STATUS_BITS = list(range(289, 297))       # P3
# P6 port rename to strap_* (OWNER option B) is a plan delta (KV plan owner); off until the plan declares the straps:
# the single landing register already makes pc__pc / pc__cfg_stack face_guard-clean registered inputs.
STRAP_RENAME = False


def _sub1(s, old, new):
    assert s.count(old) == 1, (s.count(old), old[:160])
    return s.replace(old, new)


def _module(text, name):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    return i, j


def return_slots(text, mut=0):
    """P1 + P2 on qkd_static_kv_return_slots_mc_nc"""
    i, j = _module(text, "qkd_static_kv_return_slots_mc_nc")
    s = text[i:j]
    s = _sub1(s, " output reg actual_valid,output reg [9:0] actual_sector,\n output reg [15:0] actual_epoch,output reg [5:0] actual_layer,\n output reg [255:0] actual_data,",
              " (* keep *) output reg actual_valid,(* keep *) output reg [9:0] actual_sector,\n"
              " (* keep *) output reg [15:0] actual_epoch,(* keep *) output reg [5:0] actual_layer,\n"
              " (* keep *) output reg [255:0] actual_data,")
    s = _sub1(s, "   if(slot)begin\n    actual_data<=read_data[255:0];actual_sector<=read_data[265:256];\n"
                 "    actual_layer<=read_data[271:266];actual_epoch<=read_data[287:272];\n"
                 "    consumed[ra]<=~rp[AW];rp<=rp+1'b1;\n   end\n",
              "   if(slot)begin\n    consumed[ra]<=~rp[AW];rp<=rp+1'b1;\n   end\n")
    add = (" // PATH-KV-PC 10-25 (P1): the actual_* port flops drive their ports only; the hold loop lives on the internal\n"
           " // copy act_i (same enable rs_a && slot, same data): port <= en ? new : act_i, equal on every edge (0 cycles)\n"
           " (* keep *) reg [287:0] act_i;\n"
           " wire act_en = rs_a && slot;\n"
           " wire [287:0] act_n = read_data[287:0]" + (" ^ 288'd1" if mut == 11 else "") + ";\n"
           " always @(posedge ck) begin\n"
           "  if(act_en)act_i<=act_n;\n"
           "  {actual_epoch,actual_layer,actual_sector,actual_data}<=act_en?act_n:act_i;\n"
           " end\n")
    s = _sub1(s, " always @(posedge ck)fault_core<=rs_a", add + " always @(posedge ck)fault_core<=rs_a")
    return text[:i] + s + text[j:]


def forward_launch(text, mut=0):
    """P4 (codex/kv-pc-0719@5dc2556f5 forward_launch)"""
    old = '    assign dout = {bt, c[F_BT-1:F_CV+1], cv, c[F_CV-1:F_SS+1], ss, c[F_SS-1:F_EV+2], ev1, ev0, c[F_EV-1:0]};'
    new = '''    // PATH-KV-PC 10-25 (P4): private outgoing launch; input capture c stays local, only dout gains one edge.
    wire [779:0] port_fwd_d = {bt, c[F_BT-1:F_CV+1], cv, c[F_CV-1:F_SS+1], ss, c[F_SS-1:F_EV+2], ev1, ev0, c[F_EV-1:0]}''' + (" ^ 780'd2147483648" if mut == 14 else "") + ''';
    for (genvar fp = 0; fp < 780; fp = fp + 1) begin : g_port_forward
        if (fp == 0 || fp == 1 || fp == 615 || fp == 616 || fp == 719 || fp == 754 || fp == 779) begin : g_control
            (* keep *) ot_kvpc_pin_ar0 u_q (.ck(ck), .rn(rs_q), .d(port_fwd_d[fp]), .q(dout[fp]));
        end else begin : g_data
            (* keep *) ot_kvpc_pin_dff u_q (.ck(ck), .d(port_fwd_d[fp]), .q(dout[fp]));
        end
    end'''
    return _sub1(text, old, new)


def pi_capture_merge(text):
    """P5 (codex forward): identical rv_q captures share one pin flop"""
    text = _sub1(text, '    (* keep *) reg         rv_q,rawslot_q;', '    reg rv_q; (* keep *) reg rawslot_q;   // PATH-KV-PC P5: shares the pi[0] capture')
    return _sub1(text, '    (* keep *) reg rv_q, col_v_q, col_we_q, col_sr_q;', '    reg rv_q; (* keep *) reg col_v_q, col_we_q, col_sr_q;   // PATH-KV-PC P5')


def strap_landing(text, head):
    """P6: the chain station reads the landed strap copies (one pin flop per strap bit)"""
    if head:
        return _sub1(text, ".ck(ck), .rst_n(rsi), .cfg_stack(cfg_stack), .di(chain_i)",
                     ".ck(ck), .rst_n(rsi), .cfg_stack(st_sr) /* PATH-KV-PC P6: landed strap */, .di(chain_i)")
    return _sub1(text, ".ck(ck), .rst_n(rsi), .pc(pc), .cfg_stack(cfg_stack), .di(chain_i)",
                 ".ck(ck), .rst_n(rsi), .pc(pc_sr), .cfg_stack(st_sr) /* PATH-KV-PC P6: landed straps */, .di(chain_i)")


def return_head(text, mut=0):
    """P7 (head only): upo[298:1] kept pin flops"""
    i, j = _module(text, "qkd_embedding_static_return_head")
    s = text[i:j]
    s = _sub1(s, "    output reg [298:0] upo,", "    output wire [298:0] upo,")
    s = _sub1(s, "        upo[298:1]<=ts_q?retained:298'd0;\n", "")
    s = _sub1(s, "upo[0]<=0;", "upo0<=0;")
    s = _sub1(s, "            upo[0]<=ts_q;", "            upo0<=ts_q;")
    s = _sub1(s, "    reg occupied;", "    reg occupied;\n    reg upo0;\n    assign upo[0] = upo0;\n"
              "    // PATH-KV-PC 10-25 (P7): kept record pin flops (bits constant for one PC are not folded into a shared tie)\n"
              "    wire [297:0] upo_d = ts_q ? retained : 298'd0;\n"
              "    for (genvar ub = 1; ub < 299; ub = ub + 1) begin : g_upo\n"
              "        (* keep *) ot_kvpc_pin_dff u_q (.ck(ck), .d(upo_d[ub-1]), .q(upo[ub]));\n    end")
    return text[:i] + s + text[j:]


def wrapper(text, mod, mut=0):
    """P3 status pin flops on o_grp[296:289]; P6 strap port names"""
    head = mod.endswith("_h_head_p")
    i, j = _module(text, mod)
    s = text[i:j]
    for k in STATUS_BITS:
        old = f"    assign o_grp[{k}] = n0[{k}];\n"
        d = f"~n0[{k}]" if (mut == 13 and k == 294) else f"n0[{k}]"
        s = _sub1(s, old, f"    (* keep *) ot_kvpc_pin_dff u_ogrp_{k} (.ck(ck[0]), .d({d}), .q(o_grp[{k}]));   // PATH-KV-PC P3 (+1 edge)\n")
    if STRAP_RENAME:
        ids = [("pc__cfg_stack", "strap_stack", 2)] + ([] if head else [("pc__pc", "strap_pc", 5)])
        for old, new, w in ids:
            s = _sub1(s, f"    input wire [{w-1}:0] {old},\n", f"    input wire [{w-1}:0] {new},\n")
            s = _sub1(s, f".{old}({old}[{w-1}:0])", f".{old}({new}[{w-1}:0])")
    return text[:i] + s + text[j:]


def apply_kit(rtl_dir, mod, mut=0):
    d = Path(rtl_dir)
    head = mod.endswith("_h_head_p")
    (d / "ot_kvpc_pin_ff.sv").write_text(FFS)
    p = d / "qkd_static_kv_pc_path_nc.sv"; p.write_text(return_slots(p.read_text(), mut))
    p = d / "qkd_ctrl_pc_nc.sv"; p.write_text(pi_capture_merge(p.read_text()))
    p = d / ("qkd_static_kv_pc_path_fan_nc_b_head_p.sv" if head else "qkd_static_kv_pc_path_fan_nc_b.sv")
    p.write_text(strap_landing(p.read_text(), head))
    if head:
        p = d / "qkd_embedding_static_return_head.sv"; p.write_text(return_head(p.read_text(), mut))
    else:
        p = d / "qkd_kv_pc_chain_station_b.sv"; p.write_text(forward_launch(p.read_text(), mut))
    p = d / f"{mod}.sv"; p.write_text(wrapper(p.read_text(), mod, mut))
    return ["ot_kvpc_pin_ff.sv"]


IDS = {"pc__pc": "strap_pc", "pc__cfg_stack": "strap_stack"}


def _ren(name, head):
    for o, n in IDS.items():
        if head and o == "pc__pc":
            continue
        name = re.sub(rf"^{o}(?=\[|$)", n, name)
    return name


def core_json_update(cj):
    head = cj["module"].endswith("_h_head_p")
    pd = {}
    for b, v in cj["port_decl"].items():
        pd[_ren(b, head)] = v
    pc = {}
    for n, c in cj["pin_class"].items():
        nn = _ren(n, head)
        pc[nn] = c
    cj["port_decl"], cj["pin_class"] = pd, pc
    cj.setdefault("report", {}).setdefault("straps", [])
    for o, n in IDS.items():
        if head and o == "pc__pc":
            continue
        cj["report"]["straps"].append(dict(port=n, kind="id_strap", width=5 if n == "strap_pc" else 2, was=o,
                                           landing="one pin register per bit (pc_sr / st_sr)"))
    return cj


def plan_pins_update(pins, head=False):
    return [dict(p, name=_ren(p["name"], head)) for p in pins]


def pins_update(pins, head=False):
    return [dict(p, bus=_ren(p["bus"], head)) for p in pins]


if __name__ == "__main__":
    import sys
    apply_kit(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
