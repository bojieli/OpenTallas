#!/usr/bin/env python3
"""S81-P9-FACE (2026-10-23): per-slice FACE MASKS of the 16 regional service slices dsdv_svc_rs, read from the role ROMs
of record (no hand lists):
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_roles.svh  (svc_rs_tree.py: rs_role parent / children, rs_pface P path faces)
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx_roles.svh  (svc_rs_embed.py: sx_role gather / scatter sources and outputs)
and the PORT VARIANTS that carry only the faces a slice's role uses (owner rule: no tied / open face ports).

Face index f = 0..3 = N, E, S, W (the RTL's packed order {W, S, E, N} = [3:0]).  Ten 4-bit masks per slice:
  DI dn stream in   = parent face             DO dn stream out = children
  UI up status in   = children                UO up status out = parent face
  RI P.V return in  = children | P path in    RO P.V return out = parent face | P path out
  GI gather in      = faces read by ga / gb / go_X (codes 2..5)      GO gather out  = faces with go_X != 0
  SI scatter in     = faces read by ss / so_X / ts (codes 1..4)      SO scatter out = faces with so_X != 0
(the same decode as dsdv_svc_sx_hrow g_used / s_used and dsdv_svc_rs_c chm / par / pf).  Packed parameter FM = {SO, SI, GO,
GI, RO, RI, UO, UI, DO, DI} (40 b, DI = [3:0]); FM = all ones is the pre-mask slice (every face).

Outputs (default, repo root):
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_faces.svh   rs_fmask(sid): the role-derived mask (the core's runtime check that
                                                      the strap sid matches the variant's FM; sticky fault otherwise)
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_fv.sv       one port variant per distinct (kind, FM): dsdv_svc_rs_fv_<FM hex>
                                                      (the 14 tree slices) and dsdv_svc_rs_pvso_entry_fv_<FM hex> (entries)
  results/arch/s81_dv_1016/svc_rs/faces.json          per sid: masks, variant, kept / dropped face bits
  physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_fv.sv
  physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_pvso_entry.sv
                                                      S81-SVC-H8W 11-20: the bind178 PORTFIX overlays the die bind reads,
                                                      GENERATED here too (a stale H16 hand copy shadowed the H-aware rtl
                                                      form in J3 r7).  PORTFIX ABI: entry q [512:0], no so_* status ports
                                                      (fault sticky inside the entry).  SUPERSET gather pins (owner 11-20):
                                                      every gather face port is GP = `OT_SVC_GP b (default 2132, the die
                                                      netlist / plan attnh lane), the H lane GW = H*132+20 low-aligned in it;
                                                      the pad bits above GW are inputs with no reader and outputs driven 0.
Usage: python3 tools/s81_dv/svc_rs/svc_rs_faces.py [--root REPO] [--check]   (--check: fail if the outputs are stale;
       the bind runs it on the PORTFIX overlays: FRESH)
"""
import argparse
import json
import os
import re
import sys

FACES = "nesw"                                   # f = 0..3 = N, E, S, W
GROUPS = ["DI", "DO", "UI", "UO", "RI", "RO", "GI", "GO", "SI", "SO"]
# group -> (core port(s), direction, per-face width of each port)
PORTS = {
    "DI": [("dn_i", "input", 805)], "DO": [("dn_o", "output", 805)],
    "UI": [("up_i", "input", 16)], "UO": [("up_o", "output", 16)],
    "RI": [("ri", "input", 514)], "RO": [("ro", "output", 514)],
    # S81-SVCRS R5 (11-08): the gather lane is H-dependent (132 H + 20 b: 2,132 at H 16, 1,076 at H 8): width "GW"
    "GI": [("gi_v", "input", 1), ("gi_d", "input", "GW")], "GO": [("go_v", "output", 1), ("go_d", "output", "GW")],
    "SI": [("si_v", "input", 1), ("si_d", "input", 1076)], "SO": [("so_v", "output", 1), ("so_d", "output", 1076)],
}
ENTRIES = (5, 11)
PORTFIX_FV = "physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_fv.sv"
PORTFIX_EN = "physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_pvso_entry.sv"


