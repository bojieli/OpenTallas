#!/usr/bin/env python3
"""SVC-CUT-DEPTH RTL patch (FABLE-UNC-S81-SVC + S81-SVC-J9, rc15; COORD + OPUS-FIX-S81-SVC-R9 11-23): uniform extra depth on the hi svc
attention cut.  Applies to the two hi4 source files of a tree (s81_svc_r5_hi4_sources/), on top of whatever is there
(BCAST's p_sync patch lands first); refuses if an anchor is missing or the patch is already in.

  dsdv_svc_att_cut_j7_hi4.sv  parameter CUT_D (default 1 + `OT_SVC_CUT_KA): CUT_D - 1 plain relay stages on every registered
                              in-lane ahead of the capture register and on every registered out-lane ahead of the output
                              relay (inside u_att = the att piece).
  dsdv_svc_rs_c_j7_hi4.sv     `OT_SVC_CUT_KR plain relay stages on the same lanes on the rest side of the cut: in-lanes after
                              the cs capture (u_cutr_i), out-lanes after u_att (u_cutr_o); instance names are outside the
                              u_att content regex, so they belong to the rest piece.
  Both defines default 0 = the files as built (no logic added).  --ka / --kr write the values as `define lines at the top of
  dsdv_svc_rs_c_j7_hi4.sv (the hi-only switch form of OT_SVC_ATTCUT).
Effect at (KA, KR): the attention share runs 1 + KA + KR edges later against the dn stream and its lanes reach the slice
2 x (1 + KA + KR) edges later; the HBM page-cache lanes stay unregistered.  Plan: every internal cut lane of the pair
takes + (KA + KR) fixed cycles (cut_depth_row.py).
usage: apply_cutdepth.py SRC_DIR OUT_DIR [--ka N] [--kr N] | --main   (v3, S81-SVC-J9 11-23: --main patches the main wrapper; stages are plain flop vectors in generate-for loops, no register arrays)"""
import argparse, os, re, sys
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--ka", type=int, default=0); ap.add_argument("--kr", type=int, default=0)
ap.add_argument("--main", action="store_true", help="main form: only the wrapper rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv (CUT_D, default 1); main dsdv_svc_rs_c does not instantiate the wrapper")
a = ap.parse_args()
WF, RF, IM = ("dsdv_svc_att_cut.sv", None, "dsdv_svc_att") if a.main else ("dsdv_svc_att_cut_j7_hi4.sv", "dsdv_svc_rs_c_j7_hi4.sv", "dsdv_svc_att_j7_hi4")
if a.main and (a.ka or a.kr): sys.exit("--main takes no --ka/--kr")
def must(s, old, new, n=1):
    if s.count(old) != n: sys.exit("ANCHOR missing or repeated (%d): %r" % (s.count(old), old[:70]))
    return s.replace(old, new)
