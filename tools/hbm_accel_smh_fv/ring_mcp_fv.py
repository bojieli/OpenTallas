#!/usr/bin/env python3
"""Formal proof that fc_bc's ring multicycle (bulk_copy_mc2.sdc: -setup 2 / -hold 1 -from *u_ring) is design
intent, not masking.  ot_hbm_accel_bulk_copy_oq5 RING_MACRO=1 as instantiated in fc_bc / front_c
(LINE_BITS 1088, DEPTH 1024, SRAM_RING 1).  A checker is spliced into a SCRATCH copy of the RTL (the source file
is not touched); macros are stubbed (data is not in the property's cone).  Proved by k-induction:
  P1  a ring group (each macro) is never read on two consecutive edges -> rd_out launched at E holds until E+2;
  P2  every output-queue capture (we0..3[d]) of a domain whose select is group g = par2[d] happens exactly two
      edges after g's read and with no read of g on the edge between (capture only on the second edge).
Mutants (must FAIL): mcp1 = capture one edge after the read (we from the take, select par1);
                     ce2  = group parity dropped from r_ce (a group read on consecutive edges).
"""
import os, re, subprocess, sys, tempfile, json
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OQ5 = os.path.join(ROOT, "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv")
BC = os.path.join(ROOT, "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv")
DEPTH_K = int(os.environ.get("FV_K", "6"))

CHECK = r"""
        if (1) begin : g_fv
            wire [2*NB-1:0] rce;
            reg  [2*NB-1:0] rce_q1, rce_q2;
            reg fv1, fv2;
            genvar fm, fg;
            for (fm = 0; fm < NB; fm = fm + 1) begin : g_fm
                for (fg = 0; fg < 2; fg = fg + 1) begin : g_fg
                    assign rce[2*fm+fg] = RCE_EXPR;     // = u_ring.r_ce_in
                end
            end
            initial begin fv1 = 0; fv2 = 0; end
            always @(posedge clk) begin rce_q1 <= rce; rce_q2 <= rce_q1; fv1 <= rst_n; fv2 <= fv1 && rst_n; end
            wire [NW-1:0] fsel = SEL;
            for (fm = 0; fm < 2*NB; fm = fm + 1) begin : g_p1
                always @(*) if (fv2 && rst_n) assert(!(rce[fm] && rce_q1[fm]));
            end
            for (fm = 0; fm < NW; fm = fm + 1) begin : g_p2
                always @(*) if (fv2 && rst_n && (we0[fm] | we1[fm] | we2[fm] | we3[fm])) begin
                    assert(rce_q2[2*(fm/4) + fsel[fm]]);
                    assert(!rce_q1[2*(fm/4) + fsel[fm]]);
                end
            end
        end
"""
STUB = """
module ot_sram_1r1w_512x256_m1_r2c2 (input clk, r_ce_in, input [8:0] r_addr_in, output reg [255:0] rd_out,
 input w_ce_in, input [8:0] w_addr_in, input [255:0] wd_in, w_mask_in, input [1:0] rr_en, input [17:0] rr_addr,
 input [1:0] cr_en, input [15:0] cr_sel);
 initial rd_out = 0;
endmodule
module fv_top(input clk, input rst_n, input d_valid, input [31:0] d_base, input [23:0] d_lines, input req_ready,
 input rsp_v, input [9:0] rsp_tag, input s_ready, input [33:0] s_ready_v);
 reg init = 1; always @(posedge clk) init <= 0;
 always @(*) if (init) assume(!rst_n);
 wire d_ready, req_v, s_valid, idle; wire [31:0] req_addr; wire [9:0] req_tag; wire [1087:0] s_data;
 wire [33:0] s_valid_v; wire [9:0] outstanding;
 ot_hbm_accel_bulk_copy_oq5 #(.ENABLE(1), .LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(512), .SRAM_RING(1), .RING_MACRO(1))
  dut (.clk(clk), .rst_n(rst_n), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines),
  .req_v(req_v), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v), .rsp_tag(rsp_tag),
  .rsp_data(1088'd0), .s_valid(s_valid), .s_ready(s_ready), .s_data(s_data), .s_valid_v(s_valid_v),
  .s_ready_v(s_ready_v), .outstanding(outstanding), .idle(idle));
endmodule
"""

