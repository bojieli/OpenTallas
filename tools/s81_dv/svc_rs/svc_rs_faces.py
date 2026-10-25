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
Usage: python3 tools/s81_dv/svc_rs/svc_rs_faces.py [--root REPO] [--check]   (--check: fail if the outputs are stale)

S81/SVCG (2026-10-25, OWNER DECISION 12 / DEC12 FOLD 2-BEAT CONTRACT): also the F2B port variants of the DEC12 die
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_fv_f2b.sv   dsdv_svc_rs_fv_<FM hex>_f2b<FH hex> / dsdv_svc_rs_pvso_entry_fv_<FM>_f2b<FH>
                                                      (core F2B = 1, FH = sx_fh(sid) of dsdv_svc_sx_f2b.svh = svc_rs_embed.py
                                                      --fold-extra): a 2-beat fold gather face carries gh_o_<f> / gh_i_<f>
                                                      (1,068 b {beat, payload 1,067}) INSTEAD of go_v/go_d_<f> / gi_v/gi_d_<f>
  results/arch/s81_dv_1016/svc_rs/faces_f2b.json      per sid: variant, FH, ports
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
    "GI": [("gi_v", "input", 1), ("gi_d", "input", 2132)], "GO": [("go_v", "output", 1), ("go_d", "output", 2132)],
    "SI": [("si_v", "input", 1), ("si_d", "input", 1076)], "SO": [("so_v", "output", 1), ("so_d", "output", 1076)],
}
ENTRIES = (5, 11)


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


def fh_masks(root):
    """S81/SVCG: sid -> FH = {GI 4, GO 4} 2-beat fold gather faces (dsdv_svc_sx_f2b.svh sx_fh, svc_rs_embed.py --fold-extra)."""
    txt = open(os.path.join(root, "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx_f2b.svh")).read()
    out = {int(s): int(v, 16) for s, v in re.findall(r"4'd(\d+): sx_fh = 8'h([0-9a-fA-F]+);", txt)}
    assert sorted(out) == list(range(16)), out
    return out


def variant_f2b(s, m, fh):
    return variant(s, m) + "_f2b%02x" % fh


def face_ports(m, fh=None):
    """[(new port, core port, dir, width, face)] of the faces this mask keeps.  S81/SVCG: with fh (F2B variant), a 2-beat
    fold gather face carries gh_o_<f> / gh_i_<f> (1,068 b) instead of its go_* / gi_* ports."""
    out = []
    hx = {"GO": 0 if fh is None else fh & 0xF, "GI": 0 if fh is None else fh >> 4}
    for g in GROUPS:
        for p, d, w in PORTS[g]:
            for f in range(4):
                if m[g] >> f & 1 and not (hx.get(g, 0) >> f & 1):
                    out.append((f"{p}_{FACES[f]}", p, d, w, f))
        if g in ("GI", "GO") and hx[g]:
            for f in range(4):
                if hx[g] >> f & 1:
                    out.append((f"gh_{'i' if g == 'GI' else 'o'}_{FACES[f]}", "gh_" + ("i" if g == "GI" else "o"),
                                "input" if g == "GI" else "output", 1068, f))
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
ENTRY_IO = ("input wire [32:0] j, output wire [1:0] jd, input wire [512:0] q, input wire [291:0] hw, output wire [8:0] hc,\n"
            "    output wire fault, output wire [1:0] st_rg, output wire pv_v, output wire [512:0] pv_d, output wire [47:0] pv_x,\n"
            "    input wire [561:0] local_pv_landed, input wire [561:0] peer_pv,\n"
            "    output wire so_ready, output wire so_done, output wire [11:0] so_fault_code")
OBS = ("`ifdef RS_OBS\n    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d,"
       " output wire [11:0] w_st\n    , output wire [2678:0] obs\n`endif\n")