def _cases(text, fn):
    m = re.search(r"function automatic \[\d+:0\] %s\(.*?endfunction" % fn, text, re.S)
    assert m, fn
    out = {}
    for s, v in re.findall(r"4'd(\d+): %s = \d+'h([0-9a-fA-F]+);" % fn, m.group(0)):
        out[int(s)] = int(v, 16)
    return out


def masks(root):
    d = os.path.join(root, "rtl/dsrom_sys/s81_dv/svc_rs")
    rs = open(os.path.join(d, "dsdv_svc_rs_roles.svh")).read()
    sx = open(os.path.join(d, "dsdv_svc_sx_roles.svh")).read()
    role, pface, sxr = _cases(rs, "rs_role"), _cases(rs, "rs_pface"), _cases(sx, "sx_role")
    res = {}
    for s in range(16):
        r = role[s]
        chm, par = (r >> 4) & 0xF, (r >> 8) & 0x7
        pf = pface.get(s, 0)
        pin, pout = (pf >> 4) & 0xF, pf & 0xF
        pm = (1 << (par - 1)) if par else 0
        x = sxr[s]
        ga, gb = x & 7, (x >> 3) & 7
        go = [(x >> (6 + 3 * f)) & 7 for f in range(4)]
        ss = (x >> 19) & 7
        so = [(x >> (24 + 3 * f)) & 7 for f in range(4)]
        ts = (x >> 36) & 7
        gi = si = 0
        for f in range(4):
            if 2 + f in [ga, gb] + go:
                gi |= 1 << f
            if 1 + f in [ss, ts] + so:
                si |= 1 << f
        m = dict(DI=pm, DO=chm, UI=chm, UO=pm, RI=chm | pin, RO=pm | pout,
                 GI=gi, GO=sum(1 << f for f in range(4) if go[f]), SI=si, SO=sum(1 << f for f in range(4) if so[f]))
        res[s] = m
    return res


def fm_word(m):
    return sum(m[g] << (4 * i) for i, g in enumerate(GROUPS))


def fm_hex(m):
    return "%010x" % fm_word(m)


def variant(s, m):
    return ("dsdv_svc_rs_pvso_entry_fv_" if s in ENTRIES else "dsdv_svc_rs_fv_") + fm_hex(m)


def face_ports(m):
    """[(new port, core port, dir, width, face)] of the faces this mask keeps."""
    out = []
    for g in GROUPS:
        for p, d, w in PORTS[g]:
            for f in range(4):
                if m[g] >> f & 1:
                    out.append((f"{p}_{FACES[f]}", p, d, w, f))
    return out


def svh(ms):
    L = ["// generated by tools/s81_dv/svc_rs/svc_rs_faces.py (S81-P9-FACE 2026-10-23) from dsdv_svc_rs_roles.svh +",
         "// dsdv_svc_sx_roles.svh -- do not edit.  rs_fmask(sid) = {SO, SI, GO, GI, RO, RI, UO, UI, DO, DI} 4 b each (bit f = face",
         "// N / E / S / W): the faces slice sid's role uses.  The core faults (sticky) when its strap sid needs a face its",
         "// variant FM does not carry.",
         "function automatic [39:0] rs_fmask(input [3:0] sid);",
         "    case (sid)"]
    for s in range(16):
        L.append(f"        4'd{s}: rs_fmask = 40'h{fm_hex(ms[s])};")
    L += ["        default: rs_fmask = 40'h0;", "    endcase", "endfunction", ""]
    return "\n".join(L)


COMMON_IN = ("input wire ck, input wire rst, input wire [3:0] sid,\n"
             "    output wire [2*341-1:0] rq, input wire [1:0] rk, input wire [1:0] wd, input wire [1:0] rv,\n"
             "    input wire [2*256-1:0] r_data, input wire [2*17-1:0] r_tag, input wire [2*4-1:0] r_beat, input wire [1:0] hs")
ENTRY_IO_PORTFIX = ("input wire [32:0] j, output wire [1:0] jd, input wire [512:0] q, input wire [291:0] hw, output wire [8:0] hc,\n"
                    "    output wire fault, output wire [1:0] st_rg, output wire pv_v, output wire [512:0] pv_d, output wire [47:0] pv_x,\n"
                    "    input wire [561:0] local_pv_landed, input wire [561:0] peer_pv")
