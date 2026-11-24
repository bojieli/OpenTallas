"""SERDES-DCHN-KLOCK-J9 (S81-MISC-SERDES-J9 11-23): opt-in negedge lockup on the k_* landing outputs at the hard u_chn face
of ot_s81_kp4_dec_native_flat_lp.

Cause (serdes__t2 post-hook CTS, TT): u_lpl_2_r.g_ck[11].u_local/o[1] -> u_chn k_lo[265] hold -102.13 ps; the hard
ot_s81_kp4_dchn (DCHN_FACE input register inside the macro) carries a 170.8 ps ETM hold on its k_* pins.
Form: under OT_S81_DCHN_KLOCK the four landing outputs (k_v 4, k_lo 310, k_L 5, k_any 1) are re-sampled on the FALLING
edge of ck_chn; u_chn still captures them on the next RISING edge, so every k_* word reaches the macro in the same
cycle (FIXEDCYC 0) with half a period of hold margin.  Undefined = the original netlist (every `else branch is the
original assign, byte for byte).  KLOCK_MUT_POS (bench only): posedge re-sample, +1 cycle on k_* only -> the two-die
link bench (tools/s81_link/run_serdes_col_bench.sh col) must FAIL.

Applied by tools/landed_parent/lp.py gen() as a post-pass for top_lp ot_s81_kp4_dec_native_flat_lp (same pattern as
s81_rck_am.add_face3_option), and idempotent, so a regen reproduces the tree file."""
import re
import sys

FLAG = "OT_S81_DCHN_KLOCK"
SIGS = (("k_v__l_chn", "lpl_1_o", 4), ("k_lo__l_chn", "lpl_2_o", 310), ("k_L__l_chn", "lpl_3_o", 5),
        ("k_any__l_chn", "lpl_4_o", 1))


def _block(dst, src, w):
    r = f"{dst}__lk"
    dec = f"reg [{w - 1}:0] {r}" if w > 1 else f"reg {r}"
    return (f"`ifdef {FLAG}\n    (* keep *) {dec};\n"
            f"`ifdef KLOCK_MUT_POS\n    always @(posedge ck_chn) {r} <= {src};\n`else\n"
            f"    always @(negedge ck_chn) {r} <= {src};   // lockup: same cycle at the u_chn rising edge\n`endif\n"
            f"    assign {dst} = {r};\n`else\n    assign {dst} = {src};\n`endif\n")


def add_klock_option(rtl):
    """Insert the define-gated lockup; a text that already carries every block is returned unchanged."""
    if all(_block(*s) in rtl for s in SIGS):
        return rtl
    if FLAG in rtl:
        raise ValueError("KLOCK option present but incomplete or edited; review the cut")
    for dst, src, w in SIGS:
        old = f"    assign {dst} = {src};\n"
        if rtl.count(old) != 1:
            raise ValueError(f"KLOCK: landing output template changed for {dst}; review the cut")
        rtl = rtl.replace(old, _block(dst, src, w))
    return rtl


def strip_klock_option(rtl):
    """Inverse of add_klock_option (the define-off text)."""
    for dst, src, w in SIGS:
        b = _block(dst, src, w)
        if rtl.count(b) != 1:
            raise ValueError(f"KLOCK block for {dst} missing or edited")
        rtl = rtl.replace(b, f"    assign {dst} = {src};\n")
    if FLAG in rtl:
        raise ValueError("stray KLOCK text")
    return rtl


if __name__ == "__main__":
    s = open(sys.argv[1]).read()
    open(sys.argv[2], "w").write(add_klock_option(s))