def module(kind_entry, m, fh=None):
    name = ("dsdv_svc_rs_pvso_entry_fv_" if kind_entry else "dsdv_svc_rs_fv_") + fm_hex(m)
    if fh is not None:
        name += "_f2b%02x" % fh
    fp = face_ports(m, fh)
    ports = [COMMON_IN] + ([ENTRY_IO] if kind_entry else [])
    for np_, _cp, d, w, _f in fp:
        ports.append(f"{d} wire [{w - 1}:0] {np_}" if w > 1 else f"{d} wire {np_}")
    hdr = (f"// slice role faces: " + ", ".join(f"{g} {''.join(FACES[f].upper() for f in range(4) if m[g] >> f & 1) or '-'}"
                                                 for g in GROUPS) + "\n")
    L = [hdr + f"module {name} #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,\n"
         f"    parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1"
         + (", parameter integer PVSO_ENABLE = 0" if kind_entry else "") + ") (\n    "
         + ",\n    ".join(ports) + "\n" + OBS + ");",
         "    /*verilator hier_block*/",
         "`ifndef RS_OBS",
         "    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;",
         "`endif"]
    # packed core-side buses: kept faces wired to the variant ports; dropped faces do not exist in the core (FM generate)
    # so the inputs below carry no logic and the outputs are not driven by any register
    conn = {}
    hx = {"GO": 0 if fh is None else fh & 0xF, "GI": 0 if fh is None else fh >> 4}
    for g in GROUPS:
        for p, d, w in PORTS[g]:
            n = f"c_{p}"
            L.append(f"    wire [{4 * w - 1}:0] {n};")
            for f in range(4):
                if hx.get(g, 0) >> f & 1:     # S81/SVCG: 2-beat fold face -> the core's gh_* (go_* constant 0, gi_* not read)
                    sl = f"{n}[{w * f}]" if w == 1 else f"{n}[{w * f + w - 1}:{w * f}]"
                    if d == "input":
                        L.append(f"    assign {sl} = {w}'d0;   // 2-beat fold face: the core reads gh_i here")
                elif m[g] >> f & 1:
                    sl = f"{n}[{w * f}]" if w == 1 else f"{n}[{w * f + w - 1}:{w * f}]"
                    if d == "input":
                        L.append(f"    assign {sl} = {p}_{FACES[f]};")
                    else:
                        L.append(f"    assign {p}_{FACES[f]} = {sl};")
                elif d == "input":
                    sl = f"{n}[{w * f}]" if w == 1 else f"{n}[{w * f + w - 1}:{w * f}]"
                    L.append(f"    assign {sl} = {w}'d0;   // face not in FM: the core has no logic on it")
            conn[p] = n
    # S81/SVCG: the 2-beat fold gather faces (F2B variant) / the core's unused gh ports (pre-DEC12 variant)
    if fh is not None:
        L.append("    wire [4*1068-1:0] c_gh_i, c_gh_o;")
        for f in range(4):
            sl = f"[{1068 * f + 1067}:{1068 * f}]"
            if fh >> (4 + f) & 1:
                L.append(f"    assign c_gh_i{sl} = gh_i_{FACES[f]};")
            else:
                L.append(f"    assign c_gh_i{sl} = 1068'd0;   // not a 2-beat fold face: the core does not read it")
            if fh >> f & 1:
                L.append(f"    assign gh_o_{FACES[f]} = c_gh_o{sl};")
        conn["gh_i"] = "c_gh_i"; conn["gh_o"] = "c_gh_o"
    elif not kind_entry:   # the legacy entry master dsdv_svc_rs_pvso_entry has no gh ports (it ties its core's)
        conn["gh_i"] = "4272'd0"; conn["gh_o"] = ""
    fmv = f"40'h{fm_hex(m)}"
    f2b = "" if fh is None else f", .FH(8'h{fh:02x})"
    pc = ", ".join(f".{p}({n})" for p, n in conn.items())
    if kind_entry:
        L.append(f"    dsdv_svc_rs_pvso_entry{'' if fh is None else '_f2b'} #(.PVSO_ENABLE(PVSO_ENABLE), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), "
                 f".SRAM_MACRO(SRAM_MACRO), .PV_IDENTITY(PV_IDENTITY), .SMT(SMT), .FM({fmv}){f2b}) u (\n"
                 f"        .ck(ck), .rst(rst), .sid(sid), .j(j), .jd(jd), .q({{2'b00, q}}), .hw(hw), .hc(hc), .fault(fault), .st_rg(st_rg),\n"
                 f"        {pc},\n"
                 f"        .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),\n"
                 f"        .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .local_pv_landed(local_pv_landed), .peer_pv(peer_pv),\n"
                 f"        .so_ready(so_ready), .so_done(so_done), .so_fault_code(so_fault_code)\n"
                 "`ifdef RS_OBS\n        , .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st), .obs(obs)\n`endif\n        );")
    else:
        L.append("    wire [1:0] jd_nc; wire [8:0] hc_nc; wire fault_nc; wire pv_v_nc; wire [512:0] pv_d_nc; wire [47:0] pv_x_nc;"
                 " wire [1:0] st_rg_nc;")
        L.append(f"    dsdv_svc_rs_c #(.ENTRY(0), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), "
                 f".PV_IDENTITY(PV_IDENTITY), .FM({fmv}){'' if fh is None else ', .F2B(1)' + f2b}) u (\n"
                 f"        .ck(ck), .rst(rst), .sid(sid), .j(33'd0), .jd(jd_nc), .q(515'd0), .hw(292'd0), .hc(hc_nc), .fault(fault_nc),\n"
                 f"        .st_rg(st_rg_nc), {pc},\n"
                 f"        .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs),\n"
                 f"        .pv_v(pv_v_nc), .pv_d(pv_d_nc), .pv_x(pv_x_nc), .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st)\n"
                 "`ifdef RS_OBS\n        , .obs(obs)\n`endif\n        );")
    L.append("endmodule\n")
    return name, "\n".join(L)