def build(mut):
    src = open(OQ5).read()
    rce_rtl = ".r_ce_in(take_c[3+mb] && cslot[0] == gg)"
    assert src.count(rce_rtl) == 1
    sel = "g_m2.par2"
    if mut == "mcp1":      # capture one edge after the read: we from the take copy, select from par1
        for k in range(4):
            a = "u_we%d (.clk(clk), .rst_n(rst_n), .d({4{rdv_s && wpn_s == 2'd%d}})" % (k, k)
            assert src.count(a) == 1
            src = src.replace(a, a.replace("rdv_s &&", "take_c[3+sl] &&"))
        a = "assign qin[64*mb +: 64] = par2[mb] ?"
        assert src.count(a) == 1
        src = src.replace(a, "assign qin[64*mb +: 64] = par1 ?")
        sel = "{NW{g_m2.par1}}"
    if mut == "ce2":       # group parity dropped: both groups read on every take
        src = src.replace(rce_rtl, ".r_ce_in(take_c[3+mb])")
    rce_expr = "take_c[3+fm]" if mut == "ce2" else "take_c[3+fm] && cslot[0] == fg"
    anchor = "        // the stream read select"
    assert src.count(anchor) == 1
    src = src.replace(anchor, CHECK.replace("RCE_EXPR", rce_expr).replace("SEL", sel) + anchor)
    return src

def run(mut, wd):
    os.makedirs(wd, exist_ok=True)
    open(f"{wd}/oq5.sv", "w").write(build(mut))
    open(f"{wd}/top.sv", "w").write(STUB)
    ys = f"""read_verilog -sv -formal {BC}
read_verilog -sv -formal {wd}/oq5.sv
read_verilog -sv -formal {wd}/top.sv
prep -top fv_top
hierarchy -check
flatten
async2sync
dffunmap
opt_clean
write_smt2 -wires {wd}/m.smt2
"""
    open(f"{wd}/m.ys", "w").write(ys)
    r = subprocess.run(["yosys", "-q", "-s", f"{wd}/m.ys"], capture_output=True, text=True)
    if r.returncode:
        return {"mut": mut, "verdict": "YOSYS_ERROR", "log": (r.stdout + r.stderr)[-1500:]}
    out = {}
    for mode, args in (("bmc", ["-t", str(DEPTH_K + 4)]), ("induction", ["-i", "-t", str(DEPTH_K)])):
        r = subprocess.run(["yosys-smtbmc", "-s", os.environ.get("FV_SOLVER", "z3"), *args, f"{wd}/m.smt2"], capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if "Status" in l or "failed" in l.lower()]
        out[mode] = {"rc": r.returncode, "status": tail[-1] if tail else r.stdout[-300:]}
    passed = out["bmc"]["rc"] == 0 and out["induction"]["rc"] == 0
    return {"mut": mut, "verdict": "PROVED" if passed else ("FAIL" if out["bmc"]["rc"] else "INDUCTION_FAIL"), **out}

if __name__ == "__main__":
    wd = tempfile.mkdtemp(prefix="ring_mcp_fv_")
    res = [run(m, f"{wd}/{m}") for m in ("base", "mcp1", "ce2")]
    print(json.dumps(res, indent=1))
    ok = res[0]["verdict"] == "PROVED" and all(r["verdict"] == "FAIL" for r in res[1:])
    print("RING_MCP_FV", "PASS" if ok else "NOT_PROVED")
    if len(sys.argv) > 1:
        json.dump({"ok": ok, "results": res, "k": DEPTH_K}, open(sys.argv[1], "w"), indent=1)
    sys.exit(0 if ok else 1)