ENTRY_IO = ("input wire [32:0] j, output wire [1:0] jd, input wire [512:0] q, input wire [291:0] hw, output wire [8:0] hc,\n"
            "    output wire fault, output wire [1:0] st_rg, output wire pv_v, output wire [512:0] pv_d, output wire [47:0] pv_x,\n"
            "    input wire [561:0] local_pv_landed, input wire [561:0] peer_pv,\n"
            "    output wire so_ready, output wire so_done, output wire [11:0] so_fault_code")
OBS = ("`ifdef RS_OBS\n    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d,"
       " output wire [11:0] w_st\n    , output wire [H*132+566:0] obs\n`endif\n")


def module(kind_entry, m, portfix=False):
    name = ("dsdv_svc_rs_pvso_entry_fv_" if kind_entry else "dsdv_svc_rs_fv_") + fm_hex(m)
    fp = face_ports(m)
    ports = [COMMON_IN] + ([ENTRY_IO_PORTFIX if portfix else ENTRY_IO] if kind_entry else [])
    gwr = "[GP-1:0]" if portfix else "[H*132+19:0]"
    for np_, _cp, d, w, _f in fp:
        ports.append(f"{d} wire {gwr} {np_}" if w == "GW" else
                     f"{d} wire [{w - 1}:0] {np_}" if w > 1 else f"{d} wire {np_}")
    hdr = (f"// slice role faces: " + ", ".join(f"{g} {''.join(FACES[f].upper() for f in range(4) if m[g] >> f & 1) or '-'}"
                                                 for g in GROUPS) + "\n")
    L = [hdr + f"module {name} #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,\n"
         f"    parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1"
         + (", parameter integer PVSO_ENABLE = 0" if kind_entry else "") + ",\n    parameter integer H = `OT_SVC_HV"
         + (", parameter integer GP = `OT_SVC_GP" if portfix else "") + ") (\n    "
         + ",\n    ".join(ports) + "\n" + OBS + ");",
         "    /*verilator hier_block*/",
         "`ifndef RS_OBS",
         "    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;",
         "`endif",
         "    localparam integer GW = H * 132 + 20;   // gather lane (S81-SVCRS R5)"]
    if portfix:
        L += ["    // superset gather pins: GP >= GW or the variant refuses to elaborate (no silent resize)",
              "    if (GP < GW) begin : g_gp_short", "        dsdv_svc_gather_pin_narrower_than_lane u_gp_guard ();", "    end"]
    # packed core-side buses: kept faces wired to the variant ports; dropped faces do not exist in the core (FM generate)
    # so the inputs below carry no logic and the outputs are not driven by any register
    conn = {}
    for g in GROUPS:
        for p, d, w in PORTS[g]:
            n = f"c_{p}"
            L.append(f"    wire [4*GW-1:0] {n};" if w == "GW" else f"    wire [{4 * w - 1}:0] {n};")
            def sl_(f):
                if w == "GW": return f"{n}[GW*{f} +: GW]"
                return f"{n}[{w * f}]" if w == 1 else f"{n}[{w * f + w - 1}:{w * f}]"
            for f in range(4):
                if m[g] >> f & 1:
                    sl = sl_(f)
                    if d == "input":
                        src = f"{p}_{FACES[f]}[GW-1:0]" if (portfix and w == "GW") else f"{p}_{FACES[f]}"
                        L.append(f"    assign {sl} = {src};" + ("   // lane low-aligned; pad [GP-1:GW] has no reader"
                                                                 if portfix and w == "GW" else ""))
                    elif portfix and w == "GW":
                        L.append(f"    assign {p}_{FACES[f]} = GP'({sl});   // lane low-aligned; pad [GP-1:GW] driven 0")
                    else:
                        L.append(f"    assign {p}_{FACES[f]} = {sl};")
                elif d == "input":
                    sl = sl_(f)
                    z = "{GW{1'b0}}" if w == "GW" else f"{w}'d0"
                    L.append(f"    assign {sl} = {z};   // face not in FM: the core has no logic on it")
            conn[p] = n
    fmv = f"40'h{fm_hex(m)}"
    pc = ", ".join(f".{p}({n})" for p, n in conn.items())
    if kind_entry:
        qx = "q" if portfix else "{2'b00, q}"
        L.append(f"    dsdv_svc_rs_pvso_entry #(.PVSO_ENABLE(PVSO_ENABLE), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), "
                 f".SRAM_MACRO(SRAM_MACRO), .PV_IDENTITY(PV_IDENTITY), .SMT(SMT), .FM({fmv}), .H(H)) u (\n"
                 f"        .ck(ck), .rst(rst), .sid(sid), .j(j), .jd(jd), .q({qx}), .hw(hw), .hc(hc), .fault(fault), .st_rg(st_rg),\n"
                 f"        {pc},\n"
                 f"        .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),\n"
                 + (f"        .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .local_pv_landed(local_pv_landed), .peer_pv(peer_pv)\n" if portfix else
                    f"        .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .local_pv_landed(local_pv_landed), .peer_pv(peer_pv),\n"
                    f"        .so_ready(so_ready), .so_done(so_done), .so_fault_code(so_fault_code)\n")
                 + "`ifdef RS_OBS\n        , .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st), .obs(obs)\n`endif\n        );")
    else:
        L.append("    wire [1:0] jd_nc; wire [8:0] hc_nc; wire fault_nc; wire pv_v_nc; wire [512:0] pv_d_nc; wire [47:0] pv_x_nc;"
                 " wire [1:0] st_rg_nc;")
        L.append(f"    dsdv_svc_rs_c #(.ENTRY(0), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), "
                 f".PV_IDENTITY(PV_IDENTITY), .FM({fmv}), .H(H)) u (\n"
                 f"        .ck(ck), .rst(rst), .sid(sid), .j(33'd0), .jd(jd_nc), .q(515'd0), .hw(292'd0), .hc(hc_nc), .fault(fault_nc),\n"
                 f"        .st_rg(st_rg_nc), {pc},\n"
                 f"        .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),\n"
                 f"        .pv_v(pv_v_nc), .pv_d(pv_d_nc), .pv_x(pv_x_nc), .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st)\n"
                 "`ifdef RS_OBS\n        , .obs(obs)\n`endif\n        );")
    L.append("endmodule\n")
    return name, "\n".join(L)