# ---------------------------------------------------------------- wrapper
w = open(os.path.join(a.src, WF)).read()
if "CUT_D" in w: sys.exit("wrapper already patched")
w = must(w, "// CUTMUT (bench only", """// CUT_D (SVC-CUT-DEPTH, FABLE-UNC-S81-SVC 11-23; default 1 = this file as built; dsdv_svc_rs_c passes 1 + `OT_SVC_CUT_KA): uniform
// cut depth on the att side.  CUT_D - 1 plain relay stages on EVERY registered in-lane ahead of the capture register and on
// EVERY registered out-lane ahead of the output relay, so the lock-step is kept.  The HBM page-cache lanes stay unregistered.
// CUTMUT (bench only""")
w = must(w, "    parameter integer CUTMUT = 0\n", "    parameter integer CUTMUT = 0,\n    parameter integer CUT_D = 1\n")
w = must(w, """    always @(posedge clk) begin
        cq_v <= q_v; cq_d <= q_d; chw_v <= hw_v; chw_d <= hw_d;
    end
""", """    localparam integer CIW = 1 + 512 + 1 + 291;
    wire [CIW-1:0] cut_in_x = {q_v, q_d, hw_v, hw_d};
    wire [CIW-1:0] cut_in_s;
    // plain flop vectors per stage (no array: nothing a memory pass could collect); CUT_D = 1 elaborates no stage
    wire [CUT_D*CIW-1:0] cut_in_c;
    assign cut_in_c[CIW-1:0] = cut_in_x;
    genvar cut_gi;
    generate
        for (cut_gi = 1; cut_gi < CUT_D; cut_gi = cut_gi + 1) begin : g_cin
            reg [CIW-1:0] st;
            always @(posedge clk) st <= cut_in_c[(cut_gi-1)*CIW +: CIW];
            assign cut_in_c[cut_gi*CIW +: CIW] = st;
        end
    endgenerate
    assign cut_in_s = cut_in_c[(CUT_D-1)*CIW +: CIW];
    wire         s_q_v, s_hw_v;
    wire [511:0] s_q_d;
    wire [290:0] s_hw_d;
    assign {s_q_v, s_q_d, s_hw_v, s_hw_d} = cut_in_s;
    always @(posedge clk) begin
        cq_v <= s_q_v; cq_d <= s_q_d; chw_v <= s_hw_v; chw_d <= s_hw_d;
    end
""")
i0 = w.index("    %s #(" % IM); i1 = w.index("    // ---- output relays")
inst = re.sub(r"\(a_(\w+)\)", r"(b_\1)", w[i0:i1]); names = [n for n in re.findall(r"\(b_(\w+)\)", inst) if n != "allq"]
d0 = w.index("    wire         a_l_v"); decl = w[d0:i0]
ow = """`ifdef OT_SVC_ALLQ
    localparam integer COW = (H*132+20) + 513 + 4 + 8 + 8 + 3 + 512 + 10 + 2 + 2 + 2 + 32 + 16 + 16 + 16 + 9 + 1;
    wire [COW-1:0] cut_out_x = {b_allq, %s};
    wire [COW-1:0] cut_out_s;
    assign {a_allq, %s} = cut_out_s;
`else
    localparam integer COW = (H*132+20) + 513 + 4 + 8 + 8 + 3 + 512 + 10 + 2 + 2 + 2 + 32 + 16 + 16 + 16 + 9;
    wire [COW-1:0] cut_out_x = {%s};
    wire [COW-1:0] cut_out_s;
    assign {%s} = cut_out_s;
`endif
    wire [CUT_D*COW-1:0] cut_out_c;
    assign cut_out_c[COW-1:0] = cut_out_x;
    generate
        for (cut_gi = 1; cut_gi < CUT_D; cut_gi = cut_gi + 1) begin : g_cout
            reg [COW-1:0] st;
            always @(posedge clk) st <= cut_out_c[(cut_gi-1)*COW +: COW];
            assign cut_out_c[cut_gi*COW +: COW] = st;
        end
    endgenerate
    assign cut_out_s = cut_out_c[(CUT_D-1)*COW +: COW];
""" % ((", ".join("b_" + n for n in names), ", ".join("a_" + n for n in names)) * 2)
w = w[:d0] + decl + decl.replace(" a_", " b_") + inst + ow + w[i1:]
# ---------------------------------------------------------------- rs_c
if a.main:
    os.makedirs(a.out, exist_ok=True); open(os.path.join(a.out, WF), "w").write(w); print("CUTDEPTH wrapper patched (main form) ->", a.out); sys.exit(0)
r = open(os.path.join(a.src, RF)).read()
if "u_cutr_i" in r: sys.exit("rs_c already patched")
r = must(r, "        .q_v(cs[0]), .q_d(cs[512:1]), .hw_v(cs[513]), .hw_d(cs[DW-1:514]),\n        .qrq(qrq)",
         "        .q_v(cut_cs[0]), .q_d(cut_cs[512:1]), .hw_v(cut_cs[513]), .hw_d(cut_cs[DW-1:514]),\n        .qrq(qrq)")
outs = [("l_v", "l_v", 1), ("l_d", "l_d", "LW"), ("pv_ov", "a_pv_v", 1), ("pv_od", "a_pv_d", 513), ("sm_st", "sm_st", 1), ("sm_kind", "sm_kind", 4),
        ("sm_jid", "sm_jid", 8), ("sm_rv", "sm_rv", 1), ("sm_rp", "sm_rp", 1), ("sm_rj", "sm_rj", 3), ("sm_rd", "sm_rd", 512), ("go_o", "go", 1),
        ("tjob_o", "tjob", 10), ("done", "done", 1), ("tagj", "tagj", 8), ("hcr", "hcr", 2), ("hack", "hack", 2), ("fault", "a_f", 1),
        ("fault_code", "a_fc", 32), ("pio_o", "pio", 16), ("pvo_o", "pvo_j", 16), ("jc_o", "jcs", 16), ("st_o", "a_st", 2), ("hb_o", "a_hb", 1)]
b0 = r.index("`ifdef OT_SVC_ATTCUT\n    dsdv_svc_att_cut\n"); b1 = r.index("    // ------------------------------------------------------------------ score exchange", b0)
blk_inst = r[b0:b1]                              # the u_att instance only: other instances use the same port names
for port, sig, wd in outs + [("allq_o", "a_allq", 1)]:
    old = ".%s(%s)" % (port, sig); n = blk_inst.count(old)
    exp = 2 if port in ("pio_o", "pvo_o", "jc_o", "st_o", "hb_o") else 1
    if n != exp: sys.exit("ANCHOR %s x%d (want %d)" % (old, n, exp))
    blk_inst = blk_inst.replace(old, ".%s(cx_%s)" % (port, sig))
