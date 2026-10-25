#!/usr/bin/env python3
"""PATH-KV-ASTK4 10-25: ASTK master successor structure after the z3/CTS1 STRUCTURAL FAIL (PATH-KV-ASTK3 14:48;
PATH-KV lead decision 14:19).  Kit-copy RTL transform, applied after astk_timing_regs + astk_write_decode.

Failing-path classification of CTS1 (codex/kv-astk2-1309@8cfc8520b1, diag STA with native TC/BC libs):
  * zn_0 (chain head): zi lands on core PIN flops (zq), so the head had no read-address replicas: zq[6:2] drives the
        16 x 128-b sd read select + oa/ob muxes directly (leaf fan-out up to 2073 loads off pin flops).
  * ctl: TT -44.68 / 19 EP = start (aq_q[0] pin flop, 116 ps CLK->Q under load) -> ~250 ps buffer tree -> sa_n / zst_n
        start-mux -> 16-b subtract -> /Z_STRIDE -> 17 zk_r copies (g_zk[*].u_zk).
Fix (industry practice):
  * zn_0: +1 cycle on the zi pin path (lead decision 14:19, NOT duplicated plan pins): zi lands on a plain pin landing
        register zp (one load per pin), zq <= zp, and 16 kept per-slice read-address replicas u_rc (qkd_astk_rep5) capture
        zp[6:2] on the same edge as zq, exactly like zn_1..3 (astk_timing_regs).  zp carries no reset (pure pipeline
        stage; zq[0] keeps its reset), so  new zn_0 == old zn_0 with a plain 1-cycle register on zi  (exact, incl. reset
        release).  KV-TOK: the ASTK zi input (u_strip_u_strip_g_zn_0_u_zn__zi) is 1 cycle later -> reprice.
  * ctl: 0 cycles, start becomes the LAST select instead of the first operand: the zk / l_slot / z_slot next states are
        computed for start=1 (from cal_q only) and start=0 (from the schedule state) and each of the 17 zk copies is one
        kept qkd_astk_zksel instance (4 FF + 4 mux2 on start), so start drives 17 x 4 mux selects and no arithmetic.
        (A registered start copy per slice at 0 cycles would need 17 extra loads on the aq[0] PIN; +1 cycle would move
        start against cal/T: not taken.)
`mut` (tb only): zn_0 replica 0 read address xor 1 / zksel copy 0 swaps its select.
"""
import json
import re
import sys
from pathlib import Path

import astk_timing_regs

ZKSEL_MOD = """
// PATH-KV-ASTK4 10-25: zk_r copy with start as the last-stage select (same next state as rep4 on 4'(z_age_rn / Z_STRIDE))
(* keep_hierarchy *) module qkd_astk_zksel (input wire ck, input wire s, input wire [3:0] a, input wire [3:0] b,
        output reg [3:0] q);
    always @(posedge ck) q <= s ? a : b;
endmodule
"""


def _mod(text, name):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    return i, j, text[i:j]


def zn_head(text, mut=False):
    name = "qkd_astk_zn_head_p"
    i, j, s = _mod(text, name)
    assert "g_rd" not in s, "head already has read replicas"
    subs = [
        ("    (* keep *) reg [137:0] zq;\n",
         "    (* keep *) reg [137:0] zq;\n"
         "    // PATH-KV-ASTK4 10-25: zi pin landing stage (+1 cycle on zi; no reset: pure pipeline, zq[0] keeps its reset)\n"
         "    (* keep *) reg [137:0] zp;\n"
         "    always @(posedge ck) zp <= zi;\n"),
        ("zq[137:1] <= zi[137:1];", "zq[137:1] <= zp[137:1];"),
        ("zq[0] <= zi[0];", "zq[0] <= zp[0];"),
    ]
    for a, b in subs:
        assert s.count(a) == 1, (name, a)
        s = s.replace(a, b)
    code = re.sub(r"//.*", "", s)
    assert len(re.findall(r"\bzi\b", code)) == 2, "zi must only feed the port decl + zp"   # decl + zp <= zi
    s = astk_timing_regs.zn(s, name, mut=mut, split=True)
    old = "u_rc (.ck(ck), .d(zi[6:2]), .q(rc));"
    assert s.count(old) == 1
    s = s.replace(old, "u_rc (.ck(ck), .d(zp[6:2]), .q(rc));   // same edge as zq <= zp")
    return text[:i] + s + text[j:]