def sv_f2b(ms, fhs):
    out = ["`timescale 1ns/1ps",
           "// generated by tools/s81_dv/svc_rs/svc_rs_faces.py (S81/SVCG 2026-10-25, OWNER DECISION 12 / DEC12 FOLD 2-BEAT",
           "// CONTRACT) -- do not edit.  The F2B port variants of the DEC12 die: as dsdv_svc_rs_fv.sv (role faces only), core",
           "// F2B = 1 + FH = sx_fh(sid) (dsdv_svc_sx_f2b.svh); a 2-beat fold gather face (svc_2k <-> svc_2k+1, lane",
           "// attnh__svc_A__svc_B) carries gh_o_<f> / gh_i_<f> = {beat, payload 1,067} instead of go_v/go_d_<f> / gi_v/gi_d_<f>.",
           ""]
    seen = set()
    for s in range(16):
        k = (s in ENTRIES, fm_hex(ms[s]), fhs[s])
        if k in seen:
            continue
        seen.add(k)
        out.append(module(s in ENTRIES, ms[s], fhs[s])[1])
    return "\n".join(out)


def table_f2b(ms, fhs):
    rows = {}
    for s in range(16):
        rows["rsv_%02d" % s] = dict(sid=s, entry=s in ENTRIES, fm="40'h" + fm_hex(ms[s]), fh="8'h%02x" % fhs[s],
                                    variant=variant_f2b(s, ms[s], fhs[s]),
                                    fold_go="".join(FACES[f].upper() for f in range(4) if fhs[s] >> f & 1),
                                    fold_gi="".join(FACES[f].upper() for f in range(4) if fhs[s] >> (4 + f) & 1),
                                    ports=[p for p, *_ in face_ports(ms[s], fhs[s])])
    return dict(schema="opentallas.s81_dv.svc_rs_faces_f2b.v1", source="tools/s81_dv/svc_rs/svc_rs_faces.py",
                contract="claude/s81-dec12-1024r@d206dfb226 FOLD 2-BEAT CONTRACT", slices=rows,
                variants=sorted({r["variant"] for r in rows.values()}))


def sv(ms):
    out = ["`timescale 1ns/1ps",
           "// generated by tools/s81_dv/svc_rs/svc_rs_faces.py (S81-P9-FACE 2026-10-23) -- do not edit.",
           "// Port variants of the regional service slice: one per distinct (kind, FM) of the 16 slices' role faces (the",
           "// role ROMs dsdv_svc_rs_roles.svh / dsdv_svc_sx_roles.svh).  A variant carries ONLY the faces its role uses, as",
           "// per-face ports <bus>_<n|e|s|w>; the core dsdv_svc_rs_c #(.FM) builds no flop, relay or logic on the others.",
           "// The 14 tree slices instantiate dsdv_svc_rs_c (ENTRY 0) like dsdv_svc_rs; the entries (rsv_05 / rsv_11) wrap",
           "// dsdv_svc_rs_pvso_entry #(.FM).  The strap sid must select the role the variant was made for (core: sticky",
           "// fault on a role face outside FM).  Entry q is the die's 513-b q lane {d 512, v}: the all-faces port's two",
           "// upper bits (q[514] transport fault / q[513], never driven by the die's slice bo source) are not ports.",
           ""]
    seen = set()
    for s in range(16):
        k = (s in ENTRIES, fm_hex(ms[s]))
        if k in seen:
            continue
        seen.add(k)
        out.append(module(s in ENTRIES, ms[s])[1])
    return "\n".join(out)


def table(ms):
    rows = {}
    for s in range(16):
        m = ms[s]
        kept = sum(w * bin(m[g]).count("1") for g in GROUPS for _p, _d, w in PORTS[g])
        full = sum(w * 4 for g in GROUPS for _p, _d, w in PORTS[g])
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
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    ms = masks(root)
    fhs = fh_masks(root)
    outs = {"rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_fv_f2b.sv": sv_f2b(ms, fhs),
            "results/arch/s81_dv_1016/svc_rs/faces_f2b.json": json.dumps(table_f2b(ms, fhs), indent=1) + "\n",
            "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_faces.svh": svh(ms),
            "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_fv.sv": sv(ms),
            "results/arch/s81_dv_1016/svc_rs/faces.json": json.dumps(table(ms), indent=1) + "\n"}
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
