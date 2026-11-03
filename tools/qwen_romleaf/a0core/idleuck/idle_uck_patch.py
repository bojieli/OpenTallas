#!/usr/bin/env python3
"""DIE-QC-66/CORES 11-03: opt-in IDLE_UCK (default 0 = unchanged elaboration): u_me.idle (ot_qwen_w12_matvec_part, the
A0 engine-drained flag that feeds the tile-root ICG enable) clocked from the UNGATED tile clock ck (new pass-through
port ck_u) instead of the gated engine clock -- the as-built NL B3 form (b3_early.tcl OT_B3_MID re-taps idle onto the
pre-ICG tree).  usage: idle_uck_patch.py FILE...  (files recognised by basename/content; exact anchors, fail-closed)"""
import sys
from pathlib import Path

P = "    parameter integer IDLE_UCK = 0,    // DIE-QC-66 11-03: 1 = u_me.idle on the ungated tile clock ck_u (as-built B3 NL form)\n"

def hdr(t, mod):
    a = f"module {mod} #(\n"
    assert t.count(a) == 1, (mod, t.count(a)); return t.replace(a, a + P)

def rep(t, a, b, n=1):
    assert t.count(a) == n, (a, t.count(a)); return t.replace(a, b)

IDLE_OLD = ("    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) idle <= 1'b1;\n"
            "        else idle <= idle_c && !(go && ready);\n    end\n")
IDLE_NEW = ("    generate if (IDLE_UCK != 0) begin : g_idle_uck\n"
            "        always @(posedge ck_u or negedge rst_n) begin\n            if (!rst_n) idle <= 1'b1;\n"
            "            else idle <= idle_c && !(go && ready);\n        end\n"
            "    end else begin : g_idle_ck\n"
            "        always @(posedge clk or negedge rst_n) begin\n            if (!rst_n) idle <= 1'b1;\n"
            "            else idle <= idle_c && !(go && ready);\n        end\n    end endgenerate\n")
CKU = "    input  wire              ck_u,     // DIE-QC-66 IDLE_UCK: ungated tile clock (unused when IDLE_UCK = 0)\n"

def patch(p):
    t = p.read_text(); o = t
    if "module ot_qwen_w12_matvec_part #(" in t:
        t = hdr(t, "ot_qwen_w12_matvec_part")
        t = rep(t, "    output reg               idle,\n", CKU + "    output reg               idle,\n")
        t = rep(t, IDLE_OLD, IDLE_NEW)
    elif "module ot_qwen_rom_tile_logic_w12 #(" in t:
        t = hdr(t, "ot_qwen_rom_tile_logic_w12"); t = hdr(t, "ot_qwen_rom_tile_w12")
        t = rep(t, "    output wire              idle\n", CKU + "    output wire              idle\n")
        t = rep(t, "    output wire              idle      // QC-PG-5 ICG: u_logic.u_me.idle",
                CKU + "    output wire              idle      // QC-PG-5 ICG: u_logic.u_me.idle")
        t = rep(t, "ot_qwen_w12_matvec_part #(", "ot_qwen_w12_matvec_part #(.IDLE_UCK(IDLE_UCK), ")
        t = rep(t, ".ready(), .idle(idle),", ".ready(), .ck_u(ck_u), .idle(idle),")
        t = rep(t, "    ot_qwen_rom_tile_logic_w12 #(\n", "    ot_qwen_rom_tile_logic_w12 #(\n        .IDLE_UCK(IDLE_UCK),\n")
        t = rep(t, ".kv_q({4*16*32{1'b0}}), .idle(idle));", ".kv_q({4*16*32{1'b0}}), .ck_u(ck_u), .idle(idle));")
    elif "module ot_qwen_rom_tile_nk #(" in t:
        t = hdr(t, "ot_qwen_rom_tile_nk")
        t = rep(t, "    output wire              idle      // QC-PG-5 ICG: u_tile.idle",
                CKU + "    output wire              idle      // QC-PG-5 ICG: u_tile.idle")
        t = rep(t, "    ot_qwen_rom_tile_w12 #(\n", "    ot_qwen_rom_tile_w12 #(\n        .IDLE_UCK(IDLE_UCK),\n")
        t = rep(t, ".kvw_mask(512'd0), .idle(idle));", ".kvw_mask(512'd0), .ck_u(ck_u), .idle(idle));")
    elif "module qfd_tile_nl_rp2_45 #(" in t:
        t = hdr(t, "qfd_tile_nl_rp2_45")
        t = rep(t, "    output wire          me_idle", "    input  wire          ck_u,     // DIE-QC-66 IDLE_UCK pass-through\n    output wire          me_idle")
        t = rep(t, "    ot_qwen_rom_tile_nk #(\n", "    ot_qwen_rom_tile_nk #(\n        .IDLE_UCK(IDLE_UCK),\n")
        t = rep(t, ".fault(tf), .idle(me_idle));", ".fault(tf), .ck_u(ck_u), .idle(me_idle));")
    elif "module qfd_tile_nl_a0c #(" in t:
        t = hdr(t, "qfd_tile_nl_a0c")
        t = rep(t, "qfd_tile_nl_rp2_45 #(", "qfd_tile_nl_rp2_45 #(.IDLE_UCK(IDLE_UCK),", n=2)
        t = rep(t, "        .me_idle(me_idle),", "        .ck_u(ck),\n        .me_idle(me_idle),")
    else:
        sys.exit(f"{p}: no known module")
    assert t != o
    p.write_text(t); print("patched", p)

for f in sys.argv[1:]:
    patch(Path(f))
