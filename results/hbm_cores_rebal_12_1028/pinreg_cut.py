#!/usr/bin/env python3
"""HBM-CORES-REBAL-12 (2026-10-28): pin-registered valid stations in hnx_lane_x (lane-cut file post-transform).

Post-synth face_guard of the C24 hnx_lane_x kit FAILED 6 bits (CHECKED, REBAL-11 run 19:10):
  * shared 4: r_bdc / r_tcc / r_g / r_x are the lane's sync reset taps (parent reset relay rr[1..4 + 4p]); they fan out
    into u_bdc / u_tcc / gather / station regs.  They are reset pins, declared as such in the kit (mk_hnx.py RST_RE),
    and face_guard_core exempts declared reset pins like every other core reset.
  * unregistered 2: iv_b / sv_f -> AND2(r_x) -> xb_v / xf_v D.  Under OT_SMH_RP4_SRST the station valid is
    `xb_v <= r_x ? iv_b : 0`, so the sync-reset gate sits between the pin and the flop.
Fix (this transform, sync-reset form only): the gate moves behind the registers,
    xb_vr <= iv_b; xf_vr <= sv_f; x_rq <= r_x;  xb_v = x_rq & xb_vr;  xf_v = x_rq & xf_vr
so iv_b / sv_f / r_x each land on one flop D.  xb_v(t) = r_x(t-1) & iv_b(t-1) in both forms (1-cycle retime of an
AND across 3 flops; reset clears it the cycle after r_x falls, as before).  The async form (no OT_SMH_RP4_SRST) keeps
the original statements byte-identical inside `else.  No port, cycle or parent change.
Usage: pinreg_cut.py IN_CUT OUT_CUT
"""
import sys

OLD_DECL = "    reg xb_v, xf_v, xb_first, xb_last, xb_fp4, xf_first, xf_last;\n"
OLD_AR = ("    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xb_v <= 0; else xb_v <= iv_b;\n"
          "    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xf_v <= 0; else xf_v <= sv_f;\n")
NEW_DECL = "    reg xb_first, xb_last, xb_fp4, xf_first, xf_last;\n"
NEW_AR = ("`ifdef OT_SMH_RP4_SRST\n"
          "    // HBM-CORES-REBAL-12 pin-registered valid stations (pinreg_cut.py): sync-reset gate behind the flops\n"
          "    reg xb_vr, xf_vr, x_rq;\n"
          "    always @(posedge clk) begin xb_vr <= iv_b; xf_vr <= sv_f; x_rq <= r_x; end\n"
          "    wire xb_v = x_rq & xb_vr, xf_v = x_rq & xf_vr;\n"
          "`else\n"
          "    reg xb_v, xf_v;\n" + OLD_AR + "`endif\n")


def main(src, out):
    t = open(src).read()
    i = t.index("module hnx_lane_x (")
    head, child = t[:i], t[i:]
    for s in (OLD_DECL, OLD_AR):
        assert child.count(s) == 1, s
    child = child.replace(OLD_DECL, NEW_DECL).replace(OLD_AR, NEW_AR)
    assert child.replace(NEW_AR, "").count("r_x") == 1, "r_x must feed only the two station valids (port decl left)"
    open(out, "w").write(head + child)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
