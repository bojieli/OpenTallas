#!/usr/bin/env python3
"""DIE-QC-66/CORES-NK 11-03: NL variant of nkp_patch.py (opt-in NKP, default 0 = unchanged elaboration).
The matvec cuts are nkp_patch.matvec() unchanged (NL ot_qwen_w12_matvec_land32.sv is byte-identical to NK's); only the
plumbing differs: the NL wrappers have no IRCK, and the tops are qfd_tile_nl_rp2_45 / qfd_tile_nl_a0c.
usage: nkp_patch_nl.py RTLDIR   (patches in place; exact anchors, fail-closed; nkp_patch.py beside this file)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nkp_patch import rep, plumb_hdr, matvec, NKPDOC

def patch(d):
    d = Path(d)
    f = d / "ot_qwen_w12_matvec_land32.sv"; f.write_text(matvec(f.read_text()))
    f = d / "ot_qwen_rom_tile_w12_land32.sv"; t = f.read_text()
    t = plumb_hdr(t, "ot_qwen_rom_tile_logic_w12",
                  "    parameter integer GLOBAL_KV_CONST0 = 0 // opt-in ROM-only global KV port is already hardwired zero\n) (",
                  "    parameter integer GLOBAL_KV_CONST0 = 0, // opt-in ROM-only global KV port is already hardwired zero\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = plumb_hdr(t, "ot_qwen_rom_tile_w12", "    parameter integer CHILD_CLOCKS = 0\n) (",
                  "    parameter integer CHILD_CLOCKS = 0,\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = rep(t, ".MUL_LAT(MUL_LAT)) u_me (", ".MUL_LAT(MUL_LAT), .NKP(NKP)) u_me (")
    t = rep(t, ".NDH(NDH), .NODE(NODE), .BMUT(BMUT)) u_logic (", ".NDH(NDH), .NODE(NODE), .BMUT(BMUT), .NKP(NKP)) u_logic (")
    f.write_text(t)
    f = d / "ot_qwen_rom_tile_nk.sv"; t = f.read_text()
    t = plumb_hdr(t, "ot_qwen_rom_tile_nk", "    parameter integer NODE = 1            // q14 r9: 0 = node-less tile (ot_qwen_rom_tile_w12 NODE)\n) (",
                  "    parameter integer NODE = 1,           // q14 r9: 0 = node-less tile (ot_qwen_rom_tile_w12 NODE)\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = rep(t, ".BMUT(BMUT), .KV_SLICE(0)) u_tile (", ".BMUT(BMUT), .KV_SLICE(0), .NKP(NKP)) u_tile (")
    f.write_text(t)
    f = d / "qfd_tile_nl_rp2_45.sv"; t = f.read_text()
    t = plumb_hdr(t, "qfd_tile_nl_rp2_45", "    parameter integer REGROOT = 0     // Q-ROMPARENT: ck_dw/ck_de/ck_rsw/ck_rnw regional roots (RPH 3)\n) (",
                  "    parameter integer REGROOT = 0,    // Q-ROMPARENT: ck_dw/ck_de/ck_rsw/ck_rnw regional roots (RPH 3)\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = rep(t, ".NDH(NDH), .NODE(0)) u_tile (", ".NDH(NDH), .NODE(0), .NKP(NKP)) u_tile (")
    f.write_text(t)
    f = d / "qfd_tile_nl_a0c.sv"; t = f.read_text()
    t = rep(t, "`ifndef SYNTHESIS\n  , parameter integer ROM_TILE = -1\n`endif\n) (",
            NKPDOC.replace("    //", "  //") + "  , parameter integer NKP = 0\n`ifndef SYNTHESIS\n  , parameter integer ROM_TILE = -1\n`endif\n) (")
    t = rep(t, "qfd_tile_nl_rp2_45 #(.ROM_TILE(ROM_TILE),.RPH(3),.REGROOT(REGROOT_MODE)) u_g (",
            "qfd_tile_nl_rp2_45 #(.ROM_TILE(ROM_TILE),.RPH(3),.REGROOT(REGROOT_MODE),.NKP(NKP)) u_g (")
    t = rep(t, "qfd_tile_nl_rp2_45 #(.RPH(3),.REGROOT(REGROOT_MODE)) u_g (",
            "qfd_tile_nl_rp2_45 #(.RPH(3),.REGROOT(REGROOT_MODE),.NKP(NKP)) u_g (")
    f.write_text(t)
    print("NKP_NL_PATCH_OK", d)

if __name__ == "__main__":
    patch(sys.argv[1])