def sv(ms, portfix=False):
    out = ["`timescale 1ns/1ps",
           "`ifndef OT_SVC_HV",
           "`ifdef OT_SVC_H8",
           "`define OT_SVC_HV 8",
           "`else",
           "`define OT_SVC_HV 16",
           "`endif",
           "`endif"] + (["`ifndef OT_SVC_GP",
                         "`define OT_SVC_GP 2132   // superset gather pin lane (die netlist w_sg / plan attnh, owner 11-20)",
                         "`endif"] if portfix else []) + [
           "// generated by tools/s81_dv/svc_rs/svc_rs_faces.py (S81-P9-FACE 2026-10-23) -- do not edit.",
           "// Port variants of the regional service slice: one per distinct (kind, FM) of the 16 slices' role faces (the",
           "// role ROMs dsdv_svc_rs_roles.svh / dsdv_svc_sx_roles.svh).  A variant carries ONLY the faces its role uses, as",
           "// per-face ports <bus>_<n|e|s|w>; the core dsdv_svc_rs_c #(.FM) builds no flop, relay or logic on the others.",
           "// The 14 tree slices instantiate dsdv_svc_rs_c (ENTRY 0) like dsdv_svc_rs; the entries (rsv_05 / rsv_11) wrap",
           "// dsdv_svc_rs_pvso_entry #(.FM).  The strap sid must select the role the variant was made for (core: sticky",
           "// fault on a role face outside FM).  Entry q is the die's 513-b q lane {d 512, v}: the all-faces port's two",
           "// upper bits (q[514] transport fault / q[513], never driven by the die's slice bo source) are not ports"
           + (" (PORTFIX-DEAD:\n// dsdv_svc_rs_pvso_entry q is [512:0]; its program has TF 0, so no q[514] reader)." if portfix else "."),
           ""]
    if portfix:
        out[-1:-1] = ["// bind178 PORTFIX overlay (--portfix form of this generator): superset gather pins GP = `OT_SVC_GP, the H lane",
                      "// GW = H*132+20 low-aligned (S81-SVC-H8W 11-20); entry ABI q [512:0], no so_* ports."]
    seen = set()
    for s in range(16):
        k = (s in ENTRIES, fm_hex(ms[s]))
        if k in seen:
            continue
        seen.add(k)
        out.append(module(s in ENTRIES, ms[s], portfix)[1])
    return "\n".join(out)