r = r[:b0] + blk_inst + r[b1:]
decl = "".join("    wire %scx_%s;\n" % ("" if wd == 1 else "[%s-1:0] " % wd, sig) for _, sig, wd in outs)
cat_x = ", ".join("cx_" + sig for _, sig, _ in outs); cat_o = ", ".join(sig for _, sig, _ in outs)
blk = """    // SVC-CUT-DEPTH (FABLE-UNC-S81-SVC 11-23): uniform extra depth on the attention cut, same count on every registered lane
    // of a direction.  `OT_SVC_CUT_KA stages on the att side (inside u_att, parameter CUT_D), `OT_SVC_CUT_KR plain relay stages
    // on the REST side of the seam, here: in-lanes after the cs capture, out-lanes after u_att.  Undefined = 0 = as built.
`ifdef OT_SVC_CUT_KA
    localparam integer CUT_KA = `OT_SVC_CUT_KA;
`else
    localparam integer CUT_KA = 0;
`endif
`ifdef OT_SVC_CUT_KR
    localparam integer CUT_KR = `OT_SVC_CUT_KR;
`else
    localparam integer CUT_KR = 0;
`endif
%s`ifdef OT_SVC_ALLQ
    wire cx_a_allq;
    localparam integer CUT_OW = LW + 1154;
    wire [CUT_OW-1:0] cut_ox = {cx_a_allq, %s};
    wire [CUT_OW-1:0] cut_os;
    assign {a_allq, %s} = cut_os;
`else
    localparam integer CUT_OW = LW + 1153;
    wire [CUT_OW-1:0] cut_ox = {%s};
    wire [CUT_OW-1:0] cut_os;
    assign {%s} = cut_os;
`endif
    wire [DW-1:0] cut_cs;
    // plain flop vectors per stage (no array: nothing a memory pass could collect); CUT_KR = 0 elaborates no stage
    wire [(CUT_KR+1)*DW-1:0] cutr_ic;
    wire [(CUT_KR+1)*CUT_OW-1:0] cutr_oc;
    assign cutr_ic[DW-1:0] = cs; assign cutr_oc[CUT_OW-1:0] = cut_ox;
    genvar cut_gk;
    generate
        for (cut_gk = 1; cut_gk <= CUT_KR; cut_gk = cut_gk + 1) begin : g_cutr
            reg [DW-1:0] u_cutr_i;
            reg [CUT_OW-1:0] u_cutr_o;
            always @(posedge ck) begin u_cutr_i <= cutr_ic[(cut_gk-1)*DW +: DW]; u_cutr_o <= cutr_oc[(cut_gk-1)*CUT_OW +: CUT_OW]; end
            assign cutr_ic[cut_gk*DW +: DW] = u_cutr_i; assign cutr_oc[cut_gk*CUT_OW +: CUT_OW] = u_cutr_o;
        end
    endgenerate
    assign cut_cs = cutr_ic[CUT_KR*DW +: DW]; assign cut_os = cutr_oc[CUT_KR*CUT_OW +: CUT_OW];
""" % (decl, cat_x, cat_o, cat_x, cat_o)
anchor = "`ifdef OT_SVC_ATTCUT\n    dsdv_svc_att_cut\n"
r = must(r, anchor, blk + anchor)
r = must(r, ".PV_IDENTITY(PV_IDENTITY), .H(H)) u_att (", ".PV_IDENTITY(PV_IDENTITY), .H(H)\n`ifdef OT_SVC_ATTCUT\n                   , .CUT_D(1 + CUT_KA)\n`endif\n                   ) u_att (")
head = "".join("`define OT_SVC_CUT_%s %d\n" % (k, v) for k, v in (("KA", a.ka), ("KR", a.kr)) if v)
tail = "".join("`undef OT_SVC_CUT_%s\n" % k for k, v in (("KA", a.ka), ("KR", a.kr)) if v)
if head:
    r = must(r, "`define OT_SVC_ATTCUT\n", "`define OT_SVC_ATTCUT\n" + head); r = must(r, "`undef OT_SVC_ATTCUT\n", "`undef OT_SVC_ATTCUT\n" + tail) if r.count("`undef OT_SVC_ATTCUT\n") == 1 else r
os.makedirs(a.out, exist_ok=True)
open(os.path.join(a.out, WF), "w").write(w); open(os.path.join(a.out, RF), "w").write(r)
print("CUTDEPTH patched KA=%d KR=%d ->" % (a.ka, a.kr), a.out)