def ctl(text, mut=False):
    name = "qkd_astk_ctl_s"
    i, j, s = _mod(text, name)
    old_slots = re.search(r"            l_slot_r <= sa_act_n && sa_n >= lmax_n - 16'd1 && sa_n < lmax_n \+ (16'd\d);\n"
                          r"            z_slot_r <= sa_act_n && sa_n >= zst_n - 16'd1 && \(z_age_n / Z_STRIDE < nblk_c\) && "
                          r"\(z_age_n % Z_STRIDE < 4\);\n", s)
    assert old_slots, "l_slot_r/z_slot_r next state not found"
    lm = old_slots.group(1)
    s = s.replace(old_slots.group(0),
                  "            l_slot_r <= start ? l_slot_s1 : l_slot_s0;   // PATH-KV-ASTK4: start = last select\n"
                  "            z_slot_r <= start ? z_slot_s1 : z_slot_s0;\n")
    anchor = "    wire [15:0] z_age_rn = (rn_q ? sa_n : 16'd0) - (zst_n - 16'd1);\n"
    assert s.count(anchor) == 1
    pre = (
        "    // PATH-KV-ASTK4 10-25: next states precomputed for start=1 (cal_q only) and start=0 (schedule state); start\n"
        "    // is the last-stage select (CTS1 TT -44.68: start -> sa_n/zst_n mux -> subtract -> /Z_STRIDE -> 17 zk copies).\n"
        "    wire [15:0] sa_n0 = (schedule_active && schedule_age != 16'hffff) ? schedule_age + 16'd1 : schedule_age;\n"
        "    wire [15:0] z_age_s1 = 16'd0 - (cal_q[31:16] - 16'd1);\n"
        "    wire [15:0] z_age_s0 = sa_n0 - (cal_r[31:16] - 16'd1);\n"
        "    wire [15:0] z_age_rs0 = (rn_q ? sa_n0 : 16'd0) - (cal_r[31:16] - 16'd1);\n"
        f"    wire        l_slot_s1 = 16'd0 >= cal_q[15:0] - 16'd1 && 16'd0 < cal_q[15:0] + {lm};\n"
        f"    wire        l_slot_s0 = schedule_active && sa_n0 >= cal_r[15:0] - 16'd1 && sa_n0 < cal_r[15:0] + {lm};\n"
        "    wire        z_slot_s1 = 16'd0 >= cal_q[31:16] - 16'd1 && (z_age_s1 / Z_STRIDE < nblk_c) && (z_age_s1 % Z_STRIDE < 4);\n"
        "    wire        z_slot_s0 = schedule_active && sa_n0 >= cal_r[31:16] - 16'd1 && (z_age_s0 / Z_STRIDE < nblk_c) && "
        "(z_age_s0 % Z_STRIDE < 4);\n"
        "    wire [3:0]  zk_s1 = 4'(z_age_s1 / Z_STRIDE);\n"
        "    wire [3:0]  zk_s0 = 4'(z_age_rs0 / Z_STRIDE);\n")
    s = s.replace(anchor, anchor + pre)
    old_zk = "        (* keep *) qkd_astk_rep4 u_zk (.ck(ck), .d(4'(z_age_rn / Z_STRIDE)), .q(zk_r));\n"
    assert s.count(old_zk) == 1
    sel = "start ^ (zg == 0)" if mut else "start"
    s = s.replace(old_zk, f"        (* keep *) qkd_astk_zksel u_zk (.ck(ck), .s({sel}), .a(zk_s1), .b(zk_s0), .q(zk_r));\n")
    return text[:i] + s + text[j:]


def expect(spec):
    """Replica-count spec for the successor: zn_0 read-address replicas 0,0..0,15 + zk copies are qkd_astk_zksel."""
    spec = json.loads(json.dumps(spec))
    seen = set()
    for r in spec["rules"]:
        if r["name"] == "zn_read_addr_replicas":
            r["groups"] = [f"0,{k}" for k in range(16)] + [g for g in r["groups"] if not g.startswith("0,")]
            seen.add(r["name"])
        if r["name"] == "ctl_zk_copies":
            r["module"] = "qkd_astk_zksel"
            seen.add(r["name"])
    assert seen == {"zn_read_addr_replicas", "ctl_zk_copies"}, seen
    spec["note"] += "; PATH-KV-ASTK4 10-25: zn_0 head read-address replicas (zp landing stage, +1 cycle on zi) + zk copies " \
                    "as qkd_astk_zksel (start last select)"
    return spec


def apply_kit(rtl_dir, mut=False):
    d = Path(rtl_dir)
    p = d / "qkd_astk_zn_head_p.sv"
    p.write_text(zn_head(p.read_text(), mut))
    p = d / "qkd_astk_static_leaves.sv"
    p.write_text(ctl(p.read_text(), mut) + ZKSEL_MOD)


if __name__ == "__main__":
    apply_kit(sys.argv[1], "mut" in sys.argv[2:])
