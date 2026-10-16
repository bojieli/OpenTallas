#!/usr/bin/env python3
"""Extract exact used capture cones; do not rewrite their arithmetic or epochs.

Candidate only. The original cluster remains the reference. All sixteen x8 data
cones are identical; the single consumed status cone is a separate dual-clock
leaf. The two half overflow signals enter g2 separately and are ORed at the
original hoq sampling edge, removing combinational logic from the parent.

DECISION B successors (2026-10-16), generated here so regeneration reproduces the
committed RTL byte for byte:
  * dsfd_capt_x8_data_e / _w are logic-free wrappers over the single-clock leaves
    dsfd_capt_x8x_t_{e,w} (ck) / dsfd_capt_x8x_s_{e,w} (ckv) of the hand-written
    ctrl_c/dsfd_capt_x8_x43.sv (1404d312f; ratio FIFO and hold queue removed).
    dsfd_capt_x8_data (no side suffix) stays the source-exact extracted cone.
  * dsfd_capt_status_dual is a logic-free wrapper over dsfd_capt_status_x43_t (ck)
    / dsfd_capt_status_x43_s (ckv) of the hand-written ctrl_c/dsfd_capt_status_x43.sv
    (f253acc24); the source-exact status cone is no longer emitted.
  * dsfd_capt_rly_64_EW uses ot_s81_rly RSREG=1 (596843a47).
The two x43 leaf files are hand-written inputs, not outputs of this script.

Usage: capture_split.py            regenerate the two outputs in place
       capture_split.py --check    exit 1 if regeneration differs from the committed files
"""
import argparse
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv"
OUT = "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv"
CANDIDATE = "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_split_candidate.sv"


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"source extraction anchor changed: {old[:80]}")
    return text.replace(old, new)


def module(text, name):
    start = re.search(r"^module " + re.escape(name) + r"\b", text, re.M).start()
    end = text.index("endmodule", start) + len("endmodule")
    return text[start:end]


# claude S-VM-CAPT-X8 1404d312f: dsfd_capt_x8_data_<side> wraps the x43 leaves of ctrl_c/dsfd_capt_x8_x43.sv.
X8_WRAPPER = '''module dsfd_capt_x8_data_SIDE (
    input wire [0:0] ck, rst, ckv, rsv,
    input wire [415:0] f_w,
    output wire [831:0] t_vm,
    output wire [0:0] t_ho
);
    // claude S-VM-CAPT-X8 2026-10-16 (DECISION B): wrapper of the two single-clock hard leaves of the static fixed-bank
    // 3:4 transfer (dsfd_capt_x8_x43.sv header: every stream sample index accepted, no hold queue, fixed latency,
    // t_ho = sticky epoch-slip fault).  Parent-visible ports unchanged; the leaves abut on the bank seam.
    wire [1663:0] b; wire [7:0] s_mark, s_par;
    dsfd_capt_x8x_t_SIDE u_t (.ck(ck), .rst(rst), .f_w(f_w), .b(b), .s_mark(s_mark), .s_par(s_par), .t_ho(t_ho));
    dsfd_capt_x8x_s_SIDE u_s (.ckv(ckv), .rsv(rsv), .b(b), .s_mark(s_mark), .s_par(s_par), .t_vm(t_vm));
endmodule'''

# claude S-VM-CAPT-STATUS f253acc24: dsfd_capt_status_dual wraps the x43 leaves of ctrl_c/dsfd_capt_status_x43.sv.
STATUS_WRAPPER = '''// dsfd_capt_status_dual (S-VM-CAPT-STATUS 2026-10-16, DECISION B): wrapper of two single-clock hard leaves, no
// logic and no clock tree of its own.  The intra-leaf ot_ratio_cdc_fifo (split1016 / split1016b: FF hold -81 ps on
// its 1-tick 4:3 arcs, hold repair stalled) is replaced by the fixed-phase 3-bank transfer of
// ctrl_c/dsfd_capt_status_x43.sv: dsfd_capt_status_x43_t (ck: f_sn sampled at stream index 0 / 2 / 3 into banks)
// and dsfd_capt_status_x43_s (ckv: fixed-edge bank read into t_st).  Same ports; rst / rsv are now the die's
// EPOCH resets (released on the common 3:4 epoch edge 0, the x34 / x43 startup contract) instead of raw resets
// synchronised in the leaf.  Latency and sample rule: header of dsfd_capt_status_x43.sv.
module dsfd_capt_status_dual (
    input wire [0:0] ck, rst, ckv, rsv,
    input wire [63:0] f_sn,
    output wire [63:0] t_st
);
    wire [63:0] b0, b2, b3; wire [2:0] bp; wire mk;
    dsfd_capt_status_x43_t u_t (.ck(ck), .rst(rst), .f_sn(f_sn), .b0(b0), .b2(b2), .b3(b3), .bpar(bp), .t_mark(mk));
    dsfd_capt_status_x43_s u_s (.ckv(ckv), .rsv(rsv), .b0(b0), .b2(b2), .b3(b3), .bpar(bp), .t_mark(mk), .t_st(t_st));
endmodule'''