# The PORTFIX service entry (bind178 ABI: q [512:0], no so_* ports, sticky fault, H16 program TF 0 / ingress_hden),
# H-parameterised (S81-SVC-H8W 11-20): under OT_SVC_H8 the _h8 SO program / half join / ingress of the rtl entry.
PORTFIX_ENTRY = "`timescale 1ns/1ps\n`ifndef OT_SVC_HV\n`ifdef OT_SVC_H8\n`define OT_SVC_HV 8\n`else\n`define OT_SVC_HV 16\n`endif\n`endif\n// Existing service entry ABI plus static all-quarter SO source assembly.\n// S81-SVC-H8W 11-20 (S81-SVC-SPLIT-1119, COORD/S81-DIE-R3 J3 r7): H-parameterised.  The gather lane is H*132+20 b a\n// face (H = `OT_SVC_HV: 16 = the frozen bind178 ABI byte for byte in behaviour, 8 under OT_SVC_H8), passed to\n// dsdv_svc_rs_c as .H(H); under OT_SVC_H8 the SO program / half join / ingress are the _h8 forms of the source\n// rtl/dsrom_sys/s81_dv/pv_so/dsdv_svc_rs_pvso_entry.sv.  The PORTFIX ABI (q [512:0], no so_* status ports, sticky\n// fault flop) is kept in both forms.  Width gate: tools/die_plan/svc_width_gate.py.\nmodule dsdv_svc_rs_pvso_entry #(parameter integer PVSO_ENABLE=0, parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,\n                           parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1,\n                           parameter logic [39:0] FM = {40{1'b1}},\n                           parameter integer H = `OT_SVC_HV) (   // S81-P9-FACE face mask / S81-SVCRS R5 heads per pass -> dsdv_svc_rs_c\n    input  wire ck, rst, input wire [3:0] sid,\n    input  wire [32:0] j, output wire [1:0] jd, input wire [512:0] q,   // the die's 513-b q lane {d 512, v}\n    input wire [291:0] hw, output wire [8:0] hc,\n    output wire fault, output wire [1:0] st_rg,\n    input  wire [4*805-1:0] dn_i, output wire [4*805-1:0] dn_o, input wire [4*16-1:0] up_i, output wire [4*16-1:0] up_o,\n    input  wire [4*514-1:0] ri, output wire [4*514-1:0] ro,\n    input  wire [3:0] gi_v, input wire [4*(H*132+20)-1:0] gi_d, output wire [3:0] go_v, output wire [4*(H*132+20)-1:0] go_d,\n    input  wire [3:0] si_v, input wire [4*1076-1:0] si_d, output wire [3:0] so_v, output wire [4*1076-1:0] so_d,\n    output wire [2*341-1:0] rq, input wire [1:0] rk, wd, rv, input wire [2*256-1:0] r_data, input wire [2*17-1:0] r_tag,\n    input  wire [2*4-1:0] r_beat, input wire [1:0] hs,\n    output wire pv_v, output wire [512:0] pv_d, output wire [47:0] pv_x,\n    input wire [561:0] local_pv_landed,peer_pv\n    // S81/PORTFIX-FLT 10-25 (S81 DECISION 4): the SO status outputs so_ready / so_done (status) and so_fault_code[11:0]\n    // (detail code) are dropped; the ingress fault (= |so_fault_code, sticky) stays OR-ed into the one fault output.\n\n`ifdef RS_OBS\n    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d, output wire [11:0] w_st\n    , output wire [H*132+566:0] obs\n`endif\n);\n    /*verilator hier_block*/\n`ifndef RS_OBS\n    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;\n`endif\n    wire so_cfg_v,so_param_v,so_launch,program_fault;\n    wire so_ready,so_done;wire[11:0]so_fault_code;   // internal (bench taps only)\n    wire[19:0]so_owner,so_param_owner;wire[20:0]so_position,so_param_position;\n    wire[7:0]so_se_jid,so_jid;wire[15:0]so_local_first,so_peer_first;\n    wire[2:0]so_param_row;wire[511:0]so_param_d;wire[514:0]q_filtered;\n`ifdef OT_SVC_H8\n    wire[15:0]so_local_first1,so_peer_first1;\n    dsdv_pv_so_program_h8 #(.ENABLE(PVSO_ENABLE),.TF(0)) u_program(.clk(ck),.rst_n(rst),.q({2'b00,q}),.q_pass(q_filtered),\n      .cfg_v(so_cfg_v),.owner(so_owner),.position(so_position),.se_jid(so_se_jid),.so_jid(so_jid),\n      .local_first(so_local_first),.peer_first(so_peer_first),.local_first1(so_local_first1),.peer_first1(so_peer_first1),\n      .param_v(so_param_v),.param_row(so_param_row),\n`else\n    dsdv_pv_so_program #(.ENABLE(PVSO_ENABLE),.TF(0)) u_program(.clk(ck),.rst_n(rst),.q({2'b00,q}),.q_pass(q_filtered),\n      .cfg_v(so_cfg_v),.owner(so_owner),.position(so_position),.se_jid(so_se_jid),.so_jid(so_jid),\n      .local_first(so_local_first),.peer_first(so_peer_first),.param_v(so_param_v),.param_row(so_param_row),\n`endif\n      .param_owner(so_param_owner),.param_position(so_param_position),.param_d(so_param_d),.launch(so_launch),.fault(program_fault));\n    wire generated_v,ingress_fault,join_fault,entry_fault;\n    wire[511:0]generated_d;wire[514:0]q_entry;\n    wire joined_v;wire[1:0]joined_quarter;wire[512:0]joined_d;\n    reg collision;\n    always @(posedge ck or negedge rst)if(!rst)collision<=0;else if(generated_v && q_filtered[0])collision<=1;\n    assign q_entry=generated_v?{2'd0,generated_d,1'b1}:q_filtered;\n    // S81/PORTFIX-FLT 10-25: the one fault output leaves a sticky flop (pin registered; +1 edge on the fault level only)\n    reg fault_q;\n    always @(posedge ck or negedge rst)if(!rst)fault_q<=0;else fault_q<=fault_q|entry_fault|ingress_fault|join_fault|collision|program_fault;\n    assign fault=fault_q;\n    generate if(PVSO_ENABLE!=0)begin:g_join\n`ifdef OT_SVC_H8\n      dsdv_pv_half_join_h8 u_join(.clk(ck),.rst_n(rst),.cfg_v(so_cfg_v),\n       .local_first(so_local_first),.peer_first(so_peer_first),.local_first1(so_local_first1),.peer_first1(so_peer_first1),\n       .local_pv(local_pv_landed),.peer_pv(peer_pv),\n`else\n      dsdv_pv_half_join u_join(.clk(ck),.rst_n(rst),.cfg_v(so_cfg_v),\n       .local_first(so_local_first),.peer_first(so_peer_first),.local_pv(local_pv_landed),.peer_pv(peer_pv),\n`endif\n       .pv_v(joined_v),.pv_quarter(joined_quarter),.pv_d(joined_d),.fault(join_fault));\n    end else begin:g_nojoin\n      assign joined_v=0;assign joined_quarter=0;assign joined_d=0;assign join_fault=0;\n    end endgenerate\n`ifdef OT_SVC_H8\n    dsdv_pv_so_ingress_h8 #(.ENABLE(PVSO_ENABLE),.HEADER_DEN(1)) u_ingress(.clk(ck),.rst_n(rst),\n      .cfg_v(so_cfg_v),.cfg_owner(so_owner),.cfg_position(so_position),.cfg_se_jid(so_se_jid),.cfg_so_jid(so_jid),\n      .pv_v(joined_v),.pv_quarter(joined_quarter),.pv_d(joined_d),\n      .param_v(so_param_v),.param_row(so_param_row),.param_owner(so_param_owner),.param_position(so_param_position),.param_d(so_param_d),\n      .den_v(1'b0),.den_mask(16'd0),.den_owner(20'd0),.den_jid(8'd0),.launch(so_launch),\n`else\n    dsdv_pv_so_ingress_hden #(.ENABLE(PVSO_ENABLE)) u_ingress(.clk(ck),.rst_n(rst),\n      .cfg_v(so_cfg_v),.cfg_owner(so_owner),.cfg_position(so_position),.cfg_se_jid(so_se_jid),.cfg_so_jid(so_jid),\n      .pv_v(joined_v),.pv_quarter(joined_quarter),.pv_d(joined_d),\n      .param_v(so_param_v),.param_row(so_param_row),.param_owner(so_param_owner),.param_position(so_param_position),.param_d(so_param_d),\n      .launch(so_launch),\n`endif\n      .q_v(generated_v),.q_d(generated_d),.ready(so_ready),.done(so_done),.fault(ingress_fault),.fault_code(so_fault_code));\n    dsdv_svc_rs_c #(.ENTRY(1), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), .PV_IDENTITY(PVSO_ENABLE!=0?1:PV_IDENTITY), .FM(FM), .H(H)) u (.ck(ck),\n        .rst(rst), .sid(sid), .j(j), .jd(jd), .q(q_entry), .hw(hw), .hc(hc), .fault(entry_fault), .st_rg(st_rg), .dn_i(dn_i),\n        .dn_o(dn_o), .up_i(up_i), .up_o(up_o), .ri(ri), .ro(ro), .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v), .go_d(go_d),\n        .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d), .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data),\n        .r_tag(r_tag), .r_beat(r_beat), .hs(hs), .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .w_v(w_v), .w_a(w_a), .w_m(w_m),\n        .w_d(w_d), .w_st(w_st)\n`ifdef RS_OBS\n        , .obs(obs)\n`endif\n        );\nendmodule\n"



