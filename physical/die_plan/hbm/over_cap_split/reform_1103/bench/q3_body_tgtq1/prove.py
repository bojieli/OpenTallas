#!/usr/bin/env python3
"""HBM-GAPS-5-BODYCTL proof of the OT_Q3CTL_TGTQ1 form of ot_hfd_coll_q3_body_ctl (target_q register).
Usage: prove.py <patched ctl.sv> <old ctl.sv (main 33ff3f432d)> <workdir> <yosys>
 1. text: the patched file without its `ifdef OT_Q3CTL_TGTQ1 ... `else and `endif lines is byte-identical to the old file,
    so with the define off nothing changes and with it on only this block differs.
 2. formal (yosys sat, bounded): old block (8 no-reset flops of hit ? 8'h34 : 0) vs new block (1 flop of hit, constant
    bits as wires): target_q equal on every cycle after the first edge, any hit sequence.  Both are a 1-deep feed-forward
    register of one input, so the state after one edge is a function of the last input and depth 8 is complete.
 3. mutants of the new block must FAIL the same proof."""
import hashlib, os, re, subprocess, sys
pat, old, wd, ys = sys.argv[1:5]
os.makedirs(wd, exist_ok=True)
S = open(pat).read().split("\n")
a = S.index("`ifdef OT_Q3CTL_TGTQ1"); e = S.index("`else", a); z = S.index("`endif", e)
recon = "\n".join(S[:a] + S[e + 1:z] + S[z + 1:])
ho, hr = hashlib.sha256(open(old, "rb").read()).hexdigest(), hashlib.sha256(recon.encode()).hexdigest()
print("TEXT old sha256", ho, "patched-minus-ifdef sha256", hr, "IDENTICAL" if ho == hr else "DIFFERENT")
ok = ho == hr
newb, oldb = S[a + 1:e], S[e + 1:z]
def clean(lines):
    t = "\n".join(lines)
    t = re.sub(r"\\u_body\.g_q3\.n_u_fj\.u_fj\.u\.u_program\.target_q\[(\d)\] ", r"tq[\1]", t)
    t = re.sub(r"\\u_body\.g_q3\.n_u_fj\.u_fj\.u\.target_eff\[(\d)\] ", r"te[\1]", t)
    return t
OLD = ("module blk_gold(input clk_program, input _018274_, output [7:0] tq);\n  wire [7:0] te;\n"
       "  assign { te[7] , te[6] , te[5] , te[4] , te[3] , te[2] , te[1] , te[0] } = _018274_ ? 8'h34 : 8'h00;\n"
       + clean(oldb) + "\nendmodule\n")
NEWT = "module blk_gate(input clk_program, input _018274_, output [7:0] tq);\n" + clean(newb) + "\nendmodule\n"
MUT = {
 "M1_bit2_tied0": ("q3ctl_tgt_hit_q, 1'b0, q3ctl_tgt_hit_q, 2'b00 }", "q3ctl_tgt_hit_q, 1'b0, 1'b0, 2'b00 }"),
 "M2_no_register": ("q3ctl_tgt_hit_q <= _018274_;", "q3ctl_tgt_hit_q <= q3ctl_tgt_hit_q;\n  wire unused_m2 = 1'b0;"),
 "M3_bit0_not_const": ("q3ctl_tgt_hit_q, 2'b00 }", "q3ctl_tgt_hit_q, 1'b0, q3ctl_tgt_hit_q }"),
 "M4_bit3_for_bit2": ("q3ctl_tgt_hit_q, 1'b0, q3ctl_tgt_hit_q, 2'b00 }", "q3ctl_tgt_hit_q, q3ctl_tgt_hit_q, 1'b0, 2'b00 }"),
}
def run(name, gate):
    open(f"{wd}/{name}.v", "w").write(OLD + gate)
    scr = (f"read_verilog {wd}/{name}.v; proc; opt_clean; miter -equiv -flatten -make_outputs blk_gold blk_gate miter; "
           f"hierarchy -top miter; flatten; opt; sat -verify -seq 8 -prove-skip 1 -set-init-undef -prove trigger 0 -show-inputs miter")
    r = subprocess.run([ys, "-q", "-p", scr], capture_output=True, text=True)
    open(f"{wd}/{name}.log", "w").write(r.stdout + r.stderr)
    return r.returncode == 0
p = run("M0_new_form", NEWT)
print("FORMAL M0 new form vs old:", "PASS" if p else "FAIL"); ok &= p
for k, (x, y) in MUT.items():
    assert x in NEWT, k
    q = run(k, NEWT.replace(x, y, 1))
    print(f"MUTANT {k}:", "caught (proof FAILS)" if not q else "NOT CAUGHT"); ok &= not q
print("RESULT", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