# 596843a47: reset pin register on the 64-bit status relay (closed split1016 view failed native: rs capture 231 > 190).
RSREG = {(64, "EW"): ", .RSREG(1)"}


def x8_wrapper(side):
    return X8_WRAPPER.replace("SIDE", side)


def render():
    """{repo-relative path: generated text}; writes nothing."""
    source = (ROOT / SOURCE).read_text()
    data = module(source, "dsfd_capt_x")
    header_end = data.index(");") + 2
    data = '''module dsfd_capt_x8_data (
    input wire [0:0] ck, rst, ckv, rsv,
    input wire [415:0] f_w,
    output wire [831:0] t_vm,
    output wire [0:0] t_ho
);
    localparam integer NR = 8, LD = 4, LOCAL_CTRL = 1;''' + data[header_end:]
    status_start = data.index("    reg [63:0] snq;")
    data = data[:status_start] + "endmodule"
    g2 = module(source, "dsfd_capt_g2")
    g2 = once(g2, "module dsfd_capt_g2 #(", "module dsfd_capt_g2_dualho #(")
    g2 = once(g2, "input  wire [0:0]          f_ho,", "input  wire [1:0]          f_ho,")
    g2 = once(g2, "else hoq <= f_ho[0];", "else hoq <= |f_ho;")
    status = STATUS_WRAPPER
    relays = []
    for width, direction in ((31, "EW"), (36, "WE"), (64, "EW"), (12, "SN")):
        relays.append(f'''module dsfd_capt_rly_{width}_{direction} (
    input wire ck, rs, input wire [{width-1}:0] i, output wire [{width-1}:0] o
);
    ot_s81_rly #(.W({width}){RSREG.get((width, direction), "")}) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule''')
    output = "`timescale 1ns/1ps\n// Generated by tools/s81_ph/capture_split.py; candidate, not adopted.\n"
    output += "// Source SHA256 " + hashlib.sha256(source.encode()).hexdigest() + "\n"
    output += "`define CAPT_KB 99\n\n" + "\n\n".join([data, x8_wrapper("e"), x8_wrapper("w"), g2, status, *relays]) + "\n"
    out = {OUT: output}

    original = (ROOT / "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv").read_text()
    parent = once(original, "module dsfd_sp_capture_c (", "module dsfd_sp_capture_split_candidate (")
    parent = once(parent, "    input wire [15:0] ckv_x,", "    input wire ck_status, ckv_status,\n    input wire [15:0] ckv_x,")
    parent = once(parent, "wire [63:0] sn_g;", "")
    parent = once(parent, "        if (g == NT / 2 - 1) begin : g_sn assign sn_g = nd; end else begin : g_z assign sn_g = 64'd0; end", "")
    parent = once(parent, "    wire [NT*64-1:0] stv;", "    wire [63:0] stw;")
    parent = once(parent, "        wire [16*52-1:0] w; wire [0:0] ho;", "        wire [16*52-1:0] w;")
    parent = once(parent, "dsfd_capt_g2 u_g", "dsfd_capt_g2_dualho u_g")
    parent = once(parent, ".t_w(w), .f_ho(ho),", ".t_w(w), .f_ho(ho_half),")
    parent = once(parent, "        wire [1:0] ho_half;\n        wire [63:0] st_unused;", "")
    parent = once(parent, "        dsfd_capt_g2_dualho u_g", "        wire [1:0] ho_half;\n        dsfd_capt_g2_dualho u_g")
    parent = once(parent, "dsfd_capt_x8_dual u_x0", "dsfd_capt_x8_data_e u_x0")
    parent = once(parent, "dsfd_capt_x8_dual u_x1", "dsfd_capt_x8_data_w u_x1")
    parent = once(parent, ", .f_sn(sn_g), .t_st(stv[64*g +: 64])", "")
    parent = once(parent, ", .f_sn(sn_g), .t_st(st_unused)", "")
    parent = once(parent, "        assign ho[0] = |ho_half;", "")
    parent = once(parent, "    wire [63:0] stw = stv[64 * (NT / 2 - 1) +: 64];", "    dsfd_capt_status_dual u_status (.ck(ck_status), .rst(rst), .ckv(ckv_status), .rsv(rsv), .f_sn(nd), .t_st(stw)); //")
    parent = once(parent, "    wire [67:0] nd_o;\n    dsfd_rly_68_EW u_sn (.ck(ck_sn), .rs(rst[0]), .i({sn_c[3:0], sn_c}), .o(nd_o));\n    assign nd = nd_o[63:0];", "    dsfd_capt_rly_64_EW u_sn (.ck(ck_sn), .rs(rst[0]), .i(sn_c), .o(nd));")
    parent = once(parent, "wire [67:0] oa; wire [53:0] ob;", "wire [67:0] oa; wire [30:0] ob;")
    parent = once(parent, "dsfd_rly_54_EW u_kb", "dsfd_capt_rly_31_EW u_kb")
    parent = once(parent, ".i({kg[22:0], kg[98:68]})", ".i(kg[98:68])")
    parent = once(parent, "wire [62:0] oa, ob;", "wire [62:0] oa; wire [35:0] ob;")
    parent = once(parent, "dsfd_rly_63_WE u_kb", "dsfd_capt_rly_36_WE u_kb")
    parent = once(parent, ".i({kg[26:0], kg[98:63]})", ".i(kg[98:63])")
    parent = once(parent, "wire [11:0] cd; wire [14:0] cd_o;", "wire [11:0] cd;")
    # S-VM-CAPT-CD2 ab1d77b6d: the CLOSED native-PASS cd view (split1016p) is the PINREG=1 form (f_st pin registers,
    # DONE toggle +1 ckv); the parent binds that view, so the candidate instantiates it.
    parent = once(parent, "dsfd_capt_cd u_cd (", "dsfd_capt_cd #(.PINREG(1)) u_cd (")
    parent = once(parent, "dsfd_rly_15_SN u_cr (.ck(ckv_r), .rs(rsv[0]), .i({cd[2:0], cd}), .o(cd_o));\n    assign t_cd = cd_o[11:0];", "dsfd_capt_rly_12_SN u_cr (.ck(ckv_r), .rs(rsv[0]), .i(cd), .o(t_cd));")
    out[CANDIDATE] = "// Candidate generated by tools/s81_ph/capture_split.py; original parent remains reference.\n" + parent
    return out, hashlib.sha256(source.encode()).hexdigest()


def check():
    """List of (path, reason) where regeneration differs from the file on disk; empty when byte-identical."""
    out, _ = render()
    bad = []
    for rel, text in out.items():
        path = ROOT / rel
        if not path.is_file():
            bad.append((rel, "missing"))
        elif path.read_text() != text:
            bad.append((rel, "differs"))
    return bad


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="compare regeneration with the committed files; write nothing")
    a = p.parse_args()
    if a.check:
        bad = check()
        for rel, why in bad:
            print("CAPTURE_SPLIT_REGEN", why.upper(), rel)
        print("CAPTURE_SPLIT_REGEN", "FAIL" if bad else "PASS", len(render()[0]) - len(bad), "of", len(render()[0]), "byte-identical")
        raise SystemExit(1 if bad else 0)
    out, sha = render()
    for rel, text in out.items():
        (ROOT / rel).write_text(text)
    print(json.dumps(dict(candidate=CANDIDATE, cones=OUT, source_sha256=sha)))


if __name__ == "__main__":
    main()