def table(ms):
    rows = {}
    for s in range(16):
        m = ms[s]
        wn = lambda w: 2132 if w == "GW" else w      # the table records the H 16 face bits (unchanged record)
        kept = sum(wn(w) * bin(m[g]).count("1") for g in GROUPS for _p, _d, w in PORTS[g])
        full = sum(wn(w) * 4 for g in GROUPS for _p, _d, w in PORTS[g])
        rows["rsv_%02d" % s] = dict(sid=s, entry=s in ENTRIES, fm="40'h" + fm_hex(m), variant=variant(s, m),
                                    faces={g: "".join(FACES[f].upper() for f in range(4) if m[g] >> f & 1) for g in GROUPS},
                                    face_bits_kept=kept, face_bits_dropped=full - kept,
                                    ports=[p for p, *_ in face_ports(m)])
    return dict(schema="opentallas.s81_dv.svc_rs_faces.v1", source="tools/s81_dv/svc_rs/svc_rs_faces.py",
                groups=GROUPS, face_order="N,E,S,W = bit 0..3", slices=rows,
                variants=sorted({r["variant"] for r in rows.values()}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only-portfix", action="store_true", help="only the two bind178 PORTFIX overlays (the bind's FRESH check)")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    ms = masks(root)
    outs = {"rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_faces.svh": svh(ms),
            "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_fv.sv": sv(ms),
            "results/arch/s81_dv_1016/svc_rs/faces.json": json.dumps(table(ms), indent=1) + "\n",
            PORTFIX_FV: sv(ms, portfix=True), PORTFIX_EN: PORTFIX_ENTRY}
    if a.only_portfix:
        outs = {k: v for k, v in outs.items() if k in (PORTFIX_FV, PORTFIX_EN)}
    bad = []
    for rel, txt in outs.items():
        p = os.path.join(root, rel)
        if a.check:
            if not os.path.exists(p) or open(p).read() != txt:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(txt)
    if a.check and bad:
        print("STALE", *bad)
        return 1
    t = table(ms)
    print(json.dumps(dict(variants=len(t["variants"]), dropped=sum(r["face_bits_dropped"] for r in t["slices"].values()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
