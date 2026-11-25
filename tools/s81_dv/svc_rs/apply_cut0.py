#!/usr/bin/env python3
"""SVC-CUT0-RSV09 (S81-SVC-J9 11-24, COORD + S81-ALLFIX-INT row): cut depth 0 on the hi svc attention cut, so the hi-row slices
(every user of dsdv_svc_rs_c_j7_hi4: the six hi tree variants of dsdv_svc_rs_fv_j8_hi.sv incl. fv_a44aa42442 = u_rsv_09, and both
dsdv_svc_rs_pvso_entry_j8_hi entries) run in step with the lo-row slices (plain dsdv_svc_rs_c, no cut).
  dsdv_svc_att_cut[_j7_hi4].sv  CUT_D = 0: no stage at all, the capture and output registers become wires (pass-through); the
                                instance u_att and its child u_a stay, so the plan part prefix ...u_att / ...u_att.u_a is kept.
                                CUT_D >= 1 elaborates as before (same flops, same names).
  dsdv_svc_rs_c_j7_hi4.sv       `define OT_SVC_CUT0 next to `define OT_SVC_ATTCUT: u_att gets .CUT_D(0); KA / KR must be 0.
Input = a hi4 source dir in the as-built form or in the SVC-CUT-DEPTH form (apply_cutdepth.py); the as-built form is first
taken through apply_cutdepth.py --ka 0 --kr 0 (proven inert, lanes/handoff/S81-SVC-J9-CUTDEPTH-row.txt).
usage: apply_cut0.py SRC_DIR OUT_DIR | --main SRC_DIR OUT_DIR (main wrapper rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv only)"""
import argparse, os, subprocess, sys, tempfile


class Anchor(Exception):
    pass


def must(s, old, new, n=1):
    if s.count(old) != n:
        raise Anchor("ANCHOR missing or repeated (%d): %r" % (s.count(old), old[:80]))
    return s.replace(old, new)


CAP = """    always @(posedge clk) begin
        cq_v <= s_q_v; cq_d <= s_q_d; chw_v <= s_hw_v; chw_d <= s_hw_d;
    end
"""
CAP_NEW = """    generate if (CUT_D == 0) begin : g_cap0
        always @* begin
            cq_v = s_q_v; cq_d = s_q_d; chw_v = s_hw_v; chw_d = s_hw_d;
        end
    end else begin : g_cap
        always @(posedge clk) begin
            cq_v <= s_q_v; cq_d <= s_q_d; chw_v <= s_hw_v; chw_d <= s_hw_d;
        end
    end endgenerate
"""


def _ind(s):
    return "".join(("    " + l if l.strip() and not l.startswith("`") else l) for l in s.splitlines(True))


def patch_wrapper(w):
    """CUT_D wrapper text -> the same text with the CUT_D 0 pass-through form (CUT_D >= 1 elaborates as before)"""
    if "CUT_D == 0" in w:
        raise Anchor("wrapper already has the CUT_D 0 form")
    w = must(w, "// CUTMUT (bench only", "// CUT_D = 0 (SVC-CUT0-RSV09, S81-SVC-J9 11-24): no register on any lane, u_att = dsdv_svc_att in a pass-through shell (the\n"
             "// hi row then runs in step with the plain-core lo row); CUTMUT has no effect at CUT_D 0.\n// CUTMUT (bench only")
    w = must(w, "    localparam integer CIW = 1 + 512 + 1 + 291;\n",
             "    localparam integer CIW = 1 + 512 + 1 + 291;\n    localparam integer CDV = (CUT_D < 1) ? 1 : CUT_D;   // vector depth (CUT_D 0 uses the stage-0 slice only)\n")
    w = must(w, "    wire [CUT_D*CIW-1:0] cut_in_c;", "    wire [CDV*CIW-1:0] cut_in_c;")
    w = must(w, "    assign cut_in_s = cut_in_c[(CUT_D-1)*CIW +: CIW];", "    assign cut_in_s = cut_in_c[(CDV-1)*CIW +: CIW];")
    w = must(w, "    wire [CUT_D*COW-1:0] cut_out_c;", "    wire [CDV*COW-1:0] cut_out_c;")
    w = must(w, "    assign cut_out_s = cut_out_c[(CUT_D-1)*COW +: COW];", "    assign cut_out_s = cut_out_c[(CDV-1)*COW +: COW];")
    w = must(w, CAP, CAP_NEW)
    key = "    always @(posedge clk) begin\n        l_v <= a_l_v;"
    if w.count(key) != 1:
        raise Anchor("ANCHOR missing or repeated (%d): output relay block" % w.count(key))
    i0 = w.index(key); i1 = w.index("endmodule", i0)
    blk = w[i0:i1]
    comb = blk.replace("always @(posedge clk) begin", "always @* begin").replace(" <= ", " = ")
    return w[:i0] + "    generate if (CUT_D == 0) begin : g_out0\n" + _ind(comb) + "    end else begin : g_out\n" + _ind(blk) + "    end endgenerate\n" + w[i1:]


def patch_core(r):
    """dsdv_svc_rs_c_j7_hi4 text (SVC-CUT-DEPTH form) -> OT_SVC_CUT0 defined: u_att .CUT_D(0)"""
    pre = r.split("module", 1)[0]
    if "OT_SVC_CUT_KA " in pre or "OT_SVC_CUT_KR " in pre:
        raise Anchor("rs_c carries KA / KR defines: CUT0 needs KA = KR = 0")
    if "OT_SVC_CUT0" in r:
        raise Anchor("rs_c already has OT_SVC_CUT0")
    r = must(r, "`define OT_SVC_ATTCUT\n", "`define OT_SVC_ATTCUT\n`define OT_SVC_CUT0   // SVC-CUT0-RSV09 (S81-SVC-J9 11-24): cut depth 0 on every user of this core (hi row)\n")
    r = must(r, "`undef OT_SVC_ATTCUT\n", "`undef OT_SVC_ATTCUT\n`undef OT_SVC_CUT0\n")
    r = must(r, "`ifdef OT_SVC_ATTCUT\n                   , .CUT_D(1 + CUT_KA)\n`endif\n",
             "`ifdef OT_SVC_ATTCUT\n`ifdef OT_SVC_CUT0\n                   , .CUT_D(0)\n`else\n                   , .CUT_D(1 + CUT_KA)\n`endif\n`endif\n")
    return r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--main", action="store_true")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    wf, rf = ("dsdv_svc_att_cut.sv", None) if a.main else ("dsdv_svc_att_cut_j7_hi4.sv", "dsdv_svc_rs_c_j7_hi4.sv")
    src = a.src
    if "CUT_D" not in open(os.path.join(src, wf)).read():
        tmp = tempfile.mkdtemp(prefix="cut0_")
        cmd = [sys.executable, "-I", os.path.join(here, "apply_cutdepth.py"), src, tmp] + (["--main"] if a.main else [])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL); src = tmp
    try:
        w = patch_wrapper(open(os.path.join(src, wf)).read())
        r = None if a.main else patch_core(open(os.path.join(src, rf)).read())
    except Anchor as e:
        sys.exit(str(e))
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, wf), "w").write(w)
    if r is not None:
        open(os.path.join(a.out, rf), "w").write(r)
    print("CUT0 %s ->" % ("wrapper form (main)" if a.main else "patched"), a.out)


if __name__ == "__main__":
    main()
