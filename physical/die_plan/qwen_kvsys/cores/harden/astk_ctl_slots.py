#!/usr/bin/env python3
"""PATH-KV-ASTK7 10-25: ASTK ctl schedule-slot registers (kit-copy RTL transform, 0 cycles).  Applied after astk_path4.

ASTK5 native route TT: schedule_age -> 16-b subtract (zst_age - 1) -> == nblk * Z_STRIDE (z_done_slot) -> zd0 -> ap[0]
and the fault flag f (l_slot / z_slot / z_done_slot comparators), zig-zagging across the 181 x 34 um ctl band.
l_slot / z_slot already have registered next-state copies (l_slot_r / z_slot_r, KV-CORES 10-25, equal on every edge);
z_done_slot gets the same treatment: z_done_r <= next-state value of z_done_slot (sa_n / zst_n / nblk_c are the next
values of schedule_age / cal_r[31:16] / nblk), async reset 0 like schedule_active.  zd0 and every f term then read
registers; schedule_age feeds only the next-state compares.  Proof: tb_astk7_ctl lockstep vs the ASTK6 ctl (all
outputs + f + slot regs every edge), mutant (z_done_r one slot late) must mismatch.
Not done (would break the pin contract): duplicating the start landing register -- face_guard requires each input
port bit to load exactly one landing flop; a same-edge copy of start = a second aq[0] landing flop.
`mut` (tb only): z_done_r compares against nblk_c * Z_STRIDE + 1.
"""
import sys
from pathlib import Path


def _mod(text, name):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    return i, j


def ctl(text, mut=False):
    i, j = _mod(text, "qkd_astk_ctl_s")
    s = text[i:j]

    def rep(a, b):
        nonlocal s
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    rep("    (* keep *) reg l_slot_r, z_slot_r;\n", "    (* keep *) reg l_slot_r, z_slot_r, z_done_r;\n")
    rep("        if (!rn_q) begin l_slot_r <= 1'b0; z_slot_r <= 1'b0; end\n",
        "        if (!rn_q) begin l_slot_r <= 1'b0; z_slot_r <= 1'b0; z_done_r <= 1'b0; end\n")
    off = " + 1" if mut else ""
    rep("            z_slot_r <= sa_act_n && sa_n >= zst_n - 16'd1 && (z_age_n / Z_STRIDE < nblk_c) && (z_age_n % Z_STRIDE < 4);\n",
        "            z_slot_r <= sa_act_n && sa_n >= zst_n - 16'd1 && (z_age_n / Z_STRIDE < nblk_c) && (z_age_n % Z_STRIDE < 4);\n"
        "            // PATH-KV-ASTK7 10-25: next-state z_done_slot (0 cycles)\n"
        f"            z_done_r <= sa_act_n && sa_n >= zst_n - 16'd1 && z_age_n == nblk_c * Z_STRIDE{off};\n")
    rep("    wire zd0 = STATIC_SCHEDULE ? z_done_slot : legacy_zd0;\n", "    wire zd0 = STATIC_SCHEDULE ? z_done_r : legacy_zd0;\n")
    rep("((l_slot && !kdone[0]) || (z_slot && !z_have) ||", "((l_slot_r && !kdone[0]) || (z_slot_r && !z_have) ||")
    rep("(z_slot && (z_hd[0] ||", "(z_slot_r && (z_hd[0] ||")
    rep("(z_done_slot && (!qgo[0]", "(z_done_r && (!qgo[0]")
    return text[:i] + s + text[j:]


def apply_kit(rtl_dir, mut=False):
    p = Path(rtl_dir) / "qkd_astk_static_leaves.sv"
    p.write_text(ctl(p.read_text(), mut))


if __name__ == "__main__":
    apply_kit(sys.argv[1], "mut" in sys.argv[2:])
